"""Thin FastAPI adapter for deterministic PromoGuard domain services."""

from io import BytesIO
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile, status

from apps.api.contracts import (
    AuditRequest,
    DatasetPathRequest,
    PanelQualityResponse,
    PromotionListRequest,
    PromotionListResponse,
)
from promoguard import __version__
from promoguard.data.panel import load_weekly_panel, validate_canonical_panel
from promoguard.insights.promotion_audit import (
    PromotionAuditResult,
    audit_promotion_event,
    detect_promotion_episodes,
    select_representative_event,
)

MAX_UPLOAD_BYTES = 120 * 1024 * 1024
MAX_PANEL_ROWS = 1_000_000

app = FastAPI(
    title="PromoGuard API",
    version=__version__,
    description="Auditable retail-promotion screening; outputs are observational, not causal.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "promoguard-api", "version": __version__}


def _load_valid_panel(input_path: str) -> pd.DataFrame:
    try:
        panel = load_weekly_panel(input_path)
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    report = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
    if not report["valid"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=report)
    return panel


async def _read_csv_upload(upload: UploadFile) -> pd.DataFrame:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be a CSV file.",
        )
    buffer = BytesIO()
    while chunk := await upload.read(1024 * 1024):
        buffer.write(chunk)
        if buffer.tell() > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Upload exceeds the {MAX_UPLOAD_BYTES}-byte limit.",
            )
    if buffer.tell() == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded CSV is empty.")
    buffer.seek(0)
    try:
        return pd.read_csv(buffer)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded CSV is empty, malformed, or has unsupported encoding.",
        ) from error


@app.post("/v1/panels/validate", response_model=PanelQualityResponse)
def validate_panel_path(request: DatasetPathRequest) -> dict[str, object]:
    panel = _load_valid_panel(request.input_path)
    return validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)


@app.post("/v1/panels/validate-upload", response_model=PanelQualityResponse)
async def validate_panel_upload(
    file: Annotated[UploadFile, File(description="Canonical weekly panel CSV")],
) -> dict[str, object]:
    panel = await _read_csv_upload(file)
    return validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)


@app.post("/v1/promotions", response_model=PromotionListResponse)
def list_promotions(request: PromotionListRequest) -> dict[str, object]:
    panel = _load_valid_panel(request.input_path)
    episodes = detect_promotion_episodes(panel)
    selected = episodes.head(request.limit)
    return {
        "count": len(episodes),
        "returned": len(selected),
        "events": selected.to_dict(orient="records"),
    }


@app.post("/v1/audits", response_model=PromotionAuditResult)
def create_audit(request: AuditRequest) -> PromotionAuditResult:
    panel = _load_valid_panel(request.input_path)
    if request.store_id is None:
        selection = select_representative_event(panel)
    else:
        selection = {
            "store_id": request.store_id,
            "upc": request.upc,
            "start_date": request.start_date,
        }
    try:
        return audit_promotion_event(
            panel,
            store_id=str(selection["store_id"]),
            upc=str(selection["upc"]),
            start_date=selection["start_date"],
            unit_margin=request.unit_margin,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

