"""Streamlit adapter for the deterministic PromoGuard promotion audit."""

from __future__ import annotations

import json
import sys
from datetime import date
from io import BytesIO
from typing import cast
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

# Streamlit executes this file as a script, so the repository root is not
# guaranteed to be on sys.path when the entrypoint is passed by file path.
# Add it before importing the sibling `apps` package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from apps.dashboard.presentation import (  # noqa: E402
    audit_comparison_records,
    audit_event_summary,
    cannibalization_candidate_records,
    cannibalization_limitation_copy,
    cannibalization_presentation,
    claim_boundary_copy,
    randomized_benchmark_presentation,
    recommendation_presentation,
    warning_presentation_records,
)
from promoguard.data.intake import assess_partner_intake  # noqa: E402
from promoguard.data.panel import load_weekly_panel, validate_canonical_panel  # noqa: E402
from promoguard.data.partner import (  # noqa: E402
    PartnerExportContract,
    PartnerPrepared,
    prepare_partner_export,
    sha256_bytes,
)
from promoguard.insights.promotion_audit import (  # noqa: E402
    ContributionAssumption,
    PromotionAuditResult,
    audit_promotion_event,
    detect_promotion_episodes,
    select_representative_event,
)

try:
    import streamlit as st
except ImportError:  # pragma: no cover - keeps core/API installs usable
    st = None

MAX_UPLOAD_BYTES = 120 * 1024 * 1024
MAX_PANEL_ROWS = 1_000_000
DEFAULT_PANEL_PATH = REPOSITORY_ROOT / "data" / "processed" / "breakfast-at-the-frat"
CAUSAL_BENCHMARK_PATH = REPOSITORY_ROOT / "reports" / "phase-06" / "criteo-uplift-itt-benchmark.json"


