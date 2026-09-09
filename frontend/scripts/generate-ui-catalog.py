"""Developer-only OFFLINE catalog generation. Never reads database/user data or runs in app."""
import ast
import json
import re
from pathlib import Path
import ctranslate2
from subword_nmt.apply_bpe import BPE
from sacremoses import MosesTokenizer, MosesDetokenizer

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "frontend/src/i18n"
MODEL = ROOT / ".cache/ui-translation/model/translate-id_en-1_9"
# This OPUS model uses Moses + subword-nmt (@@), not OpenNMT joiners.
tokenizer = MosesTokenizer(lang="id")
detokenizer = MosesDetokenizer(lang="en")
with (MODEL / "bpe.model").open() as codes:
    bpe = BPE(codes)
engine = ctranslate2.Translator(str(MODEL / "model"), device="cpu", compute_type="int8", inter_threads=1, intra_threads=4)
sources = set(json.loads((DEST / "catalog.source.json").read_text()))
templates = set()
def eligible(value):
    return 3 <= len(value) <= 1600 and bool(re.search(r"[A-Za-z]{2}", value)) and not re.search(r"^(https?:|/|mongodb)|SELECT |INSERT |MONGO_|API_KEY|PASSWORD|SECRET", value) and not re.fullmatch(r"[a-z0-9_./:-]+", value)
for path in (ROOT / "backend/routes").glob("*.py"):
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeError):
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in {"detail", "title", "body"}:
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str) and eligible(value.value):
                sources.add(value.value)
            elif isinstance(value, ast.JoinedStr):
                parts, count = [], 0
                for item in value.values:
                    if isinstance(item, ast.Constant): parts.append(str(item.value))
                    else: parts.append("{" + str(count) + "}"); count += 1
                text = "".join(parts)
                if eligible(text) and len(re.sub(r"\{\d+\}", "", text)) >= 9:
                    sources.add(text); templates.add(text)
        if path.name == "admin_permission_service.py" and isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in {"name", "label", "description"} and isinstance(value, ast.Constant) and isinstance(value.value, str): sources.add(value.value)

