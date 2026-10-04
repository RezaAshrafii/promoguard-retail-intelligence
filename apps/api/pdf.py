"""Persian, evidence-bounded PDF export for completed promotion reports."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = ROOT / "assets" / "fonts" / "Vazirmatn"
INK = colors.HexColor("#10222D")
TEAL = colors.HexColor("#00BDAA")
MUTED = colors.HexColor("#697D88")
LINE = colors.HexColor("#DCE7E8")
PALE = colors.HexColor("#EFF8F6")


def _rtl(value: object) -> str:
    return get_display(arabic_reshaper.reshape(str(value)))


def _number(value: object, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{number:,.{digits}f}".rstrip("0").rstrip(".")


def _register_fonts() -> None:
    if "PromoGuardVazir" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("PromoGuardVazir", str(FONT_DIR / "Vazirmatn-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("PromoGuardVazir-Bold", str(FONT_DIR / "Vazirmatn-Bold.ttf")))


def build_promotion_report_pdf(report: dict[str, Any]) -> bytes:
    """Build a shareable PDF that carries report identity, evidence, and limits."""
    _register_fonts()
    result = report.get("result") or {}
    audit = result.get("audit") or {}
    quality = result.get("quality") or {}
    decision = result.get("decision_support") or {}
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title="PromoGuard | گزارش ممیزی پروموشن",
        author="PromoGuard",
    )
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "PGTitle", parent=base["Title"], fontName="PromoGuardVazir-Bold", fontSize=19,
        leading=29, textColor=INK, alignment=TA_RIGHT, spaceAfter=4,
    )
    heading = ParagraphStyle(
        "PGHeading", parent=base["Heading2"], fontName="PromoGuardVazir-Bold", fontSize=12,
        leading=20, textColor=INK, alignment=TA_RIGHT, spaceBefore=8, spaceAfter=7,
    )
    body = ParagraphStyle(
        "PGBody", parent=base["BodyText"], fontName="PromoGuardVazir", fontSize=9,
        leading=15, textColor=INK, alignment=TA_RIGHT, spaceAfter=4,
    )
    small = ParagraphStyle(
        "PGSmall", parent=body, fontSize=7.5, leading=12, textColor=MUTED,
    )
    header = ParagraphStyle(
        "PGTableHeader", parent=body, fontName="PromoGuardVazir-Bold", fontSize=8,
        leading=12, textColor=colors.white, alignment=TA_RIGHT,
    )
    cell = ParagraphStyle("PGCell", parent=body, fontSize=8, leading=12)

    def para(text: object, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(_rtl(text), style)

    story: list[Any] = [
        para("PromoGuard", ParagraphStyle("PGBrand", parent=title, textColor=TEAL, fontSize=12, leading=18)),
        para("گزارش بررسی عملکرد پروموشن", title),
        para("تحلیل مشاهده‌ای برای مرور شواهد؛ نه اثبات اثر علّی یا سود خالص", small),
        Spacer(1, 5 * mm),
    ]
    for source_note in result.get("source_notes", []):
        story.append(para(f"یادداشت منبع: {source_note}", small))
    if result.get("source_notes"):
        story.append(Spacer(1, 2 * mm))

    identity = [
        [para("شناسه گزارش", cell), para(report.get("report_id", "—"), cell)],
        [para("شناسه داده", cell), para(report.get("dataset_id", "—"), cell)],
        [para("فروشگاه و کالا", cell), para(f"{audit.get('store_id', '—')} · {audit.get('upc', '—')}", cell)],
        [para("بازه پروموشن", cell), para(f"{audit.get('start_date', '—')} تا {audit.get('end_date', '—')}", cell)],
        [para("کیفیت فایل", cell), para(f"{'قابل استفاده' if quality.get('valid') else 'نیازمند بازبینی'} · {_number(quality.get('rows'), 0)} ردیف", cell)],
    ]
    story.append(Table(identity, colWidths=[45 * mm, 125 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])))

    story.append(para("خلاصه مدیریتی", heading))
    baseline = (audit.get("baseline_units") or {}).get("point")
    difference = (audit.get("estimated_units_difference_vs_baseline") or {}).get("point")
    kpis = [
        [para("فروش مشاهده‌شده", header), para("خط مبنای برآوردی", header), para("تفاوت با مبنا", header)],
        [para(f"{_number(audit.get('observed_units'), 0)} واحد", cell), para(f"{_number(baseline, 1)} واحد", cell), para(f"{_number(difference, 1)} واحد", cell)],
    ]
    story.append(Table(kpis, colWidths=[56 * mm] * 3, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("BACKGROUND", (0, 1), (-1, 1), PALE),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ])))

    story.append(para("پیشنهاد برای قدم بعدی", heading))
    story.append(para(decision.get("label", "برای تصمیم، شواهد بیشتری لازم است"), ParagraphStyle(
        "PGDecision", parent=body, fontName="PromoGuardVazir-Bold", textColor=TEAL, fontSize=10,
    )))
    if decision.get("explanation"):
        story.append(para(decision["explanation"], body))

    story.append(para("بازه‌های بررسی‌شده", heading))
    windows = audit.get("windows") or {}
    # API schema stores named summaries as pre/during/post_window.
    window_rows = [[para(x, header) for x in ("بازه", "هفته لازم", "هفته موجود", "فروش کل", "میانگین هفتگی")]]
    for key, label in (("pre_window", "قبل"), ("during_window", "حین"), ("post_window", "بعد")):
        item = audit.get(key) or windows.get(key) or {}
        window_rows.append([para(label, cell), para(item.get("requested_weeks", "—"), cell),
                            para(item.get("observed_weeks", "—"), cell), para(_number(item.get("total_units"), 0), cell),
                            para(_number(item.get("mean_units")), cell)])
    story.append(Table(window_rows, colWidths=[30 * mm, 28 * mm, 28 * mm, 38 * mm, 44 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])))

    warning_copy = {
        "OBSERVATIONAL_ONLY": "مقایسه مشاهده‌ای است و اثر علّی را شناسایی نمی‌کند.",
        "ECONOMIC_IMPACT_UNAVAILABLE": "هزینه و حاشیه سود کامل در داده نیست؛ سود خالص قابل محاسبه نیست.",
        "STOCKOUT_UNOBSERVABLE": "وضعیت موجودی در داده ثبت نشده است.",
        "FORWARD_BUY_RISK": "افت فروش پس از رویداد نیازمند بررسی است و به‌تنهایی جابه‌جایی خرید را ثابت نمی‌کند.",
        "INCOMPLETE_POST_WINDOW": "چهار هفته دقیق پس از رویداد در فایل کامل نیست.",
        "POST_WINDOW_CONTAMINATED": "پروموشن دیگری بازه پس از رویداد را مخدوش می‌کند.",
        "CANNIBALIZATION_CANDIDATE": "هم‌حرکتی کالای هم‌دسته فقط یک نشانه مشاهده‌ای است، نه اثبات جایگزینی.",
    }
    story.append(para("هشدارها و محدودیت‌ها", heading))
    warnings = audit.get("warnings") or []
    if warnings:
        for item in warnings:
            story.append(para(f"• {warning_copy.get(item.get('code'), item.get('code', 'نیازمند بررسی'))}", body))
    else:
        story.append(para("هشدار مشخصی از فهرست این ممیزی ثبت نشده است؛ این به معنی اثبات سود یا اثر علّی نیست.", body))
    story.append(Spacer(1, 2 * mm))
    story.append(para("این گزارش به‌تنهایی مجوز افزایش بودجه، تکرار کمپین یا توقف آن نیست. تصمیم نهایی باید با بررسی مدیر مسئول، داده هزینه و در صورت نیاز آزمون کنترل‌شده گرفته شود.", small))

    def footer(canvas: Any, _doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.setFont("PromoGuardVazir", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, _rtl(f"شناسه گزارش: {report.get('report_id', '—')}"))
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
