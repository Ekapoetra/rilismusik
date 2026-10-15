/* v1.1 dev.11 — Profil: halaman khusus saat avatar kanan atas diklik (bukan dropdown).
   Tiga tab: Akun (data, tema & bahasa, kata sandi, sesi aktif) · Label & akses (peran dan
   kewenangan, memakai penanda yang sama dengan Kamus Penanda) · Preferensi notifikasi
   (kanal per jenis kejadian). Ubah data memakai drawer akun v8 yang sudah ada. */
'use strict';
const profile131={tab:'akun'};
modules.push({id:'profile131',group:'system',title:['Profil','Profile'],desc:['Akun, akses, dan preferensi notifikasi.','Account, access and notification preferences.'],actions:['',''],note:['',''],access:''});
const prefKinds131=[['finance',['Pembayaran & pencairan','Payments & withdrawals']],['release',['Rilisan & pengiriman','Releases & delivery']],['support',['Tiket & percakapan','Tickets & conversations']],['personal',['Kehadiran & ulasan','Attendance & reviews']],['system',['Pemeliharaan & sistem','Maintenance & system']]];
function prefs131(){data.prefs131=data.prefs131||Object.fromEntries(prefKinds131.map(([k])=>[k,{app:true,email:k==='finance'||k==='system'}]));return data.prefs131;}
function openProfile131(tab){profile131.tab=tab||profile131.tab;try{closeModal();}catch{}try{closePop();}catch{}module102('profile131');render();window.scrollTo(0,0);}

function profilePage131(){
  const p=me();
  const tabs=`<div class="tabs" role="tablist">${[['akun',t('Akun','Account')],['akses',t('Label & akses','Labels & access')],['notif',t('Preferensi notifikasi','Notification preferences')]].map(([id,label])=>`<button type="button" role="tab" aria-selected="${profile131.tab===id}" class="${profile131.tab===id?'active':''}" data-action="profile131-tab" data-id="${id}">${label}</button>`).join('')}</div>`;
  return pageHead(t('Profil','Profile'),t('Siapa kamu di Rilis Musik, apa yang bisa kamu akses, dan bagaimana kami menghubungimu.','Who you are in Rilis Musik, what you can access, and how we reach you.'))+tabs+({akun:akunTab131,akses:aksesTab131,notif:notifPrefTab131})[profile131.tab](p);
}
function akunTab131(p){
  const d=(data.profiles&&data.profiles[p.id])||{};
  const facts=[[t('Nama tampilan','Display name'),p.name],[t('Nama administrasi','Administrative name'),d.legal||p.name],['Email',p.email],[t('Telepon','Phone'),d.phone||'—'],[t('Alamat','Address'),d.location||'—']];
  const ua=navigator.userAgent,browser=/Edg\//.test(ua)?'Edge':/Chrome\//.test(ua)?'Chrome':/Safari\//.test(ua)?'Safari':/Firefox\//.test(ua)?'Firefox':t('Peramban','Browser'),os=/Windows/.test(ua)?'Windows':/Mac/.test(ua)?'macOS':/Android/.test(ua)?'Android':/iPhone|iPad/.test(ua)?'iOS':'';
  return `<div class="profile-grid131">
<section class="panel pad"><h2>${t('Data akun','Account data')}</h2>${personCell(p)}<dl class="facts131">${facts.map(([k,v])=>`<div><dt>${k}</dt><dd>${E(v)}</dd></div>`).join('')}</dl><div class="row-actions131">${btn(t('Ubah data akun','Edit account data'),'profile131-edit','','small')}</div><p class="scope-note">${t('Dokumen yang sudah diterbitkan tetap memakai data saat diterbitkan.','Issued documents keep the data they were issued with.')}</p></section>
<section class="panel pad"><h2>${t('Tampilan & bahasa','Appearance & language')}</h2><div class="pref-row131"><span>${t('Tema gelap','Dark theme')}</span>${themeControl106()}</div><div class="pref-row131"><span>${t('Bahasa antarmuka','Interface language')}</span>${btn(state.lang==='id'?'Indonesia → English':'English → Indonesia','lang','','small')}</div></section>
<section class="panel pad"><h2>${t('Kata sandi','Password')}</h2><form data-form="profile131-password" class="form131" novalidate>${field('current',t('Kata sandi saat ini','Current password'),'','password','required autocomplete="current-password"')}${field('next',t('Kata sandi baru','New password'),'','password','required minlength="10" autocomplete="new-password"')}${field('again',t('Ulangi kata sandi baru','Repeat new password'),'','password','required autocomplete="new-password"')}<p class="scope-note">${t('Minimal 10 karakter. Sesi di perangkat lain akan diminta masuk kembali.','At least 10 characters. Sessions on other devices will be asked to sign in again.')}</p><div id="form-feedback" role="status"></div><div class="form-actions"><button type="submit" class="btn primary">${t('Perbarui kata sandi','Update password')}</button></div></form></section>
<section class="panel pad"><h2>${t('Sesi aktif','Active sessions')}</h2><div class="session131"><strong>${browser}${os?` · ${os}`:''}</strong><small>${t('Perangkat ini · sekarang','This device · now')}</small>${statusBadge111(t('Aktif','Active'),'green')}</div><div class="session131"><strong>Chrome · Android</strong><small>${t('Jakarta · 2 hari lalu','Jakarta · 2 days ago')}</small>${btn(t('Keluar','Sign out'),'profile131-signout','data-id="other"','small')}</div><div class="row-actions131">${btn(t('Keluar dari semua perangkat lain','Sign out of all other devices'),'profile131-signout','data-id="all"','small')}</div></section>
</div>`;
}
function aksesTab131(p){
  const level=k=>permission(k),toneOf=l=>l==='none'?'neutral':l==='direct'?'green':'blue',labelOf=l=>l==='none'?t('Tidak ada','None'):l==='direct'?t('Langsung','Direct'):t('Dibatasi','Limited');
  const perms=Object.entries(permissionNames).map(([k,name])=>`<div class="perm131"><span>${L(name)}</span>${statusBadge111(labelOf(level(k)),toneOf(level(k)))}</div>`).join('');
  const labels=(data.v9&&data.v9.labels||[]).filter(l=>!l.master).slice(0,4);
  return `<div class="profile-grid131">
<section class="panel pad"><h2>${t('Peran','Role')}</h2>${personCell(p)}<p class="scope-note">${p.super?t('Super Admin: seluruh modul dan keputusan akhir.','Super Admin: every module and final decisions.'):t('Admin: modul sesuai kewenangan di bawah.','Admin: modules according to the permissions below.')}</p><div class="pref-row131"><span>${t('Status akses','Access status')}</span>${statusBadge111(t('Normal','Normal'),'neutral')}</div></section>
<section class="panel pad"><h2>${t('Kewenangan','Permissions')}</h2>${perms}<p class="scope-note">${t('Perubahan kewenangan dilakukan oleh Super Admin di Staff & Akses.','Permissions are changed by a Super Admin in Staff & Access.')}</p></section>
${labels.length?`<section class="panel pad"><h2>${t('Label yang sering ditangani','Labels you handle most')}</h2>${labels.map(l=>`<div class="perm131"><span>${E(l.name)}</span><small>${E(l.city||'')}</small></div>`).join('')}</section>`:''}
</div>`;
}
function notifPrefTab131(){
  const pr=prefs131();
  return `<section class="panel pad"><h2>${t('Kanal per jenis kejadian','Channel per event type')}</h2><div class="table-wrap"><table class="prefs131"><thead><tr><th>${t('Jenis','Type')}</th><th>${t('Dalam aplikasi','In-app')}</th><th>Email</th></tr></thead><tbody>${prefKinds131.map(([k,name])=>`<tr><td>${L(name)}</td>${['app','email'].map(ch=>`<td><input type="checkbox" data-pref131="${k}:${ch}" ${pr[k][ch]?'checked':''} aria-label="${L(name)} · ${ch}"></td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="scope-note">${t('Notifikasi dalam aplikasi untuk pembayaran dan sistem tidak bisa dimatikan sepenuhnya; pilihan di sini mengatur email.','In-app notifications for payments and system cannot be fully disabled; the choices here control email.')}</p></section>`;
}
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='profile131-tab'){profile131.tab=id;render();}
  else if(a==='profile131-edit')account8();
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
  f.reset();fb.textContent='';toast(t('Kata sandi diperbarui (simulasi).','Password updated (simulation).'));
},true);
document.addEventListener('change',e=>{const c=e.target.closest('[data-pref131]');if(!c)return;const [k,ch]=c.dataset.pref131.split(':');prefs131()[k][ch]=c.checked;if(typeof save10==='function')save10();});
const modulePageBeforeProfile131=modulePage;
modulePage=function(){if(v4.module==='profile131')return profilePage131();return modulePageBeforeProfile131();};
