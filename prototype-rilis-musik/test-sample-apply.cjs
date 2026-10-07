/* Smoke test terapan sample131: boot bersih → verifikasi domain terisi →
   screenshot halaman bisnis → reload (jalur applied() harus skip). */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const OUT='C:\\Users\\rotam\\AppData\\Local\\Temp\\sample-shots';
require('node:fs').mkdirSync(OUT,{recursive:true});
const PORT='4590';

(async()=>{
 const srv=spawn('node',['serve.cjs'],{cwd:__dirname,stdio:'pipe',env:{...process.env,PORT}});
 await new Promise(r=>setTimeout(r,1500));
 const browser=await chromium.launch();
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const errors=[];
 page.on('pageerror',e=>errors.push('PAGEERROR: '+e.message+'\n'+(e.stack||'').split('\n').slice(1,4).join('\n')));

 await page.goto('http://localhost:'+PORT+'/',{waitUntil:'domcontentloaded'});
 await page.waitForTimeout(1200);
 await page.evaluate(()=>localStorage.clear());
 await page.reload({waitUntil:'domcontentloaded'});
 await page.waitForTimeout(4500);

 const info=await page.evaluate(()=>({
  sample:ten.sample131,members:ten.members.length,releases:ten.releases.length,
  tickets:Tickets112.init(ten).tickets.length,
  withdrawals:ten.royalty107?Withdraw108.init(ten.royalty107).requests.length:0,
  batches:ten.royalty107?.batches.length||0,
  ledger:ten.royalty107?.ledger.length||0,
  v9:data.v9?.labels.length||0,tasks:data.tasks?.length||0,
 }));
 console.log('== INFO ==\n'+JSON.stringify(info,null,1));

 // daftar kontrol navigasi yang tersedia
 const ctrls=await page.evaluate(()=>[...document.querySelectorAll('[data-action],[data-ten],[data-id],[data-page]')].map(e=>({t:(e.innerText||'').trim().slice(0,40),a:e.dataset.action||'',d:e.dataset.id||''})).filter(x=>x.t).slice(0,80));
 const seen=new Set(),uniq=ctrls.filter(c=>!seen.has(c.t+c.a)&&seen.add(c.t+c.a));
 console.log('\n== CONTROLS ==');uniq.forEach(c=>console.log(` [${c.a||'-'}|${c.d||'-'}] ${c.t}`));

 // klik item sidebar berdasarkan teks
 const snap=async(label,shot)=>{
  const clicked=await page.evaluate(want=>{
   const els=[...document.querySelectorAll('a,button,[role=tab],[data-action],[data-ten]')];
   const el=els.find(e=>(e.innerText||'').trim()===want)||els.find(e=>(e.innerText||'').trim().startsWith(want));
   if(!el)return false;el.click();return (el.innerText||'').trim().slice(0,40);
  },label);
  await page.waitForTimeout(1300);
  const text=await page.evaluate(()=>(document.querySelector('#main')||document.body).innerText.slice(0,700));
  await page.screenshot({path:OUT+'\\'+shot+'.png'});
  console.log(`\n== ${shot} (klik:${clicked}) ==\n${text.slice(0,550)}`);
 };
 for(const [label,shot] of [['Rilisan','01-rilisan'],['Royalti','02-royalti'],['Penarikan','03-penarikan'],['Tiket','04-tiket'],['Manajemen Label','05-label']])await snap(label,shot);

 // reload — terapan harus di-skip, render tetap normal
 await page.reload({waitUntil:'domcontentloaded'});await page.waitForTimeout(4000);
 const after=await page.evaluate(()=>({members:ten.members.length,releases:ten.releases.length,applied:!!ten.sample131,report:window.SAMPLE131_REPORT?1:0}));
 console.log('\n== AFTER RELOAD == '+JSON.stringify(after));
 console.log('\n== ERRORS ('+errors.length+') ==');errors.slice(0,8).forEach(e=>console.log(e+'\n---'));
 await browser.close();srv.kill();
 process.exit(errors.length?1:0);
})().catch(e=>{console.error('FATAL',e);process.exit(1)});
