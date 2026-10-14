const {exportSample,clean}=require('./sample');

const fx={
  labels:[
    {id:'A',label_name:'Awan',kyc_status:'verified',account_status:'active',user_id:'u1'},
    {id:'B',label_name:'Badai',kyc_status:'verified',account_status:'active',user_id:'u2'},
    {id:'C',label_name:'Cahaya',kyc_status:'pending',account_status:'active',user_id:'u3'},
    {id:'D',label_name:'Delta',kyc_status:'verified',account_status:'active',user_id:'u4'},
    {id:'L1',label_name:'Lama Satu',account_status:'legacy_unclaimed'},
    {id:'L2',label_name:'Lama Dua',account_status:'legacy_unclaimed'},
    {id:'L3',label_name:'Lama Tiga',account_status:'legacy_unclaimed'},
    {id:'L4',label_name:'Lama Empat',account_status:'legacy_unclaimed'}
  ],
  users:[{id:'u1',name:'Pemilik Awan',email:'a@x.id',responsible_whatsapp:'081299887766',password_hash:'zz',role:'label'},{id:'u3',email:'c@x.id',role:'label',active_label_id:'C'},{id:'s1',role:'super_admin',name:'Admin Asli',email:'s@x.id',reset_token:'t',google_subject:'1234567890'}],
  notifications:[{id:'n1',user_id:'u1',title:'Rilisan disetujui',body:'Halo a@x.id'},{id:'n2',user_id:'zz',title:'Lain',body:'bukan label terpilih'}],
  work_items:[{id:'w1',label_id:'A',label_name:'Awan'},{id:'w2',label_id:'ZZ',label_name:'Lain'}],
  activity_logs:[{id:'a1',user_id:'u1',action:'login'},{id:'a2',user_id:'zz',action:'login'}],
  staff_profiles:[{id:'sp1',user_id:'s1',employment_status:'active',salary:100},{id:'sp2',user_id:'other',employment_status:'active'}],
  releases:[...Array.from({length:9},(_,i)=>({id:'rA'+i,label_id:'A',release_title:'A'+i,status:'live'})),{id:'rA9',label_id:'A',status:'need_revision'},{id:'rB1',label_id:'B',status:'under_review'},{id:'rD1',label_id:'D',status:'live'}],
  tracks:[{id:'t1',release_id:'rA9',isrc:'ID123'}],
  withdraw_requests:[{id:'w1',label_id:'B',account_number:'1234567890',status:'requested'}],
  bank_accounts:[{id:'b1',label_id:'A',account_number:'99887766',account_holder_name:'Pemilik Awan',bank_name:'BCA',verified_status:'verified'}],
  kyc_documents:[{id:'k1',label_id:'C',nik:'3171234567890001',status:'pending'}],
  royalty_imports:[{id:'imp1'},{id:'imp2'}],
  royalty_lines:[{id:'l1',import_id:'imp1',label_id:'A',label_idr:100,period:'2026-08',isrc:'X',platform:'Spotify',quantity:3},{id:'l2',import_id:'imp1',label_id:'A',label_idr:50,period:'2026-08',isrc:'Y',platform:'TikTok',quantity:1}],
  support_tickets:[{id:'tk1',label_id:'D',status:'open',reason:'Konflik Internal',description:'hubungi 0812-3456-7890 atau a@x.id'}],
  ticket_comments:[{id:'c1',ticket_id:'tk1',body:'hi',user_name:'Pemilik Awan'}]
};
const match=(doc,q)=>Object.entries(q).every(([k,v])=>{
  if(k==='$or')return v.some(sub=>match(doc,sub));
  if(v&&typeof v==='object'&&'$in'in v)return v.$in.map(String).includes(String(doc[k]));
  if(v&&typeof v==='object'&&'$ne'in v)return doc[k]!==v.$ne&&doc[k]!==undefined;
  return doc[k]===v;});