manual = {
 "Saldo tersedia":"Available balance", "Saldo Tersedia":"Available Balance", "Saldo pending":"Pending balance", "Saldo Pending":"Pending Balance",
 "Penarikan Dana":"Withdrawals", "Tarik Saldo":"Withdraw Funds", "Tarik Dana":"Withdraw Funds", "Ditarik":"Withdrawn", "Belum Ditarik":"Not Yet Withdrawn",
 "Pengguna Admin":"Admin Users", "Rilisan":"Releases", "Rilisan Baru":"New Release", "Ajukan Rilisan":"Submit Release", "Submit Rilisan":"Submit Release",
 "Manajemen Label":"Label Management", "Manajemen Artis":"Artist Management", "Manajemen Rilisan":"Release Management", "Kontrak":"Contracts",
 "Bantuan":"Support", "Tiket Bantuan":"Support Tickets", "Tiket Support":"Support Tickets", "Royalti":"Royalties", "Royalti Musik":"Music Royalties",
 "Penyesuaian Saldo Royalti":"Royalty Balance Adjustments", "Inject Saldo":"Add Balance", "Cari":"Search", "Edit":"Edit", "Simpan":"Save", "Batal":"Cancel",
 "Aktif":"Active", "Draf":"Draft", "Diproses":"In Progress", "Ditolak":"Rejected", "Dibayar":"Paid", "Lunas":"Paid", "Selesai":"Completed",
 "Permintaan":"Requests", "Klaim Label":"Claim Existing Label", "Verifikasi Akun":"Account Verification", "Profil & Rekening":"Profile & Bank Account",
 "Ajukan Penarikan":"Request Withdrawal", "Ajukan penarikan":"Request withdrawal", "Total Royalti":"Total Royalties", "Bagian Label":"Label Share",
 "Artis":"Artists", "Artis Utama":"Primary Artists", "Artis Featuring":"Featured Artists", "Judul":"Title", "Judul Rilisan":"Release Title",
 "Judul Lagu":"Track Title", "Nama Label":"Label Name", "Nama Artis":"Artist Name", "Tanggal Rilis Digital":"Digital Release Date",
 "Lirik":"Lyrics", "Komposer":"Composer", "Produser":"Producer", "Penanggung Jawab":"Person in Charge", "Preview Audio":"Audio Preview",
 "Posisi pemutaran":"Playback position", "Bisukan":"Mute", "Volume":"Volume", "Label Dashboard":"Label Dashboard", "Buka menu":"Open menu",
 "Tutup menu":"Close menu", "Bentangkan sidebar":"Expand sidebar", "Ciutkan sidebar":"Collapse sidebar", "Uji suara":"Test sound",
 "Pesan Chat Baru":"New Chat Message", "Buka chat":"Open chat", "Aktifkan suara":"Enable sound", "Suara notifikasi":"Notification sounds",
 "Mode tampilan":"Appearance", "Terang":"Light", "Gelap":"Dark", "Otomatis":"Auto", "Bahasa":"Language", "Memuat…":"Loading…",
 "Tutup":"Close", "Putar":"Play", "Jeda":"Pause", "Unduh WAV":"Download WAV", "Belum tersedia":"Not available", "Tidak ada":"None",
 "Aksi":"Actions", "Aksi Cepat":"Quick Actions", "Pratinjau Tampilan":"Website Preview", "Pratinjau Role":"Role Preview", "Baca-saja":"Read-only",
 "Simulasi":"Simulation", "Data contoh — bukan data bisnis asli":"Sample data — not real business data", "Menu yang terlihat":"Visible menu",
 "Silakan pilih menu dari sidebar.":"Choose a menu from the sidebar.", "Tidak ada menu yang diizinkan.":"No menus are enabled for this role.",
 "Daftar Rilisan":"Release List", "Label":"Label", "Track dan Kredit":"Tracks & Credits", "Metode Pembayaran":"Payment Method",
 "Periode":"Period", "Sumber":"Source", "Jumlah":"Amount", "Status":"Status", "Ringkasan":"Overview", "Tagihan":"Invoices",
 "Januari":"January", "Februari":"February", "Maret":"March", "Mei":"May", "Juni":"June", "Juli":"July", "Agustus":"August", "Oktober":"October", "Desember":"December",
 "Senin":"Monday", "Selasa":"Tuesday", "Rabu":"Wednesday", "Kamis":"Thursday", "Jumat":"Friday", "Sabtu":"Saturday", "Minggu":"Sunday",
 "dari":"of", "baris":"rows", "rilisan":"releases", "label":"labels", "track":"tracks", "(opsional)":"(optional)",
}
indonesian = {
 "Command Center":"Pusat Kendali", "Admin Dashboard":"Dasbor Admin", "Label Dashboard":"Dasbor Label", "Artist Dashboard":"Dasbor Artis",
 "Admin Console":"Konsol Admin", "Dashboard":"Dasbor", "Support Tickets":"Tiket Bantuan", "Role & Permission":"Role & Izin",
 "Artist Management":"Manajemen Artis", "Release Management":"Manajemen Rilisan", "Label Management":"Manajemen Label",
 "Streams":"Pemutaran", "History":"Riwayat", "Settings":"Pengaturan", "Overview":"Ringkasan", "Pending":"Tertunda", "Active":"Aktif",
 "Approved":"Disetujui", "Rejected":"Ditolak", "Draft":"Draf", "Published":"Dipublikasikan", "Archived":"Diarsipkan",
 "Read-only":"Baca-saja", "Source":"Sumber", "Period":"Periode", "Actions":"Aksi", "Action":"Aksi", "Name":"Nama",
 "Title":"Judul", "Description":"Deskripsi", "Close":"Tutup", "Submit":"Kirim", "Save":"Simpan", "Cancel":"Batal",
 "Delete":"Hapus", "Search":"Cari", "Apply":"Terapkan", "Answer":"Jawaban", "Required":"Wajib", "Optional":"Opsional",
 "Refresh":"Muat Ulang", "Preview":"Pratinjau", "Preview Audio":"Pratinjau Audio", "Download":"Unduh", "Edit":"Ubah",
 "Brand Name":"Nama Merek", "Breakdown per Label":"Rincian per Label", "Total Rows":"Total Baris", "Total Revenue":"Total Pendapatan",
 "Unique Tracks":"Track Unik", "Recent Activity":"Aktivitas Terbaru", "Recent Releases":"Rilisan Terbaru", "View All":"Lihat Semua",
 "Permissions":"Izin", "User Management":"Manajemen Pengguna", "Module":"Modul", "Navigation":"Navigasi", "Notifications":"Notifikasi",
 "Empty":"Kosong", "Success":"Berhasil", "Error":"Kesalahan", "Loading…":"Memuat…", "Invoice":"Tagihan", "Invoices":"Tagihan",
}
sources.update(manual)
cache = {key: key for key in indonesian}
cache.update(manual)
reviewed_path = DEST / "catalog.reviewed.json"
reviewed = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else {}
cache.update(reviewed)
todo = sorted(sources - cache.keys())
def translate_many(values):
    batches = [bpe.process_line(tokenizer.tokenize(value, return_str=True)).split() for value in values]
    result = engine.translate_batch(batches, beam_size=4, max_decoding_length=400, repetition_penalty=1.1)
    return [re.sub(r"\{\s*(\d+)\s*\}", r"{\1}", detokenizer.detokenize(" ".join(row.hypotheses[0]).replace("@@ ", "").split())) for row in result]
for start in range(0, len(todo), 32):
    batch = todo[start:start + 32]
    for source, translated in zip(batch, translate_many(batch)):
        placeholders = re.findall(r"\{\d+\}", source)
        if sorted(placeholders) != sorted(re.findall(r"\{\d+\}", translated)):
            segments = re.split(r"(\{\d+\})", source)
            chunks = [item for item in segments if item and not re.fullmatch(r"\{\d+\}", item)]
            mappings = dict(zip(chunks, translate_many(chunks)))
            translated = "".join(item if item not in mappings else (" " if item.startswith(" ") else "") + mappings[item].strip() + (" " if item.endswith(" ") else "") for item in segments)
        if "RILIS MUSIK" in source or re.fullmatch(r"#[0-9a-fA-F]+", source): translated = source
        cache[source] = translated or source
    cache.update(manual)
    cache.update(reviewed)
    (DEST / "catalog.en.json").write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n")
    print(f"Translated {min(start + 32,len(todo))}/{len(todo)}", flush=True)
cache.update(manual)
cache.update(reviewed)
(DEST / "catalog.en.json").write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n")
(DEST / "catalog.id.json").write_text(json.dumps(indonesian, ensure_ascii=False, indent=2) + "\n")
(DEST / "catalog.patterns.json").write_text(json.dumps(sorted(templates), ensure_ascii=False, indent=2) + "\n")
print(f"Complete: {len(cache)} English strings, {len(indonesian)} Indonesian refinements, {len(templates)} system templates.", flush=True)