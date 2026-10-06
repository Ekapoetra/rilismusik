/* Pemetaan koleksi produksi → dokumen journey V13.0.

   Dipakai oleh GET /api/proto/bootstrap: membaca koleksi salinan produksi
   dan menyusun seed berbentuk sama dengan RM10.seed() agar lolos
   Persistence117.validateJourney di klien.

   Prinsip:
   - Hanya membaca; tidak mengubah data produksi.
   - Nomor rekening disamarkan (•••1234) pada seed preview.
   - Model opsional yang tidak bisa dipetakan dengan aman dihilangkan
     supaya prototype mengisinya sendiri daripada gagal validasi. */
const idOf=x=>String(x?.id??x?._id??'');
const stamp=v=>{const t=typeof v==='number'?v:Date.parse(v);return Number.isFinite(t)?new Date(t).toISOString():new Date().toISOString();};
const money=v=>Math.max(0,Math.round(Number(v)||0));
const mask=v=>{const s=String(v||'');return s.length>4?'•'.repeat(s.length-4)+s.slice(-4):s;};
const limit=async(cursor,n)=>cursor.limit(n).toArray();

const RELEASE_STATUS={live:'live',approved:'approved',delivered:'delivered',distributed:'delivered',submitted:'submitted',pending:'submitted',in_review:'review',review:'review',needs_revision:'revision',revision:'revision',rejected:'closed',cancelled:'closed',closed:'closed',draft:'draft'};
const TICKET_STATUS={open:'new',new:'new',pending:'new',in_progress:'handling',handling:'handling',waiting:'waiting',done:'resolved',resolved:'resolved',closed:'resolved',rejected:'rejected'};
const WITHDRAW_STATUS={pending:'requested',requested:'requested',approved:'processing',processing:'processing',paid:'paid',completed:'paid',done:'paid',rejected:'rejected',cancelled:'rejected'};
const PAYMENT_STATUS={pending:'pending',waiting:'pending',paid:'paid',success:'paid',settled:'paid',expired:'expired',failed:'failed',rejected:'failed'};

async function collect(db){
  const names=new Set(await db.listCollections().toArray().then(c=>c.map(x=>x.name)));
  const has=n=>names.has(n);
  const find=(n,q={},p=null,n2=2000)=>has(n)?db.collection(n).find(q,{projection:p||undefined}).sort({_id:-1}).limit(n2).toArray():Promise.resolve([]);
  return {find,has};
}

