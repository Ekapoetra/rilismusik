"""Generate Indonesian copyright declaration letters as PDF bytes."""
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_copyright_pdf_bytes(
    *, release: dict, tracks: list[dict], legal_entity: dict, document_settings: dict,
    signature_bytes: bytes, stamp_bytes: bytes | None = None,
) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="LetterTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=19, alignment=TA_CENTER, textColor=HexColor("#111111"), spaceAfter=6))
    styles.add(ParagraphStyle(name="LetterBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, alignment=TA_JUSTIFY, textColor=HexColor("#222222")))
    styles.add(ParagraphStyle(name="LetterSmall", parent=styles["BodyText"], fontSize=8.5, leading=12, textColor=HexColor("#555555")))
    company = legal_entity.get("company_name") or "PT. Jeeres Group Indonesia"
    city = legal_entity.get("city") or "Sintang"
    responsible = document_settings.get("responsible_person_name") or "Penanggung Jawab"
    title = document_settings.get("responsible_person_title") or "Direktur"
    issued = datetime.now(ZoneInfo("Asia/Jakarta"))
    number = f"HC/{issued:%Y%m}/{str(release.get('id') or '')[:8].upper()}"
    track_titles = [track.get("track_title") for track in tracks if track.get("track_title")]
    if not track_titles:
        track_titles = [release.get("release_title") or "—"]

    story = [
        Paragraph(f"<b>{company}</b>", styles["LetterTitle"]),
        Paragraph(f"{legal_entity.get('address_line1') or ''} {legal_entity.get('address_line2') or ''}", styles["LetterSmall"]),
        Spacer(1, 12),
        Paragraph("SURAT PERNYATAAN HAK CIPTA", styles["LetterTitle"]),
        Paragraph(f"Nomor: {number}", ParagraphStyle("Number", parent=styles["LetterSmall"], alignment=TA_CENTER)),
        Spacer(1, 18),
        Paragraph(f"Saya yang bertanda tangan di bawah ini, <b>{responsible}</b>, selaku <b>{title}</b> pada <b>{company}</b>, dengan ini menerangkan bahwa karya musik berikut dikelola untuk distribusi oleh RILIS MUSIK:", styles["LetterBody"]),
        Spacer(1, 12),
    ]
    rows = [
        ["Label", release.get("label_name") or "—"],
        ["Artist", release.get("artist_name") or "—"],
        ["Judul Rilisan", release.get("release_title") or "—"],
        ["Judul Track", ", ".join(track_titles)],
        ["© Copyright", release.get("copyright_line") or "—"],
        ["℗ Phonographic", release.get("p_line") or "—"],
    ]
    table = Table(rows, colWidths=[3.5 * cm, 11 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#F3F4F6")),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#D1D5DB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([
        table, Spacer(1, 16),
        Paragraph("Surat ini menyatakan bahwa berdasarkan data dan pernyataan yang disampaikan oleh label, hak atas karya tersebut berada pada pemilik hak yang sah dan dapat didistribusikan, dimonetisasi, serta dikelola sesuai perjanjian yang berlaku. Segala klaim pihak ketiga akan ditangani berdasarkan bukti kepemilikan dan ketentuan hukum yang berlaku.", styles["LetterBody"]),
        Spacer(1, 20), Paragraph(f"{city}, {issued:%d-%m-%Y}", styles["LetterBody"]),
        Paragraph(f"Untuk dan atas nama {company}", styles["LetterBody"]), Spacer(1, 8),
    ])
    signature = Image(BytesIO(signature_bytes), width=4.2 * cm, height=2.2 * cm, kind="proportional")
    if stamp_bytes:
        signature_table = Table([[signature, Image(BytesIO(stamp_bytes), width=2.3 * cm, height=2.3 * cm, kind="proportional")]], colWidths=[4.5 * cm, 3 * cm])
        signature_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
        story.append(signature_table)
    else:
        story.append(signature)
    story.extend([Spacer(1, 3), Paragraph(f"<b>{responsible}</b><br/>{title}", styles["LetterBody"])])
    doc.build(story)
    return output.getvalue()