/* v1.1 dev.11–14 — Profil: halaman khusus saat avatar kanan atas diklik.
   dev.14 (pemilik): tanpa sidebar aplikasi, tanpa tab "Label & akses" dan "Preferensi notifikasi"
   (aksesTab131/notifPrefTab131 disimpan untuk dipindah ke menu lain bila diperlukan).
   Tata letak kiri–kanan (dev.13): kolom kiri lengket berisi kartu FOTO yang bisa diatur langsung
   (unggah, geser untuk memposisikan, slider ukuran, simpan/batal — tanpa membuka drawer) dan
   ringkasan identitas; kolom kanan berisi tab dan kelompok pengaturan. Data akun memakai kisi
   dua kolom agar tidak banyak ruang kosong. Formulir panjang (ubah data, kata sandi) di drawer.
   Foto disimpan sebagai potongan 256 px (data.profiles[id].avatar — dipakai avatar di mana pun
   oleh v8) + sumber asli ≤ 800 px dan posisi potongan agar bisa diatur ulang tanpa unggah ulang. */
'use strict';
const profile131={tab:'akun',photo:null};
modules.push({id:'profile131',group:'system',title:['Profil','Profile'],desc:['Akun, akses, dan preferensi notifikasi.','Account, access and notification preferences.'],actions:['',''],note:['',''],access:''});
const prefKinds131=[['finance',['Pembayaran & pencairan','Payments & withdrawals'],['Invoice, konfirmasi Xendit, status pencairan.','Invoices, Xendit confirmations, withdrawal status.']],['release',['Rilisan & pengiriman','Releases & delivery'],['Hasil pemeriksaan, tayang, revisi.','Review results, go-live, revisions.']],['support',['Tiket & percakapan','Tickets & conversations'],['Balasan baru dan perubahan status tiket.','New replies and ticket status changes.']],['personal',['Kehadiran & ulasan','Attendance & reviews'],['Keputusan cuti, ulasan bulanan.','Leave decisions, monthly reviews.']],['system',['Pemeliharaan & sistem','Maintenance & system'],['Jendela pemeliharaan dan pembaruan.','Maintenance windows and updates.']]];
function prefs131(){data.prefs131=data.prefs131||Object.fromEntries(prefKinds131.map(([k])=>[k,{app:true,email:k==='finance'||k==='system'}]));return data.prefs131;}
function openProfile131(tab){profile131.tab=tab||profile131.tab;try{closeModal();}catch{}try{closePop();}catch{}module102('profile131');render();window.scrollTo(0,0);}
const prof131=()=>{const p=me();data.profiles[p.id]=data.profiles[p.id]||{};return data.profiles[p.id];};

/* Blok bangunan */
const srow131=(title,desc,ctl='')=>`<div class="srow131"><div class="srow-text131"><strong>${title}</strong>${desc?`<small>${desc}</small>`:''}</div>${ctl?`<div class="srow-ctl131">${ctl}</div>`:''}</div>`;
const group131=(title,body,foot='',lead='')=>`<section class="panel group131"><header class="group-head131"><h2>${title}</h2>${lead?`<p>${lead}</p>`:''}</header><div class="rows131">${body}</div>${foot?`<footer class="group-foot131">${foot}</footer>`:''}</section>`;
const switch131=(name,on,label)=>`<label class="sw131"><input type="checkbox" role="switch" data-pref131="${name}" ${on?'checked':''} aria-label="${label}"><span></span></label>`;

