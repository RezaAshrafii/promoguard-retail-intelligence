"""Streamlit adapter for the deterministic PromoGuard promotion audit."""

from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

# Streamlit executes this file as a script, so the repository root is not
# guaranteed to be on sys.path when the entrypoint is passed by file path.
# Add it before importing the sibling `apps` package.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from apps.dashboard.presentation import (
    audit_comparison_records,
    audit_event_summary,
    claim_boundary_copy,
    demo_mode_requested,
    recommendation_presentation,
    warning_presentation_records,
)
from promoguard.data.panel import load_weekly_panel, validate_canonical_panel
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


def _apply_reviewer_style() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stMainBlockContainer"] p,
        [data-testid="stSidebarContent"] p,
        [data-testid="stWidgetLabel"] {
            direction: rtl;
            text-align: right;
        }
        [data-testid="stMetric"], [data-testid="stAlert"] { direction: rtl; text-align: right; }
        .stButton > button[kind="primary"] {
            background: #4f46e5;
            border-color: #4f46e5;
            color: white;
        }
        .pg-hero {
            padding: 1.1rem 1.3rem;
            border: 1px solid rgba(99, 102, 241, 0.28);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(49, 46, 129, 0.82));
            color: white;
            margin-bottom: 1rem;
        }
        .pg-hero h1 {
            direction: ltr;
            unicode-bidi: isolate;
            text-align: left;
            margin: 0 0 .35rem 0;
            font-size: 2rem;
        }
        .pg-hero p { direction: rtl; text-align: right; margin: 0; opacity: .9; }
        .pg-step {
            direction: rtl;
            display: inline-block;
            padding: .28rem .7rem;
            border-radius: 999px;
            background: rgba(99, 102, 241, .12);
            color: rgb(79, 70, 229);
            font-weight: 700;
            margin: .5rem 0;
        }
        .pg-boundary {
            padding: .8rem 1rem;
            border-right: 4px solid #f59e0b;
            background: rgba(245, 158, 11, .08);
            border-radius: 10px;
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

    @st.cache_data(show_spinner="در حال بارگذاری پنل واقعی فروش...")
    def _load_local_panel(path: str) -> pd.DataFrame:
        return load_weekly_panel(path, max_bytes=MAX_UPLOAD_BYTES)

    @st.cache_data(show_spinner="در حال شناسایی دوره‌های پروموشن...")
    def _episodes(panel: pd.DataFrame) -> pd.DataFrame:
        return detect_promotion_episodes(panel)

    @st.cache_data(show_spinner="در حال انتخاب یک رویداد قابل‌ممیزی...")
    def _representative_event(panel: pd.DataFrame) -> dict[str, Any]:
        return select_representative_event(panel)


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
        "تاریخ نامعتبر": report["date_parse_errors"],
        "شناسه فروشگاه خالی": report["missing_store_id_rows"],
        "شناسه کالا خالی": report["missing_upc_rows"],
        "فروش منفی": report["negative_units_rows"],
        "فروش خالی": report["missing_units_rows"],
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


def main() -> None:
    if st is None:  # pragma: no cover
        print("Install dashboard extras with: python -m pip install -e '.[dashboard]'")
        return

    launch_in_demo = demo_mode_requested(sys.argv)
    st.set_page_config(
        page_title="PromoGuard Retail Intelligence",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="collapsed" if launch_in_demo else "expanded",
    )
    _apply_reviewer_style()
    st.markdown(
        """
        <div class="pg-hero">
          <h1>PromoGuard Retail Intelligence</h1>
          <p>غربالگری قابل‌ممیزی پروموشن خرده‌فروشی با داده واقعی و خروجی abstention-first</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    mode = st.sidebar.radio(
        "حالت اجرا",
        ["دموی داور", "تحلیل دستی"],
        index=0 if launch_in_demo else 1,
    )
    st.warning(
        "این ابزار رابطه علّی یا سود قطعی را ادعا نمی‌کند؛ خروجی برای تصمیم اولیه و طراحی آزمایش است."
    )
    if mode == "دموی داور":
        _demo_workflow()
        return

    source = st.radio(
        "منبع داده",
        ["پنل واقعی موجود در پروژه", "آپلود پنل استاندارد CSV"],
        horizontal=True,
    )
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
            st.error(str(error))
    if st.button("اجرای ممیزی", type="primary"):
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
