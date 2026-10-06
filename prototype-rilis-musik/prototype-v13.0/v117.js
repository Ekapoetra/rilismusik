/* One persisted revision covers both the legacy workspace and all newer modules. */
let legacyBusy117=false;
Object.assign(copy113English,{
 'Bukti pembayaran tidak valid. Periksa referensi, nominal, dan mata uang.':'Payment evidence is invalid. Check the reference, amount, and currency.',
 'Bukti pembayaran bertentangan. Periksa konfirmasi penyedia.':'Payment evidence conflicts. Review the provider confirmation.',
 'Nominal pembayaran tidak valid.':'The payment amount is invalid.',
 'Total pembayaran melampaui batas perhitungan yang aman.':'The payment total exceeds the safe calculation range.',
 'Dana atau bukti pembayaran perlu diperiksa kembali.':'The funds or payment evidence need to be reviewed again.'
});
const superForms117=new Set(['correct-time9','v5-time','standards9','role','assign','policy','quota','salary','surprise','holiday','leave-reject','leave-approve','op-decision','slip','void-slip','work-rule','v5-policy','v8-kpi-rule','v8-grant']);
function staffGuard117(kind='',target=''){
 if(Persistence117.blocked)throw Persistence117.error();
 const u=user114();
 if(isLabel10()||!u||u.status!=='active'||v8.loggedOut||state.preview||ui114.preview)throw Error(T('Akun ini tidak dapat mengubah data staff.','This account cannot change staff data.'));
 if(superForms117.has(kind)&&!(ten.role==='super'&&u.super))throw Error(T('Tindakan ini hanya tersedia untuk Super Admin aktif.','This action requires an active Super Admin.'));
 if(['personal','data-issue'].includes(kind)&&target&&target!==u.id&&!u.super)throw Error(T('Data berada di luar aksesmu.','These records are outside your access.'));
 if(storageChanged116())throw conflictError116();
}
// Recheck entry points and submit permissions; an old open form grants no authority.
for(const name of ['account8','photo8','correction9','roleModal','standardsEditor9']){const fn=window[name];if(typeof fn==='function')window[name]=function(...args){try{staffGuard117(name==='correction9'?'correct-time9':name==='roleModal'?'role':'');return fn(...args)}catch(err){toast(err.message)}};}
function operationGuard117(op){staffGuard117();if(op?.type==='payment')guard114('transactions','refund');if(op?.type==='task'){const task=data.tasks.find(x=>x.id===op.id);if(!task)throw Error(T('Pekerjaan tidak ditemukan.','Work item not found.'));const group=task.kind==='support'?'tickets':task.kind==='claim'?'claims':'releases',action=group==='releases'?'review':'handle',member=ten.members.find(m=>m.name===task.label)?.id||null;guard114(group,action,member);}}
for(const name of ['doOperation','applyOperation','outcomeTask']){const fn=window[name];window[name]=function(...args){operationGuard117(name==='outcomeTask'?{type:'task',id:args[0]?.id}:name==='applyOperation'?args[0]:args[2]);return fn(...args)};}
async function legacyCommit117(fn,guard){
 if(legacyBusy117)throw Error(T('Penyimpanan sebelumnya masih berlangsung.','The previous save is still in progress.'));
 guard();const before=structuredClone(ten),shared=sharedSnapshot117(),oldV8=structuredClone(v8),oldPeople=structuredClone(people),queue=[];
 const uiNames=['closeModal','render','toast','modal','drawer8','chatModal'],originals=Object.fromEntries(uiNames.map(name=>[name,window[name]]));
 const app117=document.getElementById('app'),inert117=app117.inert;app117.inert=true;
 legacyBusy117=true;transactionDepth116++;
 for(const name of uiNames)if(typeof originals[name]==='function')window[name]=(...args)=>{queue.push({name,args})};
 let open=true;
 try{const result=await fn();guard();if(queue.some(q=>q.name==='render'))originals.render();transactionDepth116--;open=false;save10();for(const [name,fn]of Object.entries(originals))window[name]=fn;for(const q of queue.filter(q=>q.name!=='render'))originals[q.name](...q.args);return result;}
 catch(err){if(open)transactionDepth116--;restoreState116(before,shared.data,shared);restoreGraph116(v8,oldV8);restoreGraph116(people,oldPeople);transactionDepth116++;try{originals.render()}finally{transactionDepth116--;}throw err;}
 finally{for(const [name,fn]of Object.entries(originals))window[name]=fn;legacyBusy117=false;app117.inert=inert117;}
}
function saveError117(form,err){let box=form.querySelector('.save-error117');if(!box){box=document.createElement('p');box.className='save-error117';box.setAttribute('role','alert');form.append(box);}box.textContent=err.code==='storage_conflict'?err.message:err.name==='QuotaExceededError'||/quota/i.test(err.message)?T('Perubahan belum tersimpan. Penyimpanan browser penuh; isianmu tetap tersedia untuk dicoba kembali.','Changes were not saved. Browser storage is full; your entries remain available to retry.'):err.message;}
const submitBefore117=handleSubmit;
handleSubmit=async function(form){
 if(!form.dataset.form)return submitBefore117(form);
 if(!form.reportValidity())return;
 form.querySelector('.save-error117')?.remove();
 try{return await legacyCommit117(()=>submitBefore117(form),()=>staffGuard117(form.dataset.form,form.dataset.id));}
 catch(err){saveError117(form,err);}
};
const writeActions117=new Map([
 ['op-reject','op-decision'],['slip-copy','slip'],['slip-issue','slip'],['slip-delete','slip'],['slip-void','slip'],['correction-decision','correct-time9'],['standards-save9','standards9'],['portrait-save9','personal'],['request-decision','op-decision'],['leave-decision','leave-reject'],['leave-approve','leave-reject'],['leave-cancel','leave'],['v8-expire','v8-grant'],['surprise-publish','surprise'],['void-slip','void-slip'],['approve','op-decision']
]);
const actionBefore117=handleAction;
handleAction=async function(button){const kind=writeActions117.get(button.dataset.action);if(!kind)return actionBefore117(button);try{return await legacyCommit117(()=>actionBefore117(button),()=>staffGuard117(kind,button.dataset.id));}catch(err){const form=document.querySelector('dialog[open] form');if(form)saveError117(form,err);else toast(typeof saveMessage118==='function'?saveMessage118(err):err.message);}};

