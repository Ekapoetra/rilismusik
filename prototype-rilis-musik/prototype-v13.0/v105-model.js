/* M02: versioned local release workflow. All amounts remain prototype credits. */
(function(root){
 'use strict';
 const copy=x=>JSON.parse(JSON.stringify(x)),cost={Standard:1,Express:2,MAX:3};
 function rule(s,r){return typeof Credit11==='undefined'?{cost,temporaryHours:48,priority:'expiry'}:Credit11.forRelease(s||root.ten||{now:Date.now()},r)}
 function rate(r,s){return rule(s,r).cost[r.service]}
 const check=(ok,message)=>{if(!ok)throw Error(message)};
 const member=(s,r)=>RM10.getMember(s,r.member);
 const log=(s,r,kind,note='')=>{const e={id:++s.serial,kind,target:r.id,note,actor:s.role,actorId102:s.actor105||s.role,at:s.now};s.events.unshift(e);r.history.push(e);};
 const notify=(s,r,key)=>s.notifications.unshift({id:++s.serial,member:r.member,key,ref:r.id,at:s.now});
 const owner=(s,r)=>check(s.role==='label'&&s.member===r.member,'permission');
 const staff=s=>check(['admin','super'].includes(s.role),'permission');
 const track=(s,title='')=>({id:'TR-'+(++s.serial),title,kind:'vocal',explicit:false,language:'',lyricLanguage:'',lyrics:'',composer:[],lyricist:[],arranger:[],producer:[],featured:[],isrc:'',preview:0,audio:null,live:false,settlement:'none',allocation:[]});
 function create(s){check(s.role==='label','permission');const m=RM10.getMember(s);const r={id:'RM-'+(++s.serial),flow105:true,member:m.id,title:'',artist:'',type:'single',genre:'',subgenre:'',year:new Date(s.now).getUTCFullYear(),copyright:'',master:'',primary:[],featured:[],cover:null,songs:[track(s)],tracks:1,service:'Standard',date:'',version:1,status:'draft',creditState:'none',allocation:[],history:[],declaration:false,created:s.now,updated:s.now,round:0};s.releases.unshift(r);log(s,r,'draft');return r;}
 function editable(s,r){owner(s,r);check(['draft','revision'].includes(r.status),'state');}
 const url=s=>{try{return ['http:','https:'].includes(new URL(s).protocol)}catch{return false}};
 function issues(r){
  const out=[],add=(field,text,step,song)=>out.push({field,text,step,song});
  for(const [field,label] of [['title','Judul rilisan'],['genre','Genre'],['subgenre','Subgenre'],['copyright','Pemilik karya'],['master','Pemilik master']])if(!String(r[field]||'').trim())add(field,label+' belum diisi.',1);
  if(!Number.isInteger(+r.year)||+r.year<1900||+r.year>2100)add('year','Tahun produksi belum sesuai.',1);
  const n=r.songs.length;if(!(r.type==='single'?n===1:r.type==='ep'?n>=2&&n<=6:n>=7&&n<=12))add('type','Jumlah lagu belum sesuai dengan jenis rilisan.',1);
  if(!r.primary.length)add('primary','Tambahkan artis utama.',2);
  const all=[...r.primary,...r.featured,...r.songs.flatMap(t=>t.featured||[])];
  for(const a of all)if(!a.name?.trim()||!a.social?.some(url))add('artist','Lengkapi nama dan tautan sosial '+(a.name||'artis')+'.',2);
  if(r.primary.some(a=>r.featured.some(b=>b.id===a.id)))add('artist','Artis utama dan tamu harus memiliki peran yang berbeda.',2);
  const used=new Set();for(const t of r.songs){
   for(const [key,label] of [['title','Judul lagu'],['language','Bahasa judul']])if(!t[key]?.trim())add(key,label+' belum diisi.',3,t.id);
   if(!t.composer?.length)add('composer','Nama komposer belum diisi.',3,t.id);
   if(t.kind==='vocal'){if(!t.lyricist?.length)add('lyricist','Penulis lirik belum diisi.',3,t.id);if(!t.lyrics?.trim())add('lyrics','Lirik belum diisi.',3,t.id);if(!t.lyricLanguage?.trim())add('lyricLanguage','Bahasa lirik belum diisi.',3,t.id);}
   if(t.isrc){if(used.has(t.isrc.toUpperCase()))add('isrc','ISRC yang sama digunakan pada dua lagu.',3,t.id);used.add(t.isrc.toUpperCase());}
   if(!t.audio?.valid)add('audio','Audio '+(t.title||'lagu')+' belum tersedia.',4,t.id);
   if(t.audio&&(+t.preview<0||+t.preview>=t.audio.duration))add('preview','Posisi cuplikan berada di luar durasi audio.',4,t.id);
  }
  if(!r.cover?.valid)add('cover','Cover 3000 × 3000 belum tersedia.',4);
  if(!r.declaration)add('declaration','Setujui pernyataan hak distribusi.',4);
  return out;
 }
 function snapshot(r){const fields=['title','type','genre','subgenre','year','copyright','master','primary','featured','cover','songs','service','date','declaration'];return copy(Object.fromEntries(fields.map(k=>[k,r[k]])));}
 const ledgerSongs=r=>r.status==='revision'&&r.submitted105?r.submitted105.songs:r.songs;
 function totals(r){return ledgerSongs(r).reduce((a,t)=>{a[t.settlement]=(a[t.settlement]||0)+t.allocation.reduce((n,x)=>n+x.amount,0);return a},{reserved:0,consumed:0,returned:0});}
 function sync(r){r.tracks=r.songs.length;r.artist=r.primary.map(a=>a.name).join(', ');r.allocation=ledgerSongs(r).filter(t=>t.settlement==='reserved').flatMap(t=>copy(t.allocation));const b=totals(r);r.creditState=b.reserved?(b.consumed?'partial':'reserved'):b.consumed?'consumed':b.returned?'returned':'none';}
 function delta(r,s){return r.songs.length*rate(r,s)-(r.status==='revision'?totals(r).reserved:0);}
 function sources(s,m,r){return m.lots.filter(l=>l.available>0&&(!l.expires||l.expires>s.now)&&(l.type!=='daily'||RM10.daily(s,m))).sort((a,b)=>typeof Credit11==='undefined'?(a.expires||Infinity)-(b.expires||Infinity):Credit11.compare(rule(s,r),a,b));}
 function reserve(s,r,amount){const m=member(s,r),lots=sources(s,m,r);check(lots.reduce((n,l)=>n+l.available,0)>=amount,'credits');let left=amount,out=[];for(const l of lots){const take=Math.min(l.available,left);if(take){l.available-=take;left-=take;out.push({lot:l.id,type:l.type,amount:take,expires:l.expires,remaining:l.expires?l.expires-s.now:null});}if(!left)break;}return out;}
 function returnParts(s,r,parts,reason){const m=member(s,r);r.returns105??=[];for(const a of parts){if(a.type==='paid'||a.expires>s.now){const lot=m.lots.find(l=>l.id===a.lot);if(lot){lot.available+=a.amount;r.returns105.push({amount:a.amount,type:a.type,expires:lot.expires,reason,at:s.now});continue;}}
   if(a.type==='daily'||a.type==='replacement'){const expires=s.now+(a.type==='daily'?rule(s,r).temporaryHours*RM10.H:Math.min(rule(s,r).temporaryHours*RM10.H,a.remaining||RM10.H));m.lots.push({id:'return-'+(++s.serial),type:'replacement',available:a.amount,expires,source:r.id,reason});r.returns105.push({amount:a.amount,type:'replacement',expires,reason,at:s.now});}
  }notify(s,r,'credit_return105');}
 function releaseReserved(s,r,reason,ids){const ledger=ledgerSongs(r);if(ledger!==r.songs){r.cancelledDraft105=snapshot(r);r.songs=copy(ledger);r.status='submitted';}for(const t of r.songs)if(t.settlement==='reserved'&&(!ids||ids.includes(t.id))){returnParts(s,r,t.allocation,reason);t.settlement='returned';t.failed=true;}sync(r);}
 function version(r,p){check(+p.version===r.version,'stale');}
 function apply(s,action,p={}){
  if(s.failNext){s.failNext=false;throw Error('save_failed')}
  if(action==='create')return create(s).id;
  const r=s.releases.find(x=>x.id===p.id&&x.flow105);check(r,'state');
  if(action==='save'){editable(s,r);version(r,p);const fields=['title','type','genre','subgenre','year','copyright','master','primary','featured','cover','songs','service','date','declaration'];for(const k of fields)if(p.patch[k]!==undefined)r[k]=copy(p.patch[k]);r.version++;r.updated=s.now;sync(r);return r.id;}
  if(action==='submit'){
   editable(s,r);version(r,p);check(!issues(r).length,'release_incomplete105');const m=member(s,r);check(m.active,'inactive');check(m.contract,'prerequisites');check(!m.blocked105,'permission');const first=RM10.earliest(s,r.service);check(first&&r.date>=first,'date');
   if(r.status==='draft'){const needed=r.songs.length*rate(r,s);check(Number.isFinite(needed),'invalid');const parts=reserve(s,r,needed);r.policy11=copy(rule(s,r));r.policyVersion11=typeof Credit11==='undefined'?1:Credit11.active(s).id;let index=0;for(const t of r.songs){let n=rate(r,s);t.allocation=[];while(n){const part=parts[index],take=Math.min(part.amount,n);t.allocation.push({...part,amount:take});part.amount-=take;n-=take;if(!part.amount)index++;}t.settlement='reserved';t.live=false;t.failed=false;}r.originalDate=r.date;r.priceSnapshot={costPerSong:rate(r,s),service:r.service,at:s.now};}
   else {const extra=delta(r,s),parts=copy(r.submitted105.songs.flatMap(t=>t.allocation));if(extra>0)parts.push(...reserve(s,r,extra));let index=0;for(const t of r.songs){let n=rate(r,s);t.allocation=[];while(n){const part=parts[index],take=Math.min(part.amount,n);t.allocation.push({...part,amount:take});part.amount-=take;n-=take;if(!part.amount)index++;}t.settlement='reserved';t.live=false;t.failed=false;}const surplus=parts.filter(p=>p.amount>0);if(surplus.length)returnParts(s,r,surplus,'revision_adjustment');r.priceSnapshot={costPerSong:rate(r,s),service:r.service,at:s.now};}
   r.previous105=r.submitted105||null;r.submitted105=snapshot(r);r.submittedVersion=++r.version;r.status='submitted';r.sent=s.now;r.round++;r.deadline=null;r.handler102=null;sync(r);log(s,r,'submitted');notify(s,r,'submitted');return r.id;
  }
  if(action==='reopen'){owner(s,r);check(r.status==='closed','state');const fresh=create(s),id=fresh.id;Object.assign(fresh,snapshot(r),{id,songs:r.songs.map(t=>({...copy(t),id:track(s).id,allocation:[],settlement:'none',live:false,failed:false})),declaration:false,previousRequest:r.id});sync(fresh);return id;}
  if(action==='cancel'){owner(s,r);check(['draft','submitted','revision'].includes(r.status),'state');releaseReserved(s,r,'cancel');r.status='closed';r.reason='cancelled';log(s,r,'cancelled');return true;}
  staff(s);version(r,p);
  if(action==='start'){check(r.status==='submitted','stale');r.status='review';r.handler102=s.actor105;}
  else if(action==='revision'){check(r.status==='review','state');check(p.notes?.length&&p.notes.every(n=>n.text?.trim()),'reason');r.reviewNotes=copy(p.notes);r.note=p.notes.map(n=>n.text).join(' · ');r.status='revision';r.revisionStarted=s.now;r.deadline=s.now+24*RM10.H;r.reminders=[];notify(s,r,'revision');}
  else if(action==='approve'){check(r.status==='review'&&p.checked,'check');r.status='approved';}
  else if(action==='deliver'){check(r.status==='approved'&&p.checked,'check');r.status='delivered';r.delivered=s.now;r.confirmedDate=p.date||r.date;r.deliveryNote=p.note||'';}
  else if(action==='codes'){check(['delivered','followup','partial'].includes(r.status),'state');check(p.upc?.trim(),'invalid');r.upc=p.upc.trim();for(const t of r.songs)if(p.codes?.[t.id])t.isrc=p.codes[t.id].trim();}
  else if(action==='live'){
   check(['delivered','followup','partial'].includes(r.status)&&p.checked,'check');check(r.upc,'evidence');const chosen=r.songs.filter(t=>p.ids?.includes(t.id)&&t.settlement==='reserved');check(chosen.length,'state');check(chosen.every(t=>t.isrc&&url(p.links?.[t.id])),'evidence');
   for(const t of chosen){t.live=true;t.settlement='consumed';t.link=p.links[t.id];t.liveAt=s.now;}r.status=r.songs.every(t=>t.live)?'live':'partial';r.checkedAt=s.now;if(r.status==='live')r.live=s.now;sync(r);notify(s,r,r.status==='live'?'live':'partial105');
  }
  else if(action==='not_found'){check(['delivered','followup','partial'].includes(r.status),'state');check(p.note?.trim(),'reason');r.followup=p.note;r.status=r.songs.some(t=>t.live)?'partial':'followup';r.checkedAt=s.now;notify(s,r,'not_found');}
  else if(action==='followup'){check(['delivered','followup','partial'].includes(r.status),'state');check(p.note?.trim(),'reason');r.followup=p.note;r.followupAt=s.now;}
  else if(action==='date_error'){check(['delivered','followup','partial'].includes(r.status),'state');check(p.note?.trim(),'reason');r.incident='date_error';r.incidentNote=p.note;r.status=r.songs.some(t=>t.live)?'partial':'followup';if(p.date)r.confirmedDate=p.date;notify(s,r,'date_error');}
  else if(action==='reject'){check(['review','submitted'].includes(r.status)&&p.note?.trim(),'reason');releaseReserved(s,r,'rejected');r.status='closed';r.reason=p.note;notify(s,r,'rejected');}
  else if(action==='close_failed'){check(s.role==='super','permission');check(['partial','followup','delivered'].includes(r.status)&&p.checked&&p.note?.trim(),'check');const ids=r.songs.filter(t=>!t.live&&t.settlement==='reserved').map(t=>t.id);check(ids.length,'state');releaseReserved(s,r,'confirmed_failure',ids);r.status=r.songs.some(t=>t.live)?'partial_closed':'closed';r.reason=p.note;}
  else if(action==='undo_live'){check(s.role==='super'&&p.note?.trim(),'permission');check(['live','partial','partial_closed'].includes(r.status),'state');const chosen=r.songs.filter(t=>p.ids?.includes(t.id)&&t.settlement==='consumed');check(chosen.length,'state');for(const t of chosen){t.live=false;t.settlement='reserved';}r.status='followup';sync(r);notify(s,r,'date_error');}
  else throw Error('invalid');
  r.version++;r.updated=s.now;log(s,r,action,p.note||'');return true;
 }
 function tick(s){for(const r of s.releases.filter(x=>x.flow105&&x.status==='revision')){if(r.deadline<=s.now){releaseReserved(s,r,'timeout');r.status='closed';r.reason='timeout';r.version++;log(s,r,'timeout');notify(s,r,'timeout');}else for(const hr of [4,12,22])if(s.now>=r.revisionStarted+hr*RM10.H&&!(r.reminders||[]).includes(hr)){(r.reminders??=[]).push(hr);notify(s,r,'reminder');}}}
 const api={apply,issues,snapshot,totals,sync,track,tick,cost,delta,rate,rule};root.Flow105=api;
 if(typeof module!=='undefined')module.exports=api;
})(typeof window==='undefined'?globalThis:window);
