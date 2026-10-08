/* B40–B45: claim authority, applicant follow-up, drafts and sensitive documents. */
function claimGuard120(id,version){
 staffGuard117();
 if(ten.role!=='super'||!super114())throw Error(T('Tindakan ini hanya tersedia untuk Super Admin aktif.','This action requires an active Super Admin.'));
 const claim=ten.claims105?.find(q=>q.id===id);
 if(!claim)throw Error(T('Klaim tidak tersedia.','The claim is unavailable.'));
 guard114('labels','review',claim.member);
 if(!['pending','conflict'].includes(claim.status)||version!==undefined&&Number(version)!==(claim.version||0))throw Error(T('Status klaim berubah. Buka kembali untuk melihat data terbaru.','The claim status changed. Reopen it to review the latest data.'));
 return claim;
}
function claimEvent120(claim,status,note){
 claim.history??=[];claim.history.push({status,note,at:ten.now,actor:isLabel10()?ten.member:state.user});
 claim.version=(claim.version||0)+1;
}
function reviewClaim120(action,id,version){
 const claim=claimGuard120(id,version);
 if(action==='claim-correct')return reviewDialogUI(T('Minta perbaikan klaim','Request claim corrections'),`<form class="ten-form" data-onboard-form105="claim-correct" data-id="${E(id)}" data-version="${claim.version||0}"><label class="full">${T('Catatan untuk pemohon','Notes for the applicant')}<textarea name="note" rows="3" required maxlength="1000"></textarea></label><footer class="review-footer-ui full"><button class="btn primary" type="submit">${T('Kirim catatan','Send note')}</button></footer></form>`);
 atomic10(()=>{const q=claimGuard120(id,version);q.status='approved';q.reviewed=ten.now;q.quarantine=true;const w=ten.royalty107?.withdraw108;if(w){w.quarantined??=[];if(!w.quarantined.includes(q.member))w.quarantined.push(q.member);w.version=(w.version||0)+1;}for(const x of ten.claims105)if(x.id!==q.id&&x.member===q.member&&['pending','conflict'].includes(x.status)){x.status='superseded';(x.history??=[]).push({status:'superseded',note:'',at:ten.now,actor:state.user});ten.notifications.unshift({id:++ten.serial,member:x.applicant,key:'claim_superseded105',ref:x.id,at:ten.now});}claimEvent120(q,'approved','');RM10.getMember(ten,q.applicant).claimedLabel105=q.member;});
 closeModal();render();
}
function correctClaim120(form,values){
 const note=String(values.note||'').trim();if(!note)throw Error(T('Tuliskan bagian yang perlu diperbaiki.','Describe what needs correction.'));
 atomic10(()=>{const q=claimGuard120(form.dataset.id,form.dataset.version);q.status='correction';q.note=note;claimEvent120(q,'correction',note);ten.notifications.unshift({id:++ten.serial,member:q.applicant,key:'claim_correction120',ref:q.id,at:ten.now});});
 closeModal();render();
}
function ownClaim120(id,status){
 if(!isLabel10())throw Error(T('Klaim ini hanya tersedia untuk pemohon.','This claim is available only to its applicant.'));
 if(storageChanged116())throw conflictError116();
 const q=ten.claims105?.find(q=>q.id===id&&q.applicant===ten.member);
 if(!q||status&&q.status!==status)throw Error(T('Klaim berubah atau tidak tersedia untuk akunmu.','The claim changed or is unavailable to this account.'));
 return q;
}
function claimFollowup120(id){
 const q=ownClaim120(id),target=RM10.getMember(ten,q.member);
 const title=q.status==='conflict'?T('Klaim label disengketakan','Label claim disputed'):q.status==='superseded'?T('Klaim label tertutup','Label claim closed'):q.status==='correction'?T('Perbaiki klaim label','Correct your label claim'):q.status==='pending'?T('Klaim sedang diperiksa','Claim under review'):T('Klaim label disetujui','Label claim approved');
 reviewDialogUI(title,`${language105()}${reviewHeadingUI(target,q.status==='correction'?'correction':q.status==='approved'?'approved':'pending')}<section class="claim-note120"><h3>${T('Catatan pemeriksa','Review notes')}</h3><p>${E(q.status==='conflict'?T('Akun lain turut mengklaim label ini. Kedua klaim ditangguhkan sampai Super Admin memutuskan kepemilikan.','Another account also claims this label. Both claims are suspended until a Super Admin decides ownership.'):q.status==='superseded'?T('Klaim lain disetujui untuk label ini. Hubungi dukungan bila Anda adalah pemilik sah.','Another claim was approved for this label. Contact support if you are the rightful owner.'):(q.note||T('Hubungan kepemilikan label sedang diperiksa.','Your label ownership connection is under review.')))}</p></section>${q.status==='correction'?`<form class="ten-form" data-claim-form120="response" data-id="${E(q.id)}" data-version="${q.version||0}"><label class="full">${T('Penjelasan perbaikan','Correction details')}<textarea name="response" rows="3" required maxlength="1000">${E(claimDrafts120[q.id]||'')}</textarea></label><p class="full muted">${T('Kirim penjelasan sesuai catatan pemeriksa. Pengajuan akan diperiksa kembali pada klaim yang sama.','Respond to the review notes. Your response will be reviewed under the same claim.')}</p><footer class="review-footer-ui full"><button type="submit" class="btn primary">${T('Ajukan kembali','Resubmit claim')} →</button></footer></form>`:`<p>${T('Perkembangan klaim tersedia di dashboard.','Claim updates are available on your dashboard.')}</p>`}`);
}
const claimDrafts120={};
document.addEventListener('input',e=>{const form=e.target.closest('[data-claim-form120=response]');if(form)claimDrafts120[form.dataset.id]=form.elements.response.value;});
window.addEventListener('click',e=>{const button=e.target.closest('[data-claim120]');if(!button)return;e.preventDefault();e.stopImmediatePropagation();try{claimFollowup120(button.dataset.id);}catch(err){toast(err.message);}},true);
window.addEventListener('submit',e=>{
 const form=e.target.closest('[data-claim-form120=response]');if(!form)return;e.preventDefault();e.stopImmediatePropagation();if(!form.reportValidity())return;
 const response=form.elements.response.value.trim();if(!response){saveError117(form,Error(T('Tuliskan penjelasan perbaikan.','Enter your correction details.')));return;}
 try{atomic10(()=>{const q=ownClaim120(form.dataset.id,'correction');if(Number(form.dataset.version)!==(q.version||0))throw Error(T('Catatan klaim berubah. Buka kembali sebelum melanjutkan.','The review notes changed. Reopen the claim before continuing.'));q.response=response;q.status='pending';q.resubmitted=ten.now;claimEvent120(q,'pending',response);});delete claimDrafts120[form.dataset.id];closeModal();render();toast(T('Perbaikan klaim dikirim untuk diperiksa.','Claim corrections submitted for review.'));}catch(err){saveError117(form,err);}
},true);
const attentionBefore120=labelAttention102;
labelAttention102=function(){
 const html=attentionBefore120();if(!isLabel10())return html;
 return html+(ten.claims105||[]).filter(q=>q.applicant===ten.member&&['pending','correction','conflict','superseded'].includes(q.status)).map(q=>`<section class="attention9 ${['pending','conflict'].includes(q.status)?'blue9':''}"><div class="spread"><h2>${q.status==='conflict'?T('Klaim label disengketakan','Your label claim is disputed'):q.status==='superseded'?T('Klaim label tertutup','Your label claim is closed'):q.status==='correction'?T('Klaim label perlu diperbaiki','Your label claim needs corrections'):T('Klaim label sedang diperiksa','Your label claim is under review')}</h2><button class="btn" type="button" data-claim120="open" data-id="${E(q.id)}">${q.status==='correction'?T('Perbaiki','Make corrections'):T('Lihat status','View status')} ↗</button></div><p>${E(q.status==='correction'?q.note:T('Perkembangan klaim akan ditampilkan di sini.','Claim updates will appear here.'))}</p></section>`).join('');
};
const notificationBefore120=notification10;
notification10=function(){
 if(!isLabel10())return notificationBefore120();
 const notices=ten.notifications.filter(n=>n.member===ten.member&&['claim_correction120','claim_conflict105','claim_superseded105','claim_released105'].includes(n.key)).slice(0,3);
 const items=notices.map(n=>{const q=ten.claims105?.find(q=>q.id===n.ref);return q?`<div class="ten-item"><div><strong>${q.status==='conflict'?T('Klaim label disengketakan','Your label claim is disputed'):q.status==='superseded'?T('Klaim label tertutup','Your label claim is closed'):q.status==='correction'?T('Klaim label perlu diperbaiki','Your label claim needs corrections'):q.status==='approved'&&q.quarantineLifted?T('Saldo warisan terbuka','Legacy balance released'):T('Perkembangan klaim label','Label claim update')}</strong><p>${E(q.status==='conflict'?T('Akun lain turut mengklaim label ini — ditangguhkan sampai diputuskan.','Another account also claims this label — suspended until decided.'):q.status==='superseded'?T('Klaim lain disetujui untuk label ini.','Another claim was approved for this label.'):q.status==='approved'&&q.quarantineLifted?T('Baseline saldo warisan disahkan. Saldo kini dapat ditarik sesuai aturan.','The legacy balance baseline is approved. The balance can now be withdrawn per the rules.'):(q.note||''))}</p><small>${date10(n.at,true)}</small></div><button type="button" class="btn" data-claim120="open" data-id="${E(q.id)}">${T('Lihat klaim','View claim')} ↗</button></div>`:'';}).join('');
 const original=ten.notifications;try{ten.notifications=original.filter(n=>!['claim_correction120','claim_conflict105','claim_superseded105','claim_released105'].includes(n.key));return items+notificationBefore120();}finally{ten.notifications=original;}
};
function claimRecovery105(){reviewDialogUI(T('Pemulihan Klaim Label','Label Claim Recovery'),`${language105()}<form class="ten-form" data-onboard-form105="claim-recovery"><label class="full">${T('Jelaskan hubunganmu dengan label dan kontak yang dapat dihubungi.','Describe your connection to the label and an available contact.')}<textarea name="note" required rows="4"></textarea></label><button class="btn primary" type="submit">${T('Kirim untuk diperiksa','Submit for review')}</button></form>`);}
function switchLanguage120(language){
 const dialog=document.querySelector('#dialog'),form=dialog.querySelector('form'),kind=form?.dataset.onboardForm105;
 const values=form?[...form.elements].filter(el=>el.name&&el.type!=='file').map(el=>({name:el.name,type:el.type,value:el.value,checked:el.checked})):[];
 const claimForm=form?.dataset.claimForm120==='response'?form:null;
 let restore;
 if(kind==='identity'){clearTimeout(onboarding105.timer);captureIdentity105(false);restore=activationStep105;}
 else if(kind==='contract')restore=activationStep105;
 else if(kind==='claim-search')restore=claimStart105;
 else if(kind==='claim-code'){const id=ten.claimDraft105?.member;restore=()=>claimResult105(RM10.getMember(ten,id));}
 else if(kind==='claim-recovery')restore=claimRecovery105;
 else if(claimForm){const id=claimForm.dataset.id;claimDrafts120[id]=claimForm.elements.response.value;restore=()=>claimFollowup120(id);}
 else if(dialog.querySelector('[data-onboard105=active-welcome]'))restore=welcome10;
 else if(dialog.querySelector('[data-onboard105=bank]'))restore=activationPopup102;
 else if(dialog.querySelector('[data-onboard105=theme]'))restore=submittedActivation105;
 else if(dialog.querySelector('[data-onboard105=new]'))restore=welcomeStart105;
 else restore=welcomeExplore105;
 state.lang=language;ten.lang=language;save10();restore();
 const next=document.querySelector('#dialog form');if(next)for(const value of values){const field=Array.from(next.elements).find(el=>el.name===value.name&&el.type===value.type);if(!field)continue;if(['checkbox','radio'].includes(value.type))field.checked=value.checked;else field.value=value.value;}
}