function recoveryPage117(){
 if(!Persistence117.blocked)return;
 document.querySelectorAll('dialog[open]').forEach(d=>d.close());document.getElementById('app').setAttribute('inert','');
 const page=document.createElement('main');page.className='recovery-page117';page.innerHTML=`<section class="recovery-card117"><strong>RILIS MUSIK · V11.7</strong><h1>Data tersimpan perlu dipulihkan</h1><p>${Persistence117.problems.some(p=>p.reason==='version')?'Data ini berasal dari versi yang belum didukung. Buka dengan versi yang sesuai atau gunakan cadangan yang kompatibel.':'Sebagian data browser tidak dapat dibaca dengan lengkap. Penyimpanan dihentikan agar data asli tetap terlindungi.'}</p><small>Data asli tidak diganti dengan contoh. Unduh salinannya sebelum melakukan pemulihan. Berkas pemulihan harus memuat data label dan staff.</small><div class="ten-actions"><button class="ten-btn primary" data-recover117="download">Unduh data tersimpan</button>${Persistence117.readBackup()?'<button class="ten-btn" data-recover117="restore">Pulihkan cadangan terakhir</button>':''}<button class="ten-btn" data-recover117="choose">Pilih berkas pemulihan</button><input data-recover117="import" type="file" accept="application/json,.json" aria-label="Berkas pemulihan" hidden><button class="ten-btn" data-recover117="retry">Periksa kembali</button></div><p class="save-error117" hidden role="alert"></p></section>`;
 document.body.append(page);document.title='Rilis Musik · Pemulihan data';
 page.addEventListener('click',e=>{const action=e.target.dataset.recover117;if(action==='download'){const blob=new Blob([JSON.stringify({format:'rm-recovery-117',sources:Persistence117.raw,problems:Persistence117.problems},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='Rilis-Musik-Data-Tersimpan.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}if(action==='choose')page.querySelector('[data-recover117=import]').click();if(action==='retry')location.reload();if(action==='restore'){if(confirm('Pulihkan seluruh data dari cadangan terakhir? Data asli sudah tersedia dalam salinan pemulihan.'))try{Persistence117.replace(Persistence117.readBackup())}catch(err){recoveryError117(page,err)}}});
 page.addEventListener('change',async e=>{if(e.target.dataset.recover117!=='import')return;try{const value=JSON.parse(await e.target.files[0].text());Persistence117.replace(value)}catch(err){recoveryError117(page,err)}});
}
function recoveryError117(page,err){const box=page.querySelector('.save-error117');box.hidden=false;box.textContent=err.message;}
const renderBefore117=render;
function stamp117(){document.title='Rilis Musik · V11.7';document.querySelectorAll('.version-pill,.floating107>strong').forEach(el=>el.textContent='V11.7');const foot=document.querySelector('.footer span');if(foot)foot.textContent='RILIS MUSIK · V11.7';}
render=function(){if(Persistence117.blocked)return;renderBefore117();stamp117();};
const scenes117=[
 ['v117-profile','admin','Profil staff tersimpan utuh','Staff profile saves completely','Ubah profil lalu muat ulang; data akun dan administrasi tetap sama.','Edit the profile, then reload; account and administrative data stay consistent.'],
 ['v117-attendance','super','Koreksi kehadiran dengan penyimpanan aman','Attendance correction with safe saving','Formulir mempertahankan isian ketika penyimpanan gagal atau tab lain memperbarui data.','The form retains entries if saving fails or another tab changes data.'],
 ['v117-refund','super','Referensi dan bukti pengembalian','Refund references and evidence','Pengembalian memerlukan dana sah dan referensi yang belum digunakan.','Refunds require valid funds and an unused reference.']
];
studioCatalog.unshift(...scenes117.map(([id,role,a,b,c,d])=>({version:'11.7',id,role,title:[a,b],description:[c,d]})));
const studioBefore117=studioStart;
studioStart=async function(id){if(!id.startsWith('v117-')){const result=await studioBefore117(id);stamp117();return result;}if(id==='v117-refund')await studioBefore117('v113-refund');else{await studioBefore117('v107-dashboard');document.querySelectorAll('dialog[open]').forEach(d=>d.close());if(id==='v117-profile'){role102('admin');state.user='adovi';account8();}else{role102('super');state.user='jeck';state.mode='staff';state.page='attendance';v8.time='17:00';render();correction9('adovi','2026-09-17');}}studioSelected=id;save10();stamp117();};
if(Persistence117.blocked){booting116=false;recoveryPage117();}else{render();booting116=false;try{save10()}catch(err){toast(err.message)}}
