/* One catalog and one role-aware entry point. Local prototype fixtures only. */
'use strict';
const studioCheckpointKey = 'rm-v11-1-studio-checkpoint';
let studioCheckpoint = null;
try { studioCheckpoint = JSON.parse(localStorage.getItem(studioCheckpointKey)); } catch {}
let studioSelected = null;
let studioRunning = false;
const studioCatalog = [
  ['10.3','bank-directory','label','Cari bank penerima','Find a recipient bank','Cari bank umum, syariah, digital, atau isi bank lain.','Find commercial, Islamic or digital banks, or enter another bank.'],
  ['10.3','location-directory','label','Lengkapi lokasi operasional','Complete the operating location','Pilih provinsi, kabupaten/kota dan kecamatan pada identitas.','Choose province, regency/city and district in the identity form.'],
  ['10.3','plans','label','Pilihan paket dan masa aktif','Plans and expiry','Bandingkan manfaat paket dari akun label.','Compare plan benefits as a label.'],
  ['10.3','credits','label','Single, EP, Album dan kredit manual','Single, EP, Album and custom credits','Buka pilihan pembelian beserta ringkasan pembayaran.','Open credit choices and the payment summary.'],
  ['10.3','profile-owner','label','Identitas sedang diperiksa','Identity under review','Lihat profil lama tetap berlaku selama perubahan diperiksa.','See the existing profile while changes await review.'],
  ['10.3','profile-review','admin','Tinjau perubahan identitas','Review identity changes','Langsung buka pengajuan label sebagai petugas pemeriksa.','Open the label request as its reviewer.'],
  ['10.3','label-updates','label','Pembaruan untuk label','Label updates','Buka dan tutup panel notifikasi dari tombol yang sama.','Open and close notifications with the same button.'],
  ['10.2','release-form','label','Siapkan rilisan dan pilih layanan','Prepare a release and choose service','Coba tanggal rilis, Standard, Express dan MAX.','Try a release date, Standard, Express and MAX.'],
  ['10.2','contracts','super','Kontrak dan versi dokumen','Contracts and document versions','Buka pengelolaan kontrak di ruang Super Admin.','Open contract management in the Super Admin workspace.'],
  ['10.1','activation','label','Aktivasi yang belum lengkap','Incomplete activation','Mulai dari dashboard calon member dan lanjutkan pengisian.','Start on a prospective member dashboard and continue activation.'],
  ['10.1','activation-review','admin','Pengajuan aktivasi menunggu','Activation awaiting review','Buka pengajuan yang siap diperiksa Admin.','Open an application ready for Admin review.'],
  ['10.1','bank-review','super','Rekening perlu diperiksa','Bank details to review','Periksa kecocokan nama penerima dan minta perbaikan.','Review the recipient name and request corrections.'],
  ['10.1','revision','label','Revisi tersisa dua jam','Two hours left for corrections','Lihat atensi merah dan lanjutkan perbaikan rilisan.','See red attention and continue release corrections.'],
  ['10.1','date-error','admin','Tanggal pengiriman perlu diperbaiki','Delivery date needs correction','Buka tindak lanjut kesalahan tanggal di Believe.','Open follow-up for a Believe date error.'],
  ['10.1','live-review','admin','Kode tersedia, tayang belum dikonfirmasi','Codes available, live status unconfirmed','Periksa tautan sebelum memberi status Tayang.','Check distribution links before confirming Live.'],
  ['10.1','friday-cutoff','label','MAX Jumat melewati pukul 12.00','Friday MAX after noon','Coba pilihan layanan setelah batas pengajuan MAX.','Try the service choice after the MAX cutoff.'],
  ['9','master','super','Master dengan label baru','Master with a new label','Lihat hubungan multi-label dan penanda pemeriksaannya.','See managed labels and their review indicators.'],
  ['9','royalties','super','Royalti label nonoperasional','Nonoperational label royalties','Buka liabilitas terpisah dan rincian label.','Open separate liabilities and label details.'],
  ['9','standards','super','Panduan status dan standar label','Label standards and status guide','Telusuri arti penanda yang tersedia pada versi ini.','Explore the indicators available in this version.'],
  ['9','urgent','admin','Pekerjaan melewati tenggat','Work past its deadline','Langsung lihat pekerjaan mendesak dan atensi merah.','See urgent work and red attention immediately.'],
  ['8','night','admin','Pekerjaan mendesak setelah jam akses','Urgent work outside access hours','Coba permintaan izin sementara pada pekerjaan terkait.','Try temporary access for the relevant work.'],
  ['8','idle','admin','Sesi berakhir saat tidak aktif','Session ended after inactivity','Rasakan kondisi masuk kembali setelah sesi berakhir.','Try signing back in after the session ends.'],
  ['8','attendance','super','Periksa rincian kehadiran','Review attendance details','Buka catatan staf dari Ringkasan Tim.','Open staff records from Team Overview.'],
  ['7','new-month','admin','Awal bulan dengan rating 0,0','New month with a 0.0 rating','Lihat Beranda Saya pada awal periode berikutnya.','See My Overview at the beginning of the next period.'],
  ['6','summary','admin','Lima ringkasan pekerjaan','Five work summaries','Buka daftar pekerjaan dari kartu ringkasan.','Open work lists from the summary cards.'],
  ['5','messages','admin','Percakapan label dan notifikasi','Label conversations and notifications','Coba panel chat, balasan, dan pergantian panel.','Try chat, replies, and switching panels.'],
  ['4','procedures','super','Prosedur pekerjaan','Work procedures','Lihat aturan tahap dan pengingat pekerjaan.','Review stage rules and work reminders.'],
  ['3','payroll','super','Dokumen kompensasi','Compensation documents','Buka pengelolaan dokumen dan riwayat pembayaran.','Open document management and payment history.'],
  ['2','leave','admin','Kehadiran dan pengajuan cuti','Attendance and leave requests','Coba pengajuan dari akun staf yang bersangkutan.','Try a request from the relevant staff account.'],
  ['1','overview','super','Ringkasan operasional platform','Platform operations overview','Jelajahi dasar dashboard Super Admin.','Explore the Super Admin dashboard foundation.']
].map(([version,id,role,idTitle,enTitle,idDescription,enDescription])=>({version,id,role,title:[idTitle,enTitle],description:[idDescription,enDescription]}));