def _apply_reviewer_style() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #f5f7fb; }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #10182b;
            border-left: 1px solid rgba(255,255,255,.08);
            width: 240px;
        }
        [data-testid="stSidebar"] * { color: #e7ecf7; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label { color: #d7deed; }
        [data-testid="stSidebar"] [data-testid="stRadio"] > label {
            color: #ffffff; font-weight: 700; font-size: .82rem;
        }
        [data-testid="stMainBlockContainer"] p,
        [data-testid="stSidebarContent"] p,
        [data-testid="stWidgetLabel"] {
            direction: rtl;
            text-align: right;
        }
        [data-testid="stMetric"], [data-testid="stAlert"] {
            direction: rtl; text-align: right;
        }
        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5eaf4;
            border-radius: 14px;
            padding: .75rem .9rem;
            box-shadow: 0 4px 16px rgba(22, 34, 64, .04);
        }
        .stButton > button {
            border-radius: 10px;
            min-height: 2.7rem;
            font-weight: 700;
            transition: all .18s ease;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #3157d5, #5746c8);
            border-color: #3157d5;
            color: white;
            box-shadow: 0 8px 18px rgba(49, 87, 213, .22);
        }
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 18px rgba(22, 34, 64, .12);
        }
        [data-testid="stFileUploader"] {
            background: #ffffff;
            border: 1px dashed #b6c2db;
            border-radius: 14px;
            padding: .4rem;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input {
            border-radius: 9px;
            background: #ffffff;
        }
        [data-testid="stRadio"] [role="radiogroup"] { gap: .5rem; }
        [data-testid="stRadio"] [role="radio"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: .35rem .7rem;
        }
        [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
            border-color: #3157d5;
            background: #eef3ff;
        }
        [data-testid="stExpander"] {
            border: 1px solid #e5eaf4;
            border-radius: 12px;
            background: #ffffff;
        }
        .pg-brand {
            display: flex; align-items: center; gap: .65rem;
            direction: ltr; margin: .4rem 0 1.25rem;
        }
        .pg-brand-mark {
            width: 34px; height: 34px; display: grid; place-items: center;
            border-radius: 10px; background: #3157d5; color: white;
            font-weight: 900; box-shadow: 0 7px 16px rgba(49,87,213,.25);
        }
        .pg-brand-name { color: #172033; font-weight: 800; letter-spacing: -.02em; }
        .pg-brand-sub { color: #64748b; font-size: .78rem; }
        .pg-shell-label {
            color: #64748b; font-size: .74rem; font-weight: 800;
            letter-spacing: .08em; text-transform: uppercase; direction: ltr;
        }
        .pg-hero {
            padding: 1.5rem 1.7rem;
            border: 1px solid #dce4f4;
            border-radius: 20px;
            background: linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%);
            color: #172033;
            margin: .2rem 0 1.25rem;
            box-shadow: 0 12px 30px rgba(31, 48, 87, .07);
            position: relative; overflow: hidden;
        }
        .pg-hero:after { content: ""; position: absolute; width: 180px; height: 180px;
            border-radius: 50%; background: rgba(49,87,213,.08); left: -60px; top: -85px; }
        .pg-hero h1 {
            direction: ltr;
            unicode-bidi: isolate;
            text-align: left;
            margin: 0 0 .35rem 0;
            font-size: clamp(1.25rem, 4vw, 1.85rem);
            letter-spacing: -.045em;
            color: #16234a;
            overflow-wrap: anywhere;
        }
        .pg-hero p { direction: rtl; text-align: right; margin: 0; color: #52627d; }
        .pg-hero .pg-kicker { direction: ltr; color: #3157d5; font-size: .72rem;
            font-weight: 800; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .6rem; }
        .pg-step {
            direction: rtl;
            display: inline-block;
            padding: .38rem .8rem;
            border-radius: 999px;
            background: #e9efff;
            color: #3157d5;
            font-weight: 700;
            margin: .5rem 0;
        }
        .pg-boundary {
            padding: .85rem 1rem;
            border-right: 4px solid #e6a72e;
            background: #fff8e8;
            color: #725018;
            border-radius: 12px;
            box-shadow: 0 4px 14px rgba(126, 87, 16, .05);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _step(number: int, title: str) -> None:
    st.markdown(
        f'<div class="pg-step">مرحله {number} از ۳ — {title}</div>',
        unsafe_allow_html=True,
    )


if st is not None:

    @st.cache_data(show_spinner="در حال بارگذاری پنل واقعی فروش...", max_entries=8)
    def _load_local_panel(path: str) -> pd.DataFrame:
        return load_weekly_panel(path, max_bytes=MAX_UPLOAD_BYTES)

    @st.cache_data(show_spinner="در حال شناسایی دوره‌های پروموشن...", max_entries=8)
    def _episodes(panel: pd.DataFrame) -> pd.DataFrame:
        return detect_promotion_episodes(panel)

    @st.cache_data(show_spinner="در حال انتخاب یک رویداد قابل‌ممیزی...", max_entries=8)
    def _representative_event(panel: pd.DataFrame) -> dict[str, Any]:
        return select_representative_event(panel)

    @st.cache_data(show_spinner=False, max_entries=2)
    def _load_causal_benchmark(path: str) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_uploaded_panel(name: str, content: bytes) -> pd.DataFrame:
    if not name.lower().endswith(".csv"):
        raise ValueError("فایل ورودی باید CSV باشد.")
    if not content:
        raise ValueError("فایل آپلودشده خالی است.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"حجم فایل از سقف {MAX_UPLOAD_BYTES:,} بایت بیشتر است.")
    try:
        return pd.read_csv(BytesIO(content))
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise ValueError("CSV خالی، خراب یا دارای encoding پشتیبانی‌نشده است.") from error


def _show_quality_report(report: dict[str, Any]) -> None:
    status_label = "معتبر" if report["valid"] else "نامعتبر"
    status_method = st.success if report["valid"] else st.error
    status_method(f"وضعیت پنل: {status_label}")
    first, second, third, fourth = st.columns(4)
    first.metric("ردیف‌ها", f"{report['rows']:,}")
    second.metric("سری‌های فروشگاه–کالا", f"{(report['series'] or 0):,}")
    third.metric("ردیف‌های پروموشن", f"{(report['promotion_rows'] or 0):,}")
    fourth.metric("ردیف تکراری", f"{(report['duplicate_grain_rows'] or 0):,}")
    st.caption(
        f"بازه زمانی: {report['date_min'] or 'نامشخص'} تا "
        f"{report['date_max'] or 'نامشخص'} | دانه‌بندی: {report['grain']}"
    )
    problems = {
        "ستون‌های ضروریِ غایب": ", ".join(report["missing_required_columns"]) or "—",
        "نام ستون تکراری": ", ".join(report["duplicate_column_names"]) or "—",
        "تاریخ نامعتبر": report["date_parse_errors"],
        "شناسه فروشگاه خالی": report["missing_store_id_rows"],
        "شناسه کالا خالی": report["missing_upc_rows"],
        "فروش منفی": report["negative_units_rows"],
        "فروش خالی": report["missing_units_rows"],
        "فروش غیرمتناهی": report["non_finite_units_rows"],
        "پرچم پروموشن نامعتبر": report["invalid_promotion_rows"],
        "بیش از سقف ردیف": report["oversized_row_count"],
    }
    with st.expander("جزئیات کنترل کیفیت"):
        st.dataframe(
            pd.DataFrame(
                [(control, str(value)) for control, value in problems.items()],
                columns=["کنترل", "نتیجه"],
            ),
            hide_index=True,
            width="stretch",
        )
        if report["warnings"]:
            st.warning(" | ".join(report["warnings"]))


def _show_partner_readiness(
    report: PartnerPrepared, intake: dict[str, Any]
) -> None:
    """Render the partner gate without presenting it as a sales or causal result."""

    if report.status == "prepared_for_observational_audit":
        st.success("فایل از دروازهٔ قرارداد و کنترل اولیه عبور کرد")
    else:
        st.error("فایل برای ممیزی مشاهده‌ای آماده نیست")
    first, second, third = st.columns(3)
    first.metric("ردیف‌ها", f"{report.rows:,}")
    second.metric("وضعیت کنترل داده", report.intake_status)
    third.metric("مدت نگهداری توافق‌شده", f"{report.retention_days} روز")
    if report.reasons:
        st.warning(
            "دلایل مسدودشدن: "
            + "، ".join(reason.value for reason in report.reasons)
        )
    if intake["warnings"]:
        st.info(" | ".join(intake["warnings"]))
    with st.expander("جزئیات قرارداد و provenance"):
        st.write(f"شناسه منبع: {report.source_id}")
        st.write(f"SHA256 فایل اصلی: {report.source_sha256}")
        st.write("نگاشت ستون‌ها:")
        st.json(report.column_mapping)
        st.caption(report.limitation)
    st.download_button(
        "دانلود گزارش آمادگی فایل شریک",
        data=json.dumps(
            {"partner": report.model_dump(mode="json"), "intake": intake},
            ensure_ascii=False,
            indent=2,
        ),
        file_name="partner-readiness-report.json",
        mime="application/json",
        width="stretch",
    )


def _partner_intake_workflow() -> None:
    """Collect a declared partner contract and render the readiness-only result."""

    upload = st.file_uploader(
        "فایل CSV شریک را انتخاب کنید",
        type=["csv"],
        help="فایل خام شریک در Git ذخیره نمی‌شود و این مسیر تحلیل اقتصادی یا علّی انجام نمی‌دهد.",
    )
    if upload is None:
        st.info("برای شروع یک CSV شامل تاریخ، فروشگاه، کالا، واحد فروش و نشانهٔ پروموشن بدهید.")
        return
    content = upload.getvalue()
    try:
        frame = _load_uploaded_panel(upload.name, content)
    except ValueError as error:
        st.error(str(error))
        return

    with st.form("partner_intake_contract"):
        st.subheader("قرارداد دادهٔ همراه فایل")
        first, second = st.columns(2)
        with first:
            source_id = st.text_input("شناسه منبع", value="partner-export-01")
            data_owner = st.text_input("مالک داده", value="نام شرکت یا واحد مالک داده")
            permission_reference = st.text_input(
                "مرجع اجازه استفاده", value="شناسه قرارداد یا ایمیل تأیید"
            )
            extraction_date = st.date_input("تاریخ استخراج", value=date.today())
            grain_label = st.selectbox("دانه‌بندی فایل", ["هفتگی فروشگاه–کالا", "روزانه فروشگاه–کالا"])
        with second:
            retention_days = st.number_input("مدت نگهداری توافق‌شده به روز", min_value=1, max_value=365, value=30)
            calendar_reference = st.text_input("مرجع تقویم و timezone", value="تقویم و timezone اعلام‌شده توسط مالک داده")
            units_definition = st.text_input("تعریف واحد فروش", value="تعداد واحد فروخته‌شده")
            zero_label = st.selectbox("معنی مقدار صفر فروش", ["فروش واقعی صفر", "نامعلوم یا احتمالاً گمشده"])
            promotion_definition = st.text_input("تعریف promotion flag", value="پرچم تأییدشدهٔ اجرای پروموشن")
        submitted = st.form_submit_button("بررسی قرارداد و فایل", type="primary", width="stretch")

    if submitted:
        try:
            contract = PartnerExportContract(
                source_id=source_id,
                data_owner=data_owner,
                permission_reference=permission_reference,
                extraction_date=cast(date, extraction_date),
                permitted_purpose="observational_data_readiness_audit",
                retention_days=int(retention_days),
                grain=("weekly_store_sku" if grain_label.startswith("هفتگی") else "daily_store_sku"),
                calendar_reference=calendar_reference,
                units_definition=units_definition,
                zero_units_meaning=("observed_zero" if zero_label.startswith("فروش واقعی") else "unknown"),
                promotion_signal_definition=promotion_definition,
            )
            _prepared_frame, report = prepare_partner_export(
                frame, contract, source_sha256=sha256_bytes(content)
            )
            st.session_state["partner_readiness"] = {
                "report": report,
                "intake": assess_partner_intake(frame),
            }
        except (ValidationError, ValueError) as error:
            st.error(f"قرارداد یا فایل قابل قبول نیست: {error}")
            return

    stored = st.session_state.get("partner_readiness")
    if stored is not None:
        _show_partner_readiness(stored["report"], stored["intake"])


def _event_label(row: pd.Series) -> str:
    start = pd.Timestamp(row["start_date"]).date().isoformat()
    return f"فروشگاه {row['store_id']} | UPC {row['upc']} | شروع {start}"


def _show_audit(result: PromotionAuditResult, *, compact_demo: bool = False) -> None:
    payload = result.model_dump(mode="json")
    presentation = recommendation_presentation(result.recommendation)
    status_method = getattr(st, presentation.style)
    st.subheader("نتیجه ممیزی قابل‌ممیزی")
    status_method(f"**{presentation.title}**\n\n{presentation.explanation}")
    st.caption("منطق دقیق و machine-readable در فایل JSON قابل دانلود حفظ شده است.")
    observed, baseline, difference = st.columns(3)
    observed.metric("فروش مشاهده‌شده", f"{result.observed_units:,.0f} واحد")
    baseline.metric(
        "فروش مبنا",
        f"{result.baseline_units.point:,.0f} واحد",
        help=(
            f"بازه عدم‌قطعیت: {result.baseline_units.lower:,.0f} تا "
            f"{result.baseline_units.upper:,.0f}"
        ),
    )
    units_difference = result.estimated_units_difference_vs_baseline
    difference.metric(
        "تفاوت مشاهده‌شده با مبنا",
        f"{units_difference.point:+,.0f} واحد",
        help=(
            f"بازه عدم‌قطعیت: {units_difference.lower:+,.0f} تا "
            f"{units_difference.upper:+,.0f}"
        ),
    )

    chart_data = pd.DataFrame(audit_comparison_records(result))
    st.vega_lite_chart(
        chart_data,
        {
            "height": 180,
            "layer": [
                {
                    "mark": {"type": "bar", "cornerRadiusEnd": 6, "size": 34},
                    "encoding": {
                        "y": {
                            "field": "label",
                            "type": "nominal",
                            "sort": None,
                            "title": None,
                        },
                        "x": {"field": "value", "type": "quantitative", "title": "واحد فروش"},
                        "color": {
                            "field": "kind",
                            "type": "nominal",
                            "scale": {
                                "domain": ["observed", "baseline"],
                                "range": ["#4f46e5", "#0f766e"],
                            },
                            "legend": None,
                        },
                        "tooltip": [
                            {"field": "label", "type": "nominal", "title": "شاخص"},
                            {"field": "value", "type": "quantitative", "title": "مقدار"},
                        ],
                    },
                },
                {
                    "transform": [{"filter": "datum.kind === 'baseline'"}],
                    "mark": {"type": "errorbar", "ticks": True, "color": "#111827"},
                    "encoding": {
                        "y": {"field": "label", "type": "nominal", "sort": None, "title": None},
                        "x": {"field": "lower", "type": "quantitative", "title": "واحد فروش"},
                        "x2": {"field": "upper"},
                    },
                },
            ],
        },
        width="stretch",
    )
    st.caption(
        "خط روی فروش مبنا بازه عدم‌قطعیت را نشان می‌دهد؛ این نمودار مستقیماً از نتیجه typed ساخته "
        "شده و هیچ محاسبه تحلیلی تازه‌ای در رابط کاربری ندارد."
    )
    if result.contribution_sensitivity is not None:
        sensitivity = result.contribution_sensitivity
        estimate = sensitivity.estimated_contribution_difference_vs_baseline
        st.info(
            "تحلیل حساسیت سهم واحد — نه سود پروموشن: "
            f"{estimate.point:+,.2f} {sensitivity.assumption.currency} "
            f"(منبع فرض: {sensitivity.assumption.source})"
        )
        st.caption(sensitivity.limitation)

    window_rows = []
    for label, window in (
        ("قبل", result.pre_window),
        ("حین", result.during_window),
        ("بعد", result.post_window),
    ):
        window_rows.append(
            {
                "بازه": label,
                "هفته مشاهده‌شده": window.observed_weeks,
                "کل فروش": window.total_units,
                "میانگین هفتگی": window.mean_units,
                "هفته پروموشن": window.promotion_weeks,
            }
        )
    with st.expander("رفتار فروش قبل، حین و بعد از رویداد", expanded=not compact_demo):
        st.dataframe(pd.DataFrame(window_rows), hide_index=True, width="stretch")

    st.subheader("بررسی جایگزینی کالاهای هم‌دسته")
    substitution = cannibalization_presentation(result)
    substitution_method = getattr(st, substitution.style)
    substitution_method(f"**{substitution.title}**\n\n{substitution.explanation}")
    summary = result.cannibalization
    st.caption(
        f"دسته کالا: {summary.category or 'نامشخص'} | "
        f"همسایه واجدشرایط: {summary.eligible_neighbor_count}"
    )
    candidates = cannibalization_candidate_records(result)
    if candidates:
        st.dataframe(pd.DataFrame(candidates), hide_index=True, width="stretch")
    st.caption(cannibalization_limitation_copy(result))

    st.subheader("هشدارها و مرز ادعا")
    warnings = warning_presentation_records(result)
    if warnings:
        st.dataframe(pd.DataFrame(warnings), hide_index=True, width="stretch")
    claim_copy, scope_copy = claim_boundary_copy()
    st.markdown(
        f'<div class="pg-boundary"><strong>مرز ادعا:</strong> {claim_copy}<br>'
        f'<strong>دامنه تصمیم:</strong> {scope_copy}</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        f"سیاست تصمیم: {result.policy.policy_id} — نسخه {result.policy.version} | "
        "مدل مبنا: recursive-naive-1 بر پایه آخرین هفته غیرپروموشنی"
    )
    with st.expander("فرض‌ها و شواهد"):
        st.write("فرض‌ها:")
        for assumption in result.assumptions:
            st.write(f"- {assumption}")
        st.write("ارجاع‌های شواهد:")
        for evidence in result.evidence_refs:
            st.code(evidence)
    st.download_button(
        "دانلود گزارش JSON قابل‌ممیزی",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"{result.audit_id}.json",
        mime="application/json",
    )


def _show_randomized_benchmark() -> None:
    """Render persisted external evidence without mixing it into the retail audit."""
    try:
        presentation = randomized_benchmark_presentation(
            _load_causal_benchmark(str(CAUSAL_BENCHMARK_PATH))
        )
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError):
        st.info("شاهد benchmark تصادفی در این نسخه محلی در دسترس نیست.")
        return
    with st.expander("شاهد مستقل روش علّی — آزمایش تصادفی Criteo", expanded=False):
        st.success(presentation.title)
        first, second, third = st.columns(3)
        first.metric("ردیف‌های واقعی پردازش‌شده", f"{presentation.rows_read:,}")
        second.metric("ITT برای visit", f"{presentation.visit_itt:+.3%}")
        third.metric("ITT برای conversion", f"{presentation.conversion_itt:+.3%}")
        st.caption(
            "اعداد دقیقاً از گزارش versioned فاز ۶ خوانده می‌شوند و رابط کاربری هیچ برآورد تازه‌ای "
            "محاسبه نمی‌کند."
        )
        st.warning(presentation.limitation)


def _demo_workflow() -> None:
    st.sidebar.success("حالت ارائه با داده واقعی فعال است")
    st.sidebar.caption("بدون API خارجی، بدون LLM و بدون داده مصنوعی")

    _step(1, "داده واقعی و کنترل کیفیت")
    st.write(
        "منبع: دیتاست عمومی **dunnhumby Breakfast at the Frat**؛ فایل خام در Git نگهداری نمی‌شود."
    )
    run_label = (
        "اجرای دوباره دموی واقعی"
        if "reviewer_demo" in st.session_state
        else "اجرای دموی واقعی با یک کلیک"
    )
    if st.button(run_label, type="primary", width="stretch"):
        try:
            with st.spinner("در حال اعتبارسنجی داده و اجرای ممیزی deterministic..."):
                panel = _load_local_panel(str(DEFAULT_PANEL_PATH))
                report = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
                if not report["valid"]:
                    st.session_state["reviewer_demo"] = {"quality": report, "result": None}
                else:
                    representative = _representative_event(panel)
                    result = audit_promotion_event(
                        panel,
                        store_id=str(representative["store_id"]),
                        upc=str(representative["upc"]),
                        start_date=representative["start_date"],
                    )
                    st.session_state["reviewer_demo"] = {
                        "quality": report,
                        "result": result,
                    }
        except (FileNotFoundError, OSError, ValueError):
            st.error(
                "داده واقعی پردازش‌شده روی این دستگاه آماده نیست. مسیر محلی برای حفظ حریم خصوصی "
                "نمایش داده نشد؛ ابتدا دستور ingest مستندشده را اجرا کنید."
            )
            st.code(
                "promoguard ingest --input data/raw/breakfast-at-the-frat "
                "--output data/processed/breakfast-at-the-frat"
            )
            return

    demo = st.session_state.get("reviewer_demo")
    if demo is None:
        st.info(
            "این یک نمونه ساختگی نیست. با کلیک روی دکمه، پنل کامل واقعی validate و همان رویداد "
            "نمایندهٔ deterministic ممیزی می‌شود."
        )
        return

    st.progress(100, text="داده واقعی بارگذاری و کنترل شد")
    _show_quality_report(demo["quality"])
    if demo["result"] is None:
        st.error("کنترل کیفیت رد شد؛ ممیزی برای جلوگیری از خروجی نامعتبر اجرا نشد.")
        return

    result: PromotionAuditResult = demo["result"]
    _step(2, "رویداد انتخاب‌شده با قانون ثابت")
    st.caption(
        f"سیستم نخستین رویدادی را انتخاب می‌کند که حداقل "
        f"{result.policy.representative_min_history_weeks} هفته تاریخچه و پنجره پس از پروموشن "
        "کامل داشته باشد؛ انتخاب دستیِ نتیجه‌پسند در Demo Mode وجود ندارد."
    )
    columns = st.columns(4)
    for column, (label, value) in zip(columns, audit_event_summary(result), strict=True):
        column.metric(label, value)

    _step(3, "نتیجه، عدم‌قطعیت و مرز تصمیم")
    _show_audit(result, compact_demo=True)
    _show_randomized_benchmark()


def main() -> None:
    if st is None:  # pragma: no cover
        print("Install dashboard extras with: python -m pip install -e '.[dashboard]'")
        return

    st.set_page_config(
        page_title="PromoGuard Retail Intelligence",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_reviewer_style()
    st.markdown(
        """
        <div class="pg-brand">
          <div class="pg-brand-mark">P</div>
          <div><div class="pg-brand-name">PromoGuard</div><div class="pg-brand-sub">Retail intelligence</div></div>
        </div>
        <div class="pg-hero">
          <div class="pg-kicker">Evidence-aware retail intelligence</div>
          <h1>PromoGuard Retail Intelligence</h1>
          <p>تحلیل قابل ممیزی پروموشن خرده فروشی با داده واقعی و تصمیم گیری مسئولانه</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    mode = st.sidebar.radio(
        "حالت اجرا",
        ["دموی داور", "تحلیل دستی"],
        index=0,
    )
    st.markdown(
        '<div class="pg-boundary"><strong>دامنه تصمیم:</strong> این ابزار برای غربالگری اولیه، '
        'کنترل کیفیت داده و طراحی آزمایش است؛ سود قطعی یا رابطه علّی را ادعا نمی کند.</div>',
        unsafe_allow_html=True,
    )
    if mode == "دموی داور":
        _demo_workflow()
        return

    source = st.radio(
        "منبع داده",
        [
            "پنل واقعی موجود در پروژه",
            "آپلود پنل استاندارد CSV",
            "بررسی آمادگی فایل شریک",
        ],
        horizontal=True,
    )
    if source == "بررسی آمادگی فایل شریک":
        _partner_intake_workflow()
        return
    panel: pd.DataFrame | None = None
    try:
        if source == "پنل واقعی موجود در پروژه":
            local_path = st.text_input("مسیر پنل", value=str(DEFAULT_PANEL_PATH))
            if st.button("بارگذاری و کنترل کیفیت", type="primary"):
                st.session_state["panel"] = _load_local_panel(local_path)
                st.session_state["panel_source"] = local_path
        else:
            upload = st.file_uploader("weekly_panel.csv را انتخاب کنید", type=["csv"])
            if upload is not None and st.button("کنترل فایل آپلودشده", type="primary"):
                st.session_state["panel"] = _load_uploaded_panel(upload.name, upload.getvalue())
                st.session_state["panel_source"] = upload.name
        panel = st.session_state.get("panel")
    except (FileNotFoundError, ValueError) as error:
        st.error(str(error))

    if panel is None:
        st.info("برای شروع، پنل واقعی پروژه را بارگذاری کنید.")
        return

    report = validate_canonical_panel(panel, max_rows=MAX_PANEL_ROWS)
    _show_quality_report(report)
    if not report["valid"]:
        st.error("تا زمانی که خطاهای کیفیت رفع نشوند، ممیزی اجرا نمی‌شود.")
        return

    try:
        events = _episodes(panel)
        if events.empty:
            st.warning("هیچ دوره پروموشنی در پنل پیدا نشد.")
            return
        representative = _representative_event(panel)
    except ValueError as error:
        st.error(str(error))
        return

    st.subheader("انتخاب پروموشن")
    eligible_start = pd.Timestamp(representative["start_date"])
    default_matches = events.index[
        events["store_id"].eq(representative["store_id"])
        & events["upc"].eq(representative["upc"])
        & events["start_date"].eq(eligible_start)
    ]
    default_index = int(default_matches[0]) if len(default_matches) else 0
    visible_events = events.head(500).copy()
    if default_index not in visible_events.index:
        visible_events = pd.concat([events.loc[[default_index]], visible_events]).drop_duplicates(
            "audit_id"
        )
    event_records = visible_events.to_dict(orient="records")
    selected = st.selectbox(
        "رویداد",
        event_records,
        index=next(
            (
                index
                for index, event in enumerate(event_records)
                if event["audit_id"] == representative["audit_id"]
            ),
            0,
        ),
        format_func=lambda event: _event_label(pd.Series(event)),
        help="برای حفظ سرعت، حداکثر ۵۰۰ رویداد نخست به‌علاوه رویداد نماینده نمایش داده می‌شود.",
    )
    include_contribution = st.checkbox("تحلیل حساسیت سهم فرضی هر واحد را نمایش بده")
    contribution_assumption = None
    contribution_input_valid = True
    if include_contribution:
        contribution_amount = st.number_input(
            "سهم فرضی هر واحد افزوده‌شده", value=1.0, step=0.1
        )
        contribution_currency = st.text_input("کد ارز سه‌حرفی", value="IRR")
        contribution_source = st.text_input(
            "منبع این فرض", value="ورودی تأییدشده کاربر برای تحلیل حساسیت"
        )
        try:
            contribution_assumption = ContributionAssumption(
                amount_per_incremental_unit=contribution_amount,
                currency=contribution_currency,
                source=contribution_source,
            )
        except ValueError as error:
            contribution_input_valid = False
            st.error(str(error))
    if st.button("اجرای ممیزی", type="primary", disabled=not contribution_input_valid):
        try:
            result = audit_promotion_event(
                panel,
                store_id=str(selected["store_id"]),
                upc=str(selected["upc"]),
                start_date=selected["start_date"],
                contribution_assumption=contribution_assumption,
            )
            _show_audit(result)
        except ValueError as error:
            st.error(str(error))


if __name__ == "__main__":
    main()
