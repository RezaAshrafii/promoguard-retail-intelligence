"""Thin FastAPI adapter for deterministic PromoGuard domain services."""

import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from apps.api.contracts import (
    AuditRequest,
    DatasetPathRequest,
    DatasetResponse,
    PanelQualityResponse,
    PromotionListRequest,
    PromotionListResponse,
    ReportCreateRequest,
    ReportResponse,
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATA_ROOT = (REPOSITORY_ROOT / "data").resolve()
RUNTIME_ROOT = (REPOSITORY_ROOT / "tmp" / "product-runtime").resolve()
UPLOAD_ROOT = RUNTIME_ROOT / "datasets"
REPORT_ROOT = RUNTIME_ROOT / "reports"
DATASETS: dict[str, dict[str, object]] = {}
REPORTS: dict[str, dict[str, object]] = {}

app = FastAPI(
    title="PromoGuard API",
    version=__version__,
    description=(
        "Evidence-aware retail promotion screening API. "
        "Outputs are observational and do not by themselves establish causality or profit."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "promoguard-api",
        "version": __version__,
        "deployment_scope": "controlled_environment",
    }


def _load_valid_panel(input_path: str) -> pd.DataFrame:
    resolved_input = Path(input_path).resolve()
    allowed_roots = (LOCAL_DATA_ROOT.resolve(), UPLOAD_ROOT.resolve())
    if not any(
        resolved_input == root or root in resolved_input.parents for root in allowed_roots
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local input must remain under a configured data root or upload dataset root.",
        )
    try:
        panel = load_weekly_panel(resolved_input, max_bytes=MAX_UPLOAD_BYTES)
    except FileNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    report = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
    if not report["valid"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=report)
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


async def _read_upload_bytes(upload: UploadFile) -> bytes:
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="فقط فایل CSV پذیرفته می‌شود.")
    buffer = BytesIO()
    while chunk := await upload.read(1024 * 1024):
        buffer.write(chunk)
        if buffer.tell() > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"حجم فایل نباید از {MAX_UPLOAD_BYTES} بایت بیشتر باشد.",
            )
    if buffer.tell() == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="فایل خالی است.")
    return buffer.getvalue()


def _quality_for_bytes(content: bytes) -> tuple[pd.DataFrame, dict[str, object]]:
    try:
        panel = pd.read_csv(BytesIO(content))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ساختار CSV قابل خواندن نیست.") from error
    return panel, validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)


@app.post("/v1/datasets", response_model=DatasetResponse)
async def create_dataset(file: Annotated[UploadFile, File(description="فایل CSV فروش هفتگی")]) -> dict[str, object]:
    """Store a validated upload behind a stable dataset identifier."""
    content = await _read_upload_bytes(file)
    _panel, quality = _quality_for_bytes(content)
    dataset_id = hashlib.sha256(content).hexdigest()[:24]
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    dataset_path = UPLOAD_ROOT / f"{dataset_id}.csv"
    dataset_path.write_bytes(content)
    record = {
        "dataset_id": dataset_id,
        "filename": file.filename or "dataset.csv",
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "path": str(dataset_path),
        "quality": quality,
        "status": "ready" if quality["valid"] else "rejected",
    }
    DATASETS[dataset_id] = record
    return {key: value for key, value in record.items() if key != "path"}