async function buildJourney(db){
  const {find}=await collect(db);
  const [labels,users,releases,payments,withdrawals,tickets,comments,notifications,imports,lines,addonOrders,wamiOrders,bankAccounts,staffProfiles]=await Promise.all([
    find('labels',{},{id:1,name:1,status:1,kyc_status:1,pic_name:1,user_id:1,owner_user_id:1,plan:1,package:1,created_at:1,city:1},500),
    find('users',{},{id:1,name:1,email:1,role:1,label_id:1,labels:1,active_label_id:1,pic_name:1},2000),
    find('releases',{},{id:1,label_id:1,title:1,name:1,artist:1,primary_artist:1,status:1,track_count:1,tracks:1,release_date:1,service:1,created_at:1,upc:1,genre:1},1000),
    find('payments',{},{id:1,label_id:1,user_id:1,amount:1,amount_idr:1,total:1,status:1,method:1,kind:1,product:1,created_at:1,invoice_id:1},500),
    find('withdraw_requests',{},{id:1,label_id:1,user_id:1,label_ids:1,amount:1,amount_idr:1,status:1,bank_name:1,account_number:1,account_holder:1,created_at:1,periods:1},500),
    find('support_tickets',{},{id:1,label_id:1,user_id:1,subject:1,title:1,category:1,status:1,priority:1,created_at:1},500),
    find('ticket_comments',{},{id:1,ticket_id:1,author:1,author_name:1,role:1,text:1,message:1,created_at:1},2000),
    find('notifications',{},{id:1,label_id:1,user_id:1,kind:1,type:1,title:1,ref:1,ref_id:1,created_at:1,read:1},1000),
    find('royalty_imports',{},{id:1,filename:1,name:1,created_at:1,exchange_rate:1,rate:1,status:1},300),
    find('royalty_lines',{},{id:1,import_id:1,label_id:1,label_name:1,label_idr:1,amount_idr:1,period:1,month:1,title:1,track_title:1,matched:1,status:1},5000),
    find('addon_orders',{},{id:1,label_id:1,user_id:1,item:1,service:1,kind:1,status:1,created_at:1,price_idr:1},500),
    find('wami_orders',{},{id:1,label_id:1,user_id:1,work:1,title:1,status:1,created_at:1},500),
    find('bank_accounts',{},{id:1,label_id:1,user_id:1,bank_name:1,bank:1,account_number:1,account_holder:1,status:1,verified:1},500),
    find('staff_profiles',{},{id:1,user_id:1,name:1,email:1,role:1,status:1},500)
  ]);

  const now=Date.now();
  const memberId=lid=>'L-'+String(lid);
  const userByLabel=new Map();
  for(const u of users){
    const lids=[u.label_id,u.active_label_id,...(Array.isArray(u.labels)?u.labels.map(l=>typeof l==='object'?l.id:l):[])].filter(Boolean);
    for(const lid of lids)if(!userByLabel.has(String(lid)))userByLabel.set(String(lid),u);
  }
  const bankByLabel=new Map();
  for(const b of bankAccounts){
    const lid=String(b.label_id||'');
    const ok=b.verified===true||['verified','approved','active'].includes(String(b.status||'').toLowerCase())||!b.status;
    if(lid&&ok&&!bankByLabel.has(lid))bankByLabel.set(lid,b);
  }

  const members=labels.map(l=>{
    const u=userByLabel.get(idOf(l))||{};
    const bank=bankByLabel.get(idOf(l));
    const verified=String(l.kyc_status||'').toLowerCase()==='verified'||['active','verified'].includes(String(l.status||'').toLowerCase());
    return {
      id:memberId(idOf(l)),name:l.name||'Label tanpa nama',plan:'Flex',period:'year',
      email:u.email||(idOf(l)+'@data.test'),emailConfirmed:Boolean(u.email),paid:true,invoice:null,
      active:verified,activatedAt:verified?stamp(l.created_at):null,version:1,
      contract:verified,identity:{person:l.pic_name||u.name||'',address:'',postal:'',country:'Indonesia',document:verified},
      application:null,
      bank:{approved:bank?{bank:bank.bank_name||bank.bank||'-',number:mask(bank.account_number),holder:bank.account_holder||'',version:1,status:'approved'}:null,pending:null,version:0},
      social:'',lots:[],joined:stamp(l.created_at).slice(0,10),welcome:false
    };
  });
  if(!members.length)members.push({id:'L-none',name:'Belum ada label',plan:'Flex',period:'year',email:'kosong@data.test',emailConfirmed:false,paid:false,invoice:null,active:false,activatedAt:null,version:1,contract:false,identity:{person:'',address:'',postal:'',country:'Indonesia',document:false},application:null,bank:{approved:null,pending:null,version:0},social:'',lots:[],joined:'2026-01-01',welcome:false});

  const mappedReleases=releases.map((r,i)=>({
    id:'RM-P'+i,member:memberId(r.label_id||''),
    title:r.title||r.name||'Tanpa judul',artist:r.artist||r.primary_artist||'-',
    type:'single',tracks:Number(r.track_count)||(Array.isArray(r.tracks)?r.tracks.length:1),
    genre:r.genre||'',service:r.service||'Standard',
    status:RELEASE_STATUS[String(r.status||'draft').toLowerCase()]||'draft',
    version:0,history:[],allocation:[],creditState:'none',upc:r.upc||null,isrc:null,link:null,
    date:String(r.release_date||'').slice(0,10)||null,createdAt:stamp(r.created_at),serial:i
  }));

  const mappedNotifications=notifications.slice(0,200).map((n,i)=>({
    id:i+1,member:n.label_id?memberId(n.label_id):members[0].id,
    key:String(n.kind||n.type||'info'),ref:String(n.ref||n.ref_id||''),at:stamp(n.created_at),
    read:Boolean(n.read),source:'production'
  }));

  /* --- Model opsional --- */
  const optional={};

  const staffUsers=[...staffProfiles.map(p=>({id:'S-'+idOf(p),name:p.name||idOf(p),email:p.email||'',status:['active','inactive','disabled','invited'].includes(p.status)?p.status:'active',super:['super','super_admin'].includes(p.role)})),...users.filter(u=>['admin','super','super_admin','staff'].includes(u.role)).map(u=>({id:'S-'+idOf(u),name:u.name||u.email||idOf(u),email:u.email||'',status:'active',super:['super','super_admin'].includes(u.role)}))];
  const seenStaff=new Set();
  optional.staff114={schema:1,users:staffUsers.filter(u=>u.id&&u.name&&!seenStaff.has(u.id)&&seenStaff.add(u.id)),roles:[],audit:[],notifications:[],handoffs:[]};
  if(!optional.staff114.users.length)delete optional.staff114;

  const commentsByTicket=new Map();
  for(const c of comments){
    const k=String(c.ticket_id||'');
    if(!commentsByTicket.has(k))commentsByTicket.set(k,[]);
    commentsByTicket.get(k).push({from:c.author_name||c.author||'-',role:c.role||'member',text:c.text||c.message||'',at:stamp(c.created_at)});
  }
  if(tickets.length)optional.tickets112={serial:tickets.length,tickets:tickets.map((t,i)=>({id:'T-'+idOf(t),member:t.label_id?memberId(t.label_id):members[0].id,subject:t.subject||t.title||'Tiket',category:t.category||'general',priority:t.priority||'normal',status:TICKET_STATUS[String(t.status||'open').toLowerCase()]||'new',messages:commentsByTicket.get(idOf(t))||[],at:stamp(t.created_at),serial:i+1})),drafts:[],notifications:[],notified:[]};

  if(payments.length)optional.commerce113={serial:payments.length,orders:payments.map((p,i)=>({id:'P-'+idOf(p),member:p.label_id?memberId(p.label_id):members[0].id,kind:p.kind||p.product||'payment',amount:money(p.amount_idr??p.amount??p.total),method:p.method||'-',status:PAYMENT_STATUS[String(p.status||'pending').toLowerCase()]||'pending',attempts:[{at:stamp(p.created_at),status:'created'}],history:[{at:stamp(p.created_at),note:String(p.status||'pending')}],at:stamp(p.created_at),serial:i+1})),provider:[],refunds:[],notifications:[]};

  if(imports.length||lines.length){
    const linesByImport=new Map();
    for(const l of lines){
      const k=String(l.import_id||'');
      if(!linesByImport.has(k))linesByImport.set(k,[]);
      linesByImport.get(k).push(l);
    }
    const batches=imports.map((im,i)=>({
      id:'IMP-'+String(i+1).padStart(3,'0'),name:im.filename||im.name||('import-'+idOf(im)),at:stamp(im.created_at),
      rate:money(im.exchange_rate??im.rate)||1,share:100,
      rows:(linesByImport.get(idOf(im))||[]).map(l=>({member:memberId(l.label_id||''),memberName:l.label_name||'',period:String(l.period||l.month||''),amount:money(l.label_idr??l.amount_idr),matched:l.matched!==false,title:l.title||l.track_title||''})),
      posted:[...new Set((linesByImport.get(idOf(im))||[]).filter(l=>l.matched!==false).map(l=>memberId(l.label_id||'')))],
      block:'',fingerprint:'prod-'+idOf(im)
    }));
    const ledger=[];
    for(const b of batches)for(const m of b.posted)ledger.push({id:b.id+':publish:'+m,ref:b.id,member:m,amount:b.rows.filter(r=>r.member===m).reduce((a,r)=>a+r.amount,0),bucket:'available',kind:'published',at:b.at});
    optional.royalty107={schema:1,serial:batches.length+1,batches,ledger,receipts:[],history:[],corrections:[],cases:[]};

    const memberById=new Map(members.map(m=>[m.id,m]));
    const accounts=[...new Set([...members.map(m=>m.id),...withdrawals.map(w=>memberId(w.label_id||''))])]
      .map(mid=>({id:'ACC-'+mid,name:memberById.get(mid)?.name||mid,members:[mid],city:'-'}));
    optional.royalty107.withdraw108={serial:withdrawals.length+1,version:0,accounts,requests:withdrawals.map((w,i)=>({id:'WD-'+String(i+1).padStart(4,'0'),account:'ACC-'+memberId(w.label_id||''),name:memberById.get(memberId(w.label_id))?.name||'',city:'-',amount:money(w.amount_idr??w.amount),parts:[{member:memberId(w.label_id||''),amount:money(w.amount_idr??w.amount)}],periods:Array.isArray(w.periods)?w.periods.map(String):[],memo:'SEP ROYALTIES',bank:{bank:w.bank_name||'-',number:mask(w.account_number),holder:w.account_holder||''},status:WITHDRAW_STATUS[String(w.status||'pending').toLowerCase()]||'requested',at:stamp(w.created_at)}))};
  }

  if(addonOrders.length)optional.addons111={catalogue:[],orders:addonOrders.map((o,i)=>({id:'A-'+idOf(o),member:o.label_id?memberId(o.label_id):members[0].id,item:o.item||o.service||o.kind||'addon',status:o.status||'ordered',price:money(o.price_idr),at:stamp(o.created_at),serial:i+1})),history:[]};

  if(wamiOrders.length)optional.wami11={orders:wamiOrders.map((o,i)=>({id:'W-'+idOf(o),member:o.label_id?memberId(o.label_id):members[0].id,work:o.work||o.title||'Karya',status:o.status||'submitted',at:stamp(o.created_at),serial:i+1})),notifications:[]};

  const journey={
    schema:1,now,role:'super',actor:'platform',member:members[0].id,
    members,releases:mappedReleases,events:[{id:1,kind:'bootstrap',target:'database',note:'Seed dari salinan produksi',actor:'system',at:now}],
    serial:mappedReleases.length+mappedNotifications.length+10,
    notifications:mappedNotifications,lang:'id',theme:'light',page:'home',
    layout:{gap:'normal',size:'normal',font:'normal',design:'plain'},failNext:false,
    storageRevision116:0,dataSource:'production-copy',bootstrappedAt:new Date(now).toISOString(),
    ...optional
  };
  const staffFirst=optional.staff114?.users?.[0];
  if(staffFirst)journey.staffUser116=staffFirst.id;
  return journey;
}

