/* B32–B39: one achievement source and transactional bonus delivery. */
function requestId119(){return id118().replace(/^SL-/,'BONUS-');}
function canJourney119(id){
 try{if(storageChanged116()){window.storageConflict116=true;conflictBanner116();return false;}}catch{return false;}
 if(!RM10.getMember(ten,id))return false;
 if(isLabel10())return ten.member===id;
 return !!user114()&&user114().status==='active'&&may114('labels','view',id)&&memberScope114(id);
}
function emblemEvent119(event){
 const earned=RM10.pending.levels.filter(l=>event.levels?.includes(l.name)||l.name===event.level).map(l=>l.id);
 return emblemUI({achievement:{earned}});
}
function saveError119(form,err){
 const message=err.name==='QuotaExceededError'?T('Bonus belum dikirim. Penyimpanan browser penuh; isianmu tetap tersedia untuk dicoba kembali.','The bonus was not sent. Browser storage is full; your entries remain available to retry.'):error10(err.message);
 saveError117(form,Object.assign(Error(message),{code:err.code}));
 if(err.code==='storage_conflict'&&!form.querySelector('[data-bonus-refresh119]')){
  const button=document.createElement('button');button.type='button';button.className='btn full';button.dataset.bonusRefresh119='';button.textContent=T('Muat data terbaru · pertahankan isian','Load latest data · keep entries');form.append(button);
 }
}
const bonusRecoveryKey119='rm-bonus-draft119';
function captureBonus119(){const form=document.querySelector('[data-pending-form=bonus]');if(form)Object.assign(pendingUI.bonusDraft||={},Object.fromEntries(new FormData(form)));return pendingUI.bonusDraft;}
const conflictBefore119=conflictReview116;
conflictReview116=function(){
 if(!document.querySelector('[data-pending-form=bonus]'))return conflictBefore119();
 captureBonus119();bonusForm();saveError119(document.querySelector('[data-pending-form=bonus]'),conflictError116());
};
document.addEventListener('click',e=>{
 if(!e.target.closest('[data-bonus-refresh119]'))return;e.preventDefault();
 const form=document.querySelector('[data-pending-form=bonus]');
 try{sessionStorage.setItem(bonusRecoveryKey119,JSON.stringify({owner:state.user,draft:captureBonus119()}));location.reload();}catch(err){saveError119(form,err);}
});
function restoreBonus119(){
 let saved;try{saved=JSON.parse(sessionStorage.getItem(bonusRecoveryKey119)||'null');sessionStorage.removeItem(bonusRecoveryKey119);}catch{return;}
 if(!saved||ten.role!=='super'||!user114()?.super||user114()?.status!=='active'||ui114.preview||saved.owner!==state.user||!saved.draft?.requestId||!may114('labels','review',saved.draft.member))return;
 pendingUI.bonusDraft=saved.draft;bonusForm();const notice=document.createElement('p');notice.className='full muted';notice.setAttribute('role','status');notice.textContent=T('Data terbaru telah dimuat. Periksa penerima dan rincian bonus sebelum mengirim.','The latest data is loaded. Review the recipient and bonus details before sending.');document.querySelector('[data-pending-form=bonus]').prepend(notice);
}
// Reusing the shared dialog must never retain a previous recipient or access marker.
const dialogBefore119=reviewDialogUI;
reviewDialogUI=function(...args){delete document.querySelector('#dialog').dataset.journey119;return dialogBefore119(...args);};
window.addEventListener('storage',e=>{if(e.key!==V10KEY&&e.key!==null)return;const d=document.querySelector('#dialog');if(d.open&&d.dataset.journey119&&!canJourney119(d.dataset.journey119)){closeModal();delete d.dataset.journey119;}});
function standardsPage119(){
 if(!isLabel10()&&user114()?.status!=='active')return denied9();
 return standardsPage9();
}
const standardsBefore119=standardsPage9;
standardsPage9=function(){
 if(!isLabel10()&&user114()?.status!=='active')return denied9();
 const box=document.createElement('div');box.innerHTML=standardsBefore119();
 box.insertAdjacentHTML('beforeend',`<details class="credit-reference119 panel"><summary>${T('Penggunaan Kredit','Using Credits')}</summary>${creditGuide11()}</details>`);
 return box.innerHTML;
};
const renderBefore119=render;
function stamp119(){document.title='Rilis Musik · V11.9';document.querySelectorAll('.version-pill,.floating107>strong').forEach(x=>x.textContent='V11.9');const f=document.querySelector('.footer span');if(f)f.textContent='RILIS MUSIK · V11.9';}
render=function(){
 if(Persistence117.blocked)return;
 renderBefore119();stamp119();
 const dialog=document.querySelector('#dialog');if(dialog.open&&dialog.dataset.journey119&&!canJourney119(dialog.dataset.journey119)){closeModal();delete dialog.dataset.journey119;}
 document.querySelectorAll('.side-scroll [data-u11=guide]').forEach(link=>{link.dataset.u11='standards';link.classList.toggle('active',state.page==='module'&&v4.module==='standards119');});
 if(state.page==='module'&&v4.module==='standards119'){
  document.querySelector('#main')?.classList.add('standards116');
  const path=document.querySelector('.header-path');if(path)path.textContent=(isLabel10()?'Label':ten.role==='super'?'Super Admin':'Admin')+' / '+T('Standar & Penanda','Standards & Markers');
 }
};
const scenes119=[
 ['v119-emblem','label','Pencapaian label baru','New label achievement','Pembayaran pertama menghasilkan Bronze I dan hadiah sekali, tanpa tautan ke data lama.','The first payment earns Bronze I and one reward, without a legacy data link.'],
 ['v119-bonus','super','Bonus kredit dan pratinjau','Credit bonus and preview','Kirim bonus dengan isian yang bertahan ketika penyimpanan gagal.','Send a bonus with entries preserved when storage fails.'],
 ['v119-guide','admin','Panduan bersama lintas akun','Shared guide across accounts','Penanda, lima belas level emblem, dan penggunaan kredit tersedia dalam satu menu.','Indicators, fifteen emblem levels and credit usage are available in one menu.']
];
studioCatalog.unshift(...scenes119.map(([id,role,a,b,c,d])=>({version:'11.9',id,role,title:[a,b],description:[c,d]})));
const studioBefore119=studioStart;
studioStart=async function(id){
 if(!id.startsWith('v119-')){const result=await studioBefore119(id);stamp119();return result;}
 await studioBefore119('overview');document.querySelectorAll('dialog[open]').forEach(d=>d.close());
 if(id==='v119-emblem'){
  role102('super');state.user='jeck';const m=ten.members.find(m=>m.id==='catalogue-8');
  m.achievement={baseline:true,owner:m.id,paid:0,earned:[],historical:false,payoutStart116:0,payoutBase116:0,payoutLegacy116:0};
  atomic10(()=>{model107().ledger.push({id:'V119-PAID',member:m.id,bucket:'paid',amount:1000000,kind:'withdrawn',at:new Date(ten.now).toISOString()});pendingInit();});
  role102('label',m.id);state.page='dashboard';state.mode='platform';render();
 }else if(id==='v119-bonus'){
  role102('super');state.user='jeck';pendingUI.tab='bonuses';state.page='liability9';state.mode='platform';render();pendingUI.bonusDraft=null;bonusForm();
 }else{role102('admin');state.user='adovi';route11('standards119');}
 studioSelected=id;save10();stamp119();
};
if(!Persistence117.blocked){try{atomic10(()=>pendingInit());render();restoreBonus119();}catch(err){toast(error10(err.message));}}