@app.get("/v1/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str) -> dict[str, object]:
    record = DATASETS.get(dataset_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset پیدا نشد.")
    return {key: value for key, value in record.items() if key != "path"}


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
    try:
        if request.store_id is None:
            selection = select_representative_event(panel)
        else:
            selection = {
                "store_id": request.store_id,
                "upc": request.upc,
                "start_date": request.start_date,
            }
        return audit_promotion_event(
            panel,
            store_id=str(selection["store_id"]),
            upc=str(selection["upc"]),
            start_date=selection["start_date"],
            contribution_assumption=request.contribution_assumption,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


def _dashboard_summary_for_path(input_path: str) -> dict[str, object]:
    """Return one stable, manager-facing payload for the web dashboard.

    The API deliberately keeps the observational boundary visible: this endpoint
    does not turn a promotion comparison into a causal or profit claim.
    """
    panel = _load_valid_panel(input_path)
    quality = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
    try:
        selection = select_representative_event(panel)
        audit = audit_promotion_event(
            panel,
            store_id=str(selection["store_id"]),
            upc=str(selection["upc"]),
            start_date=selection["start_date"],
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error

    prepared = panel.copy()
    prepared["week_end_date"] = pd.to_datetime(prepared["week_end_date"])
    event_start = pd.Timestamp(selection["start_date"])
    event_end = pd.Timestamp(audit.end_date)
    trend = prepared[
        (prepared["store_id"].astype(str) == str(selection["store_id"]))
        & (prepared["upc"].astype(str) == str(selection["upc"]))
        & (prepared["week_end_date"] >= event_start - pd.Timedelta(weeks=8))
        & (prepared["week_end_date"] <= event_end + pd.Timedelta(weeks=8))
    ].sort_values("week_end_date")
    trend_records = [
        {
            "week_end_date": row.week_end_date.date().isoformat(),
            "units": float(row.units),
            "promotion_flag": int(row.promotion_flag),
        }
        for row in trend.itertuples(index=False)
    ]
    return {
        "quality": quality,
        "audit": audit.model_dump(mode="json"),
        "trend": trend_records,
        "dataset_path": str(input_path),
    }


@app.post("/v1/dashboard/summary")
def dashboard_summary(request: DatasetPathRequest) -> dict[str, object]:
    return _dashboard_summary_for_path(request.input_path)


def _run_report(report_id: str, dataset_id: str) -> None:
    report = REPORTS[report_id]
    try:
        report["status"] = "running"
        report["progress"] = 20
        dataset = DATASETS[dataset_id]
        result = _dashboard_summary_for_path(str(dataset["path"]))
        report["progress"] = 90
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / f"{report_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        report["result"] = result
        report["progress"] = 100
        report["status"] = "ready"
    except (KeyError, OSError, TypeError, ValueError) as error:  # pragma: no cover
        report["status"] = "failed"
        report["error"] = str(error)


@app.post("/v1/reports", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
def create_report(request: ReportCreateRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
    dataset = DATASETS.get(request.dataset_id)
    if dataset is None or dataset["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="dataset برای تحلیل آماده نیست.")
    report_id = f"rpt_{uuid4().hex[:16]}"
    REPORTS[report_id] = {
        "report_id": report_id,
        "dataset_id": request.dataset_id,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
    }
    background_tasks.add_task(_run_report, report_id, request.dataset_id)
    return REPORTS[report_id]


@app.get("/v1/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str) -> dict[str, object]:
    report = REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="گزارش پیدا نشد.")
    return report


@app.get("/v1/reports/{report_id}/pdf")
def download_report_pdf(report_id: str) -> FileResponse:
    report = REPORTS.get(report_id)
    if report is None or report["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="گزارش هنوز آماده نیست.")
    pdf_path = REPORT_ROOT / f"{report_id}.pdf"
    if not pdf_path.exists():
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(pdf_path), pagesize=A4)
        _width, height = A4
        font_name = "Helvetica"
        pdf.setFont(font_name, 16)
        pdf.drawString(48, height - 56, "PromoGuard Promotion Review")
        pdf.setFont(font_name, 10)
        pdf.drawString(48, height - 80, f"Report ID: {report_id}")
        pdf.drawString(48, height - 98, f"Dataset ID: {report['dataset_id']}")
        result = report["result"] or {}
        audit = result.get("audit", {}) if isinstance(result, dict) else {}
        lines = [
            "Scope: observational screening; not a causal or profit claim.",
            f"Observed units: {audit.get('observed_units', 'n/a')}",
            f"Baseline units: {audit.get('baseline_units', {}).get('point', 'n/a')}",
            f"Recommendation: {audit.get('recommendation', 'n/a')}",
        ]
        y = height - 140
        for line in lines:
            pdf.drawString(48, y, line)
            y -= 18
        pdf.save()
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{report_id}.pdf")