/* Patch workspace staff: antrean pekerjaan & feed aktivitas dari koleksi
   produksi. Bentuk mengikuti data.tasks/data.events pada shared doc
   (disalin klien ke sharedSnapshot117 sebelum replace). */
const TASK_STAGE={submitted:'queued',pending:'queued',queued:'queued',in_review:'review',review:'review',needs_revision:'correction',revision:'correction',approved:'approval',delivered:'believe',followup:'believe'};

async function buildSharedPatch(db){
  const {find}=await collect(db);
  const [labels,releases,tickets,withdrawals,metaEdits,kycDocs,bankChanges,activityLogs]=await Promise.all([
    find('labels',{},{id:1,name:1},500),
    find('releases',{},{id:1,label_id:1,title:1,name:1,status:1,updated_at:1,created_at:1,submitted_at:1},1000),
    find('support_tickets',{},{id:1,label_id:1,subject:1,title:1,status:1,created_at:1,updated_at:1},500),
    find('withdraw_requests',{},{id:1,label_id:1,amount:1,amount_idr:1,status:1,created_at:1},300),
    find('release_metadata_edits',{},{id:1,release_id:1,label_id:1,status:1,created_at:1,updated_at:1},300),
    find('kyc_documents',{},{id:1,label_id:1,user_id:1,status:1,created_at:1,updated_at:1},300),
    find('bank_account_change_requests',{},{id:1,label_id:1,status:1,created_at:1},300),
    find('activity_logs',{},{id:1,user_id:1,user_name:1,actor:1,action:1,entity:1,target:1,created_at:1},300)
  ]);
  const nameOf=new Map(labels.map(l=>[idOf(l),l.name||idOf(l)]));
  const label=lid=>nameOf.get(String(lid))||String(lid||'-');
  const lastOf=x=>stamp(x.updated_at||x.created_at);
  const openish=s=>['pending','requested','submitted','open','new','in_progress','processing','review'].includes(String(s||'').toLowerCase());

  const tasks=[];
  for(const r of releases){
    const stage=TASK_STAGE[String(r.status||'').toLowerCase()];
    if(stage)tasks.push({id:'R-'+idOf(r),title:r.title||r.name||'Rilisan',label:label(r.label_id),kind:'release',stage,pct:null,handler:null,last:lastOf(r),overdue:false});
  }
  for(const t of tickets)if(openish(t.status)&&!['done','resolved','closed','rejected'].includes(String(t.status).toLowerCase()))
    tasks.push({id:'T-'+idOf(t),title:t.subject||t.title||'Tiket dukungan',label:label(t.label_id),kind:'support',stage:'review',pct:null,handler:null,last:lastOf(t),overdue:false});
  for(const w of withdrawals)if(openish(w.status))
    tasks.push({id:'W-'+idOf(w),title:`Penarikan Rp${money(w.amount_idr??w.amount).toLocaleString('id-ID')}`,label:label(w.label_id),kind:'finance',stage:'approval',pct:null,handler:null,last:lastOf(w),overdue:false});
  for(const m of metaEdits)if(openish(m.status))
    tasks.push({id:'M-'+idOf(m),title:'Perubahan metadata',label:label(m.label_id),kind:'release',stage:'review',pct:null,handler:null,last:lastOf(m),overdue:false});
  for(const k of kycDocs)if(openish(k.status))
    tasks.push({id:'K-'+idOf(k),title:'Verifikasi identitas',label:label(k.label_id),kind:'claim',stage:'review',pct:null,handler:null,last:lastOf(k),overdue:false});
  for(const b of bankChanges)if(openish(b.status))
    tasks.push({id:'B-'+idOf(b),title:'Perubahan rekening',label:label(b.label_id),kind:'finance',stage:'review',pct:null,handler:null,last:lastOf(b),overdue:false});

  const events=activityLogs.slice(0,60).map((a,i)=>({
    id:i+1,who:String(a.user_name||a.actor||a.user_id||'sistem').split('@')[0].toLowerCase(),
    obj:String(a.entity||a.target||''),text:[String(a.action||'aktivitas'),String(a.action||'activity')],
    time:new Date(stamp(a.created_at)).toTimeString().slice(0,5).replace(':','.')+'',category:'work'
  }));

  return {tasks:tasks.slice(0,300),events};
}

async function domainSummary(db){
  const {has}=await collect(db);
  const names=['users','labels','releases','tracks','artists','royalty_imports','royalty_lines','monthly_analytics','withdraw_requests','payments','addon_orders','wami_orders','support_tickets','ticket_comments','notifications','contracts','staff_profiles','bank_accounts','kyc_documents','chat_conversations','service_orders','proto_documents'];
  const out={};
  for(const n of names)if(has(n))try{out[n]=await db.collection(n).estimatedDocumentCount()}catch{}
  return out;
}

module.exports={buildJourney,buildSharedPatch,domainSummary};
