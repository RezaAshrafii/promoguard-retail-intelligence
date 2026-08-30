"""Streamlit adapter for the deterministic PromoGuard promotion audit."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from promoguard.data.panel import load_weekly_panel, validate_canonical_panel
from promoguard.insights.promotion_audit import (
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
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PANEL_PATH = REPOSITORY_ROOT / "data" / "processed" / "breakfast-at-the-frat"


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


def _show_audit(result: PromotionAuditResult) -> None:
    decision_labels = {
        "approve": "پایلوت کنترل‌شده قابل بررسی است",
        "reject": "برای ادامه پیشنهاد نمی‌شود",
        "experiment": "ابتدا آزمایش کنترل‌شده لازم است",
    }
    payload = result.model_dump(mode="json")
    st.subheader("نتیجه ممیزی")
    st.info(decision_labels[result.decision.value])
    st.caption(result.decision_rationale)
    observed, baseline, incremental = st.columns(3)
    observed.metric("فروش مشاهده‌شده", f"{result.observed_units:,.0f} واحد")
    baseline.metric(
        "فروش مبنا",
        f"{result.baseline_units.point:,.0f} واحد",
        help=(
            f"بازه عدم‌قطعیت: {result.baseline_units.lower:,.0f} تا "
            f"{result.baseline_units.upper:,.0f}"
        ),
    )
    incremental.metric(
        "تفاوت مشاهده‌شده با مبنا",
        f"{result.incremental_units.point:+,.0f} واحد",
        help=(
            f"بازه عدم‌قطعیت: {result.incremental_units.lower:+,.0f} تا "
            f"{result.incremental_units.upper:+,.0f}"
        ),
    )

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
    st.dataframe(pd.DataFrame(window_rows), hide_index=True, width="stretch")

    st.subheader("هشدارها و مرز ادعا")
    warnings = [warning.model_dump(mode="json") for warning in result.warnings]
    if warnings:
        st.dataframe(pd.DataFrame(warnings), hide_index=True, width="stretch")
    st.warning(result.claim_language)
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


def main() -> None:
    if st is None:  # pragma: no cover
        print("Install dashboard extras with: python -m pip install -e '.[dashboard]'")
        return

    st.set_page_config(page_title="PromoGuard Retail Intelligence", page_icon="🛡️", layout="wide")
    st.title("PromoGuard Retail Intelligence")
    st.caption("غربالگری قابل‌ممیزی پروموشن‌های خرده‌فروشی بر پایه داده واقعی")
    st.warning(
        "این ابزار رابطه علّی یا سود قطعی را ادعا نمی‌کند؛ خروجی برای تصمیم اولیه و طراحی آزمایش است."
    )

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
    include_margin = st.checkbox("سناریوی حاشیه سود واحد را هم بررسی کن")
    unit_margin = (
        st.number_input("حاشیه سود هر واحد", min_value=0.01, value=1.0, step=0.1)
        if include_margin
        else None
    )
    if st.button("اجرای ممیزی", type="primary"):
        try:
            result = audit_promotion_event(
                panel,
                store_id=str(selected["store_id"]),
                upc=str(selected["upc"]),
                start_date=selected["start_date"],
                unit_margin=unit_margin,
            )
            _show_audit(result)
        except ValueError as error:
            st.error(str(error))


if __name__ == "__main__":
    main()
