/* Pseudonimisasi cuplikan produksi (dipakai preview-api/sample.js saat ekspor
   dan prototype-rilis-musik/build-sample.cjs saat membangun sample131-data.js).

   Prinsip: DEFAULT-DENY untuk teks. Nilai string hanya dipertahankan bila
   kuncinya ada di daftar aman (status, genre, kota, nama bank, …) atau nilainya
   jelas berbentuk id/enum/tanggal. Nama label/artis/judul/orang, email, nomor
   WhatsApp, alamat, URL/berkas, ISRC/UPC dan teks bebas (tiket, chat, catatan)
   diganti nilai palsu yang deterministik: nilai asli yang sama → nilai palsu
   yang sama di seluruh dokumen (satu instance pseudonymizer per ekspor).
   Modul ini tidak menyimpan nilai asli apa pun. */

const fnv=s=>{let h=0x811c9dc5;for(const ch of String(s)){h^=ch.codePointAt(0);h=Math.imul(h,0x01000193)>>>0;}return h;};
const norm=s=>String(s??'').trim().replace(/\s+/g,' ').toLowerCase();
const slugify=s=>String(s||'').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,24)||'label';
const cross=(a,b,sep=' ')=>a.flatMap(x=>b.map(y=>x+sep+y));

const POOLS={
  label:['Nusantara Records','Senja Musik','Lentera Sound','Kenari Rekaman','Pelangi Nada','Samudra Audio','Rimba Musik','Kopi Senja Records','Bintang Timur Musik','Arunika Records','Swara Kita','Gema Pertiwi','Teras Rumah Records','Langit Jingga Musik','Ombak Selatan Records','Cakrawala Sound','Purnama Rekaman','Kabut Pagi Records','Melodi Kampung','Nada Seberang','Jati Sound','Pucuk Records','Lembayung Musik','Tanah Air Audio','Kelana Records','Biru Laut Musik','Daun Muda Records','Sinar Mentari Sound','Rumah Nada','Simfoni Timur','Lintas Nada','Pena Musik','Serambi Records','Cendana Audio','Galaksi Rekaman','Tepian Musik'],
  artist:cross(['Raka','Nara','Dimas','Sekar','Bara','Lintang','Kirana','Gilang','Ayu','Arya','Rendra','Tiara','Banyu','Satria','Laras','Bayu','Galih','Intan','Jaka','Wening'],['Senandika','Kelana','Asmara','Samudra','Pamungkas','Kencana','Biru','Nada','Swara','Jingga','Pertiwi','& Kawan','Band','Project','Trio','Akustik','Sentosa','Mahendra']),
  title:cross(['Senja','Rindu','Langit','Hujan','Pelangi','Bintang','Ombak','Angin','Cahaya','Fajar','Malam','Bulan','Samudra','Kabut','Jejak','Lentera','Mimpi','Purnama','Rembulan','Kenangan'],['di Kota','Terakhir','Biru','yang Hilang','Pertama','Selamanya','Kita','Merah','Sunyi','di Pelabuhan','Utara','Abadi','Kecil','Pagi','Jingga']),
  person:cross(['Andi','Budi','Citra','Dewi','Eka','Fajar','Gita','Hadi','Indah','Joko','Kartika','Lestari','Maya','Nanda','Oki','Putri','Rizky','Sari','Tono','Wulan','Yusuf','Zahra'],['Pratama','Wijaya','Saputra','Permana','Hidayat','Nugroho','Kusuma','Santoso','Permata','Halim','Setiawan','Rahmawati']),
  street:['Jl. Melati','Jl. Kenanga','Jl. Flamboyan','Jl. Cempaka','Jl. Anggrek','Jl. Mawar','Jl. Dahlia','Jl. Teratai']
};
const FALLBACK={label:'Label Contoh',artist:'Artis Contoh',title:'Lagu Contoh',person:'Pengguna Contoh'};

