from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "PromoGuard-General-Commercial-Proposal-FA.pdf"

FONT = ROOT / "assets" / "fonts" / "Vazirmatn" / "Vazirmatn-Regular.ttf"
FONT_BOLD = ROOT / "assets" / "fonts" / "Vazirmatn" / "Vazirmatn-Bold.ttf"
pdfmetrics.registerFont(TTFont("Vazirmatn", str(FONT)))
pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", str(FONT_BOLD)))

NAVY = colors.HexColor("#07131B")
NAVY_2 = colors.HexColor("#0C2029")
TEAL = colors.HexColor("#00C9A7")
GREEN = colors.HexColor("#5CE1B8")
INK = colors.HexColor("#12232E")
MUTED = colors.HexColor("#5E7380")
PALE = colors.HexColor("#F4F8F8")
LINE = colors.HexColor("#D9E7E6")
RED = colors.HexColor("#D95858")
AMBER = colors.HexColor("#D69236")


def fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))


def para(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(fa(text)), style)


def ltr(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def make_styles() -> dict[str, ParagraphStyle]:
    return {
        "body": ParagraphStyle(
            "body", fontName="Vazirmatn", fontSize=9.5, leading=16, textColor=INK, alignment=TA_RIGHT, spaceAfter=4
        ),
        "small": ParagraphStyle(
            "small", fontName="Vazirmatn", fontSize=7.4, leading=11, textColor=MUTED, alignment=TA_RIGHT
        ),
        "small_ltr": ParagraphStyle(
            "small_ltr", fontName="Vazirmatn", fontSize=7.4, leading=11, textColor=MUTED, alignment=TA_LEFT
        ),
        "h1": ParagraphStyle(
            "h1", fontName="Vazirmatn-Bold", fontSize=20, leading=28, textColor=INK, alignment=TA_RIGHT, spaceAfter=8
        ),
        "h2": ParagraphStyle(
            "h2", fontName="Vazirmatn-Bold", fontSize=14, leading=21, textColor=INK, alignment=TA_RIGHT, spaceBefore=5, spaceAfter=8
        ),
        "h3": ParagraphStyle(
            "h3", fontName="Vazirmatn-Bold", fontSize=10.5, leading=16, textColor=TEAL, alignment=TA_RIGHT, spaceBefore=5, spaceAfter=4
        ),
        "cover_title": ParagraphStyle(
            "cover_title", fontName="Vazirmatn-Bold", fontSize=25, leading=35, textColor=colors.white, alignment=TA_RIGHT
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontName="Vazirmatn", fontSize=12, leading=21, textColor=colors.HexColor("#D7F4EE"), alignment=TA_RIGHT
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta", fontName="Vazirmatn", fontSize=8.5, leading=14, textColor=colors.HexColor("#9FD6CC"), alignment=TA_RIGHT
        ),
        "card_title": ParagraphStyle(
            "card_title", fontName="Vazirmatn-Bold", fontSize=10.5, leading=16, textColor=INK, alignment=TA_RIGHT
        ),
        "card_value": ParagraphStyle(
            "card_value", fontName="Vazirmatn-Bold", fontSize=17, leading=23, textColor=TEAL, alignment=TA_RIGHT
        ),
        "table": ParagraphStyle(
            "table", fontName="Vazirmatn", fontSize=7.6, leading=11.5, textColor=INK, alignment=TA_RIGHT
        ),
        "table_bold": ParagraphStyle(
            "table_bold", fontName="Vazirmatn-Bold", fontSize=7.6, leading=11.5, textColor=INK, alignment=TA_RIGHT
        ),
        "table_head": ParagraphStyle(
            "table_head", fontName="Vazirmatn-Bold", fontSize=7.6, leading=11.5, textColor=colors.white, alignment=TA_RIGHT
        ),
        "center": ParagraphStyle(
            "center", fontName="Vazirmatn", fontSize=9, leading=14, textColor=INK, alignment=TA_CENTER
        ),
    }


S = make_styles()


def brand_mark(canvas, x: float, y: float, size: float, light: bool = False) -> None:
    canvas.saveState()
    canvas.setFillColor(TEAL)
    canvas.roundRect(x, y, size, size, size * 0.22, fill=1, stroke=0)
    canvas.setFillColor(NAVY if not light else colors.white)
    canvas.setFont("Vazirmatn-Bold", size * 0.54)
    canvas.drawCentredString(x + size / 2, y + size * 0.22, "P")
    canvas.restoreState()


def draw_cover(canvas, doc) -> None:
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setFillColor(NAVY_2)
    canvas.circle(w * 0.98, h * 0.96, 95 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#15434A"))
    canvas.setLineWidth(1.2)
    canvas.bezier(0, 0.14 * h, 0.30 * w, 0.05 * h, 0.75 * w, 0.18 * h, w, 0.05 * h)
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(2.2)
    canvas.bezier(0.08 * w, 0.11 * h, 0.37 * w, 0.03 * h, 0.69 * w, 0.24 * h, 0.91 * w, 0.16 * h)
    brand_mark(canvas, 35 * mm, h - 52 * mm, 18 * mm, light=True)
    canvas.setFont("Vazirmatn-Bold", 12)
    canvas.setFillColor(colors.white)
    canvas.drawString(57 * mm, h - 43 * mm, "PromoGuard")
    canvas.setFont("Vazirmatn", 8)
    canvas.setFillColor(colors.HexColor("#A8C9C6"))
    canvas.drawString(57 * mm, h - 49 * mm, "Retail intelligence")
    canvas.setFillColor(TEAL)
    canvas.rect(35 * mm, 40 * mm, 1.3 * mm, 18 * mm, fill=1, stroke=0)
    canvas.setFont("Vazirmatn", 8.5)
    canvas.setFillColor(colors.HexColor("#C8EAE4"))
    canvas.drawString(42 * mm, 51 * mm, "Evidence-aware promotion decisions")
    canvas.drawString(42 * mm, 44 * mm, "Commercial proposal | 25 Sep 2026")
    canvas.restoreState()


def draw_page(canvas, doc) -> None:
    w, h = A4
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 15 * mm, w - 18 * mm, 15 * mm)
    brand_mark(canvas, w - 35 * mm, h - 26 * mm, 10 * mm)
    canvas.setFont("Vazirmatn-Bold", 8)
    canvas.setFillColor(NAVY)
    canvas.drawRightString(w - 40 * mm, h - 21 * mm, "PromoGuard")
    canvas.setFont("Vazirmatn", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Commercial proposal | Evidence-aware retail intelligence")
    canvas.drawRightString(w - 18 * mm, 9 * mm, str(doc.page))
    canvas.restoreState()


def card(title: str, value: str, note: str = "", width: float = 52 * mm) -> Table:
    rows = [[para(title, S["card_title"])], [para(value, S["card_value"])]]
    if note:
        rows.append([para(note, S["small"])])
    t = Table(rows, colWidths=[width], rowHeights=None)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def section_heading(title: str, kicker: str = "") -> list:
    out = []
    if kicker:
        out.append(para(kicker.upper(), ParagraphStyle("kicker", parent=S["small"], textColor=TEAL, fontName="Vazirmatn-Bold", alignment=TA_RIGHT)))
    out.append(para(title, S["h1"]))
    out.append(Spacer(1, 2 * mm))
    return out


def bullets(items: list[str], style: ParagraphStyle | None = None) -> list[Paragraph]:
    use = style or S["body"]
    return [para("• " + item, use) for item in items]


def labelled_row(label: str, text: str, color=PALE) -> Table:
    data = [[para(label, S["card_title"]), para(text, S["body"])]]
    t = Table(data, colWidths=[42 * mm, 123 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def prospect_table() -> Table:
    headers = ["شرکت", "شاهد عمومی", "تناسب و پیام اول", "مسیر تماس"]
    rows = [[para(h, S["table_head"]) for h in headers]]
    entries = [
        ("Best Offer Pars", "11 تا 50 نفر؛ بیش از 300 خرده‌فروش؛ تمرکز عمومی بر consumer promotions و retail management.", "اولویت 1؛ مسئله مستقیم پروموشن و شبکه قابل اندازه‌گیری.", "LinkedIn و besto.ir"),
        ("TezolMarket", "11 تا 50 نفر؛ بیش از 30 هزار کالا؛ نزدیک به 1000 فروشگاه؛ تخفیف 20 درصدی برای کاربران تپسی.", "اولویت 2؛ داده SKU، فروشگاه و کمپین آنلاین.", "support@tezolmarket.com / 02188441909"),
        ("Draje", "واحدهای بازاریابی، دیجیتال مارکتینگ، برنامه‌ریزی و چند کانال فروش در سایت رسمی.", "اولویت 3؛ مناسب pilot روی یک دسته محصول.", "02188554412-5 / draje.ir"),
        ("PVK", "توزیع‌کننده عمده FMCG تهران؛ 11 تا 50 نفر؛ سابقه عمومی از 1978.", "اولویت 4؛ مناسب تحلیل منطقه، مشتری و SKU.", "LinkedIn / vatanmart.com"),
        ("Himart", "خدمات تامین فروشگاه و تبلیغات نقطه فروش؛ اکوسیستم تامین‌کننده و فروشنده.", "اولویت 5؛ شریک کانالی یا pilot تامین‌کننده.", "info@himart.ir / 02147638000"),
    ]
    for a, b, c, d in entries:
        rows.append([para(a, S["table_bold"]), para(b, S["table"]), para(c, S["table"]), para(d, S["table"])])
    t = Table(rows, colWidths=[29 * mm, 62 * mm, 47 * mm, 27 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=28 * mm, bottomMargin=21 * mm,
        title="PromoGuard - General Commercial Proposal", author="PromoGuard"
    )
    story: list = []

    # Cover
    story += [Spacer(1, 61 * mm), para("ممیزی قابل دفاع عملکرد پروموشن", S["cover_title"]), Spacer(1, 5 * mm), para("پیشنهاد همکاری عمومی برای تیم‌های فروش، مارکتینگ و توزیع", S["cover_sub"]), Spacer(1, 6 * mm), para("یک خدمت سبک و قابل شروع برای تبدیل فایل‌های فروش به تصمیم روشن‌تر؛ با کیفیت داده، baseline زمانی و مرز ادعا.", S["cover_meta"]), PageBreak()]

    # 2
    story += section_heading("چرا این پیشنهاد اکنون قابل بررسی است؟", "خلاصه مدیریتی")
    story.append(para("در تصمیم‌های پروموشن، افزایش فروش مشاهده‌شده همیشه به معنی فروش اضافه یا سود بیشتر نیست. ممکن است خرید مشتری جلو افتاده باشد، فروش از کالای دیگری جابه‌جا شده باشد، موجودی محدود شده باشد یا داده برای قضاوت کافی نباشد. PromoGuard یک لایه بررسی و تصمیم‌یار برای همین نقطه است.", S["body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Table([[card("درد قابل سنجش", "اثر واقعی تخفیف", "در سطح کالا، زمان و کانال") , card("خروجی اولیه", "گزارش 7 تا 10 روزه", "با فایل Excel یا CSV") , card("شروع کم‌ریسک", "یک pilot محدود", "بدون نصب ERP")]], colWidths=[55 * mm, 55 * mm, 55 * mm], style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)])))
    story.append(Spacer(1, 6 * mm))
    story.append(para("پیشنهاد اصلی", S["h2"]))
    story.extend(bullets([
        "یک فایل ناشناس از فروش، قیمت و پروموشن دریافت می‌شود.",
        "کیفیت، دانه‌بندی، پوشش زمانی و معنای ستون‌ها بررسی می‌شود.",
        "فروش مشاهده‌شده با baseline قابل توضیح مقایسه می‌شود.",
        "هشدارها، محدودیت‌ها و داده لازم برای آزمایش بعدی در گزارش می‌آید.",
    ]))
    story.append(Spacer(1, 5 * mm))
    story.append(labelled_row("تصمیم پیشنهادی", "برای شروع، یک ممیزی محدود روی یک دسته کالا، یک منطقه یا یک کمپین اخیر انتخاب می‌کنیم و پیش از هر ادعای اقتصادی، تعریف داده و معیار موفقیت را با تیم شما نهایی می‌کنیم.", colors.HexColor("#E5F8F3")))
    story.append(PageBreak())

    # 3
    story += section_heading("PromoGuard چه کاری انجام می‌دهد؟", "محصول")
    story.append(para("محصول بر پایه یک مسیر ساده طراحی شده است تا مدیر فروش بداند از فایل اولیه تا تصمیم نهایی چه اتفاقی افتاده است.", S["body"]))
    workflow = [
        [para("1\nورود فایل", S["table_head"]), para("2\nکنترل کیفیت", S["table_head"]), para("3\nممیزی", S["table_head"]), para("4\nتصمیم بعدی", S["table_head"])],
        [para("فروش، قیمت، پروموشن", S["small"]), para("ردیف ناقص، تکراری، واحد و تاریخ", S["small"]), para("قبل، حین و بعد از کمپین", S["small"]), para("تایید، اصلاح داده یا طراحی pilot", S["small"])],
    ]
    wt = Table(workflow, colWidths=[41 * mm] * 4)
    wt.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("BACKGROUND", (0,1), (-1,1), PALE),
        ("BOX", (0,0), (-1,-1), 0.6, LINE), ("INNERGRID", (0,0), (-1,-1), 0.4, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(wt)
    story.append(Spacer(1, 6 * mm))
    story.append(para("در نسخه اولیه چه چیزی تحویل می‌شود؟", S["h2"]))
    story.extend(bullets([
        "گزارش آمادگی داده با دلیل روشن برای هر نقص.",
        "روند فروش و مقایسه با خط پایه زمانی.",
        "فهرست promotionهای قابل بررسی و موارد مبهم.",
        "هشدار افت بعد از promotion، forward-buy و نیاز به اطلاعات موجودی در صورت امکان.",
        "خلاصه مدیریتی کوتاه به همراه فایل خروجی قابل بررسی.",
    ]))
    story.append(Spacer(1, 4 * mm))
    story.append(labelled_row("اصل طراحی", "هر عدد باید منبع، واحد، بازه زمانی، روش محاسبه و محدودیت خودش را داشته باشد. اگر داده برای نتیجه کافی نباشد، گزارش باید همان را صریح اعلام کند.", colors.HexColor("#E5F8F3")))
    story.append(PageBreak())

    # 4
    story += section_heading("نمونه خروجی روی داده عمومی واقعی", "شاهد فنی")
    story.append(para("برای آزمون فنی، pipeline روی مجموعه داده عمومی dunnhumby Breakfast at the Frat اجرا شده است. این داده واقعی کسب‌وکار مشتری نیست؛ فقط نشان می‌دهد محصول چطور داده را می‌خواند، هشدار می‌دهد و از نتیجه‌گیری بیش از حد جلوگیری می‌کند.", S["body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Table([[card("ردیف‌های panel", "524,950", "داده پردازش‌شده") , card("ردیف‌های promotion", "149,386", "حدود 28.4 درصد") , card("وضعیت گزارش", "نیازمند شواهد بیشتر", "گزارش مالی صادر نمی‌شود")]], colWidths=[55 * mm, 55 * mm, 55 * mm], style=TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3)])))
    story.append(Spacer(1, 6 * mm))
    result = [
        [para("شاخص", S["table_head"]), para("مقدار مشاهده‌شده", S["table_head"]), para("برداشت مدیریتی", S["table_head"])],
        [para("فروش در دوره promotion", S["table"]), ltr("128 واحد", S["table"]), para("فروش در این بازه ثبت شده است؛ به‌تنهایی اثر promotion را ثابت نمی‌کند.", S["table"])],
        [para("baseline نقطه‌ای", S["table"]), ltr("185 واحد", S["table"]), para("مقایسه زمانی ساده با تاریخچه غیرپروموشن.", S["table"])],
        [para("اختلاف مشاهده‌شده", S["table"]), ltr("-57 واحد", S["table"]), para("کمتر از baseline مشاهده شده؛ بازه عدم‌قطعیت شامل صفر است.", S["table"])],
        [para("نسبت بعد به قبل", S["table"]), ltr("0.725", S["table"]), para("هشدار افت پس از promotion و احتمال خرید جلو افتاده.", S["table"])],
    ]
    rt = Table(result, colWidths=[45 * mm, 32 * mm, 88 * mm])
    rt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]), ("BOX", (0,0), (-1,-1), 0.5, LINE), ("INNERGRID", (0,0), (-1,-1), 0.35, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)]))
    story.append(rt)
    story.append(Spacer(1, 5 * mm))
    story.append(labelled_row("مرز ادعا", "این نمونه اثر علّی، سود، موجودی یا تصمیم rollout را شناسایی نمی‌کند. نتیجه فقط برای screening مشاهده‌ای و تعیین اینکه چه داده یا آزمایشی لازم است استفاده می‌شود.", colors.HexColor("#FFF5E4")))
    story.append(PageBreak())

    # 5
    story += section_heading("برای اجرای پایلوت چه داده‌ای لازم است؟", "ورودی و خروجی")
    story.append(para("شروع کار با داده ناشناس و یک بازه محدود ممکن است. لازم نیست در روز اول کل انبار داده یا API سازمان متصل شود.", S["body"]))
    data_rows = [
        [para("داده", S["table_head"]), para("حداقل مورد نیاز", S["table_head"]), para("برای چه تصمیمی", S["table_head"])],
        [para("فروش", S["table"]), para("تاریخ، کالا، فروشگاه یا کانال، مقدار فروش", S["table"]), para("روند و baseline", S["table"])],
        [para("قیمت", S["table"]), para("قیمت عادی و قیمت فروش یا کد تخفیف", S["table"]), para("تفکیک promotion", S["table"])],
        [para("تقویم کمپین", S["table"]), para("شروع، پایان و نوع پیشنهاد", S["table"]), para("ممیزی قبل، حین و بعد", S["table"])],
        [para("موجودی", S["table"]), para("در صورت وجود: موجودی، stockout و برگشتی", S["table"]), para("تشخیص محدودیت عرضه", S["table"])],
        [para("اقتصاد", S["table"]), para("در صورت وجود: هزینه، تخفیف پرداختی و margin", S["table"]), para("تحلیل حساسیت اقتصادی", S["table"])],
    ]
    dt = Table(data_rows, colWidths=[34 * mm, 72 * mm, 59 * mm])
    dt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]), ("BOX", (0,0), (-1,-1), 0.5, LINE), ("INNERGRID", (0,0), (-1,-1), 0.35, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    story.append(dt)
    story.append(Spacer(1, 6 * mm))
    story.append(para("خروجی جلسه نهایی", S["h2"]))
    story.extend(bullets([
        "یک گزارش مدیریتی با شاخص‌های خوانا.",
        "یک گزارش فنی از کیفیت، نقص و پوشش داده.",
        "جدول کمپین‌های قابل بررسی و سطح اطمینان هرکدام.",
        "فهرست تصمیم‌هایی که با داده فعلی مجازند و تصمیم‌هایی که نیاز به داده بیشتر دارند.",
        "پیشنهاد طراحی pilot کنترل‌شده برای مرحله بعد.",
    ]))
    story.append(PageBreak())

    # 6
    story += section_heading("پیشنهاد اجرای 7 تا 10 روزه", "برنامه پایلوت")
    timeline = [
        [para("روز 1", S["table_head"]), para("روز 2-3", S["table_head"]), para("روز 4-6", S["table_head"]), para("روز 7-10", S["table_head"])],
        [para("هدف و schema", S["small"]), para("کنترل کیفیت و آماده‌سازی", S["small"]), para("ممیزی و نمودارهای تصمیم", S["small"]), para("جلسه نتیجه و next step", S["small"])],
    ]
    tt = Table(timeline, colWidths=[41 * mm] * 4)
    tt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), TEAL), ("TEXTCOLOR", (0,0), (-1,0), NAVY), ("BACKGROUND", (0,1), (-1,1), PALE), ("BOX", (0,0), (-1,-1), 0.5, LINE), ("INNERGRID", (0,0), (-1,-1), 0.35, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
    story.append(tt)
    story.append(Spacer(1, 7 * mm))
    story.append(para("معیار عبور از پایلوت", S["h2"]))
    story.extend(bullets([
        "مالک کسب‌وکار تعریف promotion و KPI را تایید کرده باشد.",
        "دانه‌بندی و واحدها بدون ابهام ثبت شده باشند.",
        "حداقل یک تصمیم واقعی از گزارش استخراج شده باشد.",
        "برای نتیجه‌های مهم، داده لازم برای کنترل، موجودی یا margin مشخص شده باشد.",
        "گزارش توسط مدیر فروش یا مدیر trade marketing قابل توضیح و بازبینی باشد.",
    ]))
    story.append(Spacer(1, 4 * mm))
    story.append(labelled_row("شرط تجاری", "تا زمانی که داده و مسئله واقعی تایید نشده، پیشنهاد به شکل پایلوت محدود ارائه می‌شود. پس از تایید، نسخه ماهانه یا استقرار خصوصی تعریف می‌شود.", colors.HexColor("#E5F8F3")))
    story.append(PageBreak())

    # 7
    story += section_heading("مدل همکاری قابل شروع", "خدمات")
    service_rows = [
        [para("مرحله", S["table_head"]), para("تحویل", S["table_head"]), para("مناسب برای", S["table_head"]), para("تصمیم بعدی", S["table_head"])],
        [para("Discovery", S["table"]), para("جلسه 20 تا 30 دقیقه‌ای و صورت مسئله", S["table"]), para("سنجش تناسب", S["table"]), para("انتخاب dataset و مالک داده", S["table"])],
        [para("Data Readiness & Promotion Audit", S["table"]), para("گزارش 7 تا 10 روزه و خلاصه مدیریتی", S["table"]), para("اولین خرید یا پایلوت", S["table"]), para("ادامه، اصلاح داده یا توقف", S["table"])],
        [para("Pilot Measurement Design", S["table"]), para("تعریف کنترل، KPI و پروتکل اندازه‌گیری", S["table"]), para("کمپین حساس یا پرهزینه", S["table"]), para("اجرای pilot کنترل‌شده", S["table"])],
        [para("Monthly Monitoring", S["table"]), para("گزارش دوره‌ای و جلسه تصمیم", S["table"]), para("مشتری مرجع و داده تکرارشونده", S["table"]), para("قرارداد دوره‌ای", S["table"])],
    ]
    st = Table(service_rows, colWidths=[38 * mm, 54 * mm, 39 * mm, 40 * mm])
    st.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]), ("BOX", (0,0), (-1,-1), 0.5, LINE), ("INNERGRID", (0,0), (-1,-1), 0.35, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)]))
    story.append(st)
    story.append(Spacer(1, 7 * mm))
    story.append(para("منطق قیمت‌گذاری", S["h2"]))
    story.extend(bullets([
        "قیمت نسخه اول بعد از مشخص شدن تعداد SKU، بازه زمانی، تعداد کانال و سطح محرمانگی اعلام می‌شود.",
        "پایلوت باید قیمت ثابت و محدوده روشن داشته باشد؛ درصدی از سود آینده مبنای شروع نباشد.",
        "هزینه اتصال API، استقرار خصوصی یا گزارش دوره‌ای در مرحله بعد جداگانه تعریف می‌شود.",
        "پیشنهاد عمومی فعلی برای فروش مستقیم طراحی نشده و پس از discovery باید اختصاصی شود.",
    ]))
    story.append(PageBreak())

    # 8
    story += section_heading("بهترین گزینه‌ها برای موج اول تماس", "پژوهش بازار")
    story.append(para("این فهرست از شرکت‌های بسیار بزرگ شروع نمی‌شود. معیار اول، تناسب مسئله و امکان شروع گفت‌وگوی مستقیم است. شواهد عمومی را باید در تماس تایید کرد.", S["body"]))
    story.append(Spacer(1, 3 * mm))
    story.append(prospect_table())
    story.append(Spacer(1, 6 * mm))
    story.append(labelled_row("انتخاب اول", "Best Offer Pars بیشترین تناسب آشکار را دارد، چون در معرفی عمومی خود هم شبکه خرده‌فروشی دارد و هم consumer promotions را جزو تخصص‌ها آورده است. پیشنهاد اولیه باید درباره ممیزی عملکرد offer در 300 فروشگاه باشد، نه فروش یک پلتفرم بزرگ.", colors.HexColor("#E5F8F3")))
    story.append(PageBreak())

    # 9
    story += section_heading("پیشنهاد گفت‌وگوی اختصاصی برای هر گروه", "پیام فروش")
    msg_rows = [
        [para("گروه", S["table_head"]), para("مسئله‌ای که مطرح می‌کنیم", S["table_head"]), para("خروجی قابل پیشنهاد", S["table_head"])],
        [para("پخش و شبکه فروش", S["table"]), para("کدام منطقه، مشتری یا کالا بعد از offer بهتر عمل کرده و کجا افت بعدی دیده می‌شود؟", S["table"]), para("گزارش SKU × منطقه × بازه و data gap", S["table"])],
        [para("فروشگاه آنلاین", S["table"]), para("کدام کمپین در سطح کالا و فروشگاه آنلاین رشد مشاهده‌شده داشته و کجا نیاز به آزمون دارد؟", S["table"]), para("تحلیل cohort کمپین و baseline زمانی", S["table"])],
        [para("برند FMCG", S["table"]), para("فروش بیشتر به خود promotion مربوط است یا تقویم، کانال و موجودی؟", S["table"]), para("promotion audit و طراحی measurement pilot", S["table"])],
        [para("شریک داده/تحقیق بازار", S["table"]), para("چطور کیفیت داده و مرز ادعا را قبل از ارائه به مشتری نهایی روشن کنیم؟", S["table"]), para("ماژول تکمیلی white-label یا گزارش مشترک", S["table"])],
    ]
    mt = Table(msg_rows, colWidths=[35 * mm, 79 * mm, 57 * mm])
    mt.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), NAVY), ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]), ("BOX", (0,0), (-1,-1), 0.5, LINE), ("INNERGRID", (0,0), (-1,-1), 0.35, LINE), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7)]))
    story.append(mt)
    story.append(Spacer(1, 7 * mm))
    story.append(para("متن پیشنهادی برای تماس اول", S["h2"]))
    story.append(labelled_row("پیام", "سلام وقت بخیر. برای یک گفت‌وگوی کوتاه درباره تحلیل داده فروش و سنجش عملکرد تخفیف تماس گرفتم. ما فعلاً اتصال سنگین یا دسترسی محرمانه نمی‌خواهیم؛ فقط می‌خواهیم بفهمیم تصمیم promotion امروز با چه گزارشی گرفته می‌شود و آیا یک بررسی محدود روی فایل ناشناس می‌تواند برای تیم فروش مفید باشد. این موضوع را با چه شخصی باید مطرح کنم؟", colors.HexColor("#F4F8F8")))
    story.append(Spacer(1, 5 * mm))
    story.extend(bullets([
        "پیام اول را کوتاه نگه دارید.",
        "قبل از ارسال PDF کامل، مسئله و مالک تصمیم را پیدا کنید.",
        "اگر پاسخ مثبت بود، یک نمونه schema ناشناس بخواهید.",
        "اگر پاسخ منفی بود، دلیل را ثبت کنید؛ آن را مشتری قطعی حساب نکنید.",
    ]))
    story.append(PageBreak())

    # 10
    story += section_heading("پرسش‌های سخت و پاسخ تجاری", "شفافیت")
    qa = [
        ("آیا افزایش فروش را تضمین می‌کنید؟", "خیر. ابتدا نشان می‌دهیم داده چه چیزی را قابل دفاع می‌کند و برای اثر علّی یا سود به چه pilot و داده‌ای نیاز است."),
        ("چه فایلی لازم است؟", "یک Excel یا CSV ناشناس با تاریخ، کالا، فروشگاه یا کانال، مقدار فروش و اطلاعات قیمت یا promotion کافی است تا readiness بررسی شود."),
        ("داده ما کجا می‌ماند؟", "در پایلوت می‌توان تحلیل را در محیط محدود و با حداقل نسخه داده انجام داد. نگهداری، حذف و دسترسی در قرارداد ثبت می‌شود."),
        ("اگر داده ناقص باشد چه می‌شود؟", "تحلیل متوقف یا سطح نتیجه محدود می‌شود و دقیقاً فهرست نقص و داده موردنیاز را تحویل می‌گیریم."),
        ("چرا فقط نمودار نمی‌سازید؟", "چون نمودار بدون تعریف واحد، baseline و محدودیت می‌تواند تصمیم اشتباه ایجاد کند. هر خروجی باید به تصمیم وصل باشد."),
        ("چقدر زمان می‌برد؟", "پایلوت محدود معمولاً 7 تا 10 روز کاری پس از دریافت داده و تایید schema زمان می‌برد."),
    ]
    for q, a in qa:
        story.append(labelled_row(q, a, colors.white))
        story.append(Spacer(1, 2 * mm))
    story.append(PageBreak())

    # 11 sources
    story += section_heading("منابع و حدود پژوهش", "پیوست")
    story.append(para("انتخاب شرکت‌ها با صفحات رسمی، صفحات LinkedIn و مسیرهای تماس عمومی انجام شده است. این منابع برای ساخت lead list مناسب‌اند، اما مصاحبه و داده مجاز را جایگزین نمی‌کنند.", S["body"]))
    sources = [
        "[S1] Best Offer Pars — https://ae.linkedin.com/company/best-offer-pars",
        "[S2] TezolMarket — https://www.linkedin.com/company/tezol-market",
        "[S3] TezolMarket official offer and contact — https://www.tezolmarket.com/home/tezoltap30",
        "[S4] Draje official about/contact — https://draje.ir/about/ و https://draje.ir/contact/",
        "[S5] PVK — https://www.linkedin.com/company/parsvatankala",
        "[S6] Himart official — https://himart.ir/",
        "[S7] IRANFMCG — https://www.linkedin.com/company/iranfmcg",
        "[S8] Safapakhsh — https://ir.linkedin.com/company/safapakhsh",
        "[S9] Barjil — https://www.linkedin.com/company/barjil",
        "[S10] Hyperfamili — https://www.linkedin.com/company/hyperefamili",
        "[S11] dunnhumby source files — https://www.dunnhumby.com/source-files/",
    ]
    for source in sources:
        story.append(ltr(source, S["small_ltr"]))
        story.append(Spacer(1, 1.5 * mm))
    story.append(Spacer(1, 5 * mm))
    story.append(labelled_row("قانون استفاده", "تا قبل از تایید انسانی، هیچ نامی در این سند مشتری PromoGuard محسوب نمی‌شود. مرحله بعد، تماس اکتشافی، ثبت پاسخ، تایید مالک داده و دریافت sample ناشناس است.", colors.HexColor("#FFF5E4")))
    story.append(Spacer(1, 7 * mm))
    story.append(para("PromoGuard\nSmarter promotions. Stronger decisions.", ParagraphStyle("end", parent=S["center"], textColor=TEAL, fontName="Vazirmatn-Bold", fontSize=12, leading=20)))

    doc.build(story, onFirstPage=draw_cover, onLaterPages=draw_page)
    print(OUTPUT)


if __name__ == "__main__":
    build()
