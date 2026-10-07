"""Thin FastAPI adapter for deterministic PromoGuard domain services."""

import hashlib
import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from apps.api.contracts import (
    AuditRequest,
    DatasetImportRequest,
    DatasetPathRequest,
    DatasetResponse,
    HillstromReportCreateRequest,
    PanelQualityResponse,
    PromotionListRequest,
    PromotionListResponse,
    ReportCreateRequest,
    ReportResponse,
)
from apps.api.storage import PilotStore
from promoguard import __version__
from promoguard.data.intake import assess_partner_intake
from promoguard.data.panel import load_weekly_panel, validate_canonical_panel
from promoguard.experiments.hillstrom import (
    HILLSTROM_DATASET,
    HillstromAnalysisConfig,
    evaluate_hillstrom_csv,
)
from promoguard.experiments.hillstrom import (
    sha256_file as hillstrom_sha256_file,
)
from promoguard.insights.decision_support import (
    ManagerDecisionSupport,
    build_manager_decision_support,
)
from promoguard.insights.promotion_audit import (
    DEFAULT_AUDIT_POLICY,
    PromotionAuditResult,
    audit_promotion_event,
    detect_promotion_episodes,
    select_representative_event,
)

MAX_UPLOAD_BYTES = 120 * 1024 * 1024
MAX_PANEL_ROWS = 1_000_000
REPORT_RESULT_SCHEMA_VERSION = "2.2.0"
HILLSTROM_REPORT_SCHEMA_VERSION = "1.1.0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATA_ROOT = (REPOSITORY_ROOT / "data").resolve()
HILLSTROM_DATASET_PATH = LOCAL_DATA_ROOT / "raw" / "hillstrom" / "hillstrom-email-analytics-2008.csv"
RUNTIME_ROOT = (REPOSITORY_ROOT / "tmp" / "product-runtime").resolve()
UPLOAD_ROOT = RUNTIME_ROOT / "datasets"
REPORT_ROOT = RUNTIME_ROOT / "reports"
DATASETS: dict[str, dict[str, object]] = {}
REPORTS: dict[str, dict[str, object]] = {}
LOGGER = logging.getLogger(__name__)


def _store() -> PilotStore:
    return PilotStore(RUNTIME_ROOT)


def _dataset_record(dataset_id: str) -> dict[str, object] | None:
    return _store().get("dataset", dataset_id)


def _report_record(report_id: str) -> dict[str, object] | None:
    return _store().get("report", report_id)


def _save_report(report: dict[str, object]) -> None:
    _store().put("report", str(report["report_id"]), report)
    REPORTS[str(report["report_id"])] = report


def _source_notes(dataset_name: str | None) -> list[str]:
    """Return prominent provenance caveats for derived benchmark fixtures."""
    name = (dataset_name or "").lower()
    if "week-index-not-real-dates" not in name:
        return []
    return [
        (
            "این فایل از جدول فروش هفتگیِ تجمیع‌شدهٔ Complete Journey ساخته شده است. "
            "شمارهٔ هفته در منبع شاخص ترتیبی است؛ تاریخ‌های این گزارش فقط برچسب نمایشی‌اند و تاریخ واقعی نیستند."
        ),
        (
            "فروش و پروموشن در سطح همهٔ فروشگاه‌های موجود در جدول تجمیع شده‌اند؛ تفاوت فروشگاه‌ها قابل بررسی نیست. "
            "پروموشن یعنی کالا در دست‌کم یک فروشگاه در خبرنامه یا نمایش بوده است."
        ),
    ]


def _write_snapshot(path: Path, content: bytes) -> None:
    """Never expose a partially written dataset to an analysis worker."""
    temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _store().recover_interrupted()
    yield