const TEXT={
  label:['Halo admin, mohon bantuan untuk pengecekan rilisan kami.','Baik, terima kasih atas informasinya.','Sudah kami perbaiki sesuai catatan, mohon dicek kembali.','Apakah ada dokumen tambahan yang perlu kami kirim?','Mohon info estimasi waktu prosesnya.','Terima kasih, kami tunggu kabar selanjutnya.'],
  admin:['Halo, permintaan Anda sudah kami terima dan sedang diproses.','Mohon lengkapi data yang diminta agar dapat kami lanjutkan.','Sudah kami teruskan ke tim terkait, mohon ditunggu.','Proses sudah selesai, silakan dicek kembali.','Terima kasih, data sudah kami perbarui.','Mohon maaf atas keterlambatannya, kami sedang menindaklanjuti.'],
  system:['Status tiket diperbarui.','Permintaan diteruskan ke agregator.','Tiket ditutup oleh sistem.','Permintaan dicatat oleh sistem.'],
  note:['Mohon perbaiki metadata sesuai panduan.','Sampul perlu disesuaikan dengan ketentuan platform.','Data sudah sesuai, siap diproses.','Periksa kembali ejaan judul dan nama artis.','Menunggu konfirmasi dari label.'],
  kyc:['Dokumen identitas kurang jelas, mohon unggah ulang.','Nama pada dokumen tidak sesuai dengan data akun.','Dokumen sudah kedaluwarsa, mohon unggah dokumen terbaru.'],
  ticket:['Mohon bantuan untuk menindaklanjuti permintaan terkait rilisan ini.','Kami ingin memperbarui data rilisan sesuai informasi terbaru.','Permintaan penurunan rilisan dari seluruh platform.','Mohon dicek karena ada ketidaksesuaian data di platform.'],
  generic:['Teks contoh untuk prototipe.','Keterangan disamarkan untuk prototipe.','Catatan contoh (data asli tidak disertakan).']
};

/* Alasan takedown yang berupa pilihan tetap (bukan teks bebas) — aman dipertahankan. */
const KNOWN_REASONS=new Set(['Revisi Metadata','Pindah Aggregator','Konflik Hak Cipta','Konflik Internal']);

function createPseudonymizer(){
  const maps={slug:new Map(),label:new Map(),artist:new Map(),title:new Map(),person:new Map(),email:new Map(),phone:new Map(),address:new Map(),isrc:new Map(),upc:new Map(),ref:new Map(),file:new Map(),digits:new Map()};
  const skip={label:0,artist:0,title:0,person:0};
  const reserved=new Set();
  const used=new Set();
  const emails=new Set();
  const pick=(kind,real)=>{
    const k=norm(real);if(!k)return real;
    const m=maps[kind];if(m.has(k))return m.get(k);
    const pool=POOLS[kind];let out=null;
    while(!out){
      const i=m.size+skip[kind];
      const cand=i<pool.length?pool[(i*7)%pool.length]:`${FALLBACK[kind]} ${i-pool.length+1}`;
      /* Tolak kandidat yang sama dengan nilai asli mana pun — termasuk bila
         salah satu kata/pasangan katanya adalah nilai asli (mis. judul asli satu kata). */
      const fromPool=i<pool.length;
      const words=norm(cand).split(' ');
      const parts=fromPool?[norm(cand),...words.filter(x=>x.length>=4),...words.slice(1).map((x,j)=>words[j]+' '+x)]:[norm(cand)];
      if(parts.some(x=>reserved.has(x))||used.has(kind+'|'+norm(cand))){skip[kind]++;continue;}
      out=cand;
    }
    used.add(kind+'|'+norm(out));m.set(k,out);return out;
  };
  const seq=(kind,real,fmt)=>{const k=norm(real);if(!k)return real;const m=maps[kind];if(!m.has(k))m.set(k,fmt(m.size+1));return m.get(k);};
  const ps={
    /* Kumpulkan semua string pendek dari data asli supaya nilai palsu tidak
       kebetulan sama dengan nilai asli mana pun. */
    reserveFrom(v){const walk=x=>{if(Array.isArray(x))x.forEach(walk);else if(x&&typeof x==='object')Object.values(x).forEach(walk);else if(typeof x==='string'&&x.length<=80)reserved.add(norm(x));};walk(v);return ps;},
    label:v=>pick('label',v),
    artist:v=>pick('artist',v),
    title:v=>pick('title',v),
    person:v=>pick('person',v),
    email:(v,hint)=>seq('email',v,n=>{let e=(hint?slugify(hint):'pengguna-'+n)+'@contoh.test';if(emails.has(e))e=e.replace('@','-'+n+'@');emails.add(e);return e;}),
    phone:v=>seq('phone',String(v).replace(/\D/g,'')||v,n=>`0812-0000-${String(n).padStart(4,'0')}`),
    address:v=>seq('address',v,n=>`${POOLS.street[(n-1)%POOLS.street.length]} No. ${n}`),
    isrc:v=>seq('isrc',v,n=>{const yy=/^[A-Z]{2}[A-Z0-9]{3}(\d{2})/i.exec(String(v))?.[1]||'26';return 'IDP00'+yy+String(n).padStart(5,'0');}),
    upc:v=>seq('upc',v,n=>'899000'+String(n).padStart(7,'0')),
    slug:v=>seq('slug',v,n=>'contoh-'+n),
    ref:v=>seq('ref',v,n=>'REF-P'+String(n).padStart(4,'0')),
    file:v=>seq('file',v,n=>{const ext=/\.([a-z0-9]{2,5})$/i.exec(String(v))?.[1];return 'berkas-contoh-'+n+(ext?'.'+ext.toLowerCase():'');}),
    url:v=>v?'https://contoh.test/berkas/'+seq('file',v,n=>String(n)):v,
    /* Nomor rekening yang sudah disamarkan (••••1234): digit asli diganti. */
    maskedNumber:v=>{const s=String(v??'');if(!s)return s;const tail=seq('digits',s,n=>String(1000+n).slice(-4));return s.replace(/\d{1,4}$/,'').replace(/\d/g,'•')+tail;},
    text:(kind,v)=>{if(v==null||v==='')return v;const pool=TEXT[kind]||TEXT.generic;return pool[fnv(v)%pool.length];},
    maps
  };
  return ps;
}