/* ---------- kartu foto ---------- */
const PH131=120; /* diameter pratinjau (px) */
/* Tata letak gambar dalam lingkaran: cx/cy = titik gambar (0–1) di tengah lingkaran. */
function layoutPhoto131(){
  const dr=profile131.photo,img=document.getElementById('ph-img131');if(!dr||!img||!dr.w)return;
  const s=Math.max(PH131/dr.w,PH131/dr.h)*dr.zoom,W=dr.w*s,H=dr.h*s;
  const hx=PH131/(2*W),hy=PH131/(2*H);dr.cx=Math.min(1-hx,Math.max(hx,dr.cx));dr.cy=Math.min(1-hy,Math.max(hy,dr.cy));
  Object.assign(img.style,{width:W+'px',height:H+'px',left:(PH131/2-dr.cx*W)+'px',top:(PH131/2-dr.cy*H)+'px'});
}
function startDraft131(src,crop){const im=new Image();im.onload=()=>{profile131.photo={src,w:im.naturalWidth,h:im.naturalHeight,cx:crop?.cx??.5,cy:crop?.cy??.5,zoom:crop?.zoom??1};render();};im.src=src;}
function loadFile131(file){
  if(!file)return;if(!/^image\/(png|jpeg|webp)$/.test(file.type))return toast(t('Format foto harus PNG, JPEG atau WebP.','Photo must be PNG, JPEG or WebP.'));
  if(file.size>5*1024*1024)return toast(t('Ukuran foto maksimal 5 MB.','Photo must be 5 MB or smaller.'));
  const rd=new FileReader();rd.onload=()=>{const im=new Image();im.onload=()=>{const k=Math.min(1,800/Math.max(im.naturalWidth,im.naturalHeight)),c=document.createElement('canvas');c.width=Math.round(im.naturalWidth*k);c.height=Math.round(im.naturalHeight*k);c.getContext('2d').drawImage(im,0,0,c.width,c.height);startDraft131(c.toDataURL('image/jpeg',.88));};im.src=rd.result;};rd.readAsDataURL(file);
}
function savePhoto131(){
  const dr=profile131.photo;if(!dr)return;const im=new Image();im.onload=()=>{
    const s=Math.max(PH131/dr.w,PH131/dr.h)*dr.zoom,sw=PH131/s,c=document.createElement('canvas');c.width=c.height=256;
    c.getContext('2d').drawImage(im,dr.cx*dr.w-sw/2,dr.cy*dr.h-sw/2,sw,sw,0,0,256,256);
    const d=prof131();d.avatar=c.toDataURL('image/jpeg',.9);d.avatarSrc131=dr.src;d.avatarCrop131={cx:dr.cx,cy:dr.cy,zoom:dr.zoom};
    profile131.photo=null;if(typeof save10==='function')save10();render();toast(t('Foto profil diperbarui.','Profile photo updated.'));};im.src=dr.src;
}

/* dev.16: Profil tanpa judul halaman — satu layar penuh dengan sentuhan lebih hidup:
   pita identitas (atmosfer lembut seperti header Dashboard) berisi foto yang bisa diatur langsung,
   nama, peran, kontak, dan tiga sorotan (masa kerja · penyelesaian bulan ini · sesi aktif);
   di bawahnya tiga kartu: Data akun · Kinerja 2 bulan · Keamanan & tampilan. Foto tanpa bayangan. */
