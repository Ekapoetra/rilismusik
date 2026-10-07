const {exportSample,clean}=require('./sample');

const fx={
  labels:[
    {id:'A',name:'Awan',kyc_status:'verified',user_id:'u1'},
    {id:'B',name:'Badai',kyc_status:'verified',user_id:'u2'},
    {id:'C',name:'Cahaya',kyc_status:'pending',user_id:'u3'},
    {id:'D',name:'Delta',kyc_status:'verified',user_id:'u4'}
  ],
  users:[{id:'u1',email:'a@x.id',password_hash:'zz',role:'label',label_id:'A'},{id:'u3',email:'c@x.id',role:'label',label_id:'C'},{id:'s1',role:'super',email:'s@x.id',reset_token:'t'}],
  releases:[...Array.from({length:9},(_,i)=>({id:'rA'+i,label_id:'A',title:'A'+i})),{id:'rB1',label_id:'B'},{id:'rD1',label_id:'D'}],
  tracks:[{id:'t1',release_id:'rA0',isrc:'ID123'}],
  withdraw_requests:[{id:'w1',label_id:'B',account_number:'1234567890',status:'pending'}],
  bank_accounts:[{id:'b1',label_id:'A',account_number:'99887766',bank_name:'BCA'}],
  kyc_documents:[{id:'k1',label_id:'C',nik:'3171234567890001',status:'pending'}],
  royalty_imports:[{id:'imp1'},{id:'imp2'}],
  royalty_lines:[{id:'l1',import_id:'imp1',label_id:'A',label_idr:100}],
  support_tickets:[{id:'tk1',label_id:'D'}],
  ticket_comments:[{id:'c1',ticket_id:'tk1',text:'hi'}]
};
const match=(doc,q)=>Object.entries(q).every(([k,v])=>v&&typeof v==='object'&&'$in'in v?v.$in.map(String).includes(String(doc[k])):v&&typeof v==='object'&&'$ne'in v?doc[k]!==v.$ne:doc[k]===v);
function fakeDb(data){
  return {databaseName:'fx',listCollections:()=>({toArray:async()=>Object.keys(data).map(name=>({name}))}),
    collection:n=>({
      find:(q={})=>{const rows=(data[n]||[]).filter(d=>match(d,q));const c={sort:()=>c,limit:l=>({toArray:async()=>rows.slice(0,l)}),toArray:async()=>rows};return c;},
      aggregate:([{$match},{$group}])=>({toArray:async()=>{const f=$group._id.slice(1),m=new Map();for(const d of (data[n]||[]).filter(d=>match(d,$match)))m.set(d[f],(m.get(d[f])||0)+1);return [...m].map(([k,v])=>({_id:k,n:v}));}})
    })};
}
let fails=0;const check=(name,ok,extra='')=>{console.log((ok?'PASS':'FAIL')+' '+name+(extra?' — '+extra:''));if(!ok)fails++;};
(async()=>{
  const s=await exportSample(fakeDb(fx),{labels:3,releasesPerLabel:2,imports:1});
  const ids=s.meta.selection.map(x=>x.id);
  check('3 label terpilih',ids.length===3,ids.join(','));
  check('label belum-KYC ikut',ids.includes('C'));
  check('label skor tertinggi ikut',ids.includes('A'));
  check('rilisan per label dibatasi',s.data.releases.filter(r=>r.label_id==='A').length===2);
  check('tracks mengikuti rilisan terpilih',s.data.tracks.length===1);
  check('password_hash dibuang',!s.data.users.some(u=>'password_hash'in u));
  check('reset_token dibuang',!s.data.users.some(u=>'reset_token'in u));
  check('account_number disamarkan',s.data.bank_accounts[0].account_number.endsWith('7766')&&s.data.bank_accounts[0].account_number.startsWith('•'));
  check('nik disamarkan',s.data.kyc_documents.length?s.data.kyc_documents[0].nik.endsWith('0001')&&s.data.kyc_documents[0].nik.startsWith('•'):true);
  check('import dibatasi',s.data.royalty_imports.length===1);
  check('komentar tiket ikut',s.data.ticket_comments.length===(ids.includes('D')?1:0));
  check('meta.counts ada',typeof s.meta.counts.labels==='number');
  check('clean: Date → ISO',typeof clean({at:new Date(0)}).at==='string');
  const empty=await exportSample(fakeDb({}),{labels:5});
  check('DB kosong aman',empty.meta.selection.length===0&&Array.isArray(empty.data.labels));
  process.exit(fails?1:0);
})().catch(e=>{console.error(e);process.exit(1)});