/* ---------- Dokumen mentah (ekspor preview-api) ---------- */
const ID_LIKE=/^(?:[0-9a-f]{24}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
const DATE_LIKE=/^\d{4}-\d{2}(-\d{2}([T ][\d:.]+(Z|[+-]\d{2}:?\d{2})?)?)?$/;
const ENUM_LIKE=/^[a-z0-9_.:\/-]{0,48}$/;
const NUM_LIKE=/^-?\d+(\.\d+)?$/;
const ID_KEY=/^(id|uuid)$|_ids?$/i;
const SAFE_KEY=/^(status|.*_status|role|role_name|kind|type|.*_type|category|category_label|genre|subgenre|language|.*_language|platform|platforms|country|city|province|bank_name|currency|period|period_from|period_to|plan|tier|subscription_tier|payment_type|source|action|module|work_type|completion_action|label_type|auto_created_from|vocal_type|release_type|month|year|ticket_no|unit|channel|method|gateway)$/i;
const SAFE_NAME_COLLECTIONS=new Set(['payment_products','service_orders','addon_orders']);
const SAFE_NAME_PARENTS=new Set(['selected_addons','addons','items','products']);

const K={
  masked:/account_number|^nik$|^nib$|id_number|ktp|npwp|card_number/i,
  slug:/slug/i,
  ident:/google_(subject|provider_id)|provider_id|device_id|ip_address|user_agent/i,
  email:/email/i,
  phone:/whatsapp|phone|mobile|telp|(^|_)wa($|_)/i,
  address:/address|street|postal|zip|alamat/i,
  isrc:/isrc/i,
  upc:/(^|_)(upc|ean|barcode)($|_)/i,
  url:/url|(^|_)uri($|_)|link|picture|avatar|photo|image|logo|cover|previews|social|instagram|tiktok|youtube|spotify|facebook|twitter|website|(^|_)web($|_)|handle|username/i,
  file:/file|path|storage_key|(^|_)key$/i,
  label:/label_name|company_name|brand_name|site_title/i,
  artist:/artist|performer|featuring/i,
  person:/pic_name|responsible_name|holder|by_name|user_name|sender_name|claim_legacy_name|composer|lyricist|producer|arranger|songwriter|author|decided_by|completed_by|accepted_by|created_by|deleted_by|updated_by|reviewed_by|approved_by|(^|_)name$/i,
  title:/title/i,
  copyright:/copyright|p_line|pline|c_line/i,
  reference:/reference|invoice|external_id|transaction_id|payment_ref/i,
  lyrics:/lyric/i,
  text:/body|description|desc$|note|reason|message|comment|text|content|subject|summary|preview|remark|memo|quote|headline|feedback|details|entity_ref|^q$|^a$/i
};

function scrubString(ps,key,s,ctx){
  if(s==='')return s;
  const k=String(key||'');
  if(ID_LIKE.test(s)||DATE_LIKE.test(s))return s;
  if(K.masked.test(k))return ps.maskedNumber(s);
  if(K.email.test(k))return ps.email(s);
  if(K.ident.test(k))return '[disamarkan]';
  if(K.slug.test(k))return ps.slug(s);
  if(ID_KEY.test(k))return s;
  if(K.phone.test(k))return ps.phone(s);
  /* role hanya aman sebagai enum/peran akun (bukan mis. jabatan pada testimoni). */
  if(/^role(_name)?$/i.test(k)&&!(ENUM_LIKE.test(s)||ctx.collection==='users'))return '[disamarkan]';
  if(SAFE_KEY.test(k))return s;
  if(K.isrc.test(k))return ps.isrc(s);
  if(K.upc.test(k))return ps.upc(s);
  if(K.address.test(k))return ps.address(s);
  if(K.url.test(k))return ps.url(s);
  if(K.file.test(k))return ps.file(s);
  if(k==='name'){
    if(SAFE_NAME_COLLECTIONS.has(ctx.collection)||SAFE_NAME_PARENTS.has(ctx.parent))return s;
    if(ctx.collection==='labels'&&!ctx.parent)return ps.label(s);
    if(/artist/i.test(ctx.parent||'')||ctx.collection==='artists')return ps.artist(s);
    return ps.person(s);
  }
  if(K.label.test(k))return ps.label(s);
  if(K.artist.test(k))return /_ids?$/.test(k)?s:ps.artist(s);
  if(K.person.test(k))return ENUM_LIKE.test(s)?s:ps.person(s);
  if(K.lyrics.test(k))return '[lirik disamarkan]';
  if(K.copyright.test(k))return '℗ '+ps.label(s);
  if(K.title.test(k))return ps.title(s);
  if(K.reference.test(k))return ENUM_LIKE.test(s)?s:ps.ref(s);
  if(k==='reason'&&KNOWN_REASONS.has(s))return s;
  if(SAFE_NAME_COLLECTIONS.has(ctx.collection)&&/^(name|description)$/.test(k))return s;
  if(K.text.test(k))return ps.text(/kyc|rejection/i.test(k)?'kyc':/note/i.test(k)?'note':'generic',s);
  if(ENUM_LIKE.test(s)||NUM_LIKE.test(s))return s;
  return '[disamarkan]';
}

/* Telusuri nilai (ObjectId/Date sudah diubah oleh sample.clean) dan samarkan
   setiap string sesuai kuncinya. ctx: {collection, parent}. */
function scrubValue(ps,v,ctx={},key=''){
  /* Elemen array memakai kunci array-nya (platforms[] → 'platforms'). */
  if(Array.isArray(v))return v.map(x=>scrubValue(ps,x,ctx,key));
  if(v&&typeof v==='object'){
    const out={};
    for(const [k,x] of Object.entries(v))out[k]=scrubValue(ps,x,{...ctx,parent:key||ctx.parent||''},k);
    return out;
  }
  if(typeof v==='string')return scrubString(ps,key,v,ctx);
  if(typeof v==='number'&&K.phone.test(key))return ps.phone(String(v));
  return v;
}

/* ---------- Bentuk ringkas sample131-data.js (build-sample.cjs) ---------- */
function pseudonymizeCompact(src){
  const out=JSON.parse(JSON.stringify(src));
  const ps=createPseudonymizer().reserveFrom(src);
  const reservedIds=new Set(['awan','embun']);
  const uniq=base=>{let id=base,n=2;while(reservedIds.has(id))id=base+'-'+n++;reservedIds.add(id);return id;};
  const idMap=new Map();
  const nz=(v,fn)=>v?fn(v):v;

  for(const l of out.labels||[]){
    const name=ps.label(l.name);
    idMap.set(l.id,uniq(slugify(name)));
    l.id=idMap.get(l.id);l.name=name;
    l.pic=nz(l.pic,ps.person);
    l.email=nz(l.email,e=>ps.email(e,name));
    l.address=nz(l.address,ps.address);
    l.whatsapp=nz(l.whatsapp,ps.phone);
    l.kycReason=nz(l.kycReason,v=>ps.text('kyc',v));
    l.contractBy=nz(l.contractBy,ps.person);
    l.logo=null;
    if(l.bank){l.bank.holder=nz(l.bank.holder,ps.person);l.bank.number=ps.maskedNumber(l.bank.number);}
  }
  const lid=v=>idMap.get(v)??v;
  if(out.source?.selection)for(const s of out.source.selection){s.id=lid(s.id);s.name=nz(s.name,ps.label);}
  const labelName=new Map((out.labels||[]).map(l=>[l.id,l.name]));
  const isSystem=v=>/^(system|sistem|admin)$/i.test(String(v||''));
  const yearOf=r=>String(r.year||String(r.date||'').slice(0,4)||'').trim();

  for(const r of out.releases||[]){
    r.label=lid(r.label);
    r.title=nz(r.title,ps.title);
    r.artists=(r.artists||[]).map(ps.artist);
    r.featured=(r.featured||[]).map(ps.artist);
    const holder=labelName.get(r.label)||'Label Contoh';
    r.copyright=nz(r.copyright,()=>['©',yearOf(r),holder].filter(Boolean).join(' '));
    r.pline=nz(r.pline,()=>['℗',yearOf(r),holder].filter(Boolean).join(' '));
    r.upc=nz(r.upc,ps.upc);
    r.cover=null;
    r.note=nz(r.note,v=>ps.text('note',v));
    for(const h of r.history||[])h.by=h.by&&!isSystem(h.by)?ps.person(h.by):h.by;
    for(const t of r.tracks||[]){
      t.title=nz(t.title,ps.title);t.isrc=nz(t.isrc,ps.isrc);
      t.composer=nz(t.composer,ps.person);t.lyricist=nz(t.lyricist,ps.person);t.producer=nz(t.producer,ps.person);
    }
  }
  const R=out.royalty||{};
  for(const im of R.imports||[])im.file=`believe_${im.period||'periode'}.csv`;
  for(const x of R.summary||[])x.label=lid(x.label);
  for(const x of R.byTrack||[]){x.label=lid(x.label);x.title=nz(x.title,ps.title);x.artist=nz(x.artist,ps.artist);x.isrc=nz(x.isrc,ps.isrc);}
  for(const x of R.byPlatform||[])x.label=lid(x.label);
  for(const w of out.withdrawals||[]){
    w.label=lid(w.label);
    if(w.bank){w.bank.holder=nz(w.bank.holder,ps.person);w.bank.number=ps.maskedNumber(w.bank.number);}
    w.reference=nz(w.reference,ps.ref);
    w.note=nz(w.note,v=>ps.text('note',v));
  }
  for(const t of out.tickets||[]){
    t.label=lid(t.label);
    t.releaseTitle=nz(t.releaseTitle,ps.title);
    t.subject=nz(t.subject,()=>`${t.categoryLabel||'Permintaan'}${t.releaseTitle?' — '+t.releaseTitle:''}`);
    t.description=nz(t.description,v=>ps.text('ticket',v));
    t.reason=nz(t.reason,v=>KNOWN_REASONS.has(v)?v:ps.text('ticket',v));
    if(t.newMetadata)t.newMetadata=scrubValue(ps,t.newMetadata,{collection:'support_tickets'});
    for(const c of t.comments||[]){
      c.who=c.who&&!/^sistem$/i.test(c.who)?ps.person(c.who):c.who;
      c.body=nz(c.body,v=>ps.text(c.system||c.role==='system'?'system':c.role==='label'?'label':'admin',v));
    }
  }
  for(const c of out.chats||[]){
    c.label=lid(c.label);
    for(const m of c.messages||[]){m.who=nz(m.who,ps.person);m.body=nz(m.body,v=>ps.text(m.role==='label'?'label':'admin',v));}
  }
  for(const s of out.services||[])s.label=lid(s.label);
  return out;
}

module.exports={createPseudonymizer,scrubValue,pseudonymizeCompact,slugify,KNOWN_REASONS};
