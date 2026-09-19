from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "PromoGuard_Business_Discovery_Report_FA.pdf"
NAVY = colors.HexColor("#173554")
TEAL = colors.HexColor("#07847d")
TEXT = colors.HexColor("#182536")
MUTED = colors.HexColor("#687486")
BLUE = colors.HexColor("#e8f2f3")
YELLOW = colors.HexColor("#fff3cf")
LIGHT = colors.HexColor("#f6f8fa")
LINE = colors.HexColor("#d8e1e7")
GREEN = colors.HexColor("#e6f5ee")
RED = colors.HexColor("#fbecec")
pdfmetrics.registerFont(TTFont("Tahoma", r"C:\Windows\Fonts\tahoma.ttf"))
pdfmetrics.registerFont(TTFont("Tahoma-Bold", r"C:\Windows\Fonts\tahomabd.ttf"))

def rtl(value):
    return get_display(arabic_reshaper.reshape(str(value)))

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleFA", fontName="Tahoma-Bold", fontSize=19, leading=29, textColor=NAVY, alignment=TA_RIGHT, spaceAfter=7*mm))
styles.add(ParagraphStyle(name="SubFA", fontName="Tahoma", fontSize=10.5, leading=18, textColor=MUTED, alignment=TA_RIGHT, spaceAfter=7*mm))
styles.add(ParagraphStyle(name="H1FA", fontName="Tahoma-Bold", fontSize=14, leading=23, textColor=TEAL, alignment=TA_RIGHT, spaceBefore=2*mm, spaceAfter=4*mm))
styles.add(ParagraphStyle(name="H2FA", fontName="Tahoma-Bold", fontSize=10.6, leading=18, textColor=NAVY, alignment=TA_RIGHT, spaceBefore=2*mm, spaceAfter=2*mm))
styles.add(ParagraphStyle(name="BodyFA", fontName="Tahoma", fontSize=9.2, leading=18, textColor=TEXT, alignment=TA_RIGHT, spaceAfter=2.2*mm))
styles.add(ParagraphStyle(name="SmallFA", fontName="Tahoma", fontSize=7.8, leading=13.5, textColor=MUTED, alignment=TA_RIGHT))
styles.add(ParagraphStyle(name="TableFA", fontName="Tahoma", fontSize=7.6, leading=13, textColor=TEXT, alignment=TA_RIGHT))
styles.add(ParagraphStyle(name="TableHeadFA", fontName="Tahoma-Bold", fontSize=7.8, leading=13, textColor=colors.white, alignment=TA_RIGHT))
styles.add(ParagraphStyle(name="FAQQ", fontName="Tahoma-Bold", fontSize=9.6, leading=15, textColor=NAVY, alignment=TA_RIGHT, spaceBefore=1*mm, spaceAfter=1*mm))
styles.add(ParagraphStyle(name="FAQA", fontName="Tahoma", fontSize=8.5, leading=14, textColor=TEXT, alignment=TA_RIGHT, spaceAfter=1*mm))

def P(text, style="BodyFA"):
    return Paragraph(rtl(text), styles[style])

def bullet(text):
    return P("• " + text)

def callout(text, bg=BLUE):
    t = Table([[P(text)]], colWidths=[170*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bg),("BOX",(0,0),(-1,-1),0.5,bg),
                           ("LEFTPADDING",(0,0),(-1,-1),7*mm),("RIGHTPADDING",(0,0),(-1,-1),7*mm),
                           ("TOPPADDING",(0,0),(-1,-1),4*mm),("BOTTOMPADDING",(0,0),(-1,-1),4*mm)]))
    return t

def grid(headers, rows, widths):
    data = [[P(x, "TableHeadFA") for x in headers]]
    data += [[P(x, "TableFA") for x in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="RIGHT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("GRID",(0,0),(-1,-1),0.35,LINE),
                           ("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(0,0),(-1,-1),"RIGHT"),
                           ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,LIGHT]),
                           ("LEFTPADDING",(0,0),(-1,-1),3*mm),("RIGHTPADDING",(0,0),(-1,-1),3*mm),
                           ("TOPPADDING",(0,0),(-1,-1),2.5*mm),("BOTTOMPADDING",(0,0),(-1,-1),2.5*mm)]))
    return t

