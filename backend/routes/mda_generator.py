"""Master Distribution Agreement (MDA) PDF generator.

Auto-creates a single-source-of-truth distribution agreement when a label
registers. Uses reportlab to render a multi-page legal document with the
label's data merged into a static template + the CMS-driven legal entity
info (PT. Jeeres Group Indonesia + NIB, etc.).

The MDA is non-expiring (lifetime / until terminated). Payment tier
(Pay-Per-Release vs Subscription) is referenced as Schedule A but does
NOT affect the MDA's validity — the label can switch tier at any time.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)


PRIMARY = HexColor("#7C3AED")  # violet — matches frontend gradient
DARK = HexColor("#1A1A1A")


def _fmt_dmy(iso_date: str) -> str:
    """2026-06-24 -> 24 Juni 2026"""
    try:
        dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    except Exception:
        try:
            dt = datetime.strptime(iso_date[:10], "%Y-%m-%d")
        except Exception:
            return iso_date
    months_id = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{dt.day} {months_id[dt.month - 1]} {dt.year}"


def _styles():
    base = getSampleStyleSheet()
    s = {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=18, textColor=DARK, alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName="Helvetica",
            fontSize=10, textColor=grey, alignment=TA_CENTER, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=11, textColor=PRIMARY, spaceBefore=10, spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=DARK, alignment=TA_JUSTIFY,
            leading=13.5, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontName="Helvetica",
            fontSize=8, textColor=grey, alignment=TA_LEFT, leading=10,
        ),
        "sig": ParagraphStyle(
            "Sig", parent=base["Normal"], fontName="Helvetica",
            fontSize=9, textColor=DARK, alignment=TA_LEFT, leading=12,
        ),
    }
    return s


def build_mda_text(label: Dict[str, Any], legal: Dict[str, Any], accepted_at: str) -> Dict[str, str]:
    """Build a dict of dynamic text blocks for the MDA template."""
    company = legal.get("company_name") or "PT. Jeeres Group Indonesia"
    address = ", ".join(filter(None, [
        legal.get("address_line1"),
        legal.get("address_line2"),
        legal.get("city"),
        legal.get("postal_code"),
        legal.get("country"),
    ])) or "Sintang, Indonesia"
    nib = legal.get("nib") or "—"
    whatsapp = legal.get("whatsapp") or "—"
    return {
        "company_name": company,
        "company_address": address,
        "company_nib": nib,
        "company_wa": whatsapp,
        "label_name": label.get("label_name") or "—",
        "label_pic": label.get("pic_name") or "—",
        "label_email": label.get("email") or "—",
        "label_wa": label.get("whatsapp") or "—",
        "label_type": "Label Musik" if label.get("label_type") == "label" else "Artis Independen",
        "accepted_at_dmy": _fmt_dmy(accepted_at),
        "accepted_at_iso": accepted_at,
    }


def generate_mda_pdf(label: Dict[str, Any], legal_entity: Dict[str, Any], output_path: Path) -> Path:
    """Render the MDA PDF and write it to `output_path`.

    Returns the path (same as input) for convenience.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_at = label.get("created_at") or datetime.now(timezone.utc).isoformat()
    d = build_mda_text(label, legal_entity, accepted_at)
    s = _styles()

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title=f"MDA — {d['label_name']}",
        author=d["company_name"],
    )

    story = []

    # --- Header ---
    story.append(Paragraph("MASTER DISTRIBUTION AGREEMENT", s["title"]))
    story.append(Paragraph(f"Perjanjian Distribusi Musik Digital · No. {d['label_name'][:6].upper().replace(' ', '')}-{d['accepted_at_iso'][:10].replace('-', '')}", s["subtitle"]))
    story.append(Spacer(1, 8))

    # --- Parties table ---
    parties_data = [
        [Paragraph("<b>PIHAK PERTAMA (Distributor)</b>", s["body"]),
         Paragraph("<b>PIHAK KEDUA (Label)</b>", s["body"])],
        [Paragraph(
            f"<b>{d['company_name']}</b><br/>"
            f"{d['company_address']}<br/>"
            f"NIB: {d['company_nib']}<br/>"
            f"WhatsApp: {d['company_wa']}",
            s["body"]),
         Paragraph(
            f"<b>{d['label_name']}</b><br/>"
            f"PIC: {d['label_pic']}<br/>"
            f"Email: {d['label_email']}<br/>"
            f"WhatsApp: {d['label_wa']}<br/>"
            f"Jenis: {d['label_type']}",
            s["body"])],
    ]
    parties_table = Table(parties_data, colWidths=[8.5 * cm, 8.5 * cm])
    parties_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F4F4F5")),
        ("BOX", (0, 0), (-1, -1), 0.5, grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 10))

    # --- Recitals ---
    story.append(Paragraph(
        f"Pada hari ini, <b>{d['accepted_at_dmy']}</b>, Pihak Pertama dan Pihak Kedua "
        f"(secara bersama disebut sebagai &quot;Para Pihak&quot;) sepakat untuk mengikatkan "
        f"diri dalam Perjanjian Distribusi Musik Digital (&quot;Perjanjian&quot;) dengan "
        f"ketentuan-ketentuan sebagai berikut:",
        s["body"]
    ))

    # --- Sections ---
    sections = [
        ("PASAL 1 — DEFINISI",
         "<b>1.1 RILIS MUSIK</b> adalah platform distribusi musik digital yang dioperasikan oleh Pihak Pertama. "
         "<b>1.2 DSP (Digital Service Provider)</b> meliputi Spotify, Apple Music, YouTube Music, TikTok, "
         "Deezer, dan platform musik digital lainnya yang menjadi mitra distribusi Pihak Pertama. "
         "<b>1.3 Royalti</b> adalah pendapatan yang dihasilkan dari pemutaran/pembelian Konten di DSP, "
         "sesuai laporan resmi dari mitra agregator Believe. "
         "<b>1.4 Konten</b> adalah master rekaman, metadata, dan cover art yang diunggah oleh Pihak Kedua "
         "ke dalam dashboard RILIS MUSIK."),

        ("PASAL 2 — LISENSI DISTRIBUSI",
         "<b>2.1</b> Pihak Kedua menunjuk Pihak Pertama sebagai distributor <b>non-eksklusif</b> Konten ke "
         "150+ DSP melalui mitra agregator Believe. "
         "<b>2.2</b> Pihak Kedua menyatakan dan menjamin bahwa seluruh Konten yang diunggah adalah ciptaan "
         "asli, tidak melanggar hak cipta pihak ketiga, dan Pihak Kedua memiliki/menguasai seluruh hak "
         "ekonomi yang diperlukan untuk distribusi global. "
         "<b>2.3</b> Pihak Pertama berhak menolak, meminta revisi, atau melakukan takedown atas Konten "
         "yang melanggar hukum atau pedoman DSP."),

        ("PASAL 3 — SKEMA PEMBAYARAN (Schedule A)",
         "<b>3.1 Pay Per Release:</b> Pihak Kedua membayar Rp 35.000,- per submission rilisan, dibayar di "
         "muka via invoice Xendit. "
         "<b>3.2 Annual Normal:</b> Rp 350.000,- per tahun untuk unlimited submit. "
         "<b>3.3 Annual VIP:</b> Rp 500.000,- per tahun untuk unlimited submit + GRATIS pendaftaran "
         "WAMI/LMKN semua lagu + GRATIS konten promosi. "
         "<b>3.4 Add-on WAMI:</b> Rp 100.000,- per lagu untuk pendaftaran ke Lembaga Manajemen "
         "Kolektif Nasional (LMKN/WAMI), gratis untuk Pihak Kedua dengan paket Annual VIP aktif. "
         "<b>3.5</b> Pihak Kedua dapat berpindah skema pembayaran sewaktu-waktu tanpa membatalkan "
         "Perjanjian ini."),

        ("PASAL 4 — ROYALTI DAN BIAYA DISTRIBUTOR",
         "<b>4.1</b> Pihak Pertama memungut biaya distributor sebesar <b>5%</b> dari pendapatan kotor "
         "(gross revenue) Konten sebagaimana tercantum dalam laporan resmi Believe. "
         "<b>4.2</b> Pendapatan bersih (net revenue) dikonversi dari EUR ke IDR menggunakan kurs yang "
         "ditetapkan oleh Pihak Pertama per periode laporan. "
         "<b>4.3</b> Royalti dilaporkan secara transparan per lagu, per platform, dan per negara di "
         "dashboard Pihak Kedua dalam mata uang IDR. "
         "<b>4.4</b> Bagian Pihak Kedua atas royalti diatur secara internal oleh Pihak Pertama "
         "sebagai bagian dari skema kemitraan dan dapat dilihat sebagai nilai akhir IDR di dashboard."),

        ("PASAL 5 — JADWAL WITHDRAW",
         "<b>5.1</b> Pihak Kedua dapat mengajukan withdraw saldo IDR pada tanggal 1–14 setiap bulan. "
         "<b>5.2</b> Pembayaran dilakukan pada tanggal 15–20 setiap bulan ke rekening bank yang "
         "telah diverifikasi. "
         "<b>5.3</b> Minimum withdraw adalah <b>Rp 1.000.000,-</b> (satu juta rupiah). "
         "<b>5.4</b> Pengajuan di luar window tersebut akan ditolak otomatis oleh sistem."),

        ("PASAL 6 — KEPATUHAN DAN TAKEDOWN",
         "<b>6.1</b> Pihak Kedua wajib mematuhi pedoman komunitas masing-masing DSP. "
         "<b>6.2</b> Pihak Pertama dapat melakukan takedown Konten yang menerima klaim hak cipta, "
         "pengaduan plagiarism, atau pelanggaran ketentuan DSP, dengan/tanpa pemberitahuan terlebih dahulu. "
         "<b>6.3</b> Pihak Kedua dapat mengajukan takedown sukarela melalui tiket support."),

        ("PASAL 7 — JANGKA WAKTU DAN PENGAKHIRAN",
         "<b>7.1</b> Perjanjian ini berlaku sejak tanggal akseptasi dan terus berjalan tanpa batas waktu "
         "(<b>lifetime</b>) hingga salah satu Pihak melakukan pengakhiran tertulis. "
         "<b>7.2</b> Pihak Kedua dapat mengakhiri Perjanjian sewaktu-waktu dengan pemberitahuan 30 hari "
         "sebelumnya melalui tiket support. "
         "<b>7.3</b> Pihak Pertama dapat mengakhiri Perjanjian secara segera apabila Pihak Kedua "
         "melanggar Pasal 2.2 (jaminan hak cipta) atau ketentuan DSP secara materiil. "
         "<b>7.4</b> Setelah pengakhiran, Pihak Pertama akan menyelesaikan takedown seluruh Konten "
         "dalam 30 hari kerja, dan saldo IDR akan dibayarkan pada window withdraw berikutnya."),

        ("PASAL 8 — HUKUM YANG BERLAKU",
         "<b>8.1</b> Perjanjian ini tunduk pada hukum Republik Indonesia. "
         "<b>8.2</b> Setiap sengketa yang timbul akan diselesaikan terlebih dahulu secara musyawarah. "
         "<b>8.3</b> Apabila tidak tercapai kesepakatan, Para Pihak sepakat untuk menyelesaikannya di "
         "Pengadilan Negeri Sintang, Kalimantan Barat."),

        ("PASAL 9 — PERSETUJUAN ELEKTRONIK",
         "<b>9.1</b> Pihak Kedua mengakui bahwa persetujuan checkbox &quot;Saya Setuju MDA&quot; pada "
         "halaman registrasi RILIS MUSIK pada tanggal <b>{d_accepted}</b> memiliki kekuatan hukum yang "
         "sama dengan tanda tangan basah berdasarkan UU ITE No. 11/2008 jo. UU No. 19/2016. "
         "<b>9.2</b> Catatan akseptasi disimpan dalam sistem RILIS MUSIK sebagai bukti elektronik."
         .replace("{d_accepted}", d["accepted_at_dmy"])),
    ]
    for title, body in sections:
        story.append(Paragraph(title, s["h2"]))
        story.append(Paragraph(body, s["body"]))

    story.append(Spacer(1, 14))

    # --- Signature block ---
    sig_data = [
        [Paragraph("<b>PIHAK PERTAMA</b>", s["sig"]),
         Paragraph("<b>PIHAK KEDUA</b>", s["sig"])],
        [Paragraph(f"{d['company_name']}", s["sig"]),
         Paragraph(f"{d['label_name']}", s["sig"])],
        [Paragraph("<i>Ditandatangani secara digital melalui sistem RILIS MUSIK</i>", s["small"]),
         Paragraph(
            f"<i>Disetujui melalui checkbox elektronik pada {d['accepted_at_dmy']} "
            f"oleh <b>{d['label_pic']}</b>.</i>",
            s["small"])],
    ]
    sig_table = Table(sig_data, colWidths=[8.5 * cm, 8.5 * cm])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 1), (-1, 1), 0.5, grey),
    ]))
    story.append(sig_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Dokumen ini di-generate otomatis oleh RILIS MUSIK pada {d['accepted_at_iso']}. "
        f"Verifikasi keaslian dapat dilakukan melalui {d['company_wa']}.",
        s["small"]
    ))

    doc.build(story)
    return output_path