// Sensitive content is removed, not merely covered, when its session becomes stale.
let sensitivePanel120=null,openingSensitive120=null;
function sensitiveAllowed120(marker=sensitivePanel120){
 try{if(!marker||Persistence117.blocked||storageChanged116())return false;
 if(marker.role!==ten.role||marker.actor!==(isLabel10()?ten.member:state.user))return false;
 if(isLabel10())return !marker.member||marker.member===ten.member;
 if(user114()?.status!=='active'||v8.loggedOut)return false;
 return marker.permissions.every(permission=>may114('labels',permission,marker.member));
 }catch{return false;}
}
function closeSensitive120(){
 const dialog=document.querySelector('#dialog');if(!sensitivePanel120||!dialog.open)return;
 dialog.querySelectorAll('img,audio,video').forEach(el=>{el.removeAttribute('src');el.remove();});
 sensitivePanel120=null;onboarding105.document=false;onboarding105.bank=false;closeModal();dialog.replaceChildren();
}
function mayReadDocument120(node){const dialog=document.querySelector('#dialog');if(!node?.isConnected||!dialog.open||!dialog.contains(node))return false;if(!sensitiveAllowed120()){closeSensitive120();return false;}return isLabel10()||may114('labels','document',sensitivePanel120?.member);}
const dialogBefore120=reviewDialogUI;
reviewDialogUI=function(...args){
 sensitivePanel120=null;const result=dialogBefore120(...args),dialog=document.querySelector('#dialog');
 if(openingSensitive120||dialog.querySelector('.identity-image-review,.document-upload,#document-workbench-slot')){
  sensitivePanel120={role:ten.role,actor:isLabel10()?ten.member:state.user,member:openingSensitive120?.member|| (isLabel10()?ten.member:null),permissions:[...(openingSensitive120?.permissions||[])]};
  if(dialog.querySelector('.identity-image-review')&&!sensitivePanel120.permissions.includes('document'))sensitivePanel120.permissions.push('document');
  if(!sensitiveAllowed120()){closeSensitive120();toast(T('Data atau akses berubah. Muat ulang sebelum membuka dokumen ini.','Data or access changed. Reload before opening this document.'));}
 }
 return result;
};
for(const [name,permission]of [['identityModal10','review'],['bankModal10','bank'],['reviewDocumentPending','document'],['cleanupOpen','review']]){
 const previous=window[name];window[name]=function(id,...args){
  const marker={role:ten.role,actor:isLabel10()?ten.member:state.user,member:String(id).split('|')[0],permissions:[permission]};
  if(!sensitiveAllowed120(marker))return toast(T('Data atau akses berubah. Muat ulang sebelum membuka informasi ini.','Data or access changed. Reload before opening this information.'));
  openingSensitive120=marker;try{return previous.call(this,id,...args);}finally{openingSensitive120=null;}
 };
}
const readIdentityBefore120=identityRead10;
identityRead10=function(identity){if(!isLabel10()&&!may114('labels','document'))return `<p class="muted">${T('Dokumen identitas memerlukan izin melihat dokumen.','Identity documents require document access permission.')}</p>`;return readIdentityBefore120(identity);};
window.addEventListener('storage',event=>{if(event.key!==V10KEY&&event.key!==null)return;if(sensitivePanel120&&!sensitiveAllowed120())closeSensitive120();});
document.addEventListener('click',event=>{if(!event.target.closest('#dialog .identity-image-review,#dialog .review-document-ui'))return;if(sensitivePanel120&&!sensitiveAllowed120()){event.preventDefault();event.stopImmediatePropagation();closeSensitive120();}},true);
const renderBefore120=render;
function stamp120(){document.title='Rilis Musik · V12.0';document.querySelectorAll('.version-pill,.floating107>strong').forEach(el=>el.textContent='V12.0');const foot=document.querySelector('.footer span');if(foot)foot.textContent='RILIS MUSIK · V12.0';}
render=function(){if(sensitivePanel120&&!sensitiveAllowed120())closeSensitive120();renderBefore120();stamp120();};
const studioBefore120=studioStart;
const scenes120=[
 ['v120-claim-correction','label','Klaim Label · catatan dan perbaikan','Label Claim · notes and corrections','Lanjutkan perbaikan melalui kartu atensi dan ajukan kembali klaim yang sama.','Continue from the attention card and resubmit the same claim.'],
 ['v120-claim-review','super','Klaim Label · pemeriksaan akses','Label Claim · access checks','Persetujuan dan koreksi memerlukan Super Admin aktif serta data terbaru.','Approval and corrections require an active Super Admin and current data.'],
 ['v120-activation','label','Aktivasi · isian dan bahasa','Activation · entries and language','Ganti bahasa tanpa kehilangan isian atau langkah aktivasi.','Switch languages without losing entries or the activation step.']
];
studioCatalog.unshift(...scenes120.map(([id,role,a,b,c,d])=>({version:'12.0',id,role,title:[a,b],description:[c,d]})));
studioStart=async function(id){
 closeSensitive120();clearTimeout(onboarding105.timer);
 if(!id.startsWith('v120-')){const result=await studioBefore120(id);stamp120();return result;}
 if(id==='v120-activation'){await studioBefore120('v105-activation');}
 else{
  await studioBefore120('v105-claim');closeModal();member10().name='Embun Label';member10().onboardingSeen105=true;
  const correction=id==='v120-claim-correction';
  ten.claims105=[{id:'CLAIM-120',member:'awan',applicant:'embun',status:correction?'correction':'pending',version:1,note:correction?'Jelaskan hubunganmu dengan label dan kontak yang dapat dihubungi.':'Kontak lama telah dikonfirmasi dalam simulasi.',at:ten.now,history:[]}];
  if(correction){state.page='dashboard';state.mode='platform';}else{role102('super');module102('labels');}
  save10();render();
 }
 studioSelected=id;save10();stamp120();
};
render();