const ghead131=(title,action='')=>`<header class="ghead131"><h2>${title}</h2>${action}</header>`;
function tenure131(from){const a=new Date(from+'T00:00:00'),b=new Date('2026-09-18T00:00:00');let m=(b.getFullYear()-a.getFullYear())*12+b.getMonth()-a.getMonth();const y=Math.floor(m/12);m%=12;return T(`${y} th ${m} bln`,`${y} yr ${m} mo`);}
function monthName131(k){const [y,m]=k.split('-').map(Number);return new Date(y,m-1,1).toLocaleDateString(state.lang==='id'?'id-ID':'en-US',{month:'long'});}
function photoCard131(p){
  const d=prof131(),draft=profile131.photo,has=!!(draft||d.avatar);
  const preview=draft?`<img id="ph-img131" src="${draft.src}" alt="" draggable="false">`:d.avatar?`<img class="ph-cover131" src="${d.avatar}" alt="${E(p.name)}">`:`<span class="ph-initials131">${p.initials}</span>`;
  const zoom=draft?draft.zoom:(d.avatarCrop131?.zoom||1);
  const tools=draft?`<div class="ph-tools131"><label class="ph-zoom131"><span>${t('Ukuran','Size')}</span><input type="range" id="ph-zoom131" min="1" max="3" step="0.01" value="${zoom}" aria-label="${t('Ukuran foto','Photo size')}"></label><div class="ph-actions131">${btn(t('Simpan','Save'),'profile131-photo-save','','small primary')}${btn(t('Batal','Cancel'),'profile131-photo-cancel','','small')}</div></div>`
    :`<div class="ph-actions131 ph-min131"><label class="btn small ph-upload131" title="${t('PNG, JPEG atau WebP, maksimal 5 MB','PNG, JPEG or WebP, up to 5 MB')}">${t(has?'Ganti foto':'Unggah foto',has?'Replace photo':'Upload photo')}<input type="file" id="ph-file131" accept="image/png,image/jpeg,image/webp" hidden></label>${d.avatarSrc131?btn(t('Atur','Adjust'),'profile131-photo-adjust','','small'):''}${has?btn(t('Hapus','Remove'),'profile131-photo-remove','','small text'):''}</div>`;
  return `<div class="ph-wrap131"><div class="ph-frame131 ${draft?'editing':''}" id="ph-frame131" style="--ph:${PH131}px" ${draft?`title="${t('Geser untuk memposisikan','Drag to position')}"`:''}>${preview}${draft?'<span class="ph-hint131">'+t('Geser foto','Drag photo')+'</span>':''}</div>${tools}</div>`;
}
function profilePage131(){
  const p=me(),d=prof131();
  let sc={};try{sc=scores[p.id]||{};}catch{}
  const months=Object.keys(sc).sort(),last=months[months.length-1],cur=last?sc[last]:null,rate=cur&&cur[0]?Math.round(cur[1]/cur[0]*100):null;
  const leaves=(data.leaves||[]).filter(l=>l.staff===p.id&&l.status!=='rejected'),leaveDays=leaves.reduce((n,l)=>n+(l.days||0),0);
  const hero=`<section class="phero131">${photoCard131(p)}
    <div class="phero-id131"><div class="phero-chips131">${statusBadge111(p.super?'Super Admin':'Admin','blue')}${statusBadge111(t('Akses normal','Normal access'),'neutral')}</div><h1>${E(p.name)}</h1><p>${E(p.email)}${d.phone?` · ${E(d.phone)}`:''}${d.location?` · ${E(d.location)}`:''}</p></div>
    <div class="phero-stats131">
      <div><small>${t('Masa kerja','Tenure')}</small><strong>${p.joined?tenure131(p.joined):'—'}</strong><span>${p.joined?t('sejak ','since ')+new Date(p.joined+'T00:00:00').toLocaleDateString(state.lang==='id'?'id-ID':'en-US',{day:'numeric',month:'short',year:'numeric'}):''}${d.contract?` · ${E(d.contract)}`:''}</span></div>
      <div><small>${last?t('Selesai ','Completed ')+monthName131(last):t('Penyelesaian','Completion')}</small><strong>${cur?`${cur[1]}<em>/${cur[0]}</em>`:'—'}</strong><span>${rate!=null?`${rate}% ${t('pekerjaan tuntas','of work closed')}`:''}</span></div>
      <div><small>${t('Sesi aktif','Active sessions')}</small><strong>2</strong><span>${t('perangkat ini + 1 lainnya','this device + 1 other')}</span></div>
    </div></section>`;
  const maxA=Math.max(1,...months.map(k=>sc[k][0]));
  const perf=`<section class="panel g131">${ghead131(t('Kinerja','Performance'),btn(t('Detail','Details'),'nav','data-page="profile"','small'))}<div class="perf131"><div class="pmonths131">${months.slice(-3).map(k=>`<div class="pm131"><div class="pbars131"><i class="a" style="height:${sc[k][0]/maxA*100}%"></i><i class="b" style="height:${sc[k][1]/maxA*100}%"></i></div><b>${sc[k][1]}<em>/${sc[k][0]}</em></b><small>${monthName131(k).slice(0,3)}</small></div>`).join('')||`<p class="hint131">${t('Belum ada data.','No data yet.')}</p>`}</div>
    <ul class="pfacts131"><li><span>${t('Isu bulan ini','Issues this month')}</span><b>${cur?cur[2]:0}</b></li><li><span>${t('Cuti terpakai 2026','Leave used 2026')}</span><b>${leaveDays} ${t('hari','days')}</b></li><li><span>${t('Pengingat KPI','KPI reminder')}</span><b>${rate!=null&&rate>=90?t('Di atas target','Above target'):t('Pantau','Watch')}</b></li></ul></div>
    <div class="plegend131"><span><i class="a"></i>${t('Ditangani','Handled')}</span><span><i class="b"></i>${t('Tuntas','Closed')}</span></div></section>`;
  return `<div class="profile4-131">${hero}<div class="pgrid131">${akunTab131(p,d)}${perf}${secTab131(p)}</div></div>`;
}
function akunTab131(p,d){
  const facts=[[t('Nama tampilan','Display name'),p.name],[t('Nama administrasi','Administrative name'),d.legal||p.name],['Email',p.email],[t('Telepon','Phone'),d.phone||'—'],[t('Alamat','Address'),d.location||'—'],[t('Kontrak','Contract'),d.contract||'—']];
  return `<section class="panel g131">${ghead131(t('Data akun','Account data'),btn(t('Ubah','Edit'),'profile131-edit',`title="${t('Dokumen yang sudah diterbitkan tetap memakai data saat diterbitkan.','Issued documents keep the data they were issued with.')}"`,'small'))}<dl class="kv131">${facts.map(([k,v])=>`<div><dt>${k}</dt><dd>${E(v)}</dd></div>`).join('')}</dl></section>`;
}
function secTab131(p){
  const ua=navigator.userAgent,browser=/Edg\//.test(ua)?'Edge':/Chrome\//.test(ua)?'Chrome':/Firefox\//.test(ua)?'Firefox':/Safari\//.test(ua)?'Safari':t('Peramban','Browser'),os=/Windows/.test(ua)?'Windows':/Mac/.test(ua)?'macOS':/Android/.test(ua)?'Android':/iPhone|iPad/.test(ua)?'iOS':'';
  return `<section class="panel g131">${ghead131(t('Keamanan & tampilan','Security & appearance'))}<div class="rows131">`
    +srow131(t('Kata sandi','Password'),t('Diubah 3 bulan lalu','Changed 3 months ago'),btn(t('Ubah','Change'),'profile131-password','','small'))
    +srow131(`${browser}${os?` · ${os}`:''}`,t('Perangkat ini','This device'),statusBadge111(t('Sesi ini','This session'),'green'))
    +srow131('Chrome · Android',t('Jakarta · 2 hari lalu','Jakarta · 2 days ago'),btn(t('Keluar','Sign out'),'profile131-signout','data-id="other"','small'))
    +srow131(t('Tema gelap','Dark theme'),'',themeControl106())
    +srow131(t('Bahasa','Language'),'',btn(state.lang==='id'?'English':'Indonesia','lang','','small'))
    +`</div></section>`;
}
function aksesTab131(p){
  const level=k=>permission(k),toneOf=l=>l==='none'?'neutral':l==='direct'?'green':'blue',labelOf=l=>l==='none'?t('Tidak ada','None'):l==='direct'?t('Langsung','Direct'):t('Dibatasi','Limited');
  const labels=(data.v9&&data.v9.labels||[]).filter(l=>!l.master).slice(0,6);
  return `<div class="pair131">`+group131(t('Peran','Role'),
      srow131(t('Peran','Role'),p.super?t('Seluruh modul dan keputusan akhir.','Every module and final decisions.'):t('Modul sesuai kewenangan.','Modules within permissions.'),statusBadge111(p.super?'Super Admin':'Admin','blue'))
      +srow131(t('Status akses','Access status'),t('Tindakan tersedia sesuai kewenangan.','Actions available within permissions.'),statusBadge111(t('Normal','Normal'),'neutral')))
    +group131(t('Kewenangan','Permissions'),Object.entries(permissionNames).map(([k,name])=>srow131(L(name),'',statusBadge111(labelOf(level(k)),toneOf(level(k))))).join(''),
      `<span class="hint131">${t('Diubah oleh Super Admin di Staff & Akses.','Changed by a Super Admin in Staff & Access.')}</span>`)+`</div>`
    +(labels.length?group131(t('Label yang sering ditangani','Labels you handle most'),`<div class="labels131">${labels.map(l=>`<button type="button" class="label-chip131" data-action="nav" data-page="labels9"><span class="avatar">${initials131(l.name)}</span><span><strong>${E(l.name)}</strong><small>${E(l.id)}</small></span></button>`).join('')}</div>`):'');
}
function notifPrefTab131(){
  const pr=prefs131();
  return group131(t('Kanal per jenis kejadian','Channel per event type'),
      `<div class="srow131 srow-head131"><div class="srow-text131"></div><div class="srow-ctl131"><span>${t('Aplikasi','In-app')}</span><span>Email</span></div></div>`
      +prefKinds131.map(([k,name,desc])=>srow131(L(name),L(desc),switch131(`${k}:app`,pr[k].app,`${L(name)} · ${t('dalam aplikasi','in-app')}`)+switch131(`${k}:email`,pr[k].email,`${L(name)} · email`))).join(''),
      `<span class="hint131">${t('Tersimpan otomatis di browser ini.','Saved automatically in this browser.')}</span>`,
      t('Notifikasi dalam aplikasi muncul di lonceng dan Kotak Masuk; email dikirim ke alamat akun.','In-app notifications appear under the bell and in the Inbox; email goes to the account address.'));
}
function passwordDrawer131(){
  drawer8(t('Ubah kata sandi','Change password'),`<form data-form="profile131-password" class="form131" novalidate>${field('current',t('Kata sandi saat ini','Current password'),'','password','required autocomplete="current-password"')}${field('next',t('Kata sandi baru','New password'),'','password','required minlength="10" autocomplete="new-password"')}${field('again',t('Ulangi kata sandi baru','Repeat new password'),'','password','required autocomplete="new-password"')}<p class="hint131">${t('Minimal 10 karakter. Sesi di perangkat lain akan diminta masuk kembali.','At least 10 characters. Sessions on other devices will be asked to sign in again.')}</p>${formEnd(t('Perbarui kata sandi','Update password'))}</form>`);
}
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='profile131-edit')account8();
  else if(a==='profile131-password')passwordDrawer131();
  else if(a==='profile131-signout')toast(id==='all'?t('Semua sesi lain diakhiri (simulasi).','All other sessions ended (simulation).'):t('Sesi diakhiri (simulasi).','Session ended (simulation).'));
  else if(a==='profile131-photo-save')savePhoto131();
  else if(a==='profile131-photo-cancel'){profile131.photo=null;render();}
  else if(a==='profile131-photo-adjust'){const d=prof131();startDraft131(d.avatarSrc131,d.avatarCrop131);}
  else if(a==='profile131-photo-remove'){const d=prof131();delete d.avatar;delete d.avatarSrc131;delete d.avatarCrop131;if(typeof save10==='function')save10();render();}
  else if(a==='account'&&b.closest('.header .tools'))openProfile131();
  else return;
  e.preventDefault();e.stopImmediatePropagation();
},true);
document.addEventListener('change',e=>{
  if(e.target.id==='ph-file131'){loadFile131(e.target.files[0]);return;}
  const c=e.target.closest('[data-pref131]');if(!c)return;const [k,ch]=c.dataset.pref131.split(':');prefs131()[k][ch]=c.checked;if(typeof save10==='function')save10();});
