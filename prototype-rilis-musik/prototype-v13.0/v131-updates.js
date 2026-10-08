/* V13.0 · D14 — Panduan pembaruan V1.0 → V1.1.
   Bukan log riwayat: daftar ini hanya memuat fitur yang benar-benar tersedia saat ini.
   Perbarui entri di updateGuide131 setiap kali fitur ditambah, diubah, atau dihapus —
   fitur yang tidak jadi tidak ditulis di sini. */

const updateKinds131={baru:['Baru','New','green'],berubah:['Berubah','Changed','mustard'],dihapus:['Dihapus','Removed','red']};

const updateGuide131=[
 {id:'start',icon:'shield',title:['Mulai & aktivasi','Getting started & activation'],items:[
  ['baru','Popup sambutan setelah masuk: member baru memilih bahasa dan tema lalu menjelajah dashboard; member lama diarahkan ke klaim label.','Welcome prompt after sign-in: new members pick language and theme then explore the dashboard; returning members are guided to label claims.'],
  ['berubah','Aktivasi akun tidak lagi menunggu pembayaran — cukup identitas label, kontrak, pemeriksaan admin, dan rekening.','Account activation no longer waits for payment — it needs label identity, the contract, admin review, and bank details.'],
  ['baru','Kontrak dibuat otomatis, tanggal kesepakatan tercatat, dan dapat diunduh dari menu Kontrak.','The contract is generated automatically, its acceptance date is recorded, and it can be downloaded from Contracts.'],
  ['baru','Mode coba paket: member baru dapat merasakan manfaat tiap paket (Basic, Studio, Pro, Business) dari dashboard tanpa mengubah langganan.','Package trial mode: new members can experience each tier’s benefits (Basic, Studio, Pro, Business) from the dashboard without changing the subscription.']]},
 {id:'claims',icon:'people',title:['Klaim label lama','Legacy label claims'],items:[
  ['berubah','Klaim label berbasis kejujuran: pernyataan kepemilikan wajib dan bukti pendukung opsional — tanpa kode OTP.','Label claims are honesty-based: a required ownership statement plus optional supporting evidence — no OTP code.'],
  ['baru','Persetujuan klaim hanya oleh Super Admin; akses label yang bermasalah dapat dicabut kembali oleh Super Admin.','Claim approval is Super Admin only; problematic label access can be revoked by Super Admin.'],
  ['baru','Klaim ganda pada satu label menjadi sengketa, dan saldo warisan dikarantina sampai Super Admin mengesahkan baseline.','Duplicate claims on one label become a dispute, and inherited balances are quarantined until Super Admin approves the baseline.']]},
 {id:'plans',icon:'wallet',title:['Paket, kredit & token','Plans, credits & tokens'],items:[
  ['berubah','Empat jenjang paket: Basic, Studio, Pro, dan Business. Harga final ditentukan terakhir.','Four plan tiers: Basic, Studio, Pro, and Business. Final pricing is decided last.'],
  ['baru','Harga layanan dipatok per layanan; penawaran token hanya tampil bila lebih murah dari vonis.','Service pricing is fixed per service; token offers appear only when cheaper than the stated price.'],
  ['baru','Aturan token: gagal dari distributor = token hangus; ditolak sebelum pengiriman = kembali; kesalahan sistem = kembali atau masuk pool ganti.','Token rules: distributor failure burns the token; rejection before delivery returns it; platform errors return it or go to the replacement pool.']]},
 {id:'money',icon:'wallet',title:['Penarikan & royalti','Withdrawals & royalties'],items:[
  ['berubah','Jadwal penarikan: pengajuan tanggal 1–14, pencairan tanggal 15–20.','Withdrawal schedule: requests on the 1st–14th, payouts on the 15th–20th.'],
  ['berubah','Verifikasi rekening hanya disetujui oleh Super Admin.','Bank verification is approved by Super Admin only.'],
  ['baru','Tarif royalti per label: label lama mempertahankan tarifnya, label baru menggunakan 60%.','Per-label royalty rate: existing labels keep their rate, new labels use 60%.']]},
 {id:'tickets',icon:'support',title:['Tiket & bantuan','Tickets & support'],items:[
  ['baru','Kategori tiket baru: "Masalah Royalti" dan "Permintaan Lainnya".','New ticket categories: "Royalty Issue" and "Other Requests".']]},
 {id:'system',icon:'settings',title:['Di balik layar','Behind the scenes'],items:[
  ['baru','Halaman Sistem untuk Super Admin: konten website, navigasi, prosedur, dan jadwal pemeliharaan — dengan draf, tinjauan, dan riwayat versi.','A System page for Super Admin: website content, navigation, procedures, and maintenance windows — with drafts, review, and version history.'],
  ['baru','Monitor label menampilkan tabel tarif khusus di luar 60%.','Label monitoring includes a table of special rates outside 60%.'],
  ['dihapus','Emblem dan level pencapaian label dihapus.','Label achievement emblems and levels were removed.'],
  ['baru','Menu Pembaruan ini — panduan perubahan dari V1.0 ke V1.1 yang selalu mengikuti fitur yang tersedia.','This Updates menu — a guide of changes from V1.0 to V1.1 that always follows what is available.']]}
];

function updateItem131([kind,idText,enText]){const [a,b,c]=updateKinds131[kind];return `<article class="update-item131"><span>${statusBadge111(T(a,b),c)}</span><p>${E(T(idText,enText))}</p></article>`}
function updatesPage131(){return pageHead(T('Pembaruan · V1.0 → V1.1','Updates · V1.0 → V1.1'),T('Catatan perubahan versi — hanya fitur yang benar-benar tersedia saat ini.','Release notes — only what is actually available right now.'))+`<div class="update-legend131">${Object.values(updateKinds131).map(([a,b,c])=>statusBadge111(T(a,b),c)).join(' ')}</div>${updateGuide131.map(s=>card10(`<span class="update-head131">${icon(s.icon)} ${T(...s.title)}</span>`,s.items.map(updateItem131).join(''),'full')).join('')}<p class="policy-note115">${T('Daftar ini adalah panduan penggunaan, bukan riwayat pengembangan — isinya mengikuti penambahan, perubahan, dan penghapusan fitur yang berlaku.','This list is a usage guide, not a development log — it follows the additions, changes, and removals currently in effect.')}</p>`}
