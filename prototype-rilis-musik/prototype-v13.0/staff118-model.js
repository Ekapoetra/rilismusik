/* Staff records: effective compensation, immutable slip origins, and dated policies. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.Staff118=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const copy=x=>structuredClone(x);
 const fail=code=>{throw Object.assign(Error(code),{code})};
 const date=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s+'T12:00Z'))&&new Date(s+'T12:00Z').toISOString().slice(0,10)===s;
 const month=s=>typeof s==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(s);
 const amount=x=>Number.isSafeInteger(x)&&x>=0;
 const sum=rows=>{let n=0;for(const r of rows){if(!Number.isSafeInteger(r.amount))fail('payroll_amount');n+=r.amount;if(!Number.isSafeInteger(n))fail('payroll_amount');}return n;};
 function ensure(d,ids,idFactory,at){
  d.staff118||={schema:1,compensation:{},policies:[],migrations:[]};
  const store=d.staff118;
  if(store.schema!==1||!store.compensation||!Array.isArray(store.policies)||!Array.isArray(store.migrations))fail('staff_structure');
  for(const id of ids){
   if(!store.compensation[id]){
    store.compensation[id]=[{id:idFactory(),effective:'0001-01-01',salary:d.salaries[id]??0,allowance:d.allowances[id]??0,percent:d.bonusRules[id]??0,source:'baseline',sequence:0}];
    const next=d.nextComp?.[id];
    if(next&&date(next.effective))store.compensation[id].push({...copy(next),id:idFactory(),source:'legacy-schedule',sequence:1});
   }
  }
  if(!store.policies.length)store.policies.push({policy:copy(d.policy),effective:date(d.policy.effective)?d.policy.effective:'0001-01-01',sequence:0});
  if(!store.slipsNormalized){normalizeSlips(d,idFactory,at);store.slipsNormalized=true;}
  return store;
 }
 function compensation(d,id,m){
  if(!month(m))fail('payroll_period');
  const versions=d.staff118?.compensation[id];if(!versions?.length)fail('staff_not_found');
  const applicable=versions.filter(v=>v.effective<=m+'-31').sort((a,b)=>a.effective.localeCompare(b.effective)||(a.sequence||0)-(b.sequence||0));
  const v=applicable.at(-1);if(!v)fail('compensation_missing');
  const mid=applicable.some(x=>x.effective.startsWith(m)&&!x.effective.endsWith('-01'));
  if(mid)return {...copy(v),available:false,reason:'compensation_midmonth'};
  if(!amount(v.salary)||!amount(v.allowance)||!Number.isFinite(v.percent)||v.percent<0||v.percent>100)fail('payroll_amount');
  return {...copy(v),available:true};
 }
 function schedule(d,id,v,idFactory,at){
  if(!d.staff118?.compensation[id])fail('staff_not_found');
  if(!date(v.effective)||!v.effective.endsWith('-01'))fail('compensation_midmonth');
  if(!amount(v.salary)||!amount(v.allowance)||!Number.isFinite(v.percent)||v.percent<0||v.percent>100)fail('payroll_amount');
  if(d.slips.some(s=>s.staff===id&&s.status==='issued'&&s.month>=v.effective.slice(0,7)))fail('compensation_historical');
  const versions=d.staff118.compensation[id];
  const entry={...copy(v),id:idFactory(),sequence:Math.max(...versions.map(x=>x.sequence||0))+1,recordedAt:at,source:'scheduled'};
  versions.push(entry);d.nextComp||={};d.nextComp[id]=copy(v);return entry;
 }
 function rows(d,id,m,labels){
  const c=compensation(d,id,m),revenue=d.revenue[m],revenueReady=amount(revenue);
  const base=[['salary',labels.salary,c.available?c.salary:null,25],['allowance',labels.allowance,c.available?c.allowance:null,10],['sales',labels.sales,c.available&&revenueReady?Math.round(revenue*c.percent/100):null,28]];
  const result=base.map(([key,label,n,day])=>{
   if(n!==null&&!amount(n))fail('payroll_amount');
   const paidKey=`${id}:${m}:${key}`,explicit=d.paid[paidKey];
   // Preserve paid flags carried by an existing historical document; never infer payment for a new period.
   const historical=d.slips.filter(s=>s.staff===id&&s.month===m&&s.status==='issued').sort((a,b)=>b.version-a.version)[0]?.rows.find(r=>r.key===key);
   const paid=n!==null&&(explicit!==undefined?explicit===true:historical?.paid===true);
   return {key,label,amount:n,available:n!==null,reason:!c.available?c.reason:n===null?'revenue_missing':null,paid,scheduledDate:`${m}-${day}`,date:d.paymentDates[paidKey]||`${m}-${day}`,percent:c.percent,compensationVersion:c.id};
  });
  return result;
 }
 function slip(d,id){const found=d.slips.filter(s=>s.id===id);if(found.length!==1)fail(found.length?'slip_identity':'slip_missing');return found[0];}
 function active(d,staff,m){return d.slips.filter(s=>s.staff===staff&&s.month===m&&s.status==='issued');}
 function normalizeSlips(d,idFactory,at){
  const originals=d.slips.map(s=>({s,old:s.id})),counts=new Map();
  for(const {old}of originals)counts.set(old,(counts.get(old)||0)+1);
  const used=new Set();
  for(const {s,old}of originals){if(used.has(s.id)){s.id=idFactory();while(used.has(s.id))s.id=idFactory();s.legacyId118=old;d.staff118.migrations.push({kind:'slip-id',from:old,to:s.id,staff:s.staff,month:s.month,at});}used.add(s.id);}
  for(const {s}of originals){if(s.previous&&counts.get(s.previous)>1){const candidates=originals.filter(x=>x.old===s.previous&&x.s!==s&&x.s.staff===s.staff&&x.s.month===s.month);if(candidates.length===1){const before=s.previous;s.previous=candidates[0].s.id;d.staff118.migrations.push({kind:'slip-origin',id:s.id,from:before,to:s.previous,at});}else{s.review118='origin_ambiguous';s.legacyPrevious118=s.previous;}}}
  const pairs=new Set(d.slips.filter(s=>s.status==='issued').map(s=>s.staff+':'+s.month));
  for(const pair of pairs){const group=d.slips.filter(s=>s.status==='issued'&&s.staff+':'+s.month===pair);if(group.length>1)for(const s of group)s.review118='duplicate_active';}
 }
 function origin(d,s){
  if(s.review118==='origin_ambiguous')fail('slip_origin');
  if(!s.previous)return null;
  const p=slip(d,s.previous);if(p.staff!==s.staff||p.month!==s.month)fail('slip_origin');return p;
 }
 function copySlip(d,id,idFactory,at){
  const old=slip(d,id);if(old.status!=='issued'||active(d,old.staff,old.month).length!==1)fail('slip_stale');
  const s={...copy(old),id:idFactory(),previous:old.id,status:'draft',version:old.version+1,created:at};
  delete s.review118;delete s.legacyId118;delete s.issuedAt118;delete s.issuedBy118;
  if(d.slips.some(x=>x.id===s.id))fail('slip_identity');d.slips.push(s);return s;
 }
 function saveSlip(d,id,v,entries,idFactory,at){
  let s=id&&id!=='new'?slip(d,id):null;
  if(s&&s.status!=='draft')fail('slip_stale');
  if(!month(v.month)||!d.staff118?.compensation[v.staff])fail('staff_not_found');
  if(!Number.isSafeInteger(v.adjust)||!v.note?.trim())fail('slip_amount');
  if(s?.previous){origin(d,s);if(s.staff!==v.staff||s.month!==v.month)fail('slip_origin');}
  let p=s?.previous?origin(d,s):null;
  const current=active(d,v.staff,v.month);
  if(!p&&current.length>1)fail('slip_stale');
  if(!p)p=current[0]||null;
  const r=copy(p?.rows||entries);
  if(!Array.isArray(r)||!r.length||r.some(x=>x.amount===null||x.available===false))fail('payroll_unavailable');
  const total=sum(r)+v.adjust;if(!Number.isSafeInteger(total)||total<0)fail('slip_amount');
  if(!s){s={id:idFactory(),staff:v.staff,month:v.month,previous:p?.id||null,status:'draft',version:(p?.version||0)+1};if(d.slips.some(x=>x.id===s.id))fail('slip_identity');d.slips.push(s);}
  Object.assign(s,{staff:v.staff,month:v.month,adjust:v.adjust,note:v.note.trim(),rows:r,created:at});return s;
 }
 function issue(d,id,at,actor){
  const s=slip(d,id);if(s.status!=='draft')fail('slip_stale');
  const p=origin(d,s),current=active(d,s.staff,s.month);
  if(p&&(p.status!=='issued'||current.length!==1||current[0].id!==p.id||s.version!==p.version+1))fail('slip_stale');
  if(!p&&current.length)fail('slip_stale');
  const total=sum(s.rows)+(s.adjust||0);if(!Number.isSafeInteger(total)||total<0)fail('slip_amount');
  if(p){p.status='void';p.replacedBy118=s.id;}
  s.status='issued';s.issuedAt118=at;s.issuedBy118=actor;return s;
 }
 function chooseActive(d,id,reason,at,actor){
  const s=slip(d,id),group=active(d,s.staff,s.month);
  if(s.status!=='issued'||group.length<2||!reason?.trim())fail('slip_stale');
  for(const other of group){if(other.id!==s.id){other.status='void';other.voidReason=reason.trim();other.replacedBy118=s.id;}delete other.review118;}
  d.staff118.migrations.push({kind:'slip-active-review',staff:s.staff,month:s.month,chosen:s.id,others:group.filter(x=>x.id!==id).map(x=>x.id),reason:reason.trim(),actor,at});return s;
 }
 function quota(d,person,year,policy=d.policy){
  const joined=Number(person.joined.slice(0,4)),base=joined>year?0:joined===year&&policy.firstYear==='proportional'?Math.ceil(policy.quota*(13-Number(person.joined.slice(5,7)))/12):policy.quota;
  return base+(d.quotaAdjust[`${person.id}:${year}`]??(year===2026?d.quotaAdjust[person.id]||0:0));
 }
 function validatePolicy(d,persons,p,year){
  const minutes=s=>/^\d{2}:\d{2}$/.test(s)?Number(s.slice(0,2))*60+Number(s.slice(3)):NaN;
  const [a,b,c,e]=[p.start,p.end,p.breakStart,p.breakEnd].map(minutes);
  if(!date(p.effective)||!Number.isInteger(p.quota)||p.quota<1||p.quota>60||!['full','proportional'].includes(p.firstYear)||!p.days.length||p.days.some(x=>!Number.isInteger(x)||x<0||x>6)||!Number.isFinite(a+b+c+e)||b<=a||e<=c||c<a||e>b||!Number.isInteger(p.grace)||p.grace<0||p.grace>120||!Number.isInteger(p.notice)||p.notice<0||p.notice>30)fail('policy_invalid');
  for(const person of persons){const reserved=d.leaves.filter(l=>l.staff===person.id&&l.type==='annual'&&l.start.startsWith(String(year))&&['used','approved','pending'].includes(l.status)).reduce((n,l)=>n+l.days,0);if(quota(d,person,year,p)<reserved)fail('policy_reserved');}
  return p;
 }
 function policyForDate(d,id,at){
  const record=d.timeRecords[`${id}:${at}`];if(record?.policy8)return copy(record.policy8);
  const candidates=(d.staff118?.policies||[]).filter(x=>x.effective<=at).sort((a,b)=>a.effective.localeCompare(b.effective)||a.sequence-b.sequence);
  return copy(candidates.at(-1)?.policy||d.staff118?.policies[0]?.policy||d.policy);
 }
 function changePolicy(d,persons,p,at){
  validatePolicy(d,persons,p,Number(at.slice(0,4)));
  for(const [key,r]of Object.entries(d.timeRecords))if(!r.policy8)r.policy8=policyForDate(d,key.split(':')[0],key.slice(-10));
  d.staff118.policies.push({policy:copy(p),effective:p.effective,sequence:d.staff118.policies.length,recordedAt:at});d.policy=copy(p);
 }
 function approveTime(d,id,at,actor){
  const x=d.corrections.find(c=>c.id===id);if(!x||x.status!=='pending'||!x.times||!date(x.date)||!d.staff118?.compensation[x.staff])fail('correction_stale');
  const mins=s=>/^([01]\d|2[0-3]):[0-5]\d$/.test(s)?Number(s.slice(0,2))*60+Number(s.slice(3)):NaN;
  if(!Number.isFinite(mins(x.times.in)+mins(x.times.out))||mins(x.times.out)<=mins(x.times.in))fail('correction_invalid');
  const key=x.staff+':'+x.date,old=d.timeRecords[key]||{};
  if(x.before118&&(x.before118.in!==(old.in||null)||x.before118.out!==(old.out||null)))fail('correction_stale');
  const p=old.policy8||x.policy118||policyForDate(d,x.staff,x.date);
  d.timeRecords[key]={...copy(old),...copy(x.times),policy8:copy(p)};
  x.status='approved';x.decidedAt118=at;x.decidedBy118=actor;x.beforeApproved118=copy(old);
  return x;
 }
 return {ensure,compensation,schedule,rows,copySlip,saveSlip,issue,chooseActive,normalizeSlips,slip,active,quota,validatePolicy,policyForDate,changePolicy,approveTime,date,month,sum};
});