function studioRoleLabel(role) { return role==='label'?'Label':role==='super'?'Super Admin':'Admin'; }
function studioCapture() {
  return copy8({state,data,ten,v3,v4,v5,v6,v7,v8,v9,people,ui103,labelTab102,labelSummary102});
}
function studioRestoreObject(target,source) {
  for (const key of Object.keys(target)) delete target[key];
  Object.assign(target,copy8(source));
}
function studioRestore(snapshot) {
  closeModal(); closePop();
  data=copy8(snapshot.data); ten=copy8(snapshot.ten);
  for(const [target,key] of [[state,'state'],[v3,'v3'],[v7,'v7'],[v8,'v8'],[v9,'v9'],[ui103,'ui103']]) studioRestoreObject(target,snapshot[key]);
  for(const [target,key] of [[v4,'v4'],[v5,'v5'],[v6,'v6']])if(snapshot[key])studioRestoreObject(target,snapshot[key]);
  v5.pop=null;
  for(const p of snapshot.people) Object.assign(person(p.id),copy8(p));
  labelTab102=snapshot.labelTab102; labelSummary102=snapshot.labelSummary102;
  clock102=null; v8.lastInput=Date.now();
}
function studioAccount(role,member='awan',staff='adovi') {
  ten.role=role; ten.member=member; ten.page='home';
  Object.assign(state,{user:role==='super'?'jeck':staff,mode:'platform',page:'dashboard',preview:null,profile:null});
  v5.group=null; v9.photo=null; v9.work='all'; v9.labelFilter='all'; v9.labelSearch='';
  labelTab102='all'; labelSummary102=null;
  v8.loggedOut=false; v8.lastInput=Date.now();
}
function studioRelease(stage='review') {
  ten.role='label';
  const id=RM10.act(ten,'draft',{title:'Langkah Baru',artist:'Nara',tracks:1,service:'Standard',date:RM10.earliest(ten,'Standard')});
  RM10.act(ten,'submit',{id}); ten.role='admin'; RM10.act(ten,'start',{id});
  if(stage==='delivered') { RM10.act(ten,'approve',{id}); RM10.act(ten,'deliver',{id,checked:true}); }
  return id;
}
async function studioStart(id) {
  const scene=studioCatalog.find(x=>x.id===id);
  if(!scene||studioRunning) return;
  studioRunning=true;
  const language=state.lang, theme=state.theme;
  try {
    if(!studioCheckpoint) {
      studioCheckpoint=studioCapture();
      // Keep the original session recoverable even when a scenario is reloaded.
      localStorage.setItem(studioCheckpointKey,JSON.stringify(studioCheckpoint));
    }
    studioRestore(studioCheckpoint);
    clearTimeout(toastTimer);$('#toast').classList.remove('show');$('#toast').textContent='';
    ten=RM10.seed(); ten.workspace102=true; ten.lang=language; ten.theme=theme;
    state.lang=language; state.theme=theme;
    Object.assign(v8,{scene:'normal',connected:true,failSave:false,loggedOut:false,grants:[],requests:[],time:'09:00',lastInput:Date.now()});
    v7.scene='normal'; v7.slide=0; v3.scenario='today'; v3.day=RM10.day(ten.now);
    tenConfig=false; tenStep=1; tenDetail=null; tenDraftService='Standard';
    studioAccount(scene.role); studioSelected=scene.id;
    // Seed linked catalog once, before assigning scenario-specific records.
    render(); closeModal();
    let open=()=>{};
    if(['plans','credits','release-form','friday-cutoff'].includes(id)) {
      if(id==='friday-cutoff') ten.now=Date.parse('2026-09-25T13:00:00+07:00');
      module102('releases');
      if(id==='plans') open=plans10;
      if(id==='credits') open=purchase10;
      if(['release-form','friday-cutoff'].includes(id)) open=()=>releaseForm10(null);
    } else if(['profile-owner','profile-review'].includes(id)) {
      ten.role='label'; RM10.act(ten,'profile_edit',{name:member10().name+' Studio'});
      ten.role=scene.role;
      if(id==='profile-review') { state.page='labels9'; open=()=>reviewProfile103('awan'); }
      else { ui103.profileTab='identity'; module102('account'); }
    } else if(['bank-directory','location-directory'].includes(id)) {
      ui103.profileTab=id==='bank-directory'?'bank':'identity'; module102('account');
      if(id==='location-directory')open=editProfile103;
    } else if(id==='label-updates') {
      ten.notifications.unshift({id:++ten.serial,member:'awan',key:'profile_approve',at:ten.now});
      open=()=>studioTogglePanel('notifications');
    } else if(id==='contracts') module102('contracts');
    else if(['activation','activation-review'].includes(id)) {
      ten.member='embun'; ten.role='label'; const m=member10();
      if(id==='activation') {
        m.paid=false; m.lots=[]; m.welcome=false;
      } else {
        RM10.act(ten,'profile',{identity:{person:'Laras Senja',address:'Jl. Nada 8, Jakarta',postal:'10110',document:true,country:'Indonesia'}});
        RM10.act(ten,'contract'); RM10.act(ten,'apply'); ten.role='admin';
        state.page='labels9'; labelTab102='prospects'; open=()=>identityModal10('embun');
      }
    } else if(id==='bank-review') {
      const m=member10(); m.bank.approved=null; m.bank.version=1;
      m.bank.pending={bank:'BCA',number:'0001234500',holder:'Nama berbeda',status:'pending',version:1};
      module102('banks'); open=()=>bankModal10(m.id);
    } else if(['revision','date-error','live-review','urgent','night'].includes(id)) {
      const rid=studioRelease(['date-error','live-review'].includes(id)?'delivered':'review');
      const r=RM10.getRelease(ten,rid);
      if(id==='revision') {
        RM10.act(ten,'revision',{id:rid,note:T('Sesuaikan nama artis dengan profil resminya.','Match the artist name to the official profile.')});
        ten.now+=22*RM10.H;
      } else if(id==='date-error') RM10.act(ten,'date_error',{id:rid,note:T('Tanggal di Believe lebih lambat dari tanggal pengajuan.','The Believe date is later than the requested date.')});
      else if(id==='live-review') RM10.act(ten,'codes',{id:rid,upc:'123456789012',isrc:'IDABC2600001'});
      else { r.urgent102=true; r.date='2026-09-24'; }
      ten.role=scene.role;
      if(id==='night') ten.now=Date.parse('2026-09-25T21:00:00+07:00');
      if(['date-error','live-review'].includes(id)) { module102('releases'); open=()=>releaseModal10(rid); }
    } else if(id==='master') { state.page='labels9'; open=()=>labelDetail9('L06'); }
    else if(id==='royalties') state.page='liability9';
    else if(id==='standards') state.page='standards9';
    else if(id==='idle') { state.mode='staff';state.page='overview';v8.loggedOut=true; }
    else if(id==='attendance') { state.mode='staff';state.page='overview';open=()=>attendanceDrawer8('adovi'); }
    else if(id==='new-month') { ten.now=Date.parse('2026-10-01T09:00:00+07:00');state.mode='staff';state.page='overview'; }
    else if(id==='messages') {
      data.chats.label.push({who:'Senja Records',text:['Nama artis sudah kami sesuaikan. Mohon diperiksa kembali.','We have corrected the artist name. Please review it again.']});
      v3.chatUnread=1; state.chat='label'; open=()=>studioTogglePanel('chat');
    } else if(id==='procedures') state.page='workrules';
    else if(id==='payroll') {state.mode='staff';state.page='compensation';state.comp='team';}
    else if(id==='leave') {state.user='cantika';state.mode='staff';state.page='attendance';}
    clock102=null;RM10.tick(ten);save10();save8();render();open();window.scrollTo(0,0);
  } catch(error) {
    if(studioCheckpoint) {studioRestore(studioCheckpoint);save10();save8();render();}
    studioSelected=null;
    toast(T('Kondisi belum dapat dibuka. Sesi sebelumnya dipulihkan.','The scenario could not open. Your previous session was restored.'));
    console.error(error);
  } finally {studioRunning=false;}
}

