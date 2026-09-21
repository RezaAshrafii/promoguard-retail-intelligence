"""Streamlit adapter for the deterministic PromoGuard promotion audit."""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pydantic import ValidationError

# Streamlit executes this file as a script, so the repository root is not
# guaranteed to be on sys.path when the entrypoint is passed by file path.
# Add it before importing the sibling `apps` package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from apps.dashboard.presentation import (
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
from promoguard.data.intake import assess_partner_intake
from promoguard.data.panel import load_weekly_panel, validate_canonical_panel
from promoguard.data.partner import (
    PartnerExportContract,
    PartnerPrepared,
    prepare_partner_export,
    sha256_bytes,
)
from promoguard.insights.promotion_audit import (
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
        :root {
            --pg-ink: #10222d;
            --pg-muted: #738996;
            --pg-blue: #11bfae;
            --pg-blue-soft: #e6faf6;
            --pg-green: #18bf89;
            --pg-amber: #b87913;
            --pg-border: #e4e8f0;
            --pg-surface: #ffffff;
            --pg-canvas: #f3f7f8;
        }
        [data-testid="stAppViewContainer"] { background: var(--pg-canvas); }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] {
            background: #111c31;
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
            background: var(--pg-surface);
            border: 1px solid var(--pg-border);
            border-radius: 12px;
            padding: .75rem .9rem;
            box-shadow: 0 6px 18px rgba(20, 35, 59, .035);
            min-height: 104px;
        }
        .stButton > button {
            border-radius: 9px;
            min-height: 2.55rem;
            font-weight: 700;
            transition: all .18s ease;
        }
        .stButton > button[kind="primary"] {
            background: var(--pg-blue);
            border-color: var(--pg-blue);
            color: white;
            box-shadow: 0 7px 16px rgba(49, 92, 222, .2);
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
            border: 1px solid var(--pg-border);
            border-radius: 10px;
            background: var(--pg-surface);
        }
        .pg-brand {
            display: flex; align-items: center; gap: .65rem;
            direction: ltr; margin: .35rem 0 1.5rem;
        }
        .pg-brand-mark {
            width: 36px; height: 36px; display: grid; place-items: center;
            border-radius: 12px; background: linear-gradient(135deg,#149df0,#18d6b0); color: #06171c;
            font-weight: 900; box-shadow: 0 7px 16px rgba(49,92,222,.25);
        }
        .pg-brand-name { color: #f8fafc; font-weight: 800; letter-spacing: -.02em; }
        .pg-brand-sub { color: #a7b4ca; font-size: .76rem; }
        .pg-sidebar-caption { color: #a7b4ca; font-size: .76rem; line-height: 1.8; direction: rtl; text-align: right; }
        .pg-shell-label {
            color: var(--pg-blue); font-size: .72rem; font-weight: 800;
            letter-spacing: .08em; direction: rtl; text-align: right;
        }
        .pg-hero {
            padding: .45rem 0 .9rem;
            color: var(--pg-ink);
            margin: .2rem 0 .7rem;
        }
        .pg-hero h1 {
            direction: rtl;
            unicode-bidi: isolate;
            text-align: right;
            margin: 0 0 .35rem 0;
            font-size: clamp(1.45rem, 4vw, 2rem);
            letter-spacing: -.045em;
            color: var(--pg-ink);
            overflow-wrap: anywhere;
        }
        .pg-hero p { direction: rtl; text-align: right; margin: 0; color: var(--pg-muted); font-size: .93rem; }
        .pg-hero .pg-kicker { direction: rtl; color: var(--pg-blue); font-size: .72rem;
            font-weight: 800; margin-bottom: .5rem; }
        .pg-header-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; direction: rtl; }
        .pg-header-meta { color: var(--pg-muted); font-size: .78rem; direction: rtl; text-align: right; }
        .pg-status-strip { padding: .75rem 1rem; background: #fff8e8; color: #725018; border: 1px solid #f4dfad; border-radius: 9px; direction: rtl; text-align: right; margin: .35rem 0 1.1rem; }
        .pg-empty { padding: 1.5rem; background: var(--pg-surface); border: 1px solid var(--pg-border); border-radius: 12px; direction: rtl; text-align: right; }
        .pg-empty-title { color: var(--pg-ink); font-size: 1.05rem; font-weight: 800; margin-bottom: .35rem; }
        .pg-empty-copy { color: var(--pg-muted); line-height: 1.9; }
        .pg-card-title { color: var(--pg-ink); font-size: 1rem; font-weight: 800; direction: rtl; text-align: right; margin-bottom: .2rem; }
        .pg-card-copy { color: var(--pg-muted); font-size: .82rem; line-height: 1.8; direction: rtl; text-align: right; }
        .pg-insight { padding: .7rem .8rem; border: 1px solid var(--pg-border); border-radius: 9px; background: #fff; direction: rtl; text-align: right; margin-bottom: .55rem; }
        .pg-insight strong { color: var(--pg-ink); display: block; margin-bottom: .2rem; }
        .pg-insight span { color: var(--pg-muted); font-size: .8rem; line-height: 1.7; }
        .pg-kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem; direction: rtl; margin: .4rem 0 1rem; }
        .pg-kpi { background: var(--pg-surface); border: 1px solid var(--pg-border); border-radius: 12px; padding: .85rem 1rem; min-height: 104px; box-shadow: 0 6px 18px rgba(20,35,59,.035); direction: rtl; text-align: right; }
        .pg-kpi-label { color: var(--pg-muted); font-size: .78rem; margin-bottom: .55rem; }
        .pg-kpi-value { color: var(--pg-ink); font-size: 1.42rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.2; }
        .pg-kpi-note { color: var(--pg-muted); font-size: .72rem; margin-top: .35rem; }
        .pg-kpi-positive .pg-kpi-value { color: var(--pg-green); }
        .pg-kpi-warning .pg-kpi-value { color: var(--pg-amber); }
        .pg-panel { background: var(--pg-surface); border: 1px solid var(--pg-border); border-radius: 12px; padding: 1rem; box-shadow: 0 6px 18px rgba(20,35,59,.035); direction: rtl; text-align: right; }
        .pg-panel-title { color: var(--pg-ink); font-size: 1rem; font-weight: 800; margin-bottom: .2rem; }
        .pg-panel-subtitle { color: var(--pg-muted); font-size: .78rem; line-height: 1.8; margin-bottom: .7rem; }
        .pg-finding { display: flex; align-items: flex-start; gap: .65rem; padding: .65rem 0; border-bottom: 1px solid #eef1f5; direction: rtl; }
        .pg-finding:last-child { border-bottom: 0; }
        .pg-finding-icon { width: 28px; height: 28px; flex: 0 0 28px; display: grid; place-items: center; border-radius: 8px; background: var(--pg-blue-soft); color: var(--pg-blue); font-weight: 800; }
        .pg-finding strong { display: block; color: var(--pg-ink); font-size: .83rem; margin-bottom: .15rem; }
        .pg-finding span { color: var(--pg-muted); font-size: .76rem; line-height: 1.75; }
        .pg-next-action { display: flex; gap: .65rem; align-items: center; margin-top: .75rem; padding: .75rem; border: 1px solid #dce7ff; background: #f1f5ff; border-radius: 9px; direction: rtl; }
        .pg-next-action strong { display: block; color: var(--pg-ink); font-size: .82rem; }
        .pg-next-action span { display: block; color: var(--pg-muted); font-size: .75rem; line-height: 1.7; }
        .pg-section-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; direction: rtl; margin: 1rem 0 .45rem; }
        .pg-section-heading strong { color: var(--pg-ink); font-size: 1rem; }
        .pg-section-heading span { color: var(--pg-muted); font-size: .75rem; }
        @media (max-width: 900px) { .pg-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 560px) { .pg-kpi-grid { grid-template-columns: 1fr; } }
        .pg-step {
            direction: rtl;
            display: inline-block;
            padding: .32rem .7rem;
            border-radius: 999px;
            background: var(--pg-blue-soft);
            color: var(--pg-blue);
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
        .pg-wizard {
            display: flex; gap: .55rem; margin: .75rem 0 1.1rem;
            direction: rtl;
        }
        .pg-wizard-step {
            flex: 1; min-height: 58px; padding: .7rem .8rem;
            border: 1px solid #e1e7f2; border-radius: 13px;
            background: #ffffff; color: #64748b; direction: rtl;
            box-shadow: 0 4px 12px rgba(22, 34, 64, .035);
        }
        .pg-wizard-step.is-active {
            border-color: #3157d5; background: #eef3ff; color: #3157d5;
        }
        .pg-wizard-step.is-done {
            border-color: #b7ead2; background: #ecfdf5; color: #10734b;
        }
        .pg-wizard-index { font-weight: 900; margin-left: .35rem; }
        .pg-wizard-label { font-weight: 750; font-size: .88rem; }
        .pg-section-note {
            color: #64748b; font-size: .88rem; line-height: 1.8;
            margin-top: -.45rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _sidebar_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="pg-brand">
          <div class="pg-brand-mark">P</div>
          <div><div class="pg-brand-name">PromoGuard</div><div class="pg-brand-sub">Retail intelligence</div></div>
        </div>
        <div class="pg-sidebar-caption">تحلیل دادهٔ فروش و ممیزی پروموشن برای تصمیم‌های قابل بررسی</div>
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
    status_method(f"کنترل داده: {status_label}")
    first, second, third, fourth = st.columns(4)
    first.metric("تعداد ردیف", f"{report['rows']:,}", border=True)
    second.metric("سری فروشگاه–کالا", f"{(report['series'] or 0):,}", border=True)
    third.metric("هفته‌های پروموشن", f"{(report['promotion_rows'] or 0):,}", border=True)
    fourth.metric("ردیف تکراری", f"{(report['duplicate_grain_rows'] or 0):,}", border=True)
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
        st.success("فایل برای بررسی مشاهده‌ای آماده است")
    else:
        st.error("فایل هنوز برای بررسی آماده نیست")
    first, second, third = st.columns(3)
    first.metric("تعداد ردیف", f"{report.rows:,}", border=True)
    second.metric("نتیجهٔ کنترل", report.intake_status, border=True)
    third.metric("مدت نگهداری", f"{report.retention_days} روز", border=True)
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
        "دریافت گزارش آمادگی",
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
    """Collect a declared partner contract through a guided readiness wizard."""

    step = int(st.session_state.get("partner_wizard_step", 1))
    stored = st.session_state.get("partner_readiness")
    labels = [(1, "آپلود فایل"), (2, "قرارداد داده"), (3, "گزارش آمادگی")]
    wizard_html = '<div class="pg-wizard">'
    for number, label in labels:
        state = "is-active" if number == step else ("is-done" if number < step else "")
        wizard_html += (
            f'<div class="pg-wizard-step {state}">'
            f'<span class="pg-wizard-index">{number}</span>'
            f'<span class="pg-wizard-label">{label}</span></div>'
        )
    st.markdown(wizard_html + "</div>", unsafe_allow_html=True)

    upload = st.file_uploader(
        "فایل CSV شریک را انتخاب کنید",
        type=["csv"],
        key="partner_file_upload",
        help="فایل خام شریک در Git ذخیره نمی‌شود و این مسیر تحلیل اقتصادی یا علّی انجام نمی‌دهد.",
    )
    if upload is not None:
        content = upload.getvalue()
        try:
            frame = _load_uploaded_panel(upload.name, content)
        except ValueError as error:
            st.error(str(error))
            return
        st.session_state["partner_upload"] = {
            "name": upload.name,
            "content": content,
            "frame": frame,
        }

    upload_state = st.session_state.get("partner_upload")
    if step == 1:
        with st.container(border=True):
            st.subheader("۱. فایل منبع")
            st.markdown(
                '<div class="pg-section-note">یک خروجی CSV واقعی از فروش، کالا، فروشگاه و پروموشن انتخاب کنید. '
                "فایل هنوز تحلیل اقتصادی نمی‌شود؛ فقط برای کنترل ساختار آماده می‌شود.</div>",
                unsafe_allow_html=True,
            )
            if upload_state is None:
                st.info("برای شروع یک CSV شامل تاریخ، فروشگاه، کالا، واحد فروش و نشانهٔ پروموشن بدهید.")
            else:
                st.success(f"فایل آماده است: {upload_state['name']} | {len(upload_state['frame']):,} ردیف")
                if st.button("ادامه به قرارداد داده", type="primary", width="stretch", key="partner_next_contract"):
                    st.session_state["partner_wizard_step"] = 2
                    st.rerun()
        return

    if upload_state is None:
        st.warning("ابتدا فایل CSV را در مرحلهٔ اول انتخاب کنید.")
        if st.button("بازگشت به آپلود فایل", key="partner_back_to_upload"):
            st.session_state["partner_wizard_step"] = 1
            st.rerun()
        return

    if step == 2:
        if st.button("بازگشت به آپلود فایل", key="partner_back_upload"):
            st.session_state["partner_wizard_step"] = 1
            st.rerun()
        with st.container(border=True):
            st.subheader("۲. قرارداد داده")
            st.markdown(
                '<div class="pg-section-note">این بخش مشخص می‌کند داده از کجا آمده، چه معنایی دارد و تا چه زمانی '
                "اجازهٔ نگهداری آن را داریم. بدون این اطلاعات، گزارش قابل اتکا نیست.</div>",
                unsafe_allow_html=True,
            )
            with st.form("partner_intake_contract"):
                first, second = st.columns(2)
                with first:
                    source_id = st.text_input("شناسه منبع", value="partner-export-01")
                    data_owner = st.text_input("مالک داده", value="نام شرکت یا واحد مالک داده")
                    permission_reference = st.text_input(
                        "مرجع اجازه استفاده", value="شناسه قرارداد یا ایمیل تأیید"
                    )
                    extraction_date = st.date_input(
                        "تاریخ استخراج", value=datetime.now(UTC).date()
                    )
                    grain_label = st.selectbox("دانه‌بندی فایل", ["هفتگی فروشگاه–کالا", "روزانه فروشگاه–کالا"])
                with second:
                    retention_days = st.number_input("مدت نگهداری توافق‌شده به روز", min_value=1, max_value=365, value=30)
                    calendar_reference = st.text_input("مرجع تقویم و timezone", value="تقویم و timezone اعلام‌شده توسط مالک داده")
                    units_definition = st.text_input("تعریف واحد فروش", value="تعداد واحد فروخته‌شده")
                    zero_label = st.selectbox("معنی مقدار صفر فروش", ["فروش واقعی صفر", "نامعلوم یا احتمالاً گمشده"])
                    promotion_definition = st.text_input("تعریف promotion flag", value="پرچم تأییدشدهٔ اجرای پروموشن")
                submitted = st.form_submit_button("اجرای کنترل آمادگی", type="primary", width="stretch")
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
                    upload_state["frame"], contract, source_sha256=sha256_bytes(upload_state["content"])
                )
                st.session_state["partner_readiness"] = {
                    "report": report,
                    "intake": assess_partner_intake(upload_state["frame"]),
                }
                st.session_state["partner_wizard_step"] = 3
                st.rerun()
            except (ValidationError, ValueError) as error:
                st.error(f"قرارداد یا فایل قابل قبول نیست: {error}")
        return

    if stored is None:
        st.warning("هنوز گزارشی ساخته نشده است. به مرحلهٔ قرارداد برگردید.")
        if st.button("بازگشت به قرارداد داده", key="partner_back_contract"):
            st.session_state["partner_wizard_step"] = 2
            st.rerun()
        return

    with st.container(border=True):
        st.subheader("۳. گزارش آمادگی")
        st.markdown(
            '<div class="pg-section-note">این گزارش فقط می‌گوید فایل برای ممیزی مشاهده‌ای آماده هست یا نه؛ '
            "هیچ تضمینی دربارهٔ سود، اثر علّی یا نتیجهٔ بازار نمی‌دهد.</div>",
            unsafe_allow_html=True,
        )
        _show_partner_readiness(stored["report"], stored["intake"])
        if st.button("بررسی فایل جدید", key="partner_new_file", width="stretch"):
            for key in ("partner_readiness", "partner_upload"):
                st.session_state.pop(key, None)
            st.session_state["partner_wizard_step"] = 1
            st.rerun()


def _event_label(row: pd.Series) -> str:
    start = pd.Timestamp(row["start_date"]).date().isoformat()
    return f"فروشگاه {row['store_id']} | UPC {row['upc']} | شروع {start}"


def _trend_frame(panel: pd.DataFrame, result: PromotionAuditResult) -> pd.DataFrame:
    """Build a manager-facing trend view from the already validated panel."""
    prepared = panel[
        panel["store_id"].astype(str).eq(str(result.store_id))
        & panel["upc"].astype(str).eq(str(result.upc))
    ].copy()
    prepared["week_end_date"] = pd.to_datetime(prepared["week_end_date"])
    start = pd.Timestamp(result.start_date) - pd.Timedelta(weeks=8)
    end = pd.Timestamp(result.end_date) + pd.Timedelta(weeks=8)
    prepared = prepared[prepared["week_end_date"].between(start, end)].copy()
    prepared["فروش"] = pd.to_numeric(prepared["units"], errors="coerce")
    prepared["خط مبنا"] = result.baseline_units.point / max(result.duration_weeks, 1)
    prepared["پروموشن"] = prepared["promotion_flag"].eq(1).map({True: "حین پروموشن", False: "عادی"})
    return prepared.rename(columns={"week_end_date": "تاریخ"})[["تاریخ", "فروش", "خط مبنا", "پروموشن"]]


def _show_executive_summary(result: PromotionAuditResult) -> None:
    """Render the first screen a sales manager needs before technical details."""
    difference = result.estimated_units_difference_vs_baseline
    baseline = result.baseline_units.point
    delta_pct = (difference.point / baseline * 100) if baseline else 0.0
    recommendation = recommendation_presentation(result.recommendation)
    status_label = "نیاز به بررسی بیشتر" if result.recommendation == "needs_more_evidence" else recommendation.title
    status_class = "pg-kpi-warning" if result.recommendation == "needs_more_evidence" else "pg-kpi-positive"
    st.markdown(
        f"""
        <div class="pg-section-heading"><strong>خلاصه برای مدیر فروش</strong><span>رویداد انتخاب‌شده با قانون ثابت</span></div>
        <div class="pg-kpi-grid">
          <div class="pg-kpi"><div class="pg-kpi-label">فروش در زمان پروموشن</div><div class="pg-kpi-value">{result.observed_units:,.0f}</div><div class="pg-kpi-note">واحد فروش</div></div>
          <div class="pg-kpi"><div class="pg-kpi-label">فروش معمول در همان مدت</div><div class="pg-kpi-value">{baseline:,.0f}</div><div class="pg-kpi-note">خط مبنای قبل از رویداد</div></div>
          <div class="pg-kpi"><div class="pg-kpi-label">تفاوت با خط مبنا</div><div class="pg-kpi-value">{difference.point:+,.0f}</div><div class="pg-kpi-note">{delta_pct:+.1f}% نسبت به خط مبنا</div></div>
          <div class="pg-kpi {status_class}"><div class="pg-kpi-label">نتیجهٔ فعلی</div><div class="pg-kpi-value">{status_label}</div><div class="pg-kpi-note">این نتیجه مجوز اجرای کمپین نیست</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_manager_findings(result: PromotionAuditResult) -> None:
    warning_text = {item["کد"]: item["معنی برای تصمیم"] for item in warning_presentation_records(result)}
    findings: list[tuple[str, str, str]] = []
    if result.observed_units < result.baseline_units.point:
        findings.append(("!", "فروش از خط مبنا پایین‌تر است", "در این اجرا، فروش مشاهده‌شده کمتر از فروش معمول برآوردشده بوده است."))
    else:
        findings.append(("✓", "فروش از خط مبنا بالاتر است", "این نشانه فقط برای اولویت‌بندی یک بررسی کنترل‌شده استفاده می‌شود."))
    if "FORWARD_BUY_RISK" in warning_text:
        findings.append(("!", "احتمال جابه‌جایی زمان خرید", warning_text["FORWARD_BUY_RISK"]))
    if "STOCKOUT_UNOBSERVABLE" in warning_text:
        findings.append(("i", "وضعیت موجودی مشخص نیست", "بدون دادهٔ موجودی، نمی‌توان فهمید افت فروش از کمبود کالا بوده یا کاهش تقاضا."))
    if "CANNIBALIZATION_CANDIDATE" in warning_text:
        findings.append(("!", "افت کالای هم‌دسته دیده شده", "قبل از نتیجه‌گیری دربارهٔ فروش افزایشی، کالاهای هم‌دسته باید بررسی شوند."))
    if not findings:
        findings.append(("i", "هشدار مسدودکننده‌ای ثبت نشده است", "برای تصمیم نهایی، محدودیت‌های داده همچنان باید بررسی شوند."))
    cards = "".join(
        f'<div class="pg-finding"><div class="pg-finding-icon">{icon}</div><div><strong>{title}</strong><span>{detail}</span></div></div>'
        for icon, title, detail in findings[:4]
    )
    st.markdown(
        f"""
        <div class="pg-panel">
          <div class="pg-panel-title">یافته‌ها و شواهد</div>
          <div class="pg-panel-subtitle">این بخش به زبان تصمیم توضیح می‌دهد چه چیزی دیده شده و چه چیزی هنوز قابل اثبات نیست.</div>
          {cards}
          <div class="pg-next-action"><div class="pg-finding-icon">→</div><div><strong>اقدام بعدی</strong><span>قبل از افزایش بودجه، دادهٔ موجودی و نتیجهٔ یک آزمون کنترل‌شده را بررسی کنید.</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _show_audit(
    result: PromotionAuditResult,
    *,
    compact_demo: bool = False,
    panel: pd.DataFrame | None = None,
) -> None:
    payload = result.model_dump(mode="json")
    _show_executive_summary(result)
    chart_column, findings_column = st.columns([1.65, 1], gap="medium")
    with chart_column, st.container(border=True):
        st.markdown('<div class="pg-panel-title">روند فروش</div>', unsafe_allow_html=True)
        st.markdown('<div class="pg-panel-subtitle">مقایسهٔ فروش هفتگی با خط مبنای همان رویداد</div>', unsafe_allow_html=True)
        if panel is not None:
            trend = _trend_frame(panel, result)
            if not trend.empty:
                st.line_chart(trend.set_index("تاریخ")[["فروش", "خط مبنا"]], height=285, width="stretch")
        else:
            st.vega_lite_chart(
                pd.DataFrame(audit_comparison_records(result)),
                {"mark": "bar", "encoding": {"x": {"field": "value", "type": "quantitative"}, "y": {"field": "label", "type": "nominal"}}},
                width="stretch",
            )
        st.caption("خط مبنا تخمینی است و به‌تنهایی اثر علّی یا سود کمپین را ثابت نمی‌کند.")
    with findings_column:
        _show_manager_findings(result)

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
    with st.expander("جزئیات دوره‌های قبل، حین و بعد", expanded=not compact_demo):
        st.dataframe(pd.DataFrame(window_rows), hide_index=True, width="stretch")

    st.subheader("بررسی کالاهای هم‌دسته")
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

    st.subheader("جزئیات هشدارها و محدودهٔ نتیجه")
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
        "دریافت گزارش کامل",
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
    st.sidebar.success("دمو آمادهٔ اجراست")
    st.sidebar.caption("دادهٔ واقعی عمومی، بدون API خارجی و بدون دادهٔ ساختگی")

    st.markdown(
        '<div class="pg-header-row">'
        '<div><div class="pg-shell-label">دموی داور</div>'
        '<div class="pg-hero"><h1>بررسی عملکرد پروموشن</h1>'
        '<p>یک نمونهٔ واقعی از کنترل کیفیت، مقایسه با خط مبنا و ثبت شواهد</p></div></div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="pg-status-strip"><strong>محدودهٔ این دمو:</strong> '
        'نتیجه برای اولویت‌بندی بررسی و طراحی آزمون است؛ تأیید سود یا اثر علّی نیست.</div>',
        unsafe_allow_html=True,
    )
    _step(1, "داده و کنترل کیفیت")
    st.caption("منبع: دیتاست عمومی dunnhumby — فایل خام داخل Git نگهداری نمی‌شود.")
    run_label = (
        "اجرای دوبارهٔ بررسی"
        if "reviewer_demo" in st.session_state
        else "اجرای بررسی"
    )
    if st.button(run_label, type="primary", width="stretch", icon=":material/play_arrow:"):
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
        st.markdown(
            '<div class="pg-empty">'
            '<div class="pg-empty-title">گزارش هنوز اجرا نشده است</div>'
            '<div class="pg-empty-copy">با اجرای بررسی، دادهٔ واقعی کنترل می‌شود و یک رویداد واجدشرایط '
            'برای نمایش نتیجه انتخاب خواهد شد. انتخاب رویداد دستی نیست و از قانون ثابت استفاده می‌کند.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    st.progress(100, text="داده کنترل شد")
    _show_quality_report(demo["quality"])
    if demo["result"] is None:
        st.error("کنترل کیفیت رد شد؛ ممیزی برای جلوگیری از خروجی نامعتبر اجرا نشد.")
        return

    result: PromotionAuditResult = demo["result"]
    _step(2, "رویداد انتخاب‌شده")
    st.caption(
        f"سیستم رویدادی را انتخاب می‌کند که حداقل "
        f"{result.policy.representative_min_history_weeks} هفته تاریخچه و پنجره پس از پروموشن "
        "کامل داشته باشد؛ انتخاب دستی در این حالت انجام نمی‌شود."
    )
    columns = st.columns(4)
    for column, (label, value) in zip(columns, audit_event_summary(result), strict=True):
        column.metric(label, value)

    _step(3, "نتیجه و محدودهٔ تصمیم")
    _show_audit(result, compact_demo=True, panel=panel)
    _show_randomized_benchmark()


def main() -> None:
    if st is None:  # pragma: no cover
        print("Install dashboard extras with: python -m pip install -e '.[dashboard]'")
        return

    st.set_page_config(
        page_title="PromoGuard Retail Intelligence",
        page_icon=":material/analytics:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _apply_reviewer_style()
    _sidebar_brand()
    st.sidebar.markdown("---")
    st.sidebar.caption("مسیرهای اصلی")
    st.markdown(
        """
        <div class="pg-hero">
          <div class="pg-shell-label">پشتیبانی از تصمیم‌های فروش</div>
          <h1>PromoGuard</h1>
          <p>کنترل داده و بررسی پروموشن برای تیم‌هایی که می‌خواهند قبل از تصمیم، شواهد را ببینند.</p>
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
        '<div class="pg-status-strip"><strong>محدودهٔ محصول:</strong> '
        'کنترل کیفیت، ممیزی مشاهده‌ای و آماده‌سازی تصمیم؛ بدون ادعای سود قطعی یا اثر علّی.</div>',
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
            _show_audit(result, panel=panel)
        except ValueError as error:
            st.error(str(error))


if __name__ == "__main__":
    main()