app = FastAPI(
    title="PromoGuard API",
    version=__version__,
    lifespan=lifespan,
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


@app.get("/ready")
def readiness() -> dict[str, str]:
    """Report whether the API can safely accept a pilot request.

    ``/health`` is intentionally a liveness probe and must stay independent of
    storage.  ``/ready`` is the dependency-aware probe for a local pilot: it
    verifies that the durable metadata store can be opened and queried without
    exposing the runtime path or any customer data.
    """
    try:
        with _store().connection() as connection:
            connection.execute("SELECT 1").fetchone()
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        LOGGER.warning("PromoGuard readiness check failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ذخیره‌ساز متادیتای پایلوت آماده نیست؛ فضای runtime را بررسی کنید.",
        ) from error
    return {
        "status": "ready",
        "service": "promoguard-api",
        "version": __version__,
        "storage": "ok",
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
        return pd.read_csv(buffer, dtype={"store_id": "string", "upc": "string"})
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
        panel = pd.read_csv(BytesIO(content), dtype={"store_id": "string", "upc": "string"})
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ساختار CSV قابل خواندن نیست.") from error
    if assess_partner_intake(panel)["privacy_columns"]:
        raise HTTPException(status_code=422, detail="ستون‌های اطلاعات شخصی را پیش از بارگذاری حذف کنید؛ این تحلیل فقط به فروش تجمیعی نیاز دارد.")
    return panel, validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)


@app.post("/v1/datasets", response_model=DatasetResponse)
async def create_dataset(file: Annotated[UploadFile, File(description="فایل CSV فروش هفتگی")]) -> dict[str, object]:
    """Store a validated upload behind a stable dataset identifier."""
    content = await _read_upload_bytes(file)
    _panel, quality = _quality_for_bytes(content)
    dataset_id = hashlib.sha256(content).hexdigest()[:24]
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    dataset_path = UPLOAD_ROOT / f"{dataset_id}.csv"
    _write_snapshot(dataset_path, content)
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
    _store().put("dataset", dataset_id, record)
    return {key: value for key, value in record.items() if key != "path"}


@app.post("/v1/datasets/import-path", response_model=DatasetResponse)
def import_dataset_path(request: DatasetImportRequest) -> dict[str, object]:
    """Register an approved local dataset through the product contract."""
    resolved_path = Path(request.input_path).resolve()
    allowed_roots = (LOCAL_DATA_ROOT.resolve(), UPLOAD_ROOT.resolve())
    if not any(resolved_path == root or root in resolved_path.parents for root in allowed_roots):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="مسیر داده در محیط کنترل‌شده مجاز نیست.")
    if not resolved_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="فایل داده پیدا نشد.")
    content = resolved_path.read_bytes()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="حجم فایل از حد مجاز بیشتر است.")
    _panel, quality = _quality_for_bytes(content)
    dataset_id = hashlib.sha256(content).hexdigest()[:24]
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    snapshot = UPLOAD_ROOT / f"{dataset_id}.csv"
    _write_snapshot(snapshot, content)
    DATASETS[dataset_id] = {
        "dataset_id": dataset_id,
        "filename": resolved_path.name,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "path": str(snapshot),
        "quality": quality,
        "status": "ready" if quality["valid"] else "rejected",
    }
    _store().put("dataset", dataset_id, DATASETS[dataset_id])
    return {key: value for key, value in DATASETS[dataset_id].items() if key != "path"}


