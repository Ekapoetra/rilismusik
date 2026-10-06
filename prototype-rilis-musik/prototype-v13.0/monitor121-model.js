/* Financial observation only. Never mutates royalties, withdrawals, access or rewards. */
(function(root){
 'use strict';
 const DAY=86400000, fail=m=>{throw Error(m)}, object=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
 const sum=values=>{const n=values.reduce((n,v)=>{if(!Number.isSafeInteger(v))fail('Nominal sumber tidak valid.');return n+BigInt(v)},0n);if(n>BigInt(Number.MAX_SAFE_INTEGER)||n<BigInt(Number.MIN_SAFE_INTEGER))fail('Total nominal melampaui batas aman.');return Number(n)};
 const validAt=v=>typeof v==='string'&&Number.isFinite(Date.parse(v));
 const init=s=>s.monitor121??={schema:1,version:0,cash:[],history:[]};
 function validate(s){return object(s)&&s.schema===1&&Number.isSafeInteger(s.version)&&s.version>=0&&['cash','history'].every(k=>Array.isArray(s[k])&&s[k].every(object))&&s.cash.every(x=>typeof x.id==='string'&&Number.isSafeInteger(x.amount)&&x.amount>=0&&validAt(x.asof)&&typeof x.scope==='string'&&typeof x.note==='string');}
 function age(entries,at){
  const groups=new Map();for(const e of entries){const key=e.member+'|'+e.ref;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(e)}
  const buckets=[0,0,0,0,0];const anomalies=[];
  for(const [key,rows] of groups){const balance=sum(rows.map(x=>x.amount));if(balance<0){anomalies.push(key);buckets[4]=sum([buckets[4],balance]);continue}if(!balance)continue;
   const positive=rows.filter(x=>x.amount>0),dates=new Set(positive.map(x=>x.availableAt||(x.kind==='received'?x.at:null)));
   // A deduction without an exact lot cannot establish which of several dated lots remains.
   const known=dates.size===1&&validAt([...dates][0])&&Date.parse([...dates][0])<=at;
   const index=known?((at-Date.parse([...dates][0]))/DAY<=90?0:(at-Date.parse([...dates][0]))/DAY<=180?1:(at-Date.parse([...dates][0]))/DAY<=365?2:3):4;
   buckets[index]=sum([buckets[index],balance]);
  }
  return {buckets,anomalies};
 }
 function live(royalty,members,at){
  const known=new Set(members.map(m=>m.id));if(royalty.ledger.some(e=>!known.has(e.member)))fail('Ada pemilik dana yang belum terhubung. Periksa sumber sebelum menjumlahkan.');
  const accounts=royalty.withdraw108?.accounts||[],owned=new Set(),units=[];
  for(const a of accounts){if(!Array.isArray(a.members)||a.members.some(id=>owned.has(id)))fail('Hubungan akun penarikan perlu diperiksa; dana tidak dijumlahkan dua kali.');a.members.forEach(id=>owned.add(id));units.push(a)}
  for(const m of members)if(!owned.has(m.id))units.push({id:m.id,name:m.name,members:[m.id],master:false});
  return units.map(a=>{
   const m=members.find(m=>m.id===a.id),entries=royalty.ledger.filter(x=>a.members.includes(x.member)),available=sum(entries.filter(x=>x.bucket==='available').map(x=>x.amount)),pending=sum(entries.filter(x=>x.bucket==='pending').map(x=>x.amount));
   const requests=(royalty.withdraw108?.requests||[]).filter(w=>w.account===a.id),open=requests.filter(w=>w.status!=='paid'),processing=sum(open.map(w=>w.amount)),paid=sum(entries.filter(x=>x.bucket==='paid').map(x=>x.amount));
   const aged=age(entries.filter(x=>x.bucket==='available'),at),sources=royalty.batches.filter(b=>b.posted.some(id=>a.members.includes(id))).flatMap(b=>b.rows.filter(x=>a.members.includes(x.member)&&x.matched).map(x=>({...x,batch:b.id})));
   const periods=[...new Set(sources.map(x=>x.period))].sort(),latest=periods.at(-1),income=latest?sum(sources.filter(x=>x.period===latest).map(x=>x.amount)):null;
   const payment=entries.filter(x=>x.bucket==='paid'&&x.amount>0&&validAt(x.at)).map(x=>x.at).sort().at(-1)||null;
   return {id:a.id,name:m?.name||a.name,members:a.members,master:!!a.master,source:'ledger',available,pending,processing,paid,unpaid:sum([available,processing]),held:0,age:aged.buckets,anomalies:aged.anomalies,lastPayment:payment,paymentHistoryComplete:!!a.paymentHistoryComplete,income,period:latest||null,lastActivity:m?.lastWork121||null,bank:m?.bank?.approved||null,hold:a.hold||'',open:open.length>0,requests,entries,periods,sources};
  });
 }
 function legacy(labels,members){
  // Historical snapshot stays a distinct source until an opening-balance reconciliation is approved.
  return labels.filter(l=>!l.master).map(l=>{
   const m=members.find(m=>m.source9===l.id),balance=sum([l.credit,l.adjustment||0,-l.paid]),available=sum([balance,-(l.processing||0),-(l.held||0)]);
   const master=labels.find(a=>a.master&&a.children?.some(c=>c.id===l.id));
   return {id:m?.id||l.id,name:m?.name||l.name,members:[m?.id||l.id],master:false,source:'legacy',available,pending:null,processing:l.processing||0,paid:l.paid,unpaid:balance,held:l.held||0,age:[0,0,0,0,available],anomalies:available<0?[l.id]:[],lastPayment:l.lastPayment||null,paymentHistoryComplete:false,income:l.periodIncome,period:l.report,lastActivity:l.last||null,bank:m?.bank?.approved||null,hold:l.held?'Dana ditahan pada data awal.':'',open:!!l.processing,requests:[],entries:[],periods:[l.report],sources:[],manager:master?.name||null};
  });
 }
 function totals(rows){return {unpaid:sum(rows.map(x=>x.unpaid)),available:sum(rows.map(x=>x.available)),processing:sum(rows.map(x=>x.processing)),old:sum(rows.map(x=>x.age[3])),unknown:sum(rows.map(x=>x.age[4])),held:sum(rows.map(x=>x.held)),pending:rows.some(x=>x.pending===null)?null:sum(rows.map(x=>x.pending))};}
 function catalogue(rows,completePeriods=[]){
  return rows.map(r=>{
   const periods=[...new Set(r.sources.map(x=>x.period))].sort(),current=periods.at(-1),previous=current?new Date(current+'-01T00:00:00Z'):null;if(previous)previous.setUTCMonth(previous.getUTCMonth()-1);const prev=previous?.toISOString().slice(0,7);
   const comparable=!!current&&completePeriods.includes(current)&&completePeriods.includes(prev),a=current?sum(r.sources.filter(x=>x.period===current).map(x=>x.amount)):null,b=comparable?sum(r.sources.filter(x=>x.period===prev).map(x=>x.amount)):null;
   return {...r,current,previous:prev,currentAmount:a,previousAmount:b,change:comparable&&b>0?(a-b)/b*100:null,comparable};
  });
 }
 function cashSave(s,actor,p,at){
  if(actor?.role!=='super'||actor.active===false)fail('Hanya Super Admin aktif yang dapat mencatat posisi kas.');const model=init(s);if(model.version!==p.version)fail('Data berubah. Buka kembali ringkasan terbaru.');
  if(!Number.isSafeInteger(p.amount)||p.amount<0||!validAt(p.asof)||Date.parse(p.asof)>at||!p.scope?.trim()||!p.note?.trim()||!p.checked)fail('Lengkapi nominal, waktu acuan, cakupan dan sumber kas yang sudah diperiksa.');
  const id='CASH-'+(model.cash.length+1);model.cash.push({id,amount:p.amount,asof:p.asof,scope:p.scope.trim(),note:p.note.trim(),recordedAt:new Date(at).toISOString(),actor:actor.id});model.history.push({action:'cash-observation',id,at:new Date(at).toISOString(),actor:actor.id});model.version++;return id;
 }
 const api={sum,age,live,legacy,totals,catalogue,init,validate,cashSave};root.Monitor121=api;if(typeof module!=='undefined')module.exports=api;
})(typeof window==='undefined'?globalThis:window);
