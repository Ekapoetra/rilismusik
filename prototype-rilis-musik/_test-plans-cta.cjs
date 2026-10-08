const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const OUT='C:\\Users\\rotam\\AppData\\Local\\Temp\\sample-shots';
(async()=>{
 const srv=spawn('node',['serve.cjs'],{cwd:'C:\\Users\\rotam\\OneDrive\\Documents\\Devin AI\\rilismusik\\prototype-rilis-musik',stdio:'pipe',env:{...process.env,PORT:'4591'}});
 await new Promise(r=>setTimeout(r,1500));
 const b=await chromium.launch();
 const page=await b.newPage({viewport:{width:1440,height:1100}});
 page.on('pageerror',e=>console.log('PAGEERROR',e.message.slice(0,200)));
 await page.goto('http://localhost:4591/',{waitUntil:'domcontentloaded'});await page.waitForTimeout(3500);
 await page.evaluate(()=>{ten.role='label';ten.member='awan';document.documentElement.dataset.theme='light';plans10()});
 await page.waitForTimeout(800);
 // klik "Beralih ke Studio" -> harus membuka alur invoice
 await page.click('[data-package122="Studio"] [data-u122="plan-select"]');
 await page.waitForTimeout(1200);
 const t=await page.evaluate(()=>document.querySelector('#dialog')?.innerText?.slice(0,400)||'NO DIALOG');
 console.log('AFTER-CLICK:\n'+t);
 await page.screenshot({path:OUT+'\\35-invoice.png'});
 await b.close();srv.kill();
})().catch(e=>{console.error(e);process.exit(1)});