def header_footer(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setFillColor(TEAL)
    canvas.setFont("Tahoma", 10)
    canvas.drawString(30*mm, h-18*mm, "PromoGuard")
    canvas.setStrokeColor(LINE)
    canvas.line(30*mm, h-23*mm, w-25*mm, h-23*mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Tahoma", 7.5)
    canvas.drawRightString(w-25*mm, 13*mm, rtl("گزارش داخلی کشف بازار و آمادگی فروش"))
    canvas.drawString(30*mm, 13*mm, str(doc.page))
    canvas.restoreState()

story = []
story += [
    Spacer(1,8*mm),
    P("نقشه مشتری اولیه، مسئله و برنامه ورود به بازار ایران","TitleFA"),
    P("گزارش تکمیل وظایف توسعه کسب و کار و بازاریابی PromoGuard - نسخه ۱۹ شهریور ۱۴۰۵","SubFA"),
    callout("تصمیم اجرایی: نقطه شروع PromoGuard باید یک برند یا شرکت پخش متوسط FMCG باشد که خروجی فروش و پروموشن را در سطح کالا، مشتری یا فروشگاه و تاریخ در Excel یا CSV دارد. پیشنهاد قابل فروش فعلی، ممیزی آمادگی داده و عملکرد مشاهده ای پروموشن در یک پایلوت محدود است؛ نه داشبورد عمومی، نه optimizer و نه تضمین سود."),
    Spacer(1,6*mm),
    callout("مرز گزارش: تحقیق میزکار، طراحی پیام، بخش بندی مشتری، سناریو، سوالات متداول، بسته خدمات و برنامه پیگیری انجام شده است. هنوز هیچ مصاحبه با خریدار، مجوز دریافت داده، قیمت قطعی یا مشتری تاییدشده ثبت نشده است. این موارد عمدا به عنوان اقدام انسانی باقی مانده اند.", YELLOW),
    Spacer(1,7*mm), P("خلاصه تصمیم","H1FA"),
    bullet("مشتری اول: تولیدکننده یا شرکت پخش متوسط FMCG با تصمیم های تکرارشونده درباره تخفیف، پروموشن و مناطق فروش."),
    bullet("خریدار اصلی: مدیر فروش، مدیر Trade Marketing یا مدیر Commercial؛ کاربر فنی پشتیبان: BI یا Data."),
    bullet("درد اصلی: فروش بعد از تخفیف بالا رفته، اما معلوم نیست افزایش incremental بوده یا ناشی از فصل، انتقال فروش، forward-buy یا کمبود موجودی است."),
    bullet("اولین خروجی: گزارش کیفیت داده، baseline شفاف، مقایسه قبل و بعد، هشدارها و فهرست داده لازم برای تست بعدی."),
    bullet("هدف این گزارش: آماده کردن مسیر تماس و پایلوت؛ اعتبار بازار فقط با گفت وگو و داده مجاز ساخته می شود."),
    PageBreak(),
]
story += [
    P("۱. شواهد بازار و انتخاب مشتری اولیه","H1FA"),
    P("تحقیق نشان می دهد مسئله واقعی است، اما بازار خالی نیست. شرکت های پخش و ERP از قبل سفارش، موجودی، تخفیف و گزارش فروش را پوشش می دهند. بنابراین PromoGuard نباید با وعده جایگزینی ERP وارد شود؛ باید لایه ممیزی و تصمیم قابل دفاع روی خروجی های موجود باشد."),
    grid(["شاهد بررسی شده","آنچه می گوید","نتیجه برای PromoGuard"],[
        ["پژوهش FMCG ایران","مطالعه ای کیفی روی مدیران بازاریابی FMCG ایران، سیستم اطلاعاتی شفاف، هماهنگی کانال و دانش به روز بازار را از عوامل عملکرد کانال می داند.","پیام ما باید به هماهنگی تصمیم و شفافیت داده وصل باشد، نه فقط مدل."],
        ["سپیدار پخش مویرگی","سفارش گیری، مسیر، سقف فروش، انواع تخفیف، برگشتی، موجودی و گزارش فروش را عرضه می کند.","رقیب مستقیم داشبورد ساده نیست؛ تمایز ما audit و limitation روی خروجی است."],
        ["NIQ Promotion Effectiveness","اثربخشی به داده فروش، ترفیع، مشتری، کالا و سنجه هایی مثل incremental sales و ROI نیاز دارد.","ورودی و Data Contract باید دقیق باشد و نقص داده را گزارش کند."],
        ["McKinsey CPG analytics","promotion analytics به منابع داده، ETL، تحلیل متناسب، pilot و مدیریت اجرا نیاز دارد.","نسخه اول باید pilot کوچک و قابل کنترل باشد، نه تحول سازمانی."],
        ["گزارش سالانه دیجی کالا ۱۴۰۲","یک بازیگر بزرگ ایرانی مقیاس بالای ترافیک، سفارش، فروشنده، برند و تبلیغات دارد.","فروشگاه آنلاین بزرگ مشتری بالقوه بلندمدت است، اما شروع سخت تری دارد."],
    ],[42*mm,65*mm,63*mm]),
    Spacer(1,5*mm), callout("نتیجه بازاریابی: مسئله در ادبیات و عرضه بازار شواهد دارد، اما willingness to pay در ایران هنوز validated نیست. برای اثبات آن باید حداقل ۸ مصاحبه، ۳ پیشنهاد پایلوت و یک نمونه داده ناشناس انجام شود.",YELLOW),
    Spacer(1,5*mm), P("مشتری ایده آل نسخه اول","H2FA"),
    bullet("حداقل ۶ ماه داده فروش روزانه یا هفتگی و چند SKU و چند منطقه یا مشتری."),
    bullet("تقویم تخفیف یا promotion flag و تصمیم واقعی که قرار است بر اساس گزارش گرفته شود."),
    bullet("خروجی Excel یا CSV و یک نفر که معنای ستون ها را توضیح دهد."),
    bullet("مدیر تصمیم گیرنده با اختیار شروع پایلوت محدود و تیم داده کوچک یا پراکنده."),
    PageBreak(),
]
story += [
    P("۲. بخش بندی مشتری و اولویت ورود","H1FA"),
    grid(["بخش","داده احتمالی","درد واقعی","اولویت"],[
        ["برند یا تولیدکننده FMCG","فروش کالا، مشتری یا کانال، قیمت، تخفیف، برگشتی و تقویم کمپین.","نمی داند تخفیف در کدام SKU و منطقه فروش اضافه ساخته و کجا margin را کم کرده.","A - شروع"],
        ["شرکت پخش","فاکتور، مشتری، مسیر، ویزیتور، موجودی، برگشتی، تخفیف و وصول.","مقایسه مناطق، مشتریان و کمپین ها زمان بر است.","A- - معرفی گرم"],
        ["فروشگاه زنجیره ای","POS، کالا، شعبه، قیمت، موجودی، loyalty و کمپین.","داده غنی دارد اما خرید پیچیده تر و BI داخلی قوی تر است.","B"],
        ["فروشگاه آنلاین","سفارش، کالا، قیمت، coupon، تبلیغ، session و inventory.","اثر coupon و قیمت مهم است، اما ابزار داخلی و رقابت فنی زیاد است.","B"],
        ["شرکت تحقیقات بازار","Retail audit، قیمت، سهم، distribution، پنل و داده بازار.","تحلیل و white-label می خواهد اما مالک تصمیم promotion برند نیست.","B - شریک"],
    ],[34*mm,53*mm,62*mm,21*mm]),
    Spacer(1,5*mm), P("چرا برند یا شرکت پخش متوسط؟","H2FA"),
    P("این گروه بین دو سر بازار قرار دارد: معمولا به اندازه کافی داده و هزینه تصمیم دارد، اما مثل یک خرده فروش بزرگ فرآیند procurement، امنیت و تیم کامل revenue management ندارد. برای شروع می توان با یک فایل و یک تصمیم محدود ارزش را نشان داد. این فرضیه عملی است و باید در مصاحبه رد یا تایید شود."),
    callout("قانون انتخاب lead: اگر سازمان داده تراکنشی یا تصمیم promotion ندارد، lead مناسب نیست. اگر از روز اول تضمین سود یا اجرای خودکار می خواهد، تا قبل از داده معتبر و کنترل انسانی وارد قرارداد نشویم.",RED),
    Spacer(1,5*mm), P("زبان هر نقش","H2FA"),
    grid(["نقش","نگرانی","پیام کوتاه"],[
        ["مدیر فروش","کدام تخفیف و منطقه را تکرار کنم؟","فایل شما را به تصمیم قابل دفاع تبدیل می کنیم و می گوییم کجا هنوز شواهد کافی نیست."],
        ["Trade Marketing","اثر کمپین و trade spend","فروش مشاهده شده را از توضیح های جایگزین و هشدار جدا می کنیم."],
        ["BI یا Data","کیفیت، schema و تکرارپذیری","قرارداد داده، hash، گزارش کیفیت و خروجی قابل بازبینی می دهیم."],
        ["مدیرعامل","ریسک هزینه و شروع","با یک فایل و پایلوت محدود شروع می شود و نصب سنگین لازم نیست."],
    ],[35*mm,60*mm,75*mm]),
    PageBreak(),
]
story += [
    P("۳. سه مسئله اصلی و سناریوی واقعی","H1FA"),
    P("مسئله اول - افزایش فروش واقعا از پروموشن بود؟ مدیر فروش افزایش فروش را می بیند، اما فصل، تعطیلات، تبلیغات، تغییر ترکیب کالا، توزیع و روند عادی همزمان تغییر کرده اند."),
    P("مسئله دوم - فروش بیشتر با margin بهتر همراه شد؟ حجم یا درآمد می تواند بالا برود، اما تخفیف، بهای تمام شده، برگشتی و هزینه کمپین سود را کم کنند. بدون تعریف هزینه و حاشیه، PromoGuard حق ندارد ROI بسازد."),
    P("مسئله سوم - کجا کمپین با ریسک موجودی یا forward-buy همراه شد؟ خرید زودهنگام فروش را در هفته کمپین بالا نشان می دهد و بعدا افت ایجاد می کند. اگر موجودی یا خرید مجدد در دسترس نباشد، فقط باید هشدار و limitation نشان دهیم."),
    Spacer(1,4*mm), P("سناریوی قابل ارائه به مشتری","H2FA"),
    grid(["گام","کار سیستم","خروجی برای مدیر"],[
        ["۱ - دریافت","فایل ۶ ماهه فروش در سطح تاریخ، کالا، فروشگاه یا مشتری، مقدار، قیمت و promotion flag به همراه Data Contract.","آیا فایل برای تحلیل آماده است؟ چه ستون هایی کم است؟"],
        ["۲ - اعتبارسنجی","کنترل تاریخ، grain، duplicate، missing، شناسه کالا، مقدار منفی، واحد پول، تخفیف و پوشش پروموشن.","اعتماد به ورودی و فهرست خطاهای قابل اصلاح."],
        ["۳ - اتصال رویداد","وصل کردن کمپین به کالا، بخش، منطقه و بازه زمانی؛ بدون حدس زدن مقادیر ناموجود.","دقیقا کدام event در حال بررسی است؟"],
        ["۴ - ممیزی","مقایسه قبل، حین و بعد با baseline؛ نمایش uncertainty، هشدار forward-buy و توضیح جایگزین.","تفاوت مشاهده شده چیست و چه چیزی هنوز اثبات نشده؟"],
        ["۵ - تصمیم","توصیه محدود: repeat، modify، stop یا gather more data؛ همراه limitation.","گام بعدی مشخص و کم ریسک، نه وعده سود."],
    ],[24*mm,78*mm,68*mm]),
    Spacer(1,5*mm), callout("نمونه خروجی: «در این بازه فروش در گروه X بالا رفته است، اما با داده فعلی نمی توانیم بگوییم علت آن فقط پروموشن بوده. نشانه forward-buy و نبود موجودی روزانه باعث می شود تصمیم فعلی gather more data باشد؛ برای تست بعدی موجودی، تقویم تبلیغات و گروه مقایسه لازم است.»"),
    PageBreak(),
]
faq = [
    ("این سیستم دقیقا چه کار می کند؟","فایل فروش و پروموشن را از نظر کیفیت بررسی می کند، رویداد را به کالا و بازه وصل می کند، فروش مشاهده شده را با baseline مقایسه می کند و محدودیت و هشدار می دهد."),
    ("چه فایلی باید بدهیم؟","برای شروع CSV یا Excel در سطح تاریخ، کالا، فروشگاه یا مشتری، مقدار فروش و نشانه قیمت یا پروموشن کافی است. موجودی، تقویم تعطیلات، تبلیغات و حاشیه سود دقت را بهتر می کنند."),
    ("حداقل داده چیست؟","حداقل شناسه کالا، زمان، واحد فروش یا درآمد، یک واحد تحلیل مثل فروشگاه یا کانال و تعریف روشن پروموشن لازم است. بدون اینها تحلیل محدود یا متوقف می شود."),
    ("آیا می گویید کمپین باعث افزایش فروش شد؟","فقط با طراحی و داده مناسب causal claim ممکن است. در نسخه فعلی خروجی مشاهده ای است و توضیح های جایگزین را شفاف نشان می دهد."),
    ("آیا سود یا ROI را حساب می کنید؟","فقط وقتی بهای تمام شده، تخفیف، هزینه کمپین و تعریف سود از مالک داده دریافت و راستی آزمایی شود. در غیر این صورت ROI نمی سازیم."),
    ("داده ما امن می ماند؟","فایل خام در Git قرار نمی گیرد؛ hash و metadata برای provenance ثبت می شود. محل ذخیره، حذف و سطح دسترسی باید در قرارداد انسانی مشخص شود و این MVP گواهی امنیتی نیست."),
    ("چقدر طول می کشد؟","برای فایل تمیز و use case محدود، هدف پایلوت ۷ تا ۱۰ روز کاری است. زمان قطعی بعد از دیدن sample file و تعریف خروجی تعیین می شود."),
    ("فرق با Power BI یا ERP چیست؟","جایگزین آنها نیست. ERP و BI ثبت و گزارش می کنند؛ PromoGuard روی آمادگی داده، ممیزی promotion، baseline و مرز ادعا تمرکز دارد."),
    ("اگر نتیجه قطعی نبود چه؟","این یک خروجی معتبر است. سیستم می گوید چه چیزی دیده شده، چه عاملی نتیجه را مخدوش می کند و برای تصمیم بعدی چه داده یا آزمایشی لازم است."),
    ("آیا نصب یا API لازم است؟","برای پایلوت اولیه نه. با CSV یا Excel شروع می کنیم. اتصال به ERP، database یا private deployment بعد از اثبات use case و قرارداد جداگانه است."),
]
story += [P("۴. سوالات مشتری و پاسخ آماده","H1FA")]
for i,(q,a) in enumerate(faq,1):
    story.append(KeepTogether([P(f"سوال {i}: {q}","FAQQ"),P(a,"FAQA")]))
story += [PageBreak()]
story += [
    P("۵. محصول و بسته خدماتی که الان می توان فروخت","H1FA"),
    P("نسخه اول باید یک خدمت داده محور با نرم افزار پشتیبان باشد. مشتری بابت نتیجه قابل ممیزی و تصمیم روشن پول می دهد، نه بابت تعداد نمودار یا اسم مدل."),
    grid(["بسته","دامنه","خروجی","وضعیت"],[
        ["Discovery","۳۰ دقیقه فهم مسئله، داده و تصمیم","Discovery note داخلی و تصمیم go/no-go","رایگان، انسانی"],
        ["Data Readiness Mini","یک فایل، یک دسته یا کانال، ۳ تا ۵ روز کاری","Data dictionary، کنترل کیفیت، فهرست gap و گزارش کوتاه","اولین بسته قابل فروش"],
        ["Promotion Audit Pilot","یک دسته، حداکثر ۱۰ SKU و یک بازه، ۷ تا ۱۰ روز کاری","ممیزی قبل/حین/بعد، baseline، هشدار و جلسه تحویل","پیشنهاد اصلی"],
        ["Pilot Plus","چند منطقه یا کانال با schema کامل تر","تحلیل چندبخشی و طراحی کنترل","پس از نمونه موفق"],
        ["Monitoring","دریافت دوره ای و گزارش ماهانه","تغییرات، کیفیت، هشدار و جلسه تصمیم","پس از دو اجرای واقعی"],
    ],[32*mm,54*mm,62*mm,22*mm]),
    Spacer(1,5*mm), P("قیمت گذاری آزمایشی","H2FA"),
    grid(["بسته","بازه پیشنهادی","شرط ارائه"],[
        ["Data Readiness Mini","۸ تا ۱۵ میلیون تومان","یک فایل و دامنه ثابت؛ پاکسازی سنگین جداگانه."],
        ["Promotion Audit Pilot","۲۰ تا ۴۰ میلیون تومان","یک دسته، یک بازه، حداکثر ۱۰ SKU و گزارش مشخص."],
        ["Pilot Plus","۴۰ تا ۸۰ میلیون تومان","پس از discovery و برآورد واقعی داده و جلسه."],
        ["Monitoring","۱۲ تا ۳۰ میلیون تومان در ماه","سقف ردیف و دفعات گزارش، بدون SLA مبهم."],
    ],[45*mm,42*mm,83*mm]),
    P("این اعداد نرخ رسمی بازار نیستند؛ فرضیه قیمت گذاری PromoGuard هستند و باید بعد از حداقل پنج گفت وگو و دو پیشنهاد واقعی اصلاح شوند. هزینه اتصال، استقرار، سفر و پشتیبانی اضافه جداگانه می آید.","SmallFA"),
    callout("فعلا نفروشیم: تضمین سود، causal lift با فایل ناقص، اجرای خودکار تخفیف، جایگزینی ERP، هوش مصنوعی که بهترین تخفیف را تضمین کند و تحلیل مشتری سطح فردی بدون قرارداد.",RED),
    PageBreak(),
]
story += [
    P("۶. برنامه پنج روزه تکمیل شده و خروجی آن","H1FA"),
    grid(["روز","کاری که انجام شد","خروجی آماده","باقی مانده انسانی"],[
        ["روز ۱","بخش بندی پنج گروه مشتری و انتخاب ICP.","اولویت A: برند یا پخش متوسط FMCG؛ اولویت B: زنجیره، آنلاین و تحقیقات بازار.","تایید یک فرد واقعی برای مصاحبه."],
        ["روز ۲","سه درد اصلی و مرز ادعا مشخص شد.","promotion effectiveness، margin، موجودی و forward-buy.","پرسیدن اینکه کدام درد واقعا تکرار می شود."],
        ["روز ۳","سناریوی فایل تا گزارش و تصمیم ساخته شد.","دریافت، validate، اتصال event، ممیزی و تصمیم.","گرفتن sample ناشناس و تعریف تصمیم واقعی."],
        ["روز ۴","۱۰ سوال مشتری با پاسخ غیرتبلیغاتی آماده شد.","FAQ قابل استفاده در جلسه و proposal.","ثبت اعتراض های واقعی مشتری."],
        ["روز ۵","خروجی به بسته محصول، قیمت فرضی و قیف فروش تبدیل شد.","این PDF، پیام فروش، بسته اول و برنامه ۳۰ روزه.","تماس، مصاحبه، NDA، اجازه داده و پیشنهاد."],
    ],[17*mm,59*mm,54*mm,40*mm]),
    Spacer(1,5*mm), P("چک لیست قبل از پیشنهاد","H2FA"),
    bullet("مشتری یک تصمیم مشخص دارد، نه فقط درخواست داشبورد."),
    bullet("فایل نمونه ناشناس یا فهرست دقیق ستون ها قابل دریافت است."),
    bullet("مالک داده، اجازه استفاده، هدف، retention و محل نگهداری روشن است."),
    bullet("قیمت بر اساس دامنه، زمان و خروجی نوشته شده و درصدی از سود ادعایی نیست."),
    bullet("گزارش شامل limitation و human review است و داده خام وارد GitHub نمی شود."),
    callout("کارهایی که من انجام دادم: تحقیق، تصمیم ICP، تحلیل جایگزین ها، ارزش پیشنهادی، سناریو، FAQ، بسته خدمات، قیمت فرضی و برنامه ۳۰ روزه. کارهایی که فقط شما می توانید انجام دهید: معرفی، تماس، مصاحبه، گرفتن نمونه داده و مجوز، مذاکره و امضا.",GREEN),
    PageBreak(),
]
story += [
    P("۷. برنامه ورود به بازار در ۳۰ روز","H1FA"),
    grid(["هفته","هدف","عدد قابل سنجش","خروجی"],[
        ["۱ - آماده سازی","فهرست حساب هدف و پیام شخصی سازی شده.","۲۰ سازمان، ۳۰ نقش تصمیم گیرنده، ۱۰ معرفی گرم.","one-pager و FAQ"],
        ["۲ - کشف","مصاحبه مسئله بدون فروش تهاجمی.","۸ مصاحبه، ۵ sample schema.","discovery form و pain log"],
        ["۳ - پیشنهاد","اجرای نمونه محدود با داده ناشناس.","۳ proposal با قیمت ثابت.","Proposal، Data Contract و NDA"],
        ["۴ - پایلوت","یک اجرای پولی یا design partner.","۱ قرارداد کوچک یا مجوز کتبی.","گزارش و جلسه تحویل"],
    ],[30*mm,63*mm,39*mm,38*mm]),
    Spacer(1,5*mm), P("متن معرفی کوتاه برای ارسال توسط رضا","H2FA"),
    callout("ما یک ERP یا داشبورد عمومی نمی فروشیم. در یک پایلوت ۷ تا ۱۰ روزه، یک خروجی ناشناس از فروش، قیمت و پروموشن شما را بررسی می کنیم و تحویل می دهیم: داده کجا قابل اعتماد است، کدام افزایش فروش فقط همزمان با تخفیف دیده شده، چه هشدارهایی وجود دارد و برای تصمیم بعدی چه چیزی باید اندازه گیری شود. اگر داده کافی نباشد، همان را شفاف گزارش می کنیم؛ عددسازی و وعده سود نداریم."),
    Spacer(1,5*mm), P("پرسش های انسانی هر تماس","H2FA"),
    bullet("آخرین پروموشنی که درباره اش تصمیم گرفتید چه بود و با چه گزارشی تصمیم گرفتید؟"),
    bullet("اگر فقط یک چیز را بهتر می فهمیدید، کدام تصمیم فروش تغییر می کرد؟"),
    bullet("فایل فروش در چه سطحی است: کالا، مشتری، فروشگاه، منطقه و روز یا هفته؟"),
    bullet("موجودی، stockout، تقویم تعطیلات و هزینه یا حاشیه سود در دسترس است؟"),
    bullet("برای پایلوت چه کسی مالک داده و چه کسی تصمیم گیرنده است؟"),
    bullet("اگر گزارش بگوید نتیجه قطعی نیست، سازمان حاضر است داده یا طراحی آزمایش را اصلاح کند؟"),
    callout("گیت تصمیم: اگر بعد از ۸ مصاحبه هیچ فردی درد را با یک تصمیم واقعی، داده قابل ارائه و بودجه آزمایشی تایید نکرد، ویژگی جدید نسازیم؛ اول ICP، پیام و دامنه خدمت را اصلاح کنیم.",YELLOW),
    PageBreak(),
]
story += [
    P("۸. منابع و تصمیم نهایی","H1FA"),
    P("منابع زیر برای راستی آزمایی مسئله، وجود جایگزین ها و شکل داده لازم استفاده شدند. هیچ کدام اثبات نمی کنند که یک شرکت خاص اکنون خریدار PromoGuard است."),
    grid(["منبع","استفاده در گزارش"],[
        ["Drivers of Marketing Channel Performance: Evidence from Iran","شاهد زمینه ای درباره سیستم اطلاعاتی و هماهنگی کانال در FMCG ایران. https://www.abacademies.org/articles/drivers-of-marketing-channel-performance-evidence-from-iran-8430.html"],
        ["سپیدار - نرم افزار پخش مویرگی","جایگزین عملیاتی برای سفارش، تخفیف، موجودی، مسیر و گزارش فروش. https://www.sepidarsystem.com/products/sepidar/distribution-software/"],
        ["NIQ - How to measure trade promotion effectiveness","تعریف trade promotion، incremental sales، KPI و ROI. https://nielseniq.com/global/en/insights/analysis/2022/how-to-measure-trade-promotion-effectiveness/"],
        ["NIQ - Promotion Effectiveness","نمونه عرضه تجاری مبتنی بر sales، loyalty و promotion measurement. https://nielseniq.com/global/en/products/promotion-planning-optimization/"],
        ["McKinsey - Analytics and CPG trade promotions","الگوی source of value، pilot و execution. https://www.mckinsey.com/capabilities/growth-marketing-and-sales/our-insights/how-analytics-can-drive-growth-in-consumer-packaged-goods-trade-promotions"],
        ["سپیدار - سیستم انبارداری","نشان می دهد ثبت موجودی و سود و زیان در ابزارهای موجود پوشش داده می شود. https://www.sepidarsystem.com/products/sepidar/warehouse-system/"],
        ["باشگاه مشتریان افق کوروش","نمونه عمومی تخفیف و loyalty در خرده فروشی زنجیره ای ایران. https://www.ofogh-koorosh.com/باشگاه-مشتریان/"],
        ["گزارش سالانه دیجی کالا ۱۴۰۲","شاهد مقیاس داده و پیچیدگی بازیگر آنلاین بزرگ. https://ecomotive.ir/wp-content/uploads/2024/08/Digikala-Report-1402-v16.3-web-03-05-30-standard-compress.pdf"],
    ],[57*mm,113*mm]),
    Spacer(1,6*mm), P("وضعیت نهایی تصمیم","H2FA"),
    callout("PromoGuard ایده قابل ارائه ای دارد، اما هنوز product-market fit اثبات نشده است. بهترین حرکت بعدی، تماس انسانی با یک برند یا شرکت پخش متوسط و اجرای یک Data Readiness Mini روی فایل ناشناس است. هر توسعه فنی که مستقیما به این مسیر کمک نکند فعلا اولویت پایین تری دارد.",GREEN),
    Spacer(1,5*mm), P("نسخه گزارش: ۰.۱ - تهیه شده برای تصمیم گیری داخلی تیم PromoGuard","SmallFA"),
]
OUT.parent.mkdir(parents=True, exist_ok=True)
doc = BaseDocTemplate(str(OUT), pagesize=A4, rightMargin=25*mm, leftMargin=25*mm, topMargin=29*mm, bottomMargin=22*mm, title="PromoGuard Business Discovery Report FA", author="PromoGuard")
frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
doc.addPageTemplates([PageTemplate(id="all", frames=frame, onPage=header_footer)])
doc.build(story)
print(OUT)
