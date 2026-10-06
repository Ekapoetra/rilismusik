/* Uji mapper: hasil buildJourney harus lolos Persistence117.validateJourney
   dari storage117.js (validator asli yang dipakai klien), pada fixture
   koleksi produksi maupun database kosong. */
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {buildJourney}=require('./seed');

function validator(){
  const sandbox={
    window:{setInterval:(fn)=>fn,localStorage:{getItem:()=>null,setItem:()=>{},},},
    document:{documentElement:{classList:{add:()=>{},remove:()=>{}}},getElementById:()=>({setAttribute:()=>{},removeAttribute:()=>{}})},
  };
  sandbox.window.setInterval=(fn,d)=>()=>{};
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'..','prototype-v13.0','storage117.js'),'utf8'),sandbox);
  return sandbox.window.Persistence117;
}

function fakeDb(fixtures){
  return {
    databaseName:'fixture',
    listCollections:()=>({toArray:async()=>Object.keys(fixtures).map(name=>({name}))}),
    collection:n=>{const cursor=arr=>({sort:()=>cursor(arr),limit:l=>cursor(arr.slice(0,l)),toArray:async()=>arr});return{find:()=>cursor(fixtures[n]||[])};},
  };
}

(async()=>{
  const P=validator();
  const fixtures={
    users:[{id:'u1',name:'Nara',email:'nara@x.id',role:'label',label_id:'lab1'},{id:'s1',name:'Jeck',email:'j@x.id',role:'super'}],
    labels:[{id:'lab1',name:'Awan Records',kyc_status:'verified',pic_name:'Nara',created_at:'2024-01-01'},{id:'lab2',name:'Embun Label',kyc_status:'pending'}],
    releases:[{id:'r1',label_id:'lab1',title:'Hujan',primary_artist:'Senja',status:'live',track_count:3,release_date:'2024-05-01'},{id:'r2',label_id:'lab2',title:'Kabut',status:'submitted'}],
    payments:[{id:'p1',label_id:'lab1',amount_idr:350000,status:'paid',created_at:'2024-02-01'}],
    withdraw_requests:[{id:'w1',label_id:'lab1',amount_idr:1500000,status:'paid',bank_name:'BCA',account_number:'1234567890',account_holder:'Nara',created_at:'2024-06-01'}],
    support_tickets:[{id:'t1',label_id:'lab1',subject:'Bantuan cover',status:'done',created_at:'2024-03-01'}],
    ticket_comments:[{id:'c1',ticket_id:'t1',author_name:'Jeck',role:'staff',text:'Sudah diteruskan.',created_at:'2024-03-02'}],
    notifications:[{id:'n1',label_id:'lab1',kind:'activated',created_at:'2024-01-02'}],
    royalty_imports:[{id:'imp1',filename:'believe_sep.csv',created_at:'2024-09-01',exchange_rate:18000}],
    royalty_lines:[{id:'l1',import_id:'imp1',label_id:'lab1',label_name:'Awan Records',label_idr:2500000,period:'2024-08',title:'Hujan',matched:true}],
    addon_orders:[{id:'a1',label_id:'lab1',item:'Playlist pitch',status:'done',price_idr:150000}],
    wami_orders:[{id:'w1',label_id:'lab1',work:'Hujan',status:'submitted'}],
    bank_accounts:[{id:'b1',label_id:'lab1',bank_name:'BCA',account_number:'1234567890',account_holder:'Nara',status:'verified'}],
    staff_profiles:[{id:'sp1',name:'Adovi',email:'a@x.id',role:'admin',status:'active'}],
  };
  let fails=0;
  const check=(name,ok,extra='')=>{console.log((ok?'PASS':'FAIL')+' '+name+(extra?' — '+extra:''));if(!ok)fails++;};

  for(const [label,fx] of [['fixture lengkap',fixtures],['database kosong',{}]]){
    const journey=await buildJourney(fakeDb(fx));
    const errs=[];
    const v=P.validateJourney(journey);
    check(`validateJourney: ${label}`,v===true);
    if(v!==true)console.log('  journey:',JSON.stringify(journey).slice(0,400));
    check(`members ada: ${label}`,Array.isArray(journey.members)&&journey.members.length>0);
    check(`member default ada: ${label}`,journey.members.some(m=>m.id===journey.member));
    check(`rekening tersamarkan: ${label}`,JSON.stringify(journey).includes('1234567890')===false);
    check(`tanpa model rusak: ${label}`,P.validateJourney(journey)===true);
  }

  const j=await buildJourney(fakeDb(fixtures));
  check('rilisan hidup terpetakan',j.releases.some(r=>r.status==='live'&&r.title==='Hujan'));
  check('royalty ledger available',j.royalty107.ledger.some(l=>l.member==='L-lab1'&&l.bucket==='available'&&l.amount===2500000));
  check('penarikan ada',j.royalty107.withdraw108.requests.length===1&&j.royalty107.withdraw108.requests[0].status==='paid');
  check('tiket ada',j.tickets112.tickets.length===1);
  check('staff ada',j.staff114.users.length>=2);
  check('pesanan ada',j.commerce113.orders.length===1);
  check('notifikasi ada',j.notifications.length===1);

  process.exit(fails?1:0);
})().catch(e=>{console.error('ERROR',e);process.exit(1)});
