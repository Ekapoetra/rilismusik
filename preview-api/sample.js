/* Ekspor cuplikan database produksi → JSON statis untuk bahan skenario
   prototype V13.0 (dummy tambahan, bukan hidrasi runtime).

   Pemilihan label memakai KUOTA SKENARIO supaya alur kerja nyata terwakili
   (bukan hanya label dengan rilisan terbanyak yang semuanya sudah live):
     - rilisan sedang submitted/under_review/need_revision/approved/delivered
     - tiket open/in_progress/waiting_label/submitted_to_believe
     - penarikan requested/approved
     - KYC pending/rejected, rekening belum terverifikasi, langganan expired
     - label lama belum klaim (legacy_unclaimed) — dibatasi
   lalu sisanya diisi label berskor aktivitas tertinggi.

   Dokumen diambil apa adanya (tanpa proyeksi) agar bentuk asli koleksi
   terekam; kredensial dibuang, nomor rekening/NIK disamarkan. Nama label,
   judul rilisan, email dipertahankan (keputusan user). Hanya membaca. */

const DROP_KEY=/password|hash|token|secret|otp|session|api_key|apikey|private/i;
const MASK_KEY=/account_number|^nik$|id_number|ktp|npwp|card_number/i;

const str=v=>v==null?v:typeof v==='object'&&typeof v.toHexString==='function'?v.toHexString():v;
const mask=v=>{const s=String(v??'');return s.length>4?'•'.repeat(Math.min(s.length-4,8))+s.slice(-4):s?'••••':s;};

function clean(v,key=''){
  if(Array.isArray(v))return v.map(x=>clean(x));
  if(v instanceof Date)return v.toISOString();
  if(v&&typeof v==='object'){
    if(typeof v.toHexString==='function')return v.toHexString();
    const out={};
    for(const [k,x] of Object.entries(v)){
      if(k==='_id')continue;
      if(DROP_KEY.test(k))continue;
      out[k]=MASK_KEY.test(k)?mask(x):clean(x,k);
    }
    return out;
  }
  return MASK_KEY.test(key)?mask(v):str(v);
}

const idOf=d=>String(d?.id??d?._id??'');
const RELEASE_ACTIVE=['submitted','under_review','need_revision','approved','delivered','takedown_requested','rejected'];
const TICKET_OPEN=['open','in_progress','waiting_label','submitted_to_believe'];
const WITHDRAW_OPEN=['requested','approved','processing'];

