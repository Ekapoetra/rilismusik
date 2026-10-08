/* Draft domain rules. Local preview only; deployment requires a server transaction layer. */
(function(root){
function attach(api){
 const copy=x=>JSON.parse(JSON.stringify(x)),check=(v,e='invalid')=>{if(!v)throw Error(e);};
 const fingerprint=m=>JSON.stringify({version:m.version,name:m.name,email:m.email,identity:m.identity});
 const bankFingerprint=m=>JSON.stringify({bank:m.bank,identity:fingerprint(m)});
 const init=s=>{s.bonuses??=[];s.creditHistory??=[];s.cleanupHistory??=[];for(const m of s.members)m.lots??=[];};
 const status=(s,b)=>b.status==='pending'&&b.claimBy<=s.now?'expired':b.status;
 const audit=(s,kind,m,detail)=>{const e={id:'P-'+(++s.serial),kind,target:m.id,actor:s.role,at:s.now,...detail};s.events.unshift(e);return e;};
 const grant=(s,m,amount,type,source,ref,hours=48)=>{const id='credit-'+ref;check(!m.lots.some(l=>l.id===id),'duplicate');const lot={id,type:type==='temporary'?'replacement':'paid',available:amount,expires:type==='temporary'?s.now+hours*api.H:null,source,origin:ref};m.lots.push(lot);s.creditHistory.unshift({id,member:m.id,amount,type,source,ref,at:s.now,expires:lot.expires});return lot;};
 const previous=api.act;
 api.act=function(s,action,p={}){
  init(s);const m=api.getMember(s,p.member||s.member);
  if(['bank_approve','bank_correct'].includes(action))check(p.identityReview===fingerprint(m),'identity_changed');
  if(['identity_correct','bank_correct'].includes(action))check(typeof p.note==='string'&&p.note.trim(),'reason');
  if(!['bonus_send','bonus_claim','bonus_cancel','cleanup_save','cleanup_confirm','document_approve','document_correct'].includes(action))return previous(s,action,p);
  api.tick(s);if(s.failNext){s.failNext=false;throw Error('save_failed');}check(m);
  if(['bonus_claim','cleanup_confirm'].includes(action))check(s.role==='label'&&s.member===m.id,'permission');else if(action.startsWith('document_'))check(['admin','super'].includes(s.role),'permission');else check(s.role==='super','permission');
  if(action==='document_approve'||action==='document_correct'){const q=m.documentRequest;check(q?.status==='pending'&&q.id===p.id&&q.base===m.version,'stale');if(action==='document_correct'){check(String(p.note||'').trim(),'reason');q.status='correction';q.note=p.note.trim();}else{m.identity.documentImage=copy(q.image);m.identity.document=true;m.version++;q.status='approved';}q.resolved=s.now;audit(s,action,m,{request:q.id});return true;}
  if(action==='bonus_send'){
   check(Number.isInteger(+p.amount)&&+p.amount>0&&+p.amount<=500);check(['flex','temporary'].includes(p.type));check(String(p.message||'').trim().length>0&&p.message.length<=500);check(p.requestId,'invalid');
   const existing=s.bonuses.find(b=>b.requestId===p.requestId);if(existing)return existing.id;
   const b={id:'bonus-'+(++s.serial),requestId:p.requestId,member:m.id,amount:+p.amount,type:p.type,title:'Bonus dari Rilis Musik',message:p.message.trim(),sent:s.now,claimBy:s.now+(typeof Credit11==='undefined'?48:Credit11.active(s).rules.claimHours)*api.H,temporaryHours:typeof Credit11==='undefined'?48:Credit11.active(s).rules.temporaryHours,status:'pending'};s.bonuses.unshift(b);audit(s,action,m,{bonus:b.id});s.notifications.unshift({member:m.id,key:action,ref:b.id,at:s.now});return b.id;
  }
  if(action==='bonus_claim'||action==='bonus_cancel'){
   const b=s.bonuses.find(b=>b.id===p.id&&b.member===m.id);check(b,'invalid');if(action==='bonus_claim'&&b.status==='claimed')return b.id;check(status(s,b)==='pending','offer_expired');
   if(action==='bonus_claim'){const lot=grant(s,m,b.amount,b.type,'Bonus dari Rilis Musik',b.id,b.temporaryHours||48);b.status='claimed';b.claimed=s.now;b.creditId=lot.id;b.creditExpires=lot.expires;s.notifications.unshift({role:'super',key:'bonus_claimed',ref:b.id,member:m.id,at:s.now});}
   else{b.status='cancelled';b.cancelled=s.now;}audit(s,action,m,{bonus:b.id});return b.id;
  }
  if(action==='cleanup_save'){
   check(p.base===bankFingerprint(m),'stale');check(!('number' in p),'locked_account');const before=copy({identity:m.identity,bank:m.bank.approved});
   if(p.bank){check(m.bank.approved,'bank');check(p.bank.bank&&p.bank.holder,'bank');check(['save','proposal'].includes(p.mode));}
   if(p.identity){const i=p.identity;check(i.location?.complete&&i.postal&&i.country,'location');Object.assign(m.identity,{location:copy(i.location),postal:i.postal,country:i.country,legacyAddress:m.identity.legacyAddress||m.identity.address||'',address:i.address});}
   if(p.bank){check(m.bank.approved,'bank');check(p.bank.bank&&p.bank.holder,'bank');const corrected={...m.bank.approved,bank:p.bank.bank,holder:p.bank.holder,directoryBankId:p.bank.directoryBankId||null};
    if(p.mode==='proposal'){m.bank.cleanupProposal={before:copy(m.bank.approved),after:corrected,status:'pending',at:s.now,id:'correction-'+(++s.serial)};}
    else{check(p.mode==='save');m.bank.approved=corrected;}}
   const after=copy({identity:m.identity,bank:m.bank.approved,proposal:m.bank.cleanupProposal});s.cleanupHistory.unshift({id:'cleanup-'+(++s.serial),member:m.id,before,after,actor:s.role,at:s.now});audit(s,action,m,{mode:p.mode});return true;
  }
  if(action==='cleanup_confirm'){const q=m.bank.cleanupProposal;check(q?.status==='pending'&&q.id===p.id,'stale');check(JSON.stringify(q.before)===JSON.stringify(m.bank.approved),'stale');check(p.decision==='accept'||p.decision==='decline');if(p.decision==='accept')m.bank.approved=copy(q.after);q.status=p.decision==='accept'?'accepted':'declined';q.resolved=s.now;audit(s,action,m,{decision:p.decision});return true;}
 };
 api.pending={init,status,fingerprint,bankFingerprint};return api;
}
if(typeof module!=='undefined')module.exports=attach;else attach(root.RM10);
})(typeof window==='undefined'?globalThis:window);
