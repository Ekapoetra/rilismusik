/* Uji render end-to-end: journey hasil buildJourney(fixture) disuntik ke
   localStorage, halaman dimuat ulang, lalu dicek aplikasi benar-benar render
   (bukan halaman kosong / mode recovery). Meniru apa yang dilihat user pada
   preview setelah hidrasi data produksi. */
const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const {buildJourney}=require('./seed');

const dir=path.join(__dirname,'..','prototype-v13.0');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf'};

const fixtures={
  labels:[{id:'lab1',name:'Awan Records',kyc_status:'verified',pic_name:'Nara',created_at:'2024-01-01'},{id:'lab2',name:'Embun Label',kyc_status:'pending'}],
  users:[{id:'u1',name:'Nara',email:'nara@x.id',role:'label',label_id:'lab1'},{id:'s1',name:'Jeck Rotama',email:'j@x.id',role:'super'}],
  /* Rilisan dengan label_id yatim — kasus yang diduga merusak render. */
  releases:[{id:'r1',label_id:'lab1',title:'Hujan',primary_artist:'Senja',status:'live',track_count:3,release_date:'2024-05-01'},{id:'r9',label_id:'GHOST',title:'Yatim',status:'submitted',created_at:'2024-09-01'}],
  notifications:[{id:'n1',label_id:'GHOST',kind:'x',created_at:'2024-01-02'}],
  royalty_imports:[{id:'imp1',filename:'believe_sep.csv',created_at:'2024-09-01'}],
  royalty_lines:[{id:'l1',import_id:'imp1',label_id:'lab1',label_idr:2500000,period:'2024-08',matched:true},{id:'l2',import_id:'imp1',label_id:'GHOST',label_idr:900,period:'2024-08',matched:true}],
  withdraw_requests:[{id:'w1',label_id:'GHOST',amount_idr:1500000,status:'processing',created_at:'2024-09-01'}],
};

function fakeDb(fx){
  return {listCollections:()=>({toArray:async()=>Object.keys(fx).map(name=>({name}))}),
    collection:n=>{const cursor=arr=>({sort:()=>cursor(arr),limit:l=>cursor(arr.slice(0,l)),toArray:async()=>arr});return{find:()=>cursor(fx[n]||[])};}};
}

(async()=>{
  const journey=await buildJourney(fakeDb(fixtures));
  const server=http.createServer((req,res)=>{
    const p=new URL(req.url,'http://x').pathname;
    const file=path.resolve(dir,'.'+decodeURIComponent(p==='/'?'/index.html':p));
    if(!file.startsWith(dir+path.sep)||!fs.existsSync(file)){res.writeHead(404);res.end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(r=>server.listen(0,r));
  const port=server.address().port;

  const {chromium}=require('playwright');
  const browser=await chromium.launch();
  const page=await browser.newPage();
  await page.addInitScript(()=>{
    window.__snaps=[];
    window.addEventListener('error',()=>{try{window.__snaps.push({user:typeof state!=='undefined'?state.user:null,people:typeof people!=='undefined'?people.map(p=>p.id):null,role:typeof ten!=='undefined'?ten.role:null})}catch{}});
  });
  const errors=[];
  let phase='boot';
  page.on('pageerror',e=>errors.push('['+phase+'] pageerror: '+(e.stack||e.message)));
  page.on('console',m=>{if(m.type()==='error')errors.push('['+phase+'] console: '+m.text().slice(0,160));});

  await page.goto(`http://localhost:${port}/`,{waitUntil:'load'});
  await page.waitForTimeout(2500);
  const before=errors.length;

  /* Suntik journey produksi + shared doc bawaan aplikasi. */
  await page.evaluate(j=>{
    j.legacyShared117=sharedSnapshot117();
    localStorage.setItem('rm-v11-1-journey',JSON.stringify({...j,storageRevision116:1}));
  },journey);
  phase='reload';
  await page.reload({waitUntil:'load'});
  await page.waitForTimeout(2500);
  console.log('errors boot:',before,'| total:',errors.length);
  const snaps=await page.evaluate(()=>window.__snaps||[]);
  console.log('snaps saat crash:',JSON.stringify(snaps));

  const state=await page.evaluate(()=>({
    appChildren:document.getElementById('app').childElementCount,
    recovery:document.documentElement.classList.contains('recovery117'),
    member:JSON.parse(localStorage.getItem('rm-v11-1-journey')||'{}').member,
    title:document.title,
    user:typeof state!=='undefined'?state.user:null,
    preview:typeof state!=='undefined'?state.preview:null,
    role:typeof ten!=='undefined'?ten.role:null,
    staffUser:typeof ten!=='undefined'?ten.staffUser116:null,
    staffCount:ten?.staff114?.users?.length??-1,
    peopleIds:typeof people!=='undefined'?people.map(p=>p.id):[],
    blocked:typeof Persistence117!=='undefined'?Persistence117.blocked:null,
    problems:typeof Persistence117!=='undefined'?Persistence117.problems:[],
    meOk:(()=>{try{return me()?.id}catch(e){return 'ERR:'+e.message}})(),
    personOk:(()=>{try{return person(state.user)?.id}catch(e){return 'ERR:'+e.message}})(),
    staffUsers:ten?.staff114?.users?.map(u=>u.id+':'+u.super)??[]
  }));

  let fails=0;
  const check=(name,ok,extra='')=>{console.log((ok?'PASS':'FAIL')+' '+name+(extra?' — '+extra:''));if(!ok)fails++;};
  check('aplikasi render (#app terisi)',state.appChildren>0,`children=${state.appChildren}`);
  check('bukan mode recovery',!state.recovery);
  check('pageerror kosong',errors.filter(e=>e.startsWith('pageerror')).length===0,'\n'+errors.slice(0,3).join('\n'));
  console.log('member aktif:',state.member,'| judul:',state.title);
  console.log('diag:',JSON.stringify({user:state.user,role:state.role,staffUser:state.staffUser,staffCount:state.staffCount,staffUsers:state.staffUsers,people:state.peopleIds.slice(0,8),meOk:state.meOk,personOk:state.personOk,blocked:state.blocked,problems:state.problems}));

  await browser.close();server.close();
  process.exit(fails?1:0);
})().catch(e=>{console.error('ERROR',e);process.exit(1)});