async function exportSample(db,{labels:N=15,releasesPerLabel=6,imports=4,linesPerImport=400,legacyMax=3}={}){
  const names=new Set((await db.listCollections().toArray()).map(c=>c.name));
  const col=n=>names.has(n)?db.collection(n):null;
  const all=async(n,q={},limit=5000,sort={_id:-1})=>{const c=col(n);return c?c.find(q).sort(sort).limit(limit).toArray():[];};
  const agg=async(n,pipeline)=>{const c=col(n);return c?c.aggregate(pipeline).toArray():[];};
  const count=async(n,field,match={})=>{const rows=await agg(n,[{$match:{[field]:{$ne:null},...match}},{$group:{_id:'$'+field,n:{$sum:1}}}]);return new Map(rows.map(r=>[String(r._id),r.n]));};
  const distinctLabels=async(n,match)=>new Set((await agg(n,[{$match:match},{$group:{_id:'$label_id'}}])).map(r=>String(r._id)));

  /* 1. Skor + kuota skenario */
  const labels=await all('labels',{},10000,{_id:1});
  const byId=new Map(labels.map(l=>[idOf(l),l]));
  const [rel,wd,tk,rl,pay]=await Promise.all([count('releases','label_id'),count('withdraw_requests','label_id'),count('support_tickets','label_id'),count('royalty_lines','label_id'),count('payments','label_id')]);
  const [relActive,tkOpen,wdOpen,kycPending,bankPending]=await Promise.all([
    distinctLabels('releases',{status:{$in:RELEASE_ACTIVE}}),
    distinctLabels('support_tickets',{status:{$in:TICKET_OPEN}}),
    distinctLabels('withdraw_requests',{status:{$in:WITHDRAW_OPEN}}),
    distinctLabels('kyc_documents',{status:{$in:['pending','submitted','rejected']}}),
    distinctLabels('bank_accounts',{verified_status:{$in:['pending','unverified','rejected']}})
  ]);
  const score=l=>{const id=idOf(l);return (rel.get(id)||0)+3*(wd.get(id)||0)+2*(tk.get(id)||0)+Math.min(20,(rl.get(id)||0))/4+2*(pay.get(id)||0);};
  const legacy=l=>l.account_status==='legacy_unclaimed';
  const expired=l=>l.subscription_status==='expired';
  const picked=[],reasons=new Map();
  const take=(id,why)=>{const l=byId.get(id);if(!l)return;if(!reasons.has(id)){reasons.set(id,[]);picked.push(l);}reasons.get(id).push(why);};
  const topBy=(set,why,max)=>{[...set].map(id=>byId.get(id)).filter(Boolean).sort((a,b)=>score(b)-score(a)).slice(0,max).forEach(l=>take(idOf(l),why));};
  topBy(relActive,'rilisan dalam alur kerja',4);
  topBy(tkOpen,'tiket terbuka',3);
  topBy(wdOpen,'penarikan menunggu',3);
  topBy(kycPending,'KYC pending/ditolak',2);
  topBy(bankPending,'rekening belum terverifikasi',2);
  topBy(new Set(labels.filter(expired).map(idOf)),'langganan kedaluwarsa',1);
  for(const l of labels.filter(legacy).sort((a,b)=>score(b)-score(a)).slice(0,legacyMax))take(idOf(l),'label lama belum klaim');
  for(const l of labels.filter(l=>!legacy(l)).sort((a,b)=>score(b)-score(a))){if(picked.length>=N)break;take(idOf(l),'aktivitas tertinggi');}
  if(picked.length>N)picked.length=N;
  const ids=picked.map(idOf);
  const inLabel={label_id:{$in:ids}};

  /* 2. Entitas terkait */
  const users=[...await all('users',{id:{$in:picked.map(l=>l.user_id).filter(Boolean)}},200),...await all('users',{$or:[{active_label_id:{$in:ids}},{primary_label_id:{$in:ids}}]},200),...await all('users',{role:{$in:['admin','super','super_admin','superadmin','staff','admin_support','admin_finance']}},50)];
  /* Rilisan: utamakan status non-live agar alur kerja terlihat, sisanya terbaru. */
  const releasesRaw=await all('releases',inLabel,5000);
  const rank=r=>RELEASE_ACTIVE.includes(r.status)?0:r.status==='draft'?1:r.status==='live'?2:3;
  const perLabel=new Map();const releases=[];
  for(const r of releasesRaw.slice().sort((a,b)=>rank(a)-rank(b))){const k=String(r.label_id);const n=perLabel.get(k)||0;if(n<releasesPerLabel){perLabel.set(k,n+1);releases.push(r);}}
  const relIds=releases.map(idOf);
  const [tracks,artists,withdraws,tickets,payments,kyc,banks,bankChanges,contracts,wami,addons,services,notifications,balance,workItems,activity,importsRaw,staff,metaEdits,contentId,releaseStatusCounts,ticketStatusCounts]=await Promise.all([
    all('tracks',{release_id:{$in:relIds}},2000),
    all('artists',inLabel,150),
    all('withdraw_requests',inLabel,300),
    all('support_tickets',inLabel,300),
    all('payments',inLabel,300),
    all('kyc_documents',inLabel,100),
    all('bank_accounts',inLabel,100),
    all('bank_account_change_requests',inLabel,100),
    all('contracts',inLabel,100),
    all('wami_orders',inLabel,100),
    all('addon_orders',inLabel,100),
    all('service_orders',inLabel,100),
    all('notifications',{},300),
    all('balance_transactions',inLabel,300),
    all('work_items',{},200),
    all('activity_logs',{},300),
    all('royalty_imports',{},imports),
    all('staff_profiles',{},50),
    all('release_metadata_edits',inLabel,100),
    all('contentid_assets',inLabel,100),
    agg('releases',[{$group:{_id:'$status',n:{$sum:1}}}]),
    agg('support_tickets',[{$group:{_id:'$status',n:{$sum:1}}}])
  ]);
  const ticketComments=await all('ticket_comments',{ticket_id:{$in:tickets.map(idOf)}},1000);
  const importIds=importsRaw.map(idOf);
  /* Baris royalti: contoh per import (dibatasi) + agregat lengkap per label×periode×import
     supaya total royalti tiap label tetap akurat walau barisnya dicuplik. */
  const royaltyLines=[];
  for(const iid of importIds)royaltyLines.push(...await all('royalty_lines',{import_id:iid,label_id:{$in:ids}},linesPerImport,{label_idr:-1}));
  const royaltySummary=await agg('royalty_lines',[{$match:{label_id:{$in:ids}}},{$group:{_id:{label_id:'$label_id',import_id:'$import_id',period:'$period',match_status:'$match_status'},lines:{$sum:1},label_idr:{$sum:'$label_idr'},revenue_eur:{$sum:'$revenue_eur'},quantity:{$sum:'$quantity'}}},{$sort:{'_id.period':-1}}]);
  const royaltyByPlatform=await agg('royalty_lines',[{$match:{label_id:{$in:ids}}},{$group:{_id:{label_id:'$label_id',period:'$period',platform:'$platform'},label_idr:{$sum:'$label_idr'},quantity:{$sum:'$quantity'}}}]);
  const royaltyByTrack=await agg('royalty_lines',[{$match:{label_id:{$in:ids}}},{$group:{_id:{label_id:'$label_id',period:'$period',isrc:'$isrc'},title:{$first:'$track_title_raw'},artist:{$first:'$artist_name_raw'},label_idr:{$sum:'$label_idr'},quantity:{$sum:'$quantity'}}},{$sort:{label_idr:-1}},{$limit:1500}]);
  const chats=await all('chat_conversations',inLabel,50);
  const chatMessages=await all('chat_messages',{conversation_id:{$in:chats.map(idOf)}},500);
  const products=await all('payment_products',{},50);

  const dedupe=arr=>{const seen=new Set();return arr.filter(x=>{const k=idOf(x)||JSON.stringify(x);if(seen.has(k))return false;seen.add(k);return true;});};
  const flat=rows=>rows.map(r=>({...r._id,...Object.fromEntries(Object.entries(r).filter(([k])=>k!=='_id'))}));
  const data={
    labels:picked,users:dedupe(users),releases,tracks,artists,
    royalty_imports:importsRaw,royalty_lines:royaltyLines,
    royalty_summary:flat(royaltySummary),royalty_by_platform:flat(royaltyByPlatform),royalty_by_track:flat(royaltyByTrack),
    balance_transactions:balance,
    withdraw_requests:withdraws,payments,payment_products:products,
    support_tickets:tickets,ticket_comments:ticketComments,
    kyc_documents:kyc,bank_accounts:banks,bank_account_change_requests:bankChanges,contracts,
    wami_orders:wami,addon_orders:addons,service_orders:services,contentid_assets:contentId,release_metadata_edits:metaEdits,
    notifications,work_items:workItems,activity_logs:activity,staff_profiles:staff,
    chat_conversations:chats,chat_messages:chatMessages
  };
  const out={};
  for(const [k,v] of Object.entries(data))out[k]=clean(v);
  const counts=Object.fromEntries(Object.entries(out).map(([k,v])=>[k,v.length]));
  return {meta:{
    exportedAt:new Date().toISOString(),db:db.databaseName,labels:N,
    selection:picked.map(l=>({id:idOf(l),name:l.label_name||l.name||idOf(l),score:Math.round(score(l)),account:l.account_status,kyc:l.kyc_status||null,reasons:reasons.get(idOf(l))})),
    population:{labels:labels.length,releaseStatus:Object.fromEntries(releaseStatusCounts.map(r=>[String(r._id),r.n])),ticketStatus:Object.fromEntries(ticketStatusCounts.map(r=>[String(r._id),r.n]))},
    counts,masking:'password/hash/token/secret dibuang; account_number/NIK/NPWP disamarkan'
  },data:out};
}

module.exports={exportSample,clean};
