"""Unbranded formal A4 copyright statement based on the supplied DOCX."""
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import reportlab
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, KeepTogether, LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(reportlab.__file__).parent / "fonts"
for font, filename in (("CID-Regular", "Vera.ttf"), ("CID-Bold", "VeraBd.ttf")):
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily("CID-Regular", normal="CID-Regular", bold="CID-Bold")
MONTHS = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember")


def generate_contentid_pdf(document, signature, ktp):
    output = BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=A4, leftMargin=64, rightMargin=64, topMargin=58, bottomMargin=54,
                            title="Surat Pernyataan Kepemilikan Hak Cipta Atas Lagu", author="Pencipta")
    body = ParagraphStyle("CIDBody", fontName="CID-Regular", fontSize=10.5, leading=17, alignment=TA_JUSTIFY, textColor=HexColor("#171717"), spaceAfter=11)
    title = ParagraphStyle("CIDTitle", parent=body, fontName="CID-Bold", fontSize=14, leading=21, alignment=TA_CENTER, spaceAfter=26)
    small = ParagraphStyle("CIDSmall", parent=body, fontSize=9, leading=14, spaceAfter=0)
    plain = ParagraphStyle("CIDPlain", parent=body, alignment=0, spaceAfter=0)
    p = lambda text, style=body: Paragraph(escape(str(text)).replace("\n", "<br/>"), style)
    width = A4[0] - 128
    story = [p("SURAT PERNYATAAN KEPEMILIKAN\nHAK CIPTA ATAS LAGU", title), p("Saya yang bertanda tangan di bawah ini:")]
    identity = Table([[p(label, small), p(value, plain)] for label, value in [
        ("Nama lengkap", document["creator_name"]), ("NIK", document["nik"]),
        ("Kedudukan", "Pencipta Lagu"), ("Domisili", document["domicile"])]], colWidths=[103, width - 103], hAlign="LEFT")
    identity.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 2)]))
    story += [identity, Spacer(1, 16), p("Dengan ini menyatakan bahwa karya cipta atas lagu-lagu berikut:")]
    rows = [[p("Lagu", small), p("ISRC", small)]]
    rows.extend([[p(track["track_title"] or "—", plain), p(track.get("isrc") or "—", small)] for track in document["tracks"]])
    table = LongTable(rows, colWidths=[width - 128, 128], repeatRows=1, splitByRow=1, splitInRow=1, hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), .7, HexColor("#303030")),
                              ("LINEBELOW", (0, 1), (-1, -1), .3, HexColor("#DDDDDD")), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [table, Spacer(1, 10), p(f"Judul rilisan: {document['release_title']}\nUPC: {document.get('upc') or '—'}", small), Spacer(1, 18)]
    statement = ("adalah benar ciptaan saya sendiri dan bukan merupakan ciptaan pihak lain manapun serta tidak bertentangan dengan Hak Cipta atas lagu pihak lain manapun."
                 if document["authorship"] == "sole" else
                 "adalah benar ciptaan saya bersama pencipta lain yang berhak, bukan hasil pengambilan karya pihak lain tanpa hak, serta tidak bertentangan dengan Hak Cipta atas lagu pihak lain manapun.")
    story += [p(statement), p("Jika ternyata di kemudian hari Karya Cipta atas lagu tersebut terbukti bertentangan dengan Hak Cipta atas lagu pihak lain, maka Saya bersedia untuk mempertanggungjawabkannya secara hukum."),
              p("Demikian Pernyataan Kepemilikan Hak Cipta Atas Lagu ini saya buat dengan sebenarnya untuk menghindari adanya klaim pihak lain terhadap Hak Cipta atas lagu tersebut serta untuk dipergunakan sebagaimana mestinya.")]
    issued = datetime.fromisoformat(document["issued_at"]).astimezone(ZoneInfo("Asia/Jakarta"))
    date_label = f"{document['signing_city']}, {issued.day} {MONTHS[issued.month - 1]} {issued.year}"
    sign = Image(BytesIO(signature), width=146, height=66, kind="proportional"); sign.hAlign = "LEFT"
    signature_block = Table([[p(date_label, plain)], [p("Pencipta", plain)], [sign], [p(document["creator_name"], ParagraphStyle("CIDName", parent=plain, fontName="CID-Bold"))]], colWidths=[230], hAlign="RIGHT")
    signature_block.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story += [KeepTogether([Spacer(1, 15), signature_block]), PageBreak(), p("LAMPIRAN FOTO KTP PENULIS", title),
              p(f"{document['creator_name']}\nNIK {document['nik']}", plain), Spacer(1, 24)]
    ktp_image = Image(BytesIO(ktp), width=width, height=560, kind="proportional"); ktp_image.hAlign = "CENTER"
    story.append(ktp_image)

    def footer(canvas, doc):
        canvas.saveState(); canvas.setFont("CID-Regular", 8); canvas.setFillColor(HexColor("#777777"))
        canvas.drawRightString(A4[0] - 64, 30, f"Halaman {doc.page}"); canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()