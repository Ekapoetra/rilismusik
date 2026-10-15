/* v1.1 dev.12 — Profil: halaman khusus saat avatar kanan atas diklik.
   Pola "daftar pengaturan" yang konsisten: kartu identitas di atas, lalu satu kolom
   kelompok (panel) berisi baris Judul · keterangan · kontrol di kanan. Tidak ada formulir
   panjang di halaman — ubah data & kata sandi memakai drawer, sehingga halaman tetap tenang.
   Tab: Akun · Label & akses · Preferensi notifikasi. */
'use strict';
const profile131={tab:'akun'};
modules.push({id:'profile131',group:'system',title:['Profil','Profile'],desc:['Akun, akses, dan preferensi notifikasi.','Account, access and notification preferences.'],actions:['',''],note:['',''],access:''});
const prefKinds131=[['finance',['Pembayaran & pencairan','Payments & withdrawals'],['Invoice, konfirmasi Xendit, status pencairan.','Invoices, Xendit confirmations, withdrawal status.']],['release',['Rilisan & pengiriman','Releases & delivery'],['Hasil pemeriksaan, tayang, revisi.','Review results, go-live, revisions.']],['support',['Tiket & percakapan','Tickets & conversations'],['Balasan baru dan perubahan status tiket.','New replies and ticket status changes.']],['personal',['Kehadiran & ulasan','Attendance & reviews'],['Keputusan cuti, ulasan bulanan.','Leave decisions, monthly reviews.']],['system',['Pemeliharaan & sistem','Maintenance & system'],['Jendela pemeliharaan dan pembaruan.','Maintenance windows and updates.']]];
function prefs131(){data.prefs131=data.prefs131||Object.fromEntries(prefKinds131.map(([k])=>[k,{app:true,email:k==='finance'||k==='system'}]));return data.prefs131;}
function openProfile131(tab){profile131.tab=tab||profile131.tab;try{closeModal();}catch{}try{closePop();}catch{}module102('profile131');render();window.scrollTo(0,0);}

/* Blok bangunan */
const srow131=(title,desc,ctl='')=>`<div class="srow131"><div class="srow-text131"><strong>${title}</strong>${desc?`<small>${desc}</small>`:''}</div>${ctl?`<div class="srow-ctl131">${ctl}</div>`:''}</div>`;
const group131=(title,rows,foot='',lead='')=>`<section class="panel group131"><header class="group-head131"><h2>${title}</h2>${lead?`<p>${lead}</p>`:''}</header><div class="rows131">${rows}</div>${foot?`<footer class="group-foot131">${foot}</footer>`:''}</section>`;
const switch131=(name,on,label)=>`<label class="sw131"><input type="checkbox" data-pref131="${name}" ${on?'checked':''} aria-label="${label}"><span></span></label>`;

function profilePage131(){
  const p=me(),d=(data.profiles&&data.profiles[p.id])||{};
  const hero=`<section class="panel hero131"><div class="hero-id131"><span class="avatar big131 ${p.super?'accent':''}">${p.initials}</span><div><h2>${E(p.name)}</h2><p>${E(p.email)}${d.phone?` · ${E(d.phone)}`:''}</p><div class="hero-chips131">${statusBadge111(p.super?'Super Admin':'Admin','blue')}${statusBadge111(t('Akses normal','Normal access'),'neutral')}</div></div></div><div class="hero-actions131">${btn(t('Ubah data akun','Edit account data'),'profile131-edit','','small')}</div></section>`;
  const tabs=`<div class="tabs profile-tabs131" role="tablist">${[['akun',t('Akun','Account')],['akses',t('Label & akses','Labels & access')],['notif',t('Preferensi notifikasi','Notification preferences')]].map(([id,label])=>`<button type="button" role="tab" aria-selected="${profile131.tab===id}" class="${profile131.tab===id?'active':''}" data-action="profile131-tab" data-id="${id}">${label}</button>`).join('')}</div>`;
  return pageHead(t('Profil','Profile'),t('Siapa kamu di Rilis Musik, apa yang bisa kamu akses, dan bagaimana kami menghubungimu.','Who you are in Rilis Musik, what you can access, and how we reach you.'))+`<div class="settings131">${hero}${tabs}${({akun:akunTab131,akses:aksesTab131,notif:notifPrefTab131})[profile131.tab](p,d)}</div>`;
}
function akunTab131(p,d){
  const ua=navigator.userAgent,browser=/Edg\//.test(ua)?'Edge':/Chrome\//.test(ua)?'Chrome':/Firefox\//.test(ua)?'Firefox':/Safari\//.test(ua)?'Safari':t('Peramban','Browser'),os=/Windows/.test(ua)?'Windows':/Mac/.test(ua)?'macOS':/Android/.test(ua)?'Android':/iPhone|iPad/.test(ua)?'iOS':'';
  return group131(t('Data akun','Account data'),
      srow131(t('Nama tampilan','Display name'),E(p.name))+srow131(t('Nama administrasi','Administrative name'),E(d.legal||p.name))+srow131('Email',E(p.email))+srow131(t('Telepon','Phone'),E(d.phone||'—'))+srow131(t('Alamat','Address'),E(d.location||'—')),
      `<span class="hint131">${t('Dokumen yang sudah diterbitkan tetap memakai data saat diterbitkan.','Issued documents keep the data they were issued with.')}</span>${btn(t('Ubah data akun','Edit account data'),'profile131-edit','','small')}`)
    +group131(t('Tampilan & bahasa','Appearance & language'),
      srow131(t('Tema gelap','Dark theme'),t('Mengikuti pilihanmu di perangkat ini.','Follows your choice on this device.'),themeControl106())+srow131(t('Bahasa antarmuka','Interface language'),state.lang==='id'?'Bahasa Indonesia':'English',btn(state.lang==='id'?'Switch to English':'Ganti ke Indonesia','lang','','small')))
    +group131(t('Keamanan','Security'),
      srow131(t('Kata sandi','Password'),t('Terakhir diubah 3 bulan lalu.','Last changed 3 months ago.'),btn(t('Ubah kata sandi','Change password'),'profile131-password','','small'))
      +srow131(`${browser}${os?` · ${os}`:''}`,t('Perangkat ini · sekarang','This device · now'),statusBadge111(t('Sesi ini','This session'),'green'))
      +srow131('Chrome · Android',t('Jakarta · 2 hari lalu','Jakarta · 2 days ago'),btn(t('Keluar','Sign out'),'profile131-signout','data-id="other"','small')),
      `<span class="hint131">${t('Mengubah kata sandi mengakhiri sesi di perangkat lain.','Changing the password ends sessions on other devices.')}</span>${btn(t('Keluar dari semua perangkat lain','Sign out of all other devices'),'profile131-signout','data-id="all"','small')}`);
}
function aksesTab131(p){
  const level=k=>permission(k),toneOf=l=>l==='none'?'neutral':l==='direct'?'green':'blue',labelOf=l=>l==='none'?t('Tidak ada','None'):l==='direct'?t('Langsung','Direct'):t('Dibatasi','Limited');
  const labels=(data.v9&&data.v9.labels||[]).filter(l=>!l.master).slice(0,4);
  return group131(t('Peran','Role'),
      srow131(t('Peran','Role'),p.super?t('Seluruh modul dan keputusan akhir.','Every module and final decisions.'):t('Modul sesuai kewenangan di bawah.','Modules according to the permissions below.'),statusBadge111(p.super?'Super Admin':'Admin','blue'))
      +srow131(t('Status akses','Access status'),t('Tindakan tersedia sesuai kewenangan.','Actions available within permissions.'),statusBadge111(t('Normal','Normal'),'neutral')))
    +group131(t('Kewenangan','Permissions'),
      Object.entries(permissionNames).map(([k,name])=>srow131(L(name),'',statusBadge111(labelOf(level(k)),toneOf(level(k))))).join(''),
      `<span class="hint131">${t('Perubahan kewenangan dilakukan Super Admin di Staff & Akses.','Permissions are changed by a Super Admin in Staff & Access.')}</span>`)
    +(labels.length?group131(t('Label yang sering ditangani','Labels you handle most'),labels.map(l=>srow131(E(l.name),E(l.city||''),btn(t('Buka','Open'),'nav','data-page="labels9"','small text'))).join('')):'');
}
function notifPrefTab131(){
  const pr=prefs131();
  return group131(t('Kanal per jenis kejadian','Channel per event type'),
      `<div class="srow131 srow-head131"><div class="srow-text131"></div><div class="srow-ctl131"><span>${t('Dalam aplikasi','In-app')}</span><span>Email</span></div></div>`
      +prefKinds131.map(([k,name,desc])=>srow131(L(name),L(desc),switch131(`${k}:app`,pr[k].app,`${L(name)} · ${t('dalam aplikasi','in-app')}`)+switch131(`${k}:email`,pr[k].email,`${L(name)} · email`))).join(''),
      `<span class="hint131">${t('Tersimpan otomatis di browser ini. Pembayaran dan sistem selalu tampil di dalam aplikasi.','Saved automatically in this browser. Payments and system always appear in-app.')}</span>`,
      t('Notifikasi dalam aplikasi muncul di lonceng dan Kotak Masuk; email dikirim ke alamat akun.','In-app notifications appear under the bell and in the Inbox; email goes to the account address.'));
}
function passwordDrawer131(){
  drawer8(t('Ubah kata sandi','Change password'),`<form data-form="profile131-password" class="form131" novalidate>${field('current',t('Kata sandi saat ini','Current password'),'','password','required autocomplete="current-password"')}${field('next',t('Kata sandi baru','New password'),'','password','required minlength="10" autocomplete="new-password"')}${field('again',t('Ulangi kata sandi baru','Repeat new password'),'','password','required autocomplete="new-password"')}<p class="hint131">${t('Minimal 10 karakter. Sesi di perangkat lain akan diminta masuk kembali.','At least 10 characters. Sessions on other devices will be asked to sign in again.')}</p>${formEnd(t('Perbarui kata sandi','Update password'))}</form>`);
}
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='profile131-tab'){profile131.tab=id;render();}
  else if(a==='profile131-edit')account8();
  else if(a==='profile131-password')passwordDrawer131();
  else if(a==='profile131-signout')toast(id==='all'?t('Semua sesi lain diakhiri (simulasi).','All other sessions ended (simulation).'):t('Sesi diakhiri (simulasi).','Session ended (simulation).'));
  else if(a==='account'&&b.closest('.header .tools'))openProfile131();
  else return;
  e.preventDefault();e.stopImmediatePropagation();
},true);
document.addEventListener('submit',e=>{
  const f=e.target.closest('form[data-form="profile131-password"]');if(!f)return;e.preventDefault();e.stopImmediatePropagation();
  const fb=f.querySelector('#form-feedback'),v=k=>f.elements[k].value;
  if(!v('current'))return fb.textContent=t('Isi kata sandi saat ini.','Enter your current password.');
  if(v('next').length<10)return fb.textContent=t('Kata sandi baru minimal 10 karakter.','New password needs at least 10 characters.');
  if(v('next')!==v('again'))return fb.textContent=t('Ulangan kata sandi tidak sama.','Repeated password does not match.');
  f.reset();fb.textContent='';try{closeModal();}catch{}toast(t('Kata sandi diperbarui (simulasi).','Password updated (simulation).'));
},true);
document.addEventListener('change',e=>{const c=e.target.closest('[data-pref131]');if(!c)return;const [k,ch]=c.dataset.pref131.split(':');prefs131()[k][ch]=c.checked;if(typeof save10==='function')save10();});
const modulePageBeforeProfile131=modulePage;
modulePage=function(){if(v4.module==='profile131')return profilePage131();return modulePageBeforeProfile131();};
