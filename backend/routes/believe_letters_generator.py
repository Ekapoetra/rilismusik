"""Generate Believe-facing legal documents (Indemnification Letter & DMCA
Counter Notification) as PDF bytes. Wording matches the official Believe forms
verbatim; only the variable fields are filled in."""
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

DASH = "\u2014"


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DocTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=15, leading=19, alignment=TA_CENTER, textColor=HexColor("#111111"), spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, alignment=TA_JUSTIFY, textColor=HexColor("#222222"), spaceAfter=8))
    styles.add(ParagraphStyle(name="ListItem", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, leading=15, alignment=TA_JUSTIFY, textColor=HexColor("#222222"), leftIndent=16, spaceAfter=6))
    styles.add(ParagraphStyle(name="Field", parent=styles["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=HexColor("#111111"), spaceAfter=2))
    styles.add(ParagraphStyle(name="SectionHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=15, alignment=TA_JUSTIFY, textColor=HexColor("#111111"), spaceBefore=8, spaceAfter=6))
    return styles


def generate_indemnification_pdf_bytes(
    *, isrcs: list[str], upc: str, legal_entity: dict, document_settings: dict,
    signature_bytes: bytes | None = None, stamp_bytes: bytes | None = None,
) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=2.2 * cm, leftMargin=2.2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    styles = _styles()
    company = legal_entity.get("company_name") or "RILIS MUSIK"
    city = legal_entity.get("city") or "Indonesia"
    signatory = document_settings.get("responsible_person_name") or "Authorized Signatory"
    function = document_settings.get("responsible_person_title") or "Director"
    issued = datetime.now(ZoneInfo("Asia/Jakarta"))

    body = [
        'Dear partner (\u201cContractor, You, Your\u201d),',
        'Reference is made to the digital distribution agreement (\u201cAgreement\u201d) signed with Believe (\u201cBelieve\u201d). Save where a contrary indication appears, terms defined in the Agreement have the same meaning when used in this letter.',
        'As part of Believe\u2019s audio fingerprinting checks, some Content (described below) You recently delivered to Believe has matched a preexisting sound-recording flagged as being owned or controlled by a Third-Party (\u201cMatch\u201d). This Match could involve either a conflict of rights (exclusive ownership or control) over Your track with a Third-Party (\u201cConflict\u201d), or the reproduction of any samples of a Third-Party sound-recording in Your Content (\u201cReference Overlap\u201d).',
        'Further to receipt of the Claim, You hereby instruct Believe to reinstate the following disputed Content, based on Your confirmation that You own or control all necessary rights to it.',
    ]
    story = [Paragraph("INDEMNIFICATION LETTER", styles["DocTitle"]), Spacer(1, 6)]
    for para in body:
        story.append(Paragraph(escape(para), styles["Body"]))

    isrc_text = escape(", ".join([i for i in isrcs if i]) or "\u2014")
    story.append(Paragraph(f"<b>ISRC(s) of the same UPC:</b> {isrc_text}", styles["Field"]))
    story.append(Paragraph(f"<b>UPC:</b> {escape(upc or DASH)}", styles["Field"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("As a requirement from Believe to accept to perform such reinstatement, and by signing this letter You hereby represent, warrant, acknowledge and agree that:", styles["Body"]))
    items = [
        "You have been provided with all the relevant elements regarding such Match.",
        "You hold, control or have obtained all rights required to exploit the Content described above, and You have delivered it with accurate, truthful, and exhaustive metadata.",
        "In case of a Match impacting any Content You delivered to Believe as a cover song, a) You have entirely recorded the Recording delivered to Believe as a cover song, without reproducing any sample of the original sound-recording owned or controlled by the Third-Party, b) in the metadata associated with Your cover song, You have correctly credited authors, composers and publishers of the underlying musical works.",
        "If any proceeding is brought against Believe, or should Believe receive any notice from the Third-Party related to the Match, Believe shall at its discretion a) request the immediate withdrawal from all digital platforms of the disputed Content and b) withhold any payment due to You under the Agreement until the settlement of the dispute.",
        "You shall, in accordance with the Agreement, defend, indemnify and hold Believe and its affiliates harmless against any and all losses caused by any Claim(s) against Believe and/or its affiliates for damages, liabilities, costs and expenses (including court expenses and counsel fees) arising out of such Claim(s).",
        "You understand and agree that each copyright infringement event constituting a material breach of Your representations and warranties given under the Agreement, it is Believe policy and right to terminate accounts of clients who are repeated infringers or who are repeatedly charged with copyright infringement.",
        "Believe reserves the right to enforce all remedies and take all conservatory measures deemed necessary to protect its interests and to take any further action it might consider necessary.",
    ]
    for index, item in enumerate(items, 1):
        story.append(Paragraph(f"{index}. {escape(item)}", styles["ListItem"]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("The present representations and warranties are given without prejudice to those already given in the Agreement.", styles["Body"]))
    story.append(Paragraph("This confirmation must be provided in an original document signed by an authorized signatory (attached to an email) together with documentation evidencing that the person signing the confirmation is an authorized signatory.", styles["Body"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>FOR THE CONTRACTOR:</b>", styles["Field"]))
    story.append(Paragraph(f"Made in {escape(city)}, on {issued:%d %B %Y}", styles["Field"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Company:</b> {escape(company)}", styles["Field"]))
    story.append(Paragraph(f"<b>Authorized signatory:</b> {escape(signatory)}", styles["Field"]))
    story.append(Paragraph(f"<b>Function:</b> {escape(function)}", styles["Field"]))
    story.append(Paragraph("<b>Signature:</b>", styles["Field"]))
    if signature_bytes:
        signature = Image(BytesIO(signature_bytes), width=4.2 * cm, height=2.2 * cm, kind="proportional")
        if stamp_bytes:
            sig_table = Table([[signature, Image(BytesIO(stamp_bytes), width=2.3 * cm, height=2.3 * cm, kind="proportional")]], colWidths=[4.5 * cm, 3 * cm])
            sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
            story.append(sig_table)
        else:
            story.append(signature)
    doc.build(story)
    return output.getvalue()


def _checked(styles, text: str):
    return Table(
        [[Paragraph("\u2612", ParagraphStyle("cb", parent=styles["Body"], fontName="Helvetica-Bold", fontSize=12, leading=14, spaceAfter=0)), Paragraph(escape(text), ParagraphStyle("cbtxt", parent=styles["Body"], spaceAfter=0))]],
        colWidths=[0.7 * cm, 15.3 * cm],
    )


def generate_dmca_pdf_bytes(*, items: list[dict], explanation: str, contact: dict, signature_name: str) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=2.0 * cm, leftMargin=2.0 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm)
    styles = _styles()
    story = [Paragraph("DMCA Counter Notification Form", styles["DocTitle"]), Spacer(1, 6)]

    story.append(Paragraph("1. Identification of the ISRC(s) that has been removed or to which access has been disabled and the location at which the material appeared before it was removed or access to it was disabled ;", styles["SectionHead"]))
    for item in items:
        story.append(Paragraph(f"ISRC: {escape(item.get('isrc') or DASH)}", styles["Field"]))
        story.append(Paragraph(f"Track Title: {escape(item.get('title') or DASH)}", styles["Field"]))
        story.append(Paragraph(f"Artist: {escape(item.get('artist') or DASH)}", styles["Field"]))
        story.append(Paragraph("Distributed via Believe", styles["Field"]))
        story.append(Spacer(1, 4))

    story.append(Paragraph("2. distinctly explain why you believe that the removal of this content qualifies as a mistake or misidentification.", styles["SectionHead"]))
    story.append(Paragraph(escape(explanation or ""), styles["Body"]))

    story.append(Paragraph("3. Mandatory contact information:", styles["SectionHead"]))
    contact_lines = [
        ("full legal name - do not enter a company or channel name", contact.get("legal_name")),
        ("phone number", contact.get("phone")),
        ("email", contact.get("email")),
        ("country", contact.get("country")),
        ("street address", contact.get("street")),
        ("city", contact.get("city")),
        ("country", contact.get("country")),
        ("postcode", contact.get("postcode")),
    ]
    for label, value in contact_lines:
        story.append(Paragraph(f"- {escape(label)}: {escape(str(value or ''))}", styles["Field"]))

    story.append(Paragraph("4. Review the statements below and tick the boxes to agree", styles["SectionHead"]))
    story.append(_checked(styles, "Under penalty of perjury, I have good-faith belief that the material was removed or disabled as a result of a mistake or misidentification"))
    story.append(_checked(styles, "I consent to the jurisdiction of the Federal District Court in which my address is located, or if my address is outside of the United States, for any judicial district in which Believe may be found and will accept service of process from the claimant."))
    story.append(_checked(styles, "I understand that filing fraudulent counter notification may result in a) liability for any damages, including costs and attorneys' fees, by any copyright owner (or copyright owner's authorized licensee), or by Believe b) the termination of my digital distribution agreement with Believe."))

    story.append(Paragraph("5. Enter your full legal name as your signature", styles["SectionHead"]))
    story.append(Paragraph(f"<b>{escape(signature_name or '')}</b>", styles["Field"]))
    doc.build(story)
    return output.getvalue()
