/* Ekspor cuplikan database produksi → JSON statis untuk bahan skenario
   prototype V13.0 (dummy tambahan, bukan hidrasi runtime).

   - Memilih N label "terkaya" (rilisan, penarikan, tiket, royalti) dan
     menjamin ada label yang belum terverifikasi agar skenario aktivasi ada.
   - Mengambil dokumen apa adanya (tanpa proyeksi) supaya bentuk asli koleksi
     ikut terekam; hanya kredensial yang dibuang dan nomor rekening/NIK yang
     disamarkan — nama label, judul rilisan, email dipertahankan (keputusan user).
   - Hanya membaca. */

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

async function exportSample(db,{labels:N=15,releasesPerLabel=6,imports=4}={}){
  const names=new Set((await db.listCollections().toArray()).map(c=>c.name));
  const col=n=>names.has(n)?db.collection(n):null;
  const all=async(n,q={},limit=5000,sort={_id:-1})=>{const c=col(n);return c?c.find(q).sort(sort).limit(limit).toArray():[];};
  const count=async(n,field)=>{const c=col(n);if(!c)return new Map();const rows=await c.aggregate([{$match:{[field]:{$ne:null}}},{$group:{_id:'$'+field,n:{$sum:1}}}]).toArray();return new Map(rows.map(r=>[String(r._id),r.n]));};

  /* 1. Skor label */
  const labels=await all('labels',{},5000,{_id:1});
  const [rel,wd,tk,rl,pay]=await Promise.all([count('releases','label_id'),count('withdraw_requests','label_id'),count('support_tickets','label_id'),count('royalty_lines','label_id'),count('payments','label_id')]);
  const verified=l=>String(l.kyc_status||l.status||'').toLowerCase()==='verified'||l.kyc_status==='approved';
  const scored=labels.map(l=>{const id=idOf(l);return {l,id,score:(rel.get(id)||0)+3*(wd.get(id)||0)+2*(tk.get(id)||0)+Math.min(20,(rl.get(id)||0))/4+2*(pay.get(id)||0)};}).sort((a,b)=>b.score-a.score);
  const picked=[];
  const unverified=scored.filter(x=>!verified(x.l));
  for(const x of scored){if(picked.length>=N-Math.min(3,unverified.length))break;picked.push(x);}
  for(const x of unverified){if(picked.length>=N)break;if(!picked.includes(x))picked.push(x);}
  const ids=picked.map(x=>x.id);
  const inLabel={label_id:{$in:ids}};

  /* 2. Entitas terkait */
  const users=[...await all('users',{id:{$in:picked.map(x=>x.l.user_id).filter(Boolean)}},200),...await all('users',{label_id:{$in:ids}},200),...await all('users',{role:{$in:['admin','super','super_admin','superadmin','staff']}},50)];
  const releasesRaw=await all('releases',inLabel,5000);
  const perLabel=new Map();const releases=[];
  for(const r of releasesRaw){const k=String(r.label_id);const n=perLabel.get(k)||0;if(n<releasesPerLabel){perLabel.set(k,n+1);releases.push(r);}}
  const relIds=releases.map(idOf);
  const [tracks,artists,withdraws,tickets,payments,kyc,banks,bankChanges,contracts,wami,addons,services,notifications,balance,workItems,activity,importsRaw,staff,metaEdits,contentId]=await Promise.all([
    all('tracks',{release_id:{$in:relIds}},2000),
    all('artists',inLabel,500),
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
    all('notifications',{user_id:{$in:users.map(idOf)}},400),
    all('balance_transactions',inLabel,500),
    all('work_items',{},200),
    all('activity_logs',{},300),
    all('royalty_imports',{},imports),
    all('staff_profiles',{},50),
    all('release_metadata_edits',inLabel,100),
    all('contentid_assets',inLabel,100)
  ]);
  const ticketComments=await all('ticket_comments',{ticket_id:{$in:tickets.map(idOf)}},1000);
  const royaltyLines=await all('royalty_lines',{import_id:{$in:importsRaw.map(idOf)},label_id:{$in:ids}},5000);
  const chats=await all('chat_conversations',inLabel,50);
  const chatMessages=await all('chat_messages',{conversation_id:{$in:chats.map(idOf)}},500);
  const products=await all('payment_products',{},50);

  const dedupe=arr=>{const seen=new Set();return arr.filter(x=>{const k=idOf(x)||JSON.stringify(x);if(seen.has(k))return false;seen.add(k);return true;});};
  const data={
    labels:picked.map(x=>x.l),users:dedupe(users),releases,tracks,artists,
    royalty_imports:importsRaw,royalty_lines:royaltyLines,balance_transactions:balance,
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
  return {meta:{exportedAt:new Date().toISOString(),db:db.databaseName,labels:N,selection:picked.map(x=>({id:x.id,name:x.l.name,score:Math.round(x.score),verified:verified(x.l)})),counts,masking:'password/hash/token/secret dibuang; account_number/NIK/NPWP disamarkan'},data:out};
}

module.exports={exportSample,clean};
