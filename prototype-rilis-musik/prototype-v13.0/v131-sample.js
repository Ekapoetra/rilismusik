/* V13.1 — skenario dari cuplikan produksi (window.SAMPLE131, lihat
   build-sample.cjs). Diterapkan sekali pada dokumen journey (ditandai
   ten.sample131). Data didorong lewat aksi model prototype sendiri (RM10.act,
   Royalty107.act, Tickets112.act) agar invarian tiap layer terjaga; entitas
   yang ditolak model dicatat di laporan konsol, tidak menghentikan boot.
   Tidak ada permintaan jaringan; seluruhnya tetap simulasi lokal. */
(function(){
 'use strict';
 const S=window.SAMPLE131;
 if(!S||typeof ten==='undefined'||typeof RM10==='undefined')return;
 try{if(typeof ui107!=='undefined'&&S.royalty.imports.length)ui107.period=[...S.royalty.imports.map(i=>i.period)].sort().at(-1);}catch(e){}
 const applied=()=>ten.sample131&&ten.sample131.version===S.version&&S.labels.every(l=>ten.members.some(m=>m.id===l.id));
 if(applied())return;

 const H=RM10.H,DAY=RM10.DAY,realNow=ten.now;
 const stamp=t=>new Date(t).toISOString();
 const at=d=>{const t=Date.parse((d||'2026-09-01')+'T10:00:00+07:00');return Math.min(Number.isFinite(t)?t:realNow,realNow);};
 const report={members:0,v9:0,releases:0,imports:0,withdrawals:0,tickets:0,errors:[]};
 const fail=(scope,id,e)=>report.errors.push(scope+' '+id+': '+(e&&e.message||e));
 const withNow=(t,fn)=>{const prev=ten.now;ten.now=Math.min(t,realNow);try{return fn()}finally{ten.now=prev}};
 const asRole=(role,member,fn)=>{const prev={role:ten.role,member:ten.member,user:state.user};ten.role=role;if(member)ten.member=member;if(role!=='label')state.user=role==='super'?'jeck':'adovi';try{return fn()}finally{ten.role=prev.role;ten.member=prev.member;state.user=prev.user}};
 const byId=new Map(S.labels.map(l=>[l.id,l]));
 const money=n=>Math.max(0,Math.round(Number(n)||0));

 /* 1. Member + entri Manajemen Label (data.v9) */
 const isActive=l=>l.account==='active'&&(l.kyc==='verified'||(!l.kyc&&l.contract&&l.bank?.status==='verified'));
 for(const l of S.labels){
  try{
   if(ten.members.some(m=>m.id===l.id))continue;
   const identity={person:l.pic||l.name,address:l.address||'',postal:'',country:l.country||'Indonesia',document:false,city:l.city||''};
   const m={id:l.id,name:l.name,plan:l.plan,period:'year',email:l.email||(l.id+'@example.test'),emailConfirmed:!!l.email,paid:l.account!=='legacy_unclaimed',invoice:null,active:false,activatedAt:null,version:1,contract:false,identity,application:null,bank:{approved:null,pending:null,version:0},social:'',lots:[{id:'paid-'+l.id,type:'paid',available:500,expires:null}],joined:l.joined,welcome:true,
    sample131:{source:l.source,account:l.account,kyc:l.kyc,kycReason:l.kycReason,subscription:l.subscription,tier:l.tier,legacy:l.account==='legacy_unclaimed',royaltyPercent:l.royaltyPercent,multi:l.multi,whatsapp:l.whatsapp,logo:l.logo,balance:l.balance,lastWithdrawnPeriod:l.lastWithdrawnPeriod}};
   if(isActive(l)){m.active=true;m.activatedAt=stamp(at(l.kycReviewed||l.contractAt||l.joined));m.identity.document=true;m.contract=true;m.contractVersion=1;}
   else if(l.kyc==='pending_review'){m.identity.document=true;m.contract=!!l.contract;m.contractVersion=1;m.application={status:'pending',version:1,submitted:at(l.kycSubmitted),snapshot:{name:l.name,...identity,document:true},note:''};}
   else if(l.kyc==='rejected'){m.identity.document=true;m.contract=!!l.contract;m.contractVersion=1;m.application={status:'correction',version:1,submitted:at(l.kycSubmitted),snapshot:{name:l.name,...identity,document:true},note:l.kycReason||'Dokumen identitas perlu diperbaiki.'};}
   if(m.active&&m.plan!=='Flex')m.subscriptionEnd=l.subscriptionEnd?l.subscriptionEnd+'T23:59:59+07:00':stamp(realNow+365*DAY);
   if(l.bank){const b={bank:l.bank.bank,number:l.bank.number,holder:l.bank.holder,version:1};m.bank.version=1;if(l.bank.status==='verified')m.bank.approved={...b,status:'approved'};else m.bank.pending={...b,status:'pending',note:''};}
   ten.members.push(m);report.members++;
  }catch(e){fail('member',l.id,e)}
 }

 /* 2. Rilisan — melalui alur v10 (draft→submit→start→approve→deliver→codes→live) */
 const relId=new Map(),relByLabel=new Map();
 const ISRC=(r,i)=>r.tracks[i]?.isrc||('ID'+r.label.replace(/[^a-z0-9]/g,'').slice(0,3).toUpperCase().padEnd(3,'X')+'26'+String(10000+Number(r.id.slice(2))*20+i).slice(-5));
 const UPC=r=>r.upc||('899'+String(100000000+Number(r.id.slice(2))).slice(-9)+'0');
 const releasesByLabel=new Map();
 for(const r of S.releases){if(!releasesByLabel.has(r.label))releasesByLabel.set(r.label,[]);releasesByLabel.get(r.label).push(r);}
 for(const [label,list] of releasesByLabel){
  const m=RM10.getMember(ten,label);if(!m)continue;
  const wasActive=m.active;m.active=true;
  for(const r of list){
   try{
    const artist=r.artists.join(', ')||'-',tracks=Math.max(1,Math.min(12,r.tracks.length));
    let id;
    withNow(at(r.created),()=>asRole('label',label,()=>{id=RM10.act(ten,'draft',{title:r.title,artist,tracks,service:'Standard',date:RM10.earliest(ten,'Standard')});if(r.status!=='draft'&&r.status!=='awaiting_payment')RM10.act(ten,'submit',{id});}));
    const rel=RM10.getRelease(ten,id);
    const staff=(when,fn)=>withNow(at(when),()=>asRole('super',null,fn));
    const st=r.status;
    if(['under_review','need_revision','approved','delivered','live','taken_down','rejected'].includes(st))staff(r.reviewStarted||r.submitted||r.created,()=>RM10.act(ten,'start',{id}));
    if(st==='need_revision')asRole('super',null,()=>RM10.act(ten,'revision',{id,note:r.note||'Periksa kembali metadata dan materi rilisan.',hours:24}));
    if(st==='rejected')staff(r.reviewStarted||r.created,()=>RM10.act(ten,'reject',{id,note:r.note||'Pengajuan ditolak setelah pemeriksaan.'}));
    if(['approved','delivered','live','taken_down'].includes(st))staff(r.reviewStarted||r.created,()=>RM10.act(ten,'approve',{id}));
    if(['delivered','live','taken_down'].includes(st)){staff(r.delivered||r.reviewStarted||r.created,()=>{RM10.act(ten,'deliver',{id,checked:true});RM10.act(ten,'codes',{id,upc:UPC(r),isrc:Array.from({length:tracks},(_,i)=>ISRC(r,i)).join(',')});});}
    if(['live','taken_down'].includes(st))staff(r.date&&r.date<stamp(realNow).slice(0,10)?r.date:r.delivered||r.created,()=>RM10.act(ten,'live',{id,link:'https://open.spotify.com/album/'+r.id.toLowerCase(),checked:true}));
    if(st==='taken_down'){rel.status='taken_down';rel.takenDownAt=at(r.created);}
    if(r.date)rel.date=r.date;
    if(r.created)rel.createdAt=stamp(at(r.created));
    rel.history=[...(rel.history||[]),...(r.history||[]).map(h=>({at:at(h.at),actor:'import',action:h.status,note:h.by||''}))];
    Object.assign(rel,{genre:r.genre||rel.genre,upc:rel.upc||r.upc||null,sample131:{source:r.source,cover:r.cover,type:r.type,tracks:r.tracks,artists:r.artists,featured:r.featured,language:r.language,subgenre:r.subgenre,copyright:r.copyright,pline:r.pline,explicit:r.explicit,addons:r.addons,status:r.status}});
    relId.set(r.id,id);if(!relByLabel.has(label))relByLabel.set(label,[]);relByLabel.get(label).push({id,title:r.title,status:r.status});report.releases++;
   }catch(e){fail('release',r.id+' '+r.title,e)}
  }
  m.active=wasActive;
  const lot=m.lots.find(x=>x.id==='paid-'+label);if(lot)lot.available=Math.min(lot.available,m.active?4:0);
 }

 /* 3. Royalti — import → publish → receive (Royalty107), + batch saldo awal agar
       saldo tersedia & riwayat penarikan nyata konsisten dengan buku kas model. */
 const royalty=typeof model107==='function'?model107():null;
 const sup={role:'super',id:'jeck',member:null};
 const sumBy=(rows,m)=>rows.filter(r=>r.member===m).reduce((n,r)=>n+r.amount,0);
 if(royalty&&typeof Royalty107!=='undefined'){
  const imports=S.royalty.imports.slice().sort((a,b)=>a.period.localeCompare(b.period));
  const received=new Map();
  for(const im of imports){
   try{
    const rows=[];let n=0;
    const sums=S.royalty.summary.filter(x=>x.import===im.id);
    const plats=(label,period)=>{const pl=S.royalty.byPlatform.filter(x=>x.label===label&&x.period===period&&x.idr>0);const tot=pl.reduce((a,x)=>a+x.idr,0)||1;return pl.map(x=>({p:x.platform||'Lainnya',w:x.idr/tot}));};
    for(const sm of sums){
      if(!RM10.getMember(ten,sm.label))continue;
      const dist=plats(sm.label,sm.period),top=S.royalty.byTrack.filter(t=>t.label===sm.label&&t.period===sm.period);
      let acc=0;
      for(const t of top){const amount=money(t.idr);if(!amount)continue;acc+=amount;
       let left=amount,qleft=money(t.qty);
       dist.forEach((d,j)=>{const last=j===dist.length-1,sub=last?Math.max(0,left):Math.floor(amount*d.w),qty=last?Math.max(0,qleft):Math.floor(money(t.qty)*d.w);left-=sub;qleft-=qty;if(sub<=0)return;rows.push({id:im.id+'-'+(++n),member:sm.label,track:t.isrc||('TRK-'+n),title:t.title||'Tanpa judul',release:t.title||'',artist:t.artist||'',isrc:t.isrc||('ADJ-'+sm.label+'-'+n),upc:'',period:im.period,sales:t.period,platform:d.p,country:'Semua wilayah',kind:'Streaming',quantity:Math.max(0,qty),amount:sub,matched:true});});
       if(!dist.length)rows.push({id:im.id+'-'+(++n),member:sm.label,track:t.isrc||('TRK-'+n),title:t.title||'Tanpa judul',release:t.title||'',artist:t.artist||'',isrc:t.isrc||('ADJ-'+sm.label+'-'+n),upc:'',period:im.period,sales:t.period,platform:'Gabungan platform',country:'Semua wilayah',kind:'Streaming',quantity:money(t.qty),amount,matched:true});
      }
      const rest=money(sm.idr)-acc;
      if(rest>0)rows.push({id:im.id+'-'+(++n),member:sm.label,track:'LAINNYA',title:'Baris lainnya ('+Math.max(0,sm.lines-top.length).toLocaleString('id-ID')+' baris)',release:'',artist:'',isrc:'LAINNYA-'+sm.label,upc:'',period:im.period,sales:sm.period,platform:'Gabungan platform',country:'Semua wilayah',kind:'Streaming',quantity:0,amount:rest,matched:true});
    }
    if(!rows.length)continue;
    const bid=withNow(at(im.uploaded||im.published||im.period+'-20'),()=>Royalty107.act(royalty,sup,'import',{name:im.file,rate:im.rate||17000,share:100,rows,fingerprint:'sample131-'+im.id}));
    const members=[...new Set(rows.map(r=>r.member))];
    if(['published','dana_received','completed','done'].includes(im.status)||im.published){withNow(at(im.published||im.uploaded),()=>Royalty107.act(royalty,sup,'publish',{id:bid,members}));}
    if(im.danaReceived){const amount=rows.reduce((a,r)=>a+r.amount,0);withNow(at(im.danaReceived),()=>Royalty107.act(royalty,sup,'receive',{id:bid,expectedVersion:royalty.version,reference:'BELIEVE-'+im.period.replace('-',''),date:im.danaReceived,amount,checked:true,members,note:'Dana laporan '+im.period+' diterima.'}));for(const mm of members)received.set(mm,(received.get(mm)||0)+sumBy(rows,mm));}
    const b=royalty.batches.find(x=>x.id===bid);if(b)b.sample131={source:im.source,period:im.period,status:im.status,lines:im.lines,matched:im.matched,unmatched:im.unmatched,totalEur:im.totalEur,totalIdr:im.totalIdr};
    report.imports++;
   }catch(e){fail('import',im.id,e)}
  }
  /* Saldo awal: total yang pernah ditarik + saldo tersedia saat ini, dikurangi
     yang sudah masuk lewat import di atas. */
  try{
   const rows=[];
   for(const l of S.labels){
    const m=RM10.getMember(ten,l.id);if(!m)continue;
    const paid=S.withdrawals.filter(w=>w.label===l.id&&w.status!=='rejected').reduce((a,w)=>a+money(w.amount),0);
    const need=paid+money(l.balance.requested)+money(l.balance.available)-(received.get(l.id)||0);
    if(need>0)rows.push({id:'legacy-'+l.id,member:l.id,track:'SALDO-AWAL',title:'Saldo awal migrasi',release:'',artist:'',isrc:'SALDO-'+l.id,upc:'',period:'2026-07',sales:l.lastWithdrawnPeriod||'2026-07',platform:'Gabungan platform',country:'Semua wilayah',kind:'Streaming',quantity:0,amount:need,matched:true});
   }
   if(rows.length){
    const t0=at('2026-07-15'),members=rows.map(r=>r.member);
    const bid=withNow(t0,()=>Royalty107.act(royalty,sup,'import',{name:'saldo-awal-migrasi.csv',rate:17000,share:100,rows,fingerprint:'sample131-legacy'}));
    withNow(t0,()=>Royalty107.act(royalty,sup,'publish',{id:bid,members}));
    withNow(t0+H,()=>Royalty107.act(royalty,sup,'receive',{id:bid,expectedVersion:royalty.version,reference:'MIGRASI-SALDO-AWAL',date:'2026-07-15',amount:rows.reduce((a,r)=>a+r.amount,0),checked:true,members,note:'Saldo awal dari sistem sebelumnya.'}));
   }
  }catch(e){fail('import','saldo-awal',e)}

  /* 4. Penarikan — dicatat langsung pada buku kas Withdraw108 (aturan pengajuan
        seperti tanggal 1–14 tidak berlaku untuk riwayat historis). */
  if(typeof Withdraw108!=='undefined'){
   const s=Withdraw108.init(royalty);
   const STATUS={requested:'requested',approved:'ready',processing:'processing',paid:'paid',rejected:'paid'};
   for(const w of S.withdrawals.slice().sort((a,b)=>String(a.requested).localeCompare(String(b.requested)))){
    try{
     const m=RM10.getMember(ten,w.label);if(!m||w.status==='rejected'||!money(w.amount))continue;
     if(!s.accounts.some(a=>a.id===m.id))s.accounts.push({id:m.id,name:m.name,members:[m.id],master:false});
     const portions=Withdraw108.portions(royalty,m.id).filter(p=>p.amount>0);
     let left=money(w.amount);const parts=[];
     for(const p of portions){if(!left)break;const take=Math.min(p.amount,left);parts.push({member:p.member,ref:p.ref,amount:take});left-=take;}
     if(!parts.length){fail('withdraw',w.id,'saldo buku kas tidak mencukupi');continue;}
     const amount=parts.reduce((a,p)=>a+p.amount,0),created=stamp(at(w.requested)),periods=Withdraw108.periods(royalty,parts);
     const id='WD-'+String(s.serial++).padStart(4,'0'),status=STATUS[w.status]||'requested';
     const rec={id,account:m.id,name:m.name,city:m.identity.city||'-',amount,parts,periods,memo:Withdraw108.memo(periods),bank:w.bank?{bank:w.bank.bank,number:w.bank.number,holder:w.bank.holder}:(m.bank.approved||{bank:'-',number:'-',holder:m.name}),status,cycle:created.slice(0,7),created,revision:1,events:[],handler:status==='paid'||status==='processing'?'jeck':null,uncertain:false,sample131:{source:w.id,lines:w.lines,reference:w.reference,note:w.note,proof:w.proof,adjustment:w.adjustment,amountSource:money(w.amount),periodFrom:w.periodFrom,periodTo:w.periodTo}};
     if(w.approved)rec.approved=stamp(at(w.approved));
     if(status==='paid'||status==='processing')rec.started=stamp(at(w.paid||w.approved||w.requested));
     if(status==='paid')rec.paid=stamp(at(w.paid||w.requested));
     s.requests.push(rec);
     for(const part of parts)royalty.ledger.push({...part,id:id+':reserve:'+part.member+':'+part.ref,amount:-part.amount,bucket:'available',kind:'processing',at:created});
     if(status==='paid')for(const part of parts)royalty.ledger.push({...part,id:id+':paid:1:'+part.member+':'+part.ref,bucket:'paid',kind:'withdrawn',at:rec.paid});
     report.withdrawals++;
    }catch(e){fail('withdraw',w.id,e)}
   }
   s.version++;
  }
 }

 /* 5. Tiket takedown — create → claim → send → results → finish (Tickets112) */
 if(typeof Tickets112!=='undefined'){
  for(const t of S.tickets){
   try{
    if(t.category!=='takedown'||!['done','in_progress','open','submitted_to_believe','waiting_label'].includes(t.status))continue;
    const own=(relByLabel.get(t.label)||[]).filter(x=>['delivered','live','taken_down'].includes(x.status));
    const rid=relId.get(t.release)||own.find(x=>x.title&&t.releaseTitle&&x.title.toLowerCase()===t.releaseTitle.toLowerCase())?.id||own.find(x=>x.status!=='taken_down')?.id||own[0]?.id;
    if(!rid)continue;
    const rel=RM10.getRelease(ten,rid),m=RM10.getMember(ten,t.label);if(!rel||!m)continue;
    if(rel.status==='taken_down'){rel.status='live';}
    const label={role:'label',id:m.id,member:m.id,active:true,scope:[m.id]},staff={role:'super',id:'jeck',member:null,scope:[]};
    const REASONS=['Revisi Metadata','Pindah Aggregator','Konflik Hak Cipta','Konflik Internal'];
    const tid=withNow(at(t.created),()=>Tickets112.act(ten,label,'create',{release:rid,category:'takedown',reason:REASONS.includes(t.reason)?t.reason:'Konflik Internal',checked:true,note:t.description||t.subject||'Permintaan penurunan rilisan.',source:Tickets112.catalogue(rel)}));
    const tk=()=>Tickets112.init(ten).tickets.find(x=>x.id===tid);
    const v=()=>tk().version;
    if(t.status!=='open'){withNow(at(t.created)+H,()=>Tickets112.act(ten,staff,'claim',{id:tid,version:v()}));}
    if(['submitted_to_believe','done'].includes(t.status)){withNow(at(t.believe||t.created)+2*H,()=>Tickets112.act(ten,staff,'send',{id:tid,version:v(),reference:'BLV-'+t.no,checked:true,note:'Permintaan diteruskan ke Believe.'}));}
    if(t.status==='done'){
     withNow(at(t.takedownDone||t.resolved||t.created),()=>Tickets112.act(ten,staff,'results',{id:tid,version:v(),checked:true,note:'Takedown dikonfirmasi oleh distributor.',results:tk().items.map(i=>({id:i.id,status:'confirmed',note:'Rilisan sudah diturunkan dari platform.',reference:'Believe '+t.no}))}));
     withNow(at(t.resolved||t.created)+H,()=>Tickets112.act(ten,staff,'finish',{id:tid,version:v(),checked:true,note:t.comments.filter(c=>!c.system).at(-1)?.body||'Permintaan selesai.'}));
    }
    const x=tk();
    for(const c of t.comments.filter(c=>!c.system&&c.body))x.messages.push({at:at(c.at),actor:c.role==='label'?m.id:'adovi',note:c.body,files:[]});
    x.sample131={no:t.no,source:true,subject:t.subject,reason:t.reason,comments:t.comments,status:t.status};
    report.tickets++;
   }catch(e){fail('ticket',t.no,e)}
  }
 }

 /* 6. Entri Manajemen Label (data.v9) untuk setiap label sampel */
 try{
  const v9l=data?.v9?.labels;
  if(Array.isArray(v9l)){
   S.labels.forEach((l,i)=>{
    const m=RM10.getMember(ten,l.id);if(!m)return;
    const id='S'+String(i+1).padStart(2,'0');
    if(!v9l.some(x=>x.id===id)){
     const paid=S.withdrawals.filter(w=>w.label===l.id&&w.status==='paid').reduce((a,w)=>a+money(w.amount),0);
     const rels=(releasesByLabel.get(l.id)||[]).map((r,n)=>({id:id+'-R'+n,date:r.date||r.created||'2026-01-01',valid:true}));
     const last=[...S.withdrawals.filter(w=>w.label===l.id).map(w=>w.requested),...(releasesByLabel.get(l.id)||[]).map(r=>r.created)].filter(Boolean).sort().at(-1)||null;
     const income=S.royalty.summary.filter(x=>x.label===l.id&&x.period==='2026-08').reduce((a,x)=>a+money(x.idr),0);
     v9l.push({id,name:l.name,plan:l.plan,joined:l.joined,last,paid,credit:paid+money(l.balance.available),adjustment:0,processing:money(l.balance.requested),held:0,periodIncome:income,report:'2026-08',expiry:l.subscriptionEnd||(m.active?'2027-03-01':'2026-01-01'),complete:!!(l.pic&&l.email),contact:!!(l.email||l.whatsapp),issue:false,restriction:l.blacklisted?'blocked':null,suspended:null,earned:false,review:l.kyc==='pending_review',master:!!l.multi,managedSince:null,children:[],releases:rels,lastPayment:S.withdrawals.filter(w=>w.label===l.id&&w.status==='paid').map(w=>w.paid).filter(Boolean).sort().at(-1)||null,emblemVersion:1,sample131:true});
     report.v9++;
    }
    m.source9=id;
   });
  }
 }catch(e){fail('v9','labels',e)}

 ten.sample131={version:S.version,appliedAt:stamp(realNow),exportedAt:S.exportedAt,report:{members:report.members,releases:report.releases,imports:report.imports,withdrawals:report.withdrawals,tickets:report.tickets,errors:report.errors.length}};
 if(typeof RM10.pending?.baseline==='function')try{RM10.pending.baseline(ten,data?.v9?.labels||[]);}catch(e){fail('pending','baseline',e)}
 try{RM10.tick(ten);}catch(e){fail('tick','final',e)}
 try{if(typeof save10==='function')save10();}catch(e){fail('save','journey',e)}
 try{if(typeof render==='function')render();}catch(e){fail('render','final',e)}
 window.SAMPLE131_REPORT=report;
 console.info('[sample131] diterapkan:',JSON.stringify(ten.sample131.report),report.errors.length?'\n'+report.errors.join('\n'):'');
})();