studio8=function() {
  const versions=[...new Set(studioCatalog.map(s=>s.version))];
  const current=isLabel10()?'label:'+ten.member:state.user;
  drawer8(T('Studio Pratinjau','Preview Studio'),`
    <div class="studio-intro"><p>${T('Pilih pengalaman. Akun dan halaman akan menyesuaikan.','Choose an experience. The account and page follow automatically.')}</p>
    ${info9('studio-session',T('Setiap kondisi memulai contoh baru. Akun di bawah dapat diganti untuk melanjutkan contoh yang sama. Pulihkan sesi mengembalikan data sebelum memilih kondisi pertama.','Each scenario starts a fresh example. Switch the account below to continue that same example. Restore session returns to the data before the first scenario.'))}</div>
    <label class="studio-account">${T('Lanjutkan sebagai','Continue as')}<select id="studio-account">${people.map(p=>`<option value="${p.id}" ${current===p.id?'selected':''}>${E(p.name)} · ${p.super?'Super Admin':'Admin'}</option>`).join('')}${ten.members.map(m=>`<option value="label:${E(m.id)}" ${current==='label:'+m.id?'selected':''}>${E(m.name)} · Label</option>`).join('')}</select></label>
    ${versions.map((version,i)=>`<section class="studio-version" data-version="${version}"><div class="studio-version-title"><h3>V${version}</h3>${i===0?`<span>${T('Versi terbaru','Latest version')}</span>`:''}</div><div class="studio-scenes">${studioCatalog.filter(s=>s.version===version).map(s=>`<button type="button" data-studio-scene="${s.id}" class="studio-scene ${studioSelected===s.id?'selected':''}"><span class="studio-scene-meta">${studioRoleLabel(s.role)}<span aria-hidden="true">↗</span></span><strong>${T(...s.title)}</strong><small>${T(...s.description)}</small></button>`).join('')}</div></section>`).join('')}
    ${studioCheckpoint?`<button class="btn studio-restore" data-studio-restore>${T('Pulihkan sesi sebelum simulasi','Restore the session before simulation')}</button>`:''}`);
  $('#dialog').classList.add('preview-studio');
};
studio10=studio8;guide=studio8;

