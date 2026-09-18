"""Payslip PDF for a FINALIZED payroll period. Reads the immutable payroll_item
snapshot only (no recomputation) so the slip always matches what was finalized."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

import reportlab
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

FONT_DIR = Path(reportlab.__file__).parent / "fonts"
for font, filename in (("PS-Regular", "Vera.ttf"), ("PS-Bold", "VeraBd.ttf")):
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(FONT_DIR / filename)))
pdfmetrics.registerFontFamily("PS-Regular", normal="PS-Regular", bold="PS-Bold")

LOGO_PATH = Path(__file__).resolve().parents[2] / "frontend" / "public" / "brand" / "logo-full.png"
MONTHS = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember")

INK = HexColor("#171717")
MUTED = HexColor("#6B7280")
LINE = HexColor("#E5E7EB")
BRAND = HexColor("#C026D3")
NET_BG = HexColor("#111827")


def period_label(period_key: str) -> str:
    y, m = int(period_key[:4]), int(period_key[5:7])
    return f"{MONTHS[m - 1]} {y}"


def _rp(n) -> str:
    v = int(n or 0)
    sign = "-" if v < 0 else ""
    return f"{sign}Rp {abs(v):,.0f}".replace(",", ".")


def generate_payslip_pdf(staff: dict, period: dict, item: dict) -> bytes:
    output = BytesIO()
    pk = period.get("period_key", "")
    pdf = SimpleDocTemplate(output, pagesize=A4, leftMargin=54, rightMargin=54, topMargin=48, bottomMargin=52,
                            title=f"Slip Gaji {period_label(pk)}", author="RILIS MUSIK")
    body = ParagraphStyle("PSBody", fontName="PS-Regular", fontSize=10, leading=15, textColor=INK)
    label = ParagraphStyle("PSLabel", parent=body, fontSize=8.5, textColor=MUTED)
    brand = ParagraphStyle("PSBrand", parent=body, fontName="PS-Bold", fontSize=17, textColor=INK, leading=20)
    tag = ParagraphStyle("PSTag", parent=body, fontSize=8.5, textColor=MUTED, spaceBefore=1)
    slip = ParagraphStyle("PSSlip", parent=body, fontName="PS-Bold", fontSize=11, textColor=BRAND, alignment=TA_RIGHT)
    period_st = ParagraphStyle("PSPeriod", parent=body, fontSize=9, textColor=MUTED, alignment=TA_RIGHT)
    row_lbl = ParagraphStyle("PSRowL", parent=body, fontSize=10)
    row_val = ParagraphStyle("PSRowV", parent=body, fontSize=10, alignment=TA_RIGHT)
    sub = ParagraphStyle("PSSub", parent=body, fontSize=8.5, textColor=MUTED)
    net_lbl = ParagraphStyle("PSNetL", parent=body, fontName="PS-Bold", fontSize=12, textColor=white)
    net_val = ParagraphStyle("PSNetV", parent=body, fontName="PS-Bold", fontSize=15, textColor=white, alignment=TA_RIGHT)
    width = A4[0] - 108

    story = []

    # header: logo + brand ... slip label + period
    logo = Image(str(LOGO_PATH), width=46, height=46, kind="proportional")
    left = Table([[logo, Paragraph("RILIS MUSIK<br/><font size=8.5 color='#6B7280'>Distribusi Musik Digital</font>", brand)]],
                 colWidths=[52, 210])
    left.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    right = Table([[Paragraph("SLIP GAJI", slip)], [Paragraph(f"Periode {period_label(pk)}", period_st)]], colWidths=[width - 262])
    right.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    header = Table([[left, right]], colWidths=[262, width - 262])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    story += [header, Spacer(1, 10)]
    story += [Table([[""]], colWidths=[width], style=TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, BRAND)])), Spacer(1, 14)]

    # employee info
    printed = datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d/%m/%Y %H:%M WIB")
    info_cells = [
        ("Nama", staff.get("name") or "—"), ("Status", "FINAL"),
        ("Email", staff.get("email") or "—"), ("Periode", period_label(pk)),
        ("Jabatan", (staff.get("role") or "—").replace("_", " ").title()), ("Dicetak", printed),
    ]
    info_rows = []
    for i in range(0, len(info_cells), 2):
        l1, v1 = info_cells[i]
        l2, v2 = info_cells[i + 1]
        info_rows.append([Paragraph(l1, label), Paragraph(str(v1), body), Paragraph(l2, label), Paragraph(str(v2), body)])
    info = Table(info_rows, colWidths=[62, (width / 2) - 62, 62, (width / 2) - 62])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [info, Spacer(1, 16)]

    # earnings breakdown
    rows = [[Paragraph("RINCIAN", ParagraphStyle("h", parent=label, fontName="PS-Bold", textColor=INK)),
             Paragraph("JUMLAH", ParagraphStyle("h2", parent=label, fontName="PS-Bold", textColor=INK, alignment=TA_RIGHT))]]
    styles = [("LINEBELOW", (0, 0), (-1, 0), 0.7, INK)]
    rows.append([Paragraph("Gaji Pokok", row_lbl), Paragraph(_rp(item.get("salary_idr")), row_val)])
    allo = item.get("allowance_breakdown") or []
    if allo:
        for a in allo:
            rows.append([Paragraph(f"Tunjangan · {a.get('name', '')}", sub), Paragraph(_rp(a.get("amount_idr")), row_val)])
    elif int(item.get("allowance_idr") or 0):
        rows.append([Paragraph("Tunjangan", row_lbl), Paragraph(_rp(item.get("allowance_idr")), row_val)])
    bonus_bd = item.get("bonus_breakdown") or []
    if bonus_bd:
        for b in bonus_bd:
            nm = b.get("scheme_name") or "Bonus"
            if b.get("calc_mode") == "tiered":
                for t in (b.get("tiers") or []):
                    band = f"{_rp(t.get('from_idr'))}–{_rp(t.get('to_idr')) if t.get('to_idr') is not None else '∞'}"
                    rows.append([Paragraph(f"Bonus · {nm} · {t.get('percent')}% × {_rp(t.get('base_idr'))} <font size=7 color='#9CA3AF'>({band})</font>", sub),
                                 Paragraph(_rp(t.get("amount_idr")), row_val)])
            else:
                rows.append([Paragraph(f"Bonus · {nm} ({b.get('percent')}%)", sub), Paragraph(_rp(b.get("amount_idr")), row_val)])
    elif int(item.get("bonus_idr") or 0):
        rows.append([Paragraph("Bonus", row_lbl), Paragraph(_rp(item.get("bonus_idr")), row_val)])
    adj = item.get("adjustment_breakdown") or []
    if adj:
        for a in adj:
            rows.append([Paragraph(f"Penyesuaian · {a.get('reason', '')}", sub), Paragraph(_rp(a.get("amount_idr")), row_val)])
    elif int(item.get("adjustment_idr") or 0):
        rows.append([Paragraph("Penyesuaian", row_lbl), Paragraph(_rp(item.get("adjustment_idr")), row_val)])

    n = len(rows)
    styles += [("LINEBELOW", (0, 1), (-1, n - 1), 0.3, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
               ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
               ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]
    breakdown = Table(rows, colWidths=[width - 150, 150])
    breakdown.setStyle(TableStyle(styles))
    story += [breakdown, Spacer(1, 4)]

    # net payable band
    net = Table([[Paragraph("TOTAL DITERIMA", net_lbl), Paragraph(_rp(item.get("net_payable_idr")), net_val)]], colWidths=[width - 200, 200])
    net.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NET_BG), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("LEFTPADDING", (0, 0), (0, 0), 16), ("RIGHTPADDING", (-1, 0), (-1, 0), 16),
                             ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story += [net, Spacer(1, 22)]
    story += [Paragraph("Slip gaji ini dihasilkan otomatis oleh sistem RILIS MUSIK dan sah tanpa tanda tangan basah. "
                        "Nominal mengacu pada snapshot payroll periode yang telah difinalisasi.", tag)]

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("PS-Regular", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(54, 30, "RILIS MUSIK · Slip Gaji")
        canvas.drawRightString(A4[0] - 54, 30, f"Halaman {doc.page}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
