"""Persian, evidence-bounded PDF export for completed promotion reports."""

from __future__ import annotations

from html import escape
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
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
        return Paragraph(escape(_rtl(text)), style)

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


def build_experiment_report_pdf(report: dict[str, Any]) -> bytes:
    """Build a shareable PDF for the public randomized Hillstrom evaluation."""
    _register_fonts()
    result = report.get("result") or {}
    source = result.get("source") or {}
    design = result.get("design") or {}
    outcome = result.get("primary_outcome") or {}
    uncertainty = result.get("uncertainty") or {}
    assumptions = (report.get("configuration") or {}).get("analysis", {}).get(
        "financial_assumptions"
    ) or {}

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=18 * mm,
        title="PromoGuard | گزارش ارزیابی آزمایش کمپین",
        author="PromoGuard",
    )
    base = getSampleStyleSheet()
    title = ParagraphStyle(
        "PGExperimentTitle", parent=base["Title"], fontName="PromoGuardVazir-Bold",
        fontSize=18, leading=27, textColor=INK, alignment=TA_RIGHT, spaceAfter=5,
    )
    heading = ParagraphStyle(
        "PGExperimentHeading", parent=base["Heading2"], fontName="PromoGuardVazir-Bold",
        fontSize=12, leading=19, textColor=INK, alignment=TA_RIGHT, spaceBefore=8, spaceAfter=6,
    )
    body = ParagraphStyle(
        "PGExperimentBody", parent=base["BodyText"], fontName="PromoGuardVazir",
        fontSize=8.5, leading=14, textColor=INK, alignment=TA_RIGHT, spaceAfter=4,
    )
    small = ParagraphStyle(
        "PGExperimentSmall", parent=body, fontSize=7.2, leading=11, textColor=MUTED,
    )
    header = ParagraphStyle(
        "PGExperimentTableHeader", parent=body, fontName="PromoGuardVazir-Bold",
        fontSize=7.2, leading=11, textColor=colors.white,
    )
    cell = ParagraphStyle("PGExperimentCell", parent=body, fontSize=7.2, leading=11)
    identity_label = ParagraphStyle(
        "PGExperimentIdentityLabel", parent=cell, fontName="PromoGuardVazir-Bold", textColor=INK,
    )
    emphasis = ParagraphStyle(
        "PGExperimentEmphasis", parent=body, fontName="PromoGuardVazir-Bold",
        fontSize=9, leading=15, textColor=TEAL,
    )
    ltr_cell = ParagraphStyle(
        "PGExperimentLTRCell", parent=cell, alignment=0, fontName="Helvetica",
    )

    def para(text: object, style: ParagraphStyle = body) -> Paragraph:
        return Paragraph(escape(_rtl(text)), style)

    def ltr_para(text: object, style: ParagraphStyle) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    def fmt(value: object, digits: int = 2) -> str:
        try:
            return f"{float(value):,.{digits}f}"
        except (TypeError, ValueError):
            return "نامشخص"

    def usd(value: object) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "نامشخص"
        return f"USD ({abs(number):,.2f})" if number < 0 else f"USD {number:,.2f}"

    def effect(value: object) -> str:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "نامشخص"
        if outcome.get("name") == "spend":
            return usd(number)
        return f"{number * 100:,.2f} pp"

    arm_fa = {
        "Mens E-Mail": "ایمیل محصولات مردانه",
        "Womens E-Mail": "ایمیل محصولات زنانه",
        "No E-Mail": "بدون ایمیل",
    }
    story: list[Any] = [
        para("PromoGuard", ParagraphStyle(
            "PGExperimentBrand", parent=title, textColor=TEAL, fontSize=12, leading=18,
        )),
        para("گزارش ارزیابی آزمایش کمپین", title),
        para("نتیجهٔ آزمایش تصادفی ایمیلی Hillstrom؛ درآمد ناخالص از سود جدا نگه داشته شده است.", small),
        Spacer(1, 4 * mm),
    ]

    identity = [
        [para("شناسهٔ گزارش", identity_label), para(report.get("report_id", "ثبت نشده"), cell)],
        [para("نوع تحلیل", identity_label), para("آزمایش تصادفی سه‌گروهی", cell)],
        [para("افراد تخصیص‌یافته", identity_label), para(fmt(design.get("sample_rows"), 0), cell)],
        [para("پیامد اصلی", identity_label), para(outcome.get("unit", outcome.get("name", "ثبت نشده")), cell)],
        [para("بازهٔ پیامد", identity_label), para(design.get("outcome_window", "ثبت نشده"), cell)],
    ]
    story.append(Table(identity, colWidths=[48 * mm, 122 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), PALE),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])))

    story.append(para("اندازهٔ هر گروه", heading))
    counts = design.get("arm_counts") or {}
    arm_rows = [[para("گروه", header), para("تعداد افراد", header)]]
    for arm in ("No E-Mail", "Mens E-Mail", "Womens E-Mail"):
        arm_rows.append([para(arm_fa.get(arm, arm), cell), para(fmt(counts.get(arm), 0), cell)])
    story.append(Table(arm_rows, colWidths=[125 * mm, 45 * mm], style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])))

    story.append(para("نتیجهٔ سه مقایسهٔ ازپیش‌تعیین‌شده", heading))
    result_rows = [[
        para("مقایسه", header), para("اثر به‌ازای هر نفر", header),
        para("بازهٔ هم‌زمان ۹۵٪", header), para("وضعیت", header),
    ]]
    for item in result.get("comparisons", []):
        first = arm_fa.get(item.get("treatment_arm"), item.get("treatment_arm", "نامشخص"))
        second = arm_fa.get(item.get("control_arm"), item.get("control_arm", "نامشخص"))
        if item.get("statistical_direction_status") == "positive_evidence_vs_zero":
            status_text = "افزایش نسبت به صفر پشتیبانی می‌شود"
        elif item.get("statistical_direction_status") == "negative_evidence_vs_zero":
            status_text = "کاهش نسبت به صفر پشتیبانی می‌شود"
        elif item.get("statistical_direction_status") == "insufficient_sample":
            status_text = "نمونه برای قضاوت کافی نیست"
        else:
            status_text = "تفاوت روشن نیست"
        result_rows.append([
            para(f"{first} در برابر {second}", cell),
            ltr_para(effect(item.get("incremental_effect_per_person")), ltr_cell),
            ltr_para(f"{effect(item.get('familywise_ci_lower_per_person'))} - {effect(item.get('familywise_ci_upper_per_person'))}", ltr_cell),
            para(status_text, cell),
        ])
    story.append(Table(result_rows, colWidths=[53 * mm, 34 * mm, 39 * mm, 44 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])))

    story.append(para("میانگین پیامد اصلی در هر گروه", heading))
    means_rows = [[para("گروه", header), para("میانگین پیامد", header), para("واحد", header)]]
    for item in result.get("comparisons", [])[:2]:
        arm = item.get("treatment_arm")
        means_rows.append([
            para(arm_fa.get(arm, arm or "نامشخص"), cell),
            ltr_para(effect(item.get("treatment_mean_per_person")), ltr_cell),
            para(outcome.get("unit", "به‌ازای هر فرد تخصیص‌یافته"), cell),
        ])
    if result.get("comparisons"):
        control_mean = result["comparisons"][0].get("control_mean_per_person")
        means_rows.append([para("بدون ایمیل", cell), ltr_para(effect(control_mean), ltr_cell), para(outcome.get("unit", "به‌ازای هر فرد تخصیص‌یافته"), cell)])
    story.append(Table(means_rows, colWidths=[48 * mm, 48 * mm, 74 * mm], repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])))

    if assumptions:
        story.append(para("محاسبهٔ مالیِ مشروط", heading))
        margin = assumptions.get("common_contribution_margin")
        story.append(para(
            f"این سناریو با حاشیهٔ مشارکت مشترک {fmt(float(margin or 0) * 100, 1)}٪ محاسبه شده است. "
            "اعداد زیر از منبع عمومی استخراج نشده‌اند؛ کاربر آن‌ها را وارد کرده است.", body,
        ))
        financial_rows = [[
            para("مقایسه", header), para("اختلاف هزینه / ۱۰۰۰ نفر", header),
            para("مشارکت افزودهٔ مرکزی / ۱۰۰۰ نفر", header), para("بازهٔ مشروط", header),
        ]]
        for item in result.get("comparisons", []):
            details = item.get("revenue_details") or {}
            economics = details.get("conditional_economics") or {}
            if not economics:
                continue
            arm = arm_fa.get(item.get("treatment_arm"), item.get("treatment_arm", "نامشخص"))
            comp = arm_fa.get(item.get("control_arm"), item.get("control_arm", "نامشخص"))
            contribution = economics.get("contribution_per_1000") or {}
            financial_rows.append([
                para(f"{arm} در برابر {comp}", cell),
                ltr_para(usd(economics.get("incremental_campaign_cost_per_1000")), ltr_cell),
                ltr_para(usd(contribution.get("point")), ltr_cell),
                ltr_para(f"{usd(contribution.get('lower'))} - {usd(contribution.get('upper'))}", ltr_cell),
            ])
        if len(financial_rows) > 1:
            story.append(Table(financial_rows, colWidths=[51 * mm, 34 * mm, 42 * mm, 43 * mm], repeatRows=1, style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), INK), ("BACKGROUND", (0, 1), (-1, -1), PALE),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])))
        story.append(para("منابع ورودی‌های مالی و محدودیت محاسبه", heading))
        source_lines = [
            ("منبع حاشیه", assumptions.get("margin_source")),
            ("منبع هزینهٔ نسخهٔ مردانه", assumptions.get("mens_cost_source")),
            ("منبع هزینهٔ نسخهٔ زنانه", assumptions.get("womens_cost_source")),
        ]
        story.append(Spacer(1, 2 * mm))
        for label, reference in source_lines:
            if reference:
                story.append(para(f"{label}: {reference}", small))
        story.append(para(
            "منبع‌ها توسط کاربر ثبت شده و مستقلاً راستی‌آزمایی نشده‌اند. بازه فقط عدم‌قطعیت درآمد را منتقل می‌کند؛ "
            "عدم‌قطعیت حاشیه یا هزینه را شامل نمی‌شود. این عدد مشارکت محاسباتی است، نه سود خالص.", small,
        ))
    else:
        story.append(para("هزینه و حاشیهٔ مشارکت وارد نشده", heading))
        story.append(para(
            "این فایل فقط درآمد ناخالص را می‌سنجد. بدون حاشیهٔ مشارکت و هزینهٔ واقعی کمپین، "
            "سود یا مشارکت خالص محاسبه نمی‌شود.", body,
        ))

    bootstrap = uncertainty.get("bootstrap") or {}
    if bootstrap:
        bootstrap_story: list[Any] = [
            para("بررسی پایداری نتیجه با بازنمونه‌گیری", heading),
            para(
            f"از هر گروه جداگانه {fmt(bootstrap.get('repetitions'), 0)} بار نمونهٔ هم‌اندازه با جایگذاری ساخته شد. "
            "این بازبینی مستقل از بازهٔ Welch است و فقط نشان می‌دهد نتیجه به روش محاسبه حساس هست یا نه؛ "
            "جایگزین روش اصلی یا آستانهٔ تصمیم نیست.", body,
            ),
        ]
        bootstrap_rows = [[
            para("مقایسه", header), para("بازهٔ bootstrap خانوادگی ۹۵٪", header),
            para("سازگاری با Welch", header),
        ]]
        stability_labels = {
            "consistent": "هم‌سو",
            "sensitive_to_method": "حساس به روش",
            "insufficient_sample": "نمونه ناکافی",
        }
        for item in result.get("comparisons", []):
            first = arm_fa.get(item.get("treatment_arm"), "نامشخص")
            second = arm_fa.get(item.get("control_arm"), "نامشخص")
            bootstrap_rows.append([
                para(f"{first} در برابر {second}", cell),
                ltr_para(
                    f"{effect(item.get('bootstrap_ci_lower_per_person'))} - "
                    f"{effect(item.get('bootstrap_ci_upper_per_person'))}", ltr_cell,
                ),
                para(stability_labels.get(item.get("bootstrap_stability_status"), "ثبت نشده"), cell),
            ])
        bootstrap_story.append(Table(bootstrap_rows, colWidths=[63 * mm, 65 * mm, 42 * mm], repeatRows=1, style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])))
        bootstrap_story.append(para(
            f"روش: {bootstrap.get('method', 'ثبت نشده')}؛ بازنمونه‌گیری درون هر گروه، "
            f"تصحیح Bonferroni برای {fmt(uncertainty.get('contrast_count'), 0)} مقایسه، "
            f"بذر ثابت {fmt(bootstrap.get('seed'), 0)}. بازه‌ها تقریبی‌اند و به فرض استقلال افراد در هر گروه تکیه دارند.", small,
        ))
        story.append(KeepTogether(bootstrap_story))

    story.append(para("روش و مرز تفسیر", heading))
    story.append(para(
        f"واحد تخصیص: مشتری. نتیجه بر اساس گروه تخصیص‌یافته (ITT) است. بازه با روش "
        f"{uncertainty.get('method', 'ثبت نشده')} ساخته شده و برای {fmt(uncertainty.get('contrast_count'), 0)} "
        "مقایسه تصحیح چندگانه اعمال شده است. افراد در هر گروه باید مستقل باشند و توصیف ناشر دربارهٔ تصادفی‌سازی را می‌پذیریم.", body,
    ))
    for limitation in result.get("interpretation", []):
        story.append(para(f"- {limitation}", small))
    story.append(para(f"SHA-256 فایل: {source.get('sha256', 'ثبت نشده')}", small))
    story.append(para(f"وضعیت مجوز: {source.get('license_status', 'ثبت نشده')}", small))
    story.append(Paragraph(
        escape(str(source.get("dataset_page", "ثبت نشده"))),
        ParagraphStyle("PGExperimentSourceURL", parent=small, alignment=0, fontName="Helvetica", wordWrap="CJK"),
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(para(
        "جمع‌بندی برای تصمیم‌گیر: نتیجهٔ آزمایش می‌تواند از افزایش درآمد ناخالص در مقایسه با کنترل پشتیبانی کند؛ "
        "این به‌تنهایی نشان نمی‌دهد کمپین سودآور است یا باید تکرار شود. برای تصمیم واقعی، هزینه‌ها، حاشیهٔ واقعی، "
        "تناسب با محصول و بازار، و بازبینی مسئول کسب‌وکار لازم است.", emphasis,
    ))

    def footer(canvas: Any, _doc: Any) -> None:
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 13 * mm, A4[0] - 18 * mm, 13 * mm)
        canvas.setFont("PromoGuardVazir", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, _rtl(f"شناسه گزارش: {report.get('report_id', 'ثبت نشده')}"))
        canvas.drawString(18 * mm, 8 * mm, f"{canvas.getPageNumber()}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