// Toggle only the header trigger. Rendering chat after sending/tab switching must stay open.
const studioBaseAction=handleAction;
async function studioTogglePanel(kind) {
  if(v5.pop===kind&&$('#header-popover')) {closePop();$(`.tools [data-action="${kind}"]`)?.focus();return;}
  closePop();
  if(isLabel10()) {
    if(kind!=='notifications')return;
    modal(T('Notifikasi','Notifications'),notification10());convertPopover('notifications');
    $('#header-popover [data-action="v5-read"]')?.remove();
  } else {
    const button=document.createElement('button');button.dataset.action=kind;
    await studioBaseAction(button);
  }
  studioSyncTriggers();
}
function studioSyncTriggers() {
  for(const kind of ['chat','notifications']) {
    const button=$(`.tools [data-action="${kind}"]`);
    if(button) {button.setAttribute('aria-expanded',String(v5.pop===kind&&!!$('#header-popover')));button.setAttribute('aria-controls','header-popover');}
  }
}
const studioBaseClosePop=closePop;
closePop=function(){studioBaseClosePop();studioSyncTriggers();};
handleAction=async function(button) {
  const action=button.dataset.action;
  if(['chat','notifications'].includes(action))return studioTogglePanel(action);
  if(action==='v5-pop-close') {const kind=v5.pop;closePop();$(`.tools [data-action="${kind}"]`)?.focus();return;}
  return studioBaseAction(button);
};
const studioBaseRender=render;
render=function(){studioBaseRender();studioSyncTriggers();};
window.addEventListener('click',event=>{
  const scene=event.target.closest('[data-studio-scene]');
  if(scene) {event.preventDefault();event.stopImmediatePropagation();void studioStart(scene.dataset.studioScene);}
  const restore=event.target.closest('[data-studio-restore]');
  if(restore&&studioCheckpoint) {
    event.preventDefault();event.stopImmediatePropagation();studioRestore(studioCheckpoint);
    studioCheckpoint=null;studioSelected=null;localStorage.removeItem(studioCheckpointKey);save10();save8();render();
  }
},true);
window.addEventListener('change',event=>{
  if(event.target.id!=='studio-account')return;
  event.stopImmediatePropagation();const value=event.target.value;
  if(value.startsWith('label:'))role102('label',value.slice(6));
  else {studioAccount(person(value).super?'super':'admin',ten.member,value);closeModal();save10();render();}
},true);
studioSyncTriggers();