const get=(d,p)=>p.startsWith('$')?d[p.slice(1)]:p;
function aggregate(rows,pipeline){
  let out=rows.slice();
  for(const st of pipeline){
    if(st.$match)out=out.filter(d=>match(d,st.$match));
    else if(st.$group){const m=new Map();for(const d of out){const key=typeof st.$group._id==='string'?get(d,st.$group._id):Object.fromEntries(Object.entries(st.$group._id).map(([k,v])=>[k,get(d,v)]));const ks=JSON.stringify(key);if(!m.has(ks))m.set(ks,{_id:key});const acc=m.get(ks);for(const [f,op] of Object.entries(st.$group)){if(f==='_id')continue;const [o,arg]=Object.entries(op)[0];if(o==='$sum')acc[f]=(acc[f]||0)+(arg===1?1:Number(get(d,arg))||0);if(o==='$first'&&acc[f]===undefined)acc[f]=get(d,arg);}}out=[...m.values()];}
    else if(st.$sort){const [[k,dir]]=Object.entries(st.$sort);out.sort((a,b)=>((a[k]??a._id?.[k.split('.').pop()])>(b[k]??b._id?.[k.split('.').pop()])?1:-1)*dir);}
    else if(st.$limit)out=out.slice(0,st.$limit);
  }
  return out;
}
const calls={find:0,findTimed:0,agg:0,aggTimed:0};
function fakeDb(data){
  return {databaseName:'fx',listCollections:()=>({toArray:async()=>Object.keys(data).map(name=>({name}))}),
    collection:n=>({
      find:(q={})=>{calls.find++;const rows=(data[n]||[]).filter(d=>match(d,q));let lim=rows.length;const c={sort:()=>c,limit:l=>{lim=l;return c;},maxTimeMS:ms=>{if(ms>0)calls.findTimed++;return c;},toArray:async()=>rows.slice(0,lim)};return c;},
      aggregate:(p,opt={})=>{calls.agg++;if(opt.maxTimeMS>0)calls.aggTimed++;return {toArray:async()=>aggregate(data[n]||[],p)};}
    })};
}
let fails=0;const check=(name,ok,extra='')=>{console.log((ok?'PASS':'FAIL')+' '+name+(extra?' — '+extra:''));if(!ok)fails++;};
(async()=>{
  const s=await exportSample(fakeDb(fx),{labels:6,releasesPerLabel:2,imports:1,legacyMax:2});
  const ids=s.meta.selection.map(x=>x.id);
  check('6 label terpilih',ids.length===6,ids.join(','));
  check('label dengan rilisan dalam alur kerja ikut (A,B)',ids.includes('A')&&ids.includes('B'));
  check('label tiket terbuka ikut (D)',ids.includes('D'));
  check('label KYC pending ikut (C)',ids.includes('C'));
  check('label lama dibatasi legacyMax',ids.filter(i=>i.startsWith('L')).length===2);
  check('alasan pemilihan tercatat',s.meta.selection.every(x=>x.reasons.length>0));
  const labA=s.data.labels.find(l=>l.id==='A');
  check('nama label dipseudonimkan & konsisten',s.meta.selection.find(x=>x.id==='A').name===labA.label_name&&labA.label_name!=='Awan');
  const relA=s.data.releases.filter(r=>r.label_id==='A');
  check('rilisan per label dibatasi & non-live diutamakan',relA.length===2&&relA.some(r=>r.status==='need_revision'));
  check('tracks mengikuti rilisan terpilih',s.data.tracks.length===1);
  check('password_hash dibuang',!s.data.users.some(u=>'password_hash'in u));
  check('reset_token dibuang',!s.data.users.some(u=>'reset_token'in u));
  check('account_number disamarkan',s.data.bank_accounts[0].account_number.startsWith('•')&&!s.data.bank_accounts[0].account_number.includes('7766'));
  check('nik disamarkan',s.data.kyc_documents[0].nik.startsWith('•')&&!s.data.kyc_documents[0].nik.includes('0001'));
  const blob=JSON.stringify(s);
  check('tidak ada email/WA/nama asli',!/@x\.id|0812-?3456|081299887766|Pemilik Awan|Admin Asli|1234567890/.test(blob));
  const u1=s.data.users.find(u=>u.id==='u1');
  check('email & WA dipseudonimkan',u1.email.endsWith('@contoh.test')&&/^0812-0000-\d{4}$/.test(u1.responsible_whatsapp));
  check('nama pemilik → pemegang rekening konsisten',s.data.bank_accounts[0].account_holder_name===u1.name&&s.data.ticket_comments[0].user_name===u1.name);
  const s1=s.data.users.find(u=>u.id==='s1');
  check('akun staf hanya id+peran+nama',s1&&Object.keys(s1).sort().join()==='id,name,role'&&s1.name!=='Admin Asli');
  check('notifikasi dibatasi ke pengguna label terpilih',s.data.notifications.length===1&&s.data.notifications[0].id==='n1');
  check('work_items dibatasi ke label terpilih',s.data.work_items.map(w=>w.id).join()==='w1');
  check('activity_logs dibatasi',s.data.activity_logs.map(a=>a.id).join()==='a1');
  check('staff_profiles ringkas & dibatasi',s.data.staff_profiles.length===1&&!('salary'in s.data.staff_profiles[0]));
  check('alasan takedown baku dipertahankan',s.data.support_tickets[0].reason==='Konflik Internal');
  check('teks bebas tiket diganti',!/0812|@/.test(s.data.support_tickets[0].description));
  check('maxTimeMS pada semua find/aggregate',calls.find===calls.findTimed&&calls.agg===calls.aggTimed&&calls.find>0,JSON.stringify(calls));
  check('import dibatasi',s.data.royalty_imports.length===1);
  const sum=s.data.royalty_summary.find(r=>r.label_id==='A');
  check('royalty_summary agregat per label×periode',sum&&sum.label_idr===150&&sum.lines===2,JSON.stringify(sum));
  check('royalty_by_platform ada',s.data.royalty_by_platform.length===2);
  check('royalty_by_track ada judul',s.data.royalty_by_track.length===2&&'isrc'in s.data.royalty_by_track[0]);
  check('populasi status rilisan terekam',s.meta.population.releaseStatus.live===10);
  check('komentar tiket ikut',s.data.ticket_comments.length===1);
  check('clean: Date → ISO',typeof clean({at:new Date(0)}).at==='string');
  const empty=await exportSample(fakeDb({}),{labels:5});
  check('DB kosong aman',empty.meta.selection.length===0&&Array.isArray(empty.data.labels));
  process.exit(fails?1:0);
})().catch(e=>{console.error(e);process.exit(1)});