document.addEventListener('input',e=>{if(e.target.id!=='ph-zoom131'||!profile131.photo)return;profile131.photo.zoom=+e.target.value;layoutPhoto131();});
/* geser untuk memposisikan (pointer: mouse, sentuh, pena) */
document.addEventListener('pointerdown',e=>{
  const fr=e.target.closest('#ph-frame131.editing');if(!fr||!profile131.photo)return;e.preventDefault();fr.setPointerCapture(e.pointerId);
  const dr=profile131.photo,s=Math.max(PH131/dr.w,PH131/dr.h)*dr.zoom,start={x:e.clientX,y:e.clientY,cx:dr.cx,cy:dr.cy};fr.classList.add('dragging');
  const move=ev=>{dr.cx=start.cx-(ev.clientX-start.x)/(dr.w*s);dr.cy=start.cy-(ev.clientY-start.y)/(dr.h*s);layoutPhoto131();};
  const up=()=>{fr.classList.remove('dragging');fr.removeEventListener('pointermove',move);fr.removeEventListener('pointerup',up);fr.removeEventListener('pointercancel',up);};
  fr.addEventListener('pointermove',move);fr.addEventListener('pointerup',up);fr.addEventListener('pointercancel',up);
});
document.addEventListener('keydown',e=>{const fr=e.target.closest&&e.target.closest('#ph-frame131.editing');if(!fr||!profile131.photo)return;const st=.02,m={ArrowLeft:[-st,0],ArrowRight:[st,0],ArrowUp:[0,-st],ArrowDown:[0,st]}[e.key];if(!m)return;e.preventDefault();profile131.photo.cx+=m[0];profile131.photo.cy+=m[1];layoutPhoto131();});
document.addEventListener('submit',e=>{
  const f=e.target.closest('form[data-form="profile131-password"]');if(!f)return;e.preventDefault();e.stopImmediatePropagation();
  const fb=f.querySelector('#form-feedback'),v=k=>f.elements[k].value;
  if(!v('current'))return fb.textContent=t('Isi kata sandi saat ini.','Enter your current password.');
  if(v('next').length<10)return fb.textContent=t('Kata sandi baru minimal 10 karakter.','New password needs at least 10 characters.');
  if(v('next')!==v('again'))return fb.textContent=t('Ulangan kata sandi tidak sama.','Repeated password does not match.');
  f.reset();fb.textContent='';try{closeModal();}catch{}toast(t('Kata sandi diperbarui (simulasi).','Password updated (simulation).'));
},true);
const modulePageBeforeProfile131=modulePage;
modulePage=function(){if(v4.module==='profile131')return profilePage131();return modulePageBeforeProfile131();};
/* setelah render: tata ulang gambar draf & beri fokus keyboard pada bingkai */
const renderBeforeProfile131=render;
render=function(){renderBeforeProfile131();document.body.classList.toggle('nosidebar131',!!document.querySelector('#main .inbox3-131,#main .profile3-131,#main .profile4-131'));if(profile131.photo&&v4.module==='profile131'){const fr=document.getElementById('ph-frame131');if(fr)fr.tabIndex=0;layoutPhoto131();}};
