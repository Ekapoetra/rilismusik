/* Local, deterministic preview. No production requests or payment services. */
(function(root){
 const H=3600000,DAY=24*H;
 const clone=x=>JSON.parse(JSON.stringify(x));
 const day=t=>new Date(t+7*H).toISOString().slice(0,10);
 const stamp=t=>new Date(t).toISOString();
 const noon=t=>new Date(t+7*H);
 function member(id,name,plan,active=false){return {id,name,plan,period:'year',email:id+'@example.test',emailConfirmed:true,paid:true,invoice:null,active,activatedAt:null,version:1,contract:false,identity:{person:'',address:'',postal:'',country:'Indonesia',document:false},application:null,bank:{approved:null,pending:null,version:0},social:'',lots:[],royaltyRate:60,joined:'2026-09-23',welcome:false};}
 function seed(){
  const now=Date.parse('2026-09-25T09:00:00+07:00'),a=member('awan','Awan Records','Pro',true),b=member('embun','Embun Label','Flex');
  a.identity={person:'Nara Pradana',address:'Jl. Melodi 12, Bandung',postal:'40111',country:'Indonesia',document:true};a.contract=true;a.activatedAt=stamp(now-DAY*4);a.subscriptionEnd=stamp(now+365*DAY);a.welcome=true;
  a.bank.approved={bank:'BCA',number:'0001234500',holder:'Nara Pradana',version:1};a.lots=[{id:'paid-awan',type:'paid',available:8,expires:null}];b.lots=[{id:'paid-embun',type:'paid',available:1,expires:null}];
  const s={schema:1,now,role:'label',actor:'label',member:'awan',members:[a,b],releases:[],events:[],serial:1,notifications:[],lang:'id',theme:'light',page:'home',layout:{gap:'normal',size:'normal',font:'normal',design:'plain'},failNext:false};tick(s);return s;
 }
 function log(s,kind,target,note){s.events.unshift({id:++s.serial,kind,target,note,actor:s.role,at:s.now});}
 function notify(s,m,key,ref){s.notifications.unshift({id:++s.serial,member:m,key,ref,at:s.now});}
 const getMember=(s,id=s.member)=>s.members.find(x=>x.id===id);
 const getRelease=(s,id)=>s.releases.find(x=>x.id===id);
 function assert(ok,code){if(!ok)throw Error(code);}
 function staff(s){assert(s.role==='admin'||s.role==='super','permission');}
 function owner(s,m){assert(s.role==='label'&&m.id===s.member,'permission');}
 function daily(s,m){return m.active&&m.plan!=='Flex'&&m.subscriptionEnd&&Date.parse(m.subscriptionEnd)>s.now;}
 function available(s,m){return m.lots.filter(x=>(!x.expires||x.expires>s.now)&&(x.type!=='daily'||daily(s,m)));}
 function balance(s,m){return available(s,m).reduce((a,x)=>(a[x.type]=(a[x.type]||0)+x.available,a),{paid:0,daily:0,replacement:0});}
 function tick(s){
  for(const m of s.members){
   if(daily(s,m)&&!m.lots.some(x=>x.id==='daily-'+day(s.now))){const end=Date.parse(day(s.now)+'T00:00:00+07:00')+DAY;m.lots.push({id:'daily-'+day(s.now),type:'daily',available:(typeof Credit11!=='undefined'?Credit11.active(s).rules.daily:5),expires:end,day:day(s.now)});}
   if(m.invoice?.status==='pending'&&m.invoice.expires<=s.now)m.invoice.status='expired';
  }
  for(const r of s.releases){if(r.flow105)continue;if(r.status==='revision'&&r.deadline<=s.now){releaseCredits(s,r,'timeout');r.status='closed';r.reason='timeout';notify(s,r.member,'timeout',r.id);log(s,'timeout',r.id,'');}else if(r.status==='revision'){r.reminders=r.reminders||[];for(const hr of [4,12,22])if(s.now>=r.revisionStarted+hr*H&&!r.reminders.includes(hr)){r.reminders.push(hr);notify(s,r.member,'reminder',r.id);}}}
 }
 function allocate(s,m,n){
  const lots=available(s,m).filter(x=>x.available>0).sort((a,b)=>(a.type==='paid')-(b.type==='paid')||(a.expires||Infinity)-(b.expires||Infinity));
  assert(lots.reduce((v,x)=>v+x.available,0)>=n,'credits');let left=n;const out=[];
  for(const lot of lots){const take=Math.min(left,lot.available);if(take){lot.available-=take;out.push({lot:lot.id,type:lot.type,expires:lot.expires,amount:take});left-=take;}if(!left)break;}return out;
 }
 function giveBack(s,m,a,reason,r){
  const prior=m.lots.reduce((n,l)=>n+l.available,0);
  if(a.type==='paid'){let lot=m.lots.find(x=>x.id===a.lot);if(!lot){lot={id:a.lot,type:'paid',available:0,expires:null};m.lots.push(lot);}lot.available+=a.amount;}
  else if(a.expires>s.now){const lot=m.lots.find(x=>x.id===a.lot);if(lot)lot.available+=a.amount;}
  else if(a.type==='daily'&&!['voluntary','timeout'].includes(reason)){m.lots.push({id:'replacement-'+(++s.serial),type:'replacement',available:a.amount,expires:s.now+48*H,origin:r.id});}
  const restored=m.lots.reduce((n,l)=>n+l.available,0)-prior;
  s.creditReturns??=[];s.creditReturns.unshift({id:'return-'+(++s.serial),member:m.id,release:r.id,amount:restored,allocated:a.amount,type:a.type==='daily'&&a.expires<=s.now&&restored?'replacement':a.type,expires:a.type==='paid'?null:a.expires>s.now?a.expires:restored?s.now+48*H:a.expires,reason,at:s.now});
 }
 function releaseCredits(s,r,reason){if(r.creditState!=='reserved')return;const m=getMember(s,r.member);for(const a of r.allocation)giveBack(s,m,a,reason,r);r.creditState='returned';log(s,'credit_return',r.id,reason);}
 function earliest(s,service){let d=noon(s.now);const weekday=d.getUTCDay(),hour=d.getUTCHours();if(service==='MAX'&&weekday===5){if(hour>=12)return null;d.setUTCDate(d.getUTCDate()+2);return d.toISOString().slice(0,10);}let count=service==='MAX'?3:service==='Express'?5:7;while(count){d.setUTCDate(d.getUTCDate()+1);if(![0,6].includes(d.getUTCDay()))count--;}return d.toISOString().slice(0,10);}
 function act(s,action,p={}){
  tick(s);if(s.failNext){s.failNext=false;throw Error('save_failed');}
  const m=getMember(s,p.member||s.member),r=p.id?getRelease(s,p.id):null;
  if(action==='invoice'){owner(s,m);assert(!m.invoice||m.invoice.status!=='pending','invoice_pending');assert(['Flex','Go','Pro','Business'].includes(p.plan),'invalid');m.invoice={id:'INV-'+(++s.serial),plan:p.plan,period:p.period==='month'?'month':'year',status:'pending',expires:s.now+DAY,credits:Math.max(1,Math.min(500,Number(p.credits)||1)),kind:p.kind||'activation'};log(s,action,m.id,'');}
  else if(action==='pay'){owner(s,m);assert(m.invoice?.status==='pending'&&m.invoice.expires>s.now,'invoice_expired');m.invoice.status='paid';m.paid=true;if(m.invoice.kind==='activation'){m.plan=m.invoice.plan;m.period=m.invoice.period;if(m.active&&m.plan!=='Flex'){const end=new Date(Math.max(s.now,Date.parse(m.subscriptionEnd)||0));if(m.period==='year')end.setUTCFullYear(end.getUTCFullYear()+1);else end.setUTCMonth(end.getUTCMonth()+1);m.subscriptionEnd=stamp(end.getTime());}}if(m.invoice.plan==='Flex'||m.invoice.kind==='credits')m.lots.push({id:'purchase-'+m.invoice.id,type:'paid',available:m.invoice.credits,expires:null});log(s,action,m.id,'');}
  else if(action==='profile'){owner(s,m);assert(m.application?.status!=='pending','pending');const name=String(p.name||m.name).trim(),email=String(p.email||m.email).trim(),identity={...m.identity,...p.identity};const changed=name!==m.name||email!==m.email||JSON.stringify(identity)!==JSON.stringify(m.identity);m.name=name;m.email=email;m.identity=identity;delete m.profileDraft;if(changed){m.version++;m.contract=false;if(m.application?.status==='correction')m.application.status='draft';log(s,action,m.id,'');}}
  else if(action==='contract'){owner(s,m);assert(m.identity.person&&m.identity.address&&m.identity.postal&&m.identity.document&&m.name,'identity');m.contract=true;m.contractVersion=m.version;log(s,action,m.id,'');}
  else if(action==='apply'){owner(s,m);assert(m.emailConfirmed&&m.contract&&m.contractVersion===m.version&&m.identity.document,'prerequisites');assert(m.application?.status!=='pending','pending');m.application={status:'pending',version:m.version,submitted:s.now,snapshot:clone({name:m.name,...m.identity}),note:''};notify(s,m.id,'application',m.id);log(s,action,m.id,'');}
  else if(action==='identity_approve'||action==='identity_correct'){staff(s);assert(m.application?.status==='pending'&&m.application.version===p.version&&m.version===p.version,'stale');if(action==='identity_correct'){assert(p.note,'reason');m.application.status='correction';m.application.note=p.note;notify(s,m.id,'identity_correction',m.id);}else{assert(m.contract&&m.contractVersion===m.version,'prerequisites');m.application.status='approved';m.active=true;m.activatedAt=stamp(s.now);if(m.plan!=='Flex'){const d=new Date(s.now);if(m.period==='year')d.setUTCFullYear(d.getUTCFullYear()+1);else d.setUTCMonth(d.getUTCMonth()+1);m.subscriptionEnd=stamp(d.getTime());}notify(s,m.id,'activated',m.id);}log(s,action,m.id,p.note||'');}
  else if(action==='rate_set'){assert(s.role==='super','permission');const rate=Number(p.rate);assert(Number.isInteger(rate)&&rate>0&&rate<=100,'invalid');assert(String(p.note||'').trim(),'reason');const before=m.royaltyRate??60;m.royaltyRate=rate;log(s,action,m.id,`${before}% → ${rate}% · ${String(p.note).trim()}`);}
  else if(action==='bank_submit'){owner(s,m);assert(p.bank&&/^\d{6,24}$/.test(p.number)&&p.holder,'bank');assert(m.bank.pending?.status!=='pending','pending');m.bank.version++;m.bank.pending={bank:p.bank,number:p.number,holder:p.holder,version:m.bank.version,status:'pending',note:''};log(s,action,m.id,'');}
  else if(action==='bank_approve'||action==='bank_correct'){assert(s.role==='super','permission');assert(m.bank.pending?.status==='pending'&&m.bank.pending.version===p.version,'stale');if(action==='bank_approve'){assert(m.active,'prerequisites');m.bank.approved=clone(m.bank.pending);m.bank.approved.status='approved';m.bank.pending=null;}else{assert(p.note,'reason');m.bank.pending.status='correction';m.bank.pending.note=p.note;}notify(s,m.id,action,m.id);log(s,action,m.id,p.note||'');}
  else if(action==='draft'){owner(s,m);assert(m.active,'inactive');assert(p.title&&p.artist,'invalid');const old=r;assert(!old||old.member===m.id&&old.status==='draft','state');const obj=old||{id:'RM-'+(++s.serial),member:m.id,status:'draft',version:0,history:[],allocation:[],creditState:'none'};Object.assign(obj,{title:String(p.title).trim(),artist:String(p.artist).trim(),tracks:Math.max(1,Math.min(12,Number(p.tracks)||1)),service:p.service||'Standard',date:p.date,version:obj.version+1});if(!old)s.releases.unshift(obj);log(s,action,obj.id,'');return obj.id;}
  else if(action==='submit'){owner(s,m);assert(r?.member===m.id&&r.status==='draft','state');assert(m.active,'inactive');assert(['Standard','Express','MAX'].includes(r.service),'invalid');const first=earliest(s,r.service);assert(first&&r.date>=first,'date');r.allocation=allocate(s,m,r.tracks*({Standard:1,Express:2,MAX:3}[r.service]));r.creditState='reserved';r.status='submitted';r.sent=s.now;r.originalDate=r.date;r.version++;notify(s,m.id,'submitted',r.id);log(s,action,r.id,'');}
  else if(action==='start'){staff(s);assert(r?.status==='submitted','stale');r.status='review';r.handler=s.role;log(s,action,r.id,'');}
  else if(action==='revision'){staff(s);assert(r&&['review','submitted'].includes(r.status),'state');assert(p.note,'reason');let duration=Math.max(1,Math.min(24,Number(p.hours)||24))*H;if(p.same&&r.remaining!==undefined){duration=r.remaining;if(!r.floorUsed){duration=Math.max(duration,2*H);r.floorUsed=true;}}else{r.pauseUsed=false;r.floorUsed=false;}r.status='revision';r.note=p.note;r.baseline={title:r.title,artist:r.artist,version:r.version};r.revisionStarted=s.now;r.deadline=s.now+duration;r.reminders=[];log(s,action,r.id,p.note);notify(s,r.member,'revision',r.id);}
  else if(action==='resubmit'){owner(s,m);assert(r?.member===m.id&&r.status==='revision','state');assert(p.title!==r.title||p.artist!==r.artist||String(p.response||'').trim(),'unchanged');r.remaining=Math.max(0,r.deadline-s.now);r.title=String(p.title||r.title);r.artist=String(p.artist||r.artist);r.response=p.response;r.version++;r.status='submitted';r.deadline=null;log(s,action,r.id,p.response||'');}
  else if(action==='question'){owner(s,m);assert(r?.member===m.id&&r.status==='revision'&&p.note,'state');assert(!r.pauseUsed,'pause_used');r.pauseUsed=true;r.remaining=r.deadline-s.now;r.deadline=null;r.status='clarification';r.question=p.note;log(s,action,r.id,p.note);}
  else if(action==='answer'){staff(s);assert(r?.status==='clarification'&&p.note,'state');r.answer=p.note;r.status='revision';r.deadline=s.now+Math.max(r.remaining,2*H);r.floorUsed=true;r.revisionStarted=s.now;r.reminders=[];log(s,action,r.id,p.note);notify(s,r.member,'answer',r.id);}
  else if(action==='approve'){staff(s);assert(r?.status==='review','state');r.status='approved';log(s,action,r.id,'');}
  else if(action==='deliver'){staff(s);assert(r?.status==='approved'&&p.checked,'check');r.status='delivered';r.delivered=s.now;log(s,action,r.id,'date_confirmed');}
  else if(action==='codes'){staff(s);assert(r&&['delivered','followup'].includes(r.status),'state');assert(p.upc&&p.isrc&&p.isrc.split(',').filter(v=>v.trim()).length===r.tracks,'invalid');r.upc=p.upc;r.isrc=p.isrc;log(s,action,r.id,'');}
  else if(action==='not_found'||action==='date_error'){staff(s);assert(r&&(action==='date_error'?['delivered','followup','live']:['delivered','followup']).includes(r.status),'state');if(action==='date_error')assert(p.note,'reason');r.incident=action;r.incidentNote=p.note||'';r.status='followup';if(r.creditState==='consumed')r.creditState='reserved';log(s,action,r.id,p.note||'');notify(s,r.member,action,r.id);}
  else if(action==='followup'){staff(s);assert(r?.status==='followup'&&p.note,'state');r.followup=p.note;log(s,action,r.id,p.note);}
  else if(action==='live'){staff(s);assert(r&&['delivered','followup'].includes(r.status)&&p.checked,'check');assert(r.upc&&r.isrc&&/^https:\/\//.test(p.link||''),'evidence');assert(r.creditState==='reserved','state');r.link=p.link;r.checkedAt=s.now;r.status='live';r.live=s.now;r.creditState='consumed';notify(s,r.member,'live',r.id);log(s,action,r.id,p.link);}
  else if(action==='reject'){staff(s);assert(r&&!['live','closed','draft','cancel_requested'].includes(r.status)&&p.note,'state');releaseCredits(s,r,'rejected');r.status='closed';r.reason=p.note;log(s,action,r.id,p.note);notify(s,r.member,'rejected',r.id);}
  else if(action==='cancel'){owner(s,m);assert(r?.member===m.id&&!['live','closed','cancel_requested'].includes(r.status),'state');if(['draft','submitted'].includes(r.status)){releaseCredits(s,r,'voluntary');r.status='closed';r.reason='cancelled';}else{r.previousStatus=r.status;r.status='cancel_requested';r.deadline=null;}log(s,action,r.id,'');}
  else if(action==='cancel_confirm'){staff(s);assert(r?.status==='cancel_requested'&&p.checked,'check');releaseCredits(s,r,r.incident==='date_error'?'internal':'voluntary');r.status='closed';r.reason='cancelled';log(s,action,r.id,'');}
  else if(action==='reopen'){owner(s,m);assert(r?.member===m.id&&r.status==='closed','state');const next=clone(r);Object.assign(next,{id:'RM-'+(++s.serial),status:'draft',allocation:[],creditState:'none',deadline:null,upc:null,isrc:null,link:null});s.releases.unshift(next);log(s,action,next.id,'');return next.id;}
  else if(action==='downgrade_offer'){staff(s);assert(r&&['followup','delivered','approved'].includes(r.status),'state');const cost={Standard:1,Express:2,MAX:3};assert(cost[p.service]<cost[r.service]&&p.date>=day(s.now),'invalid');r.offer={service:p.service,date:p.date};log(s,action,r.id,'');notify(s,r.member,'offer',r.id);}
  else if(action==='downgrade_accept'){owner(s,m);assert(r?.member===m.id&&r.offer&&r.creditState==='reserved','state');const cost={Standard:1,Express:2,MAX:3};let count=(cost[r.service]-cost[r.offer.service])*r.tracks;for(let i=r.allocation.length-1;i>=0&&count;i--){const a=r.allocation[i],n=Math.min(a.amount,count);giveBack(s,m,{...a,amount:n},'internal',r);a.amount-=n;count-=n;}r.allocation=r.allocation.filter(a=>a.amount);r.service=r.offer.service;r.date=r.offer.date;r.offer=null;log(s,action,r.id,'');}
  else throw Error('invalid');
  tick(s);return true;
 }
 const api={seed,tick,act,day,earliest,balance,getMember,getRelease,daily,H,DAY};
 if(typeof module!=='undefined')module.exports=api;root.RM10=api;
})(typeof window==='undefined'?globalThis:window);