@app.get("/v1/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str) -> dict[str, object]:
    record = _dataset_record(dataset_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset پیدا نشد.")
    return {key: value for key, value in record.items() if key != "path"}


@app.get("/v1/datasets/{dataset_id}/promotions", response_model=PromotionListResponse)
def list_dataset_promotions(dataset_id: str) -> dict[str, object]:
    """List selectable promotion events for an uploaded, quality-approved dataset."""
    record = _dataset_record(dataset_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="dataset پیدا نشد.")
    if record["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="dataset برای انتخاب رویداد آماده نیست.")
    panel = _load_valid_panel(str(record["path"]))
    episodes = detect_promotion_episodes(panel)
    return {
        "count": len(episodes),
        "returned": len(episodes),
        "events": episodes.to_dict(orient="records"),
    }


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


def _dashboard_summary_for_path(
    input_path: str,
    selected_event: dict[str, object] | None = None,
    dataset_name: str | None = None,
) -> dict[str, object]:
    """Return one stable, manager-facing payload for the web dashboard.

    The API deliberately keeps the observational boundary visible: this endpoint
    does not turn a promotion comparison into a causal or profit claim.
    """
    panel = _load_valid_panel(input_path)
    quality = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
    try:
        selection = selected_event or select_representative_event(panel)
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
        "decision_support": build_manager_decision_support(audit).model_dump(mode="json"),
        "trend": trend_records,
        "dataset_name": dataset_name or Path(input_path).name,
        "source_notes": _source_notes(dataset_name or Path(input_path).name),
    }


def _report_cache_key(dataset_sha256: str, selected_event: dict[str, object] | None) -> str:
    """Isolate cached analytics by exact source bytes, campaign and logic versions."""
    event_for_key = selected_event or {}
    normalized_event = {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in event_for_key.items()
    }
    cache_identity = {
        "dataset_sha256": dataset_sha256,
        "selected_event": normalized_event,
        "product_version": __version__,
        "audit_policy": DEFAULT_AUDIT_POLICY.version,
        "result_schema": REPORT_RESULT_SCHEMA_VERSION,
    }
    return hashlib.sha256(
        json.dumps(cache_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@app.post("/v1/dashboard/summary")
def dashboard_summary(request: DatasetPathRequest) -> dict[str, object]:
    return _dashboard_summary_for_path(request.input_path)


def _run_report(
    report_id: str, dataset_id: str, selected_event: dict[str, object] | None = None
) -> None:
    report = _store().claim_report(report_id)
    if report is None:
        return
    try:
        report["status"] = "running"
        report["progress"] = 20
        dataset = _dataset_record(dataset_id)
        if dataset is None:
            raise ValueError("فایل داده پیدا نشد؛ آن را دوباره بارگذاری کنید.")
        source = Path(str(dataset["path"]))
        if hashlib.sha256(source.read_bytes()).hexdigest() != dataset["sha256"]:
            raise ValueError("فایل ذخیره‌شده تغییر کرده است؛ نسخهٔ مجاز را دوباره بارگذاری کنید.")
        cache_key = _report_cache_key(str(dataset["sha256"]), selected_event)
        cache_path = REPORT_ROOT / "cache" / f"{cache_key}.json"
        result = None
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and {"quality", "audit", "decision_support", "trend"} <= cached.keys():
                    PromotionAuditResult.model_validate(cached["audit"])
                    ManagerDecisionSupport.model_validate(cached["decision_support"])
                    PanelQualityResponse.model_validate(cached["quality"])
                    result = cached
                    result["dataset_name"] = str(dataset["filename"])
                    result["source_notes"] = _source_notes(str(dataset["filename"]))
                    report["cache_hit"] = True
            except (OSError, ValueError, TypeError):
                result = None
        if result is None:
            result = _dashboard_summary_for_path(
                str(dataset["path"]), selected_event, str(dataset["filename"])
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_cache_path = cache_path.with_name(f"{cache_key}.{report_id}.tmp")
            temporary_cache_path.write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(temporary_cache_path, cache_path)
            report["cache_hit"] = False
        report["progress"] = 90
        _save_report(report)
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / f"{report_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        report["result"] = result
        report["progress"] = 100
        report["status"] = "ready"
    except HTTPException:
        report["status"] = "failed"
        report["error"] = "رویداد برای تحلیل آماده نیست؛ تاریخ کمپین، سابقهٔ فروش و کامل‌بودن فایل را بررسی کنید."
    except (KeyError, OSError, TypeError, ValueError) as error:
        report["status"] = "failed"
        report["error"] = (str(error) if isinstance(error, ValueError)
                           else "خواندن یا ذخیرهٔ گزارش ناموفق بود؛ فایل و فضای ذخیره‌سازی را بررسی کنید.")
    except Exception:
        # A background job must not remain "running" after an unexpected failure.
        LOGGER.exception("Report job failed: %s", report_id)
        report["status"] = "failed"
        report["error"] = "تحلیل با خطای داخلی متوقف شد؛ شناسهٔ گزارش را برای بررسی فنی نگه دارید."
    finally:
        _save_report(report)


def _run_hillstrom_report(report_id: str) -> None:
    """Run a public randomized-experiment report using the shared durable job store."""
    report = _store().claim_report(report_id)
    if report is None:
        return
    try:
        if not HILLSTROM_DATASET_PATH.is_file():
            raise ValueError("دادهٔ Hillstrom پیدا نشد؛ فرمان download_hillstrom را اجرا کنید.")
        expected_sha256 = str(report["configuration"]["source_sha256"])
        if hillstrom_sha256_file(HILLSTROM_DATASET_PATH) != expected_sha256:
            raise ValueError("فایل benchmark بعد از ثبت گزارش تغییر کرده؛ داده را دوباره دریافت کنید.")
        cache_identity = {
            "dataset_sha256": expected_sha256,
            "configuration": report["configuration"]["analysis"],
            "product_version": __version__,
            "result_schema": HILLSTROM_REPORT_SCHEMA_VERSION,
        }
        cache_key = hashlib.sha256(
            json.dumps(cache_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        cache_path = REPORT_ROOT / "cache" / f"hillstrom-{cache_key}.json"
        result = None
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if (
                    isinstance(cached, dict)
                    and cached.get("benchmark") == HILLSTROM_DATASET
                    and cached.get("source", {}).get("sha256") == expected_sha256
                    and len(cached.get("comparisons", [])) == 3
                ):
                    result = cached
                    report["cache_hit"] = True
            except (OSError, ValueError, TypeError):
                result = None
        if result is None:
            configuration = HillstromAnalysisConfig.model_validate(
                report["configuration"]["analysis"]
            )

            def update_progress(value: int) -> None:
                report["progress"] = value
                _save_report(report)

            result = evaluate_hillstrom_csv(
                HILLSTROM_DATASET_PATH,
                configuration,
                progress_callback=update_progress,
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_cache_path = cache_path.with_name(f"{cache_path.name}.{report_id}.tmp")
            temporary_cache_path.write_text(
                json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
            )
            os.replace(temporary_cache_path, cache_path)
            report["cache_hit"] = False
        report["progress"] = 95
        _save_report(report)
        REPORT_ROOT.mkdir(parents=True, exist_ok=True)
        (REPORT_ROOT / f"{report_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8"
        )
        report["result"] = result
        report["progress"] = 100
        report["status"] = "ready"
    except (OSError, KeyError, TypeError, ValueError) as error:
        report["status"] = "failed"
        report["error"] = str(error) if isinstance(error, ValueError) else "خواندن یا ذخیرهٔ گزارش آزمایش ناموفق بود."
    except Exception:
        LOGGER.exception("Hillstrom report job failed: %s", report_id)
        report["status"] = "failed"
        report["error"] = "تحلیل آزمایش با خطای داخلی متوقف شد؛ شناسهٔ گزارش را نگه دارید."
    finally:
        _save_report(report)


@app.post("/v1/experiments/hillstrom/reports", response_model=ReportResponse, status_code=202)
def create_hillstrom_report(
    request: HillstromReportCreateRequest, background_tasks: BackgroundTasks
) -> dict[str, object]:
    """Queue a randomized campaign evaluation of the locally available public dataset."""
    if not HILLSTROM_DATASET_PATH.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="دادهٔ Hillstrom آماده نیست؛ ابتدا tools/download_hillstrom.py را اجرا کنید.",
        )
    try:
        configuration = HillstromAnalysisConfig.model_validate(request.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    source_hash = hillstrom_sha256_file(HILLSTROM_DATASET_PATH)
    report_id = f"rpt_{uuid4().hex[:16]}"
    analysis_configuration = configuration.model_dump(mode="json")
    record: dict[str, object] = {
        "report_id": report_id,
        "dataset_id": f"hillstrom-{source_hash[:16]}",
        "analysis_type": "randomized_experiment",
        "configuration": {
            "benchmark": HILLSTROM_DATASET,
            "source_sha256": source_hash,
            "analysis": analysis_configuration,
        },
        "selected_event": None,
        "cache_hit": None,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _save_report(record)
    background_tasks.add_task(_run_hillstrom_report, report_id)
    return record
@app.post("/v1/reports", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
def create_report(request: ReportCreateRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
    dataset = _dataset_record(request.dataset_id)
    if dataset is None or dataset["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="dataset برای تحلیل آماده نیست.")
    report_id = f"rpt_{uuid4().hex[:16]}"
    selected_event = None
    if request.store_id is not None:
        selected_event = {
            "store_id": request.store_id,
            "upc": request.upc,
            "start_date": request.start_date,
        }
    REPORTS[report_id] = {
        "report_id": report_id,
        "dataset_id": request.dataset_id,
        "selected_event": selected_event,
        "cache_hit": None,
        "status": "queued",
        "progress": 0,
        "result": None,
        "error": None,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _save_report(REPORTS[report_id])
    background_tasks.add_task(_run_report, report_id, request.dataset_id, selected_event)
    return REPORTS[report_id]


@app.get("/v1/reports/{report_id}", response_model=ReportResponse)
def get_report(report_id: str) -> dict[str, object]:
    report = _report_record(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="گزارش پیدا نشد.")
    return report


@app.get("/v1/reports")
def list_reports(limit: int = Query(default=50, ge=1, le=100)) -> dict[str, object]:
    records = _store().list("report", limit)
    return {"reports": [
        {key: value for key, value in record.items() if key != "result"}
        for record in records
    ]}


@app.post("/v1/reports/{report_id}/retry", response_model=ReportResponse, status_code=202)
def retry_report(report_id: str, background_tasks: BackgroundTasks) -> dict[str, object]:
    previous = _report_record(report_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="گزارش پیدا نشد.")
    if previous["status"] != "failed":
        raise HTTPException(status_code=409, detail="فقط تحلیل ناموفق قابل تلاش مجدد است.")
    event = previous.get("selected_event") or {}
    return create_report(ReportCreateRequest(dataset_id=str(previous["dataset_id"]), **event), background_tasks)


@app.get("/v1/reports/{report_id}/pdf")
def download_report_pdf(report_id: str) -> FileResponse:
    report = _report_record(report_id)
    if report is None or report["status"] != "ready":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="گزارش هنوز آماده نیست.")
    pdf_path = REPORT_ROOT / f"{report_id}.pdf"
    if not pdf_path.exists():
        from apps.api.pdf import build_promotion_report_pdf

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(build_promotion_report_pdf(report))
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"{report_id}.pdf")

