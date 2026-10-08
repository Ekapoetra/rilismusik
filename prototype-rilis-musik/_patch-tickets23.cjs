/* Add account-level ticket categories: royalty-issue + general (D11). */
const fs = require('fs'), path = require('path');
const dir = path.join(__dirname, 'prototype-v13.0');
const rep = (file, oldS, newS) => {
  const p = path.join(dir, file); let s = fs.readFileSync(p, 'utf8');
  if (!s.includes(oldS)) throw Error('NOT FOUND in ' + file + ':\n' + oldS.slice(0, 140));
  fs.writeFileSync(p, s.replace(oldS, newS)); console.log('ok', file);
};

// --- model: categories + account-level build branch ---
rep('tickets112-model.js',
`categories=['metadata','audio','cover','takedown','cid','release-claim','disable-cid','availability'];`,
`categories=['metadata','audio','cover','takedown','cid','release-claim','disable-cid','availability','royalty-issue','general'];`);

rep('tickets112-model.js',
`function build(s,a,p){const r=s.releases.find(r=>r.id===p.release);`,
`function accountSnap112(a){return {id:'account',member:a.member,title:'Permintaan umum',artist:'',cover:null,release:{},songs:[]};}
function build(s,a,p){
 if(['royalty-issue','general'].includes(p.category)){
  let snap;
  if(p.release){const r0=s.releases.find(r=>r.id===p.release);ok(r0&&a.scope.includes(r0.member),'Rilisan berada di luar akunmu.');ok(['delivered','followup','partial','partial_closed','live','taken_down'].includes(r0.status),'Gunakan alur pada status rilisan saat ini.');snap=catalogue(r0);ok(JSON.stringify(snap)===JSON.stringify(p.source),'Data katalog berubah. Tinjau ulang data sebelum mengajukan.');}
  else{snap=accountSnap112(a);ok(JSON.stringify(snap)===JSON.stringify(p.source),'Sumber permintaan berubah. Muat ulang formulir.');}
  ok(p.note?.trim(),'Tuliskan penjelasan permintaan.');
  return {r:snap,snap,items:[item('request',p.category==='royalty-issue'?'Masalah royalti':'Permintaan lainnya')]};
 }
 const r=s.releases.find(r=>r.id===p.release);`);

// results: allow account-level tickets (no release to mutate)
rep('tickets112-model.js',
`release=cp(s.releases.find(r=>r.id===t.release));ok(release,'Rilisan tidak ditemukan.');`,
`release=t.release==='account'?null:cp(s.releases.find(r=>r.id===t.release));ok(release||t.release==='account','Rilisan tidak ditemukan.');`);

rep('tickets112-model.js',
`release.version=(release.version||0)+1;release.updated=s.now;release.history??=[];release.history.push({at:s.now,actor:a.id,action:'ticket-result112',note:p.note,ticket:t.id,results:cp(p.results)});`,
`if(release){release.version=(release.version||0)+1;release.updated=s.now;release.history??=[];release.history.push({at:s.now,actor:a.id,action:'ticket-result112',note:p.note,ticket:t.id,results:cp(p.results)});}`);

// reopen: keep synthetic source for account-level tickets
rep('tickets112-model.js',
`t.source=catalogue(s.releases.find(r=>r.id===t.release));`,
`{const found=s.releases.find(r=>r.id===t.release);t.source=found?catalogue(found):t.source;}`);

// --- UI: names, payload, category form ---
rep('v112-tickets.js',
`const names112={metadata:'Perubahan Metadata',audio:'Penggantian Audio',cover:'Penggantian Cover',takedown:'Penurunan Rilisan',cid:'Ajukan Content ID','release-claim':'Lepaskan Klaim Video','disable-cid':'Nonaktifkan Content ID',availability:'Masalah Ketersediaan Rilisan'};`,
`const names112={metadata:'Perubahan Metadata',audio:'Penggantian Audio',cover:'Penggantian Cover',takedown:'Penurunan Rilisan',cid:'Ajukan Content ID','release-claim':'Lepaskan Klaim Video','disable-cid':'Nonaktifkan Content ID',availability:'Masalah Ketersediaan Rilisan','royalty-issue':'Masalah Royalti',general:'Permintaan Lainnya'};`);

rep('v112-tickets.js',
`function fresh112(release='',category='metadata'){const r=releaseChoices112().find(r=>r.id===release)||releaseChoices112()[0];return {category,release:r?.id||'',source:r?Tickets112.catalogue(r):null,note:'',reason:'',tracks:r?.songs?.map(t=>t.id)||[],changes:[],platforms:[],condition:'missing',urls:[''],creators:[],consent:false,checked:false,files:[],audio:null,cover:null,preview:0}}`,
`function fresh112(release='',category='metadata'){const r=releaseChoices112().find(r=>r.id===release)||(['royalty-issue','general'].includes(category)?null:releaseChoices112()[0]);return {category,release:r?.id||'',source:r?Tickets112.catalogue(r):['royalty-issue','general'].includes(category)?{id:'account',member:ten.member,title:'Permintaan umum',artist:'',cover:null,release:{},songs:[]}:null,note:'',reason:'',tracks:r?.songs?.map(t=>t.id)||[],changes:[],platforms:[],condition:'missing',urls:[''],creators:[],consent:false,checked:false,files:[],audio:null,cover:null,preview:0}}`);

rep('v112-tickets.js',
`function categoryForm112(){const d=payload112;if(!d.source)return '<p>Belum ada rilisan yang dikirim atau tayang. Siapkan draft melalui menu Rilisan.</p>';`,
`function categoryForm112(){const d=payload112;if(d.category==='royalty-issue')return '<div class="notice111"><strong>Sengketa atau pertanyaan royalti</strong><p>Jelaskan periode, lagu (judul/ISRC bila tahu), dan hal yang perlu diperiksa. Boleh memilih rilisan terkait atau dibiarkan umum. Petugas meninjau langsung — tidak diteruskan ke distributor.</p></div>';if(d.category==='general')return '<div class="notice111"><strong>Permintaan lainnya</strong><p>Untuk kebutuhan di luar jenis permintaan katalog: akun, pembayaran, kerja sama, atau pertanyaan layanan. Ditangani petugas secara langsung.</p></div>';if(!d.source)return '<p>Belum ada rilisan yang dikirim atau tayang. Siapkan draft melalui menu Rilisan.</p>';`);

// release picker hint for optional-release categories
rep('v112-tickets.js',
`<label>Rilisan \${required112}<select name="release112" \${d.extension?"disabled":""}><option value="">Pilih rilisan</option>`,
`<label>Rilisan \${['royalty-issue','general'].includes(d.category)?'<small class="note107">(opsional)</small>':required112}<select name="release112" \${d.extension?"disabled":""}><option value="">\${['royalty-issue','general'].includes(d.category)?'Umum — tanpa rilisan':'Pilih rilisan'}</option>`);

// required marker on release select is only visual; make selection optional handled in build.
// Keep source-check banner for release-linked generic tickets only.
console.log('done');
