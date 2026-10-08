const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const OUT='C:\\Users\\rotam\\AppData\\Local\\Temp\\sample-shots';
(async()=>{
 const srv=spawn('node',['serve.cjs'],{cwd:'C:\\Users\\rotam\\OneDrive\\Documents\\Devin AI\\rilismusik\\prototype-rilis-musik',stdio:'pipe',env:{...process.env,PORT:'4590'}});
 await new Promise(r=>setTimeout(r,1500));
 const b=await chromium.launch();
 const page=await b.newPage({viewport:{width:1440,height:1100}});
 page.on('pageerror',e=>console.log('PAGEERROR',e.message.slice(0,200)));
 await page.goto('http://localhost:4590/',{waitUntil:'domcontentloaded'});await page.waitForTimeout(3500);
 await page.evaluate(()=>{ten.role='label';ten.member='awan';document.documentElement.dataset.theme='light';plans10()});
 await page.waitForTimeout(900);
 await page.screenshot({path:OUT+'\\40-paket-fs-light.png'});
 // slider di dalam kartu Studio -> bulanan (update in-place, kartu lain tetap tahunan)
 await page.click('[data-package122="Studio"] [data-u122="plan-period"][data-period="month"]');
 await page.waitForTimeout(800);
 await page.screenshot({path:OUT+'\\41-paket-studio-monthly.png'});
 // multi label
 await page.click('[data-u122="plan-group"][data-id="multi"]');
 await page.waitForTimeout(700);
 await page.screenshot({path:OUT+'\\42-paket-multi.png'});
 // dark
 await page.evaluate(()=>{document.documentElement.dataset.theme='dark';ui122.group='single';plans10()});
 await page.waitForTimeout(700);
 await page.screenshot({path:OUT+'\\43-paket-dark.png'});
 // mobile
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>{plans10()});
 await page.waitForTimeout(700);
 await page.screenshot({path:OUT+'\\44-paket-mobile.png'});
 // verifikasi: halaman manajemen label (super) — ikon segel verifikasi
 await page.setViewportSize({width:1440,height:1100});
 await page.evaluate(()=>{document.querySelector('#dialog')?.close();document.documentElement.dataset.theme='light';state.user=people.find(p=>p.super).id;go('labels9','staff')});
 await page.waitForTimeout(900);
 await page.screenshot({path:OUT+'\\45-labels-verify.png'});
 // pengaturan tampilan: editor desain header (super)
 await page.evaluate(()=>{document.documentElement.dataset.theme='light';role102('super');route115('appearance')});
 await page.waitForTimeout(800);
 await page.screenshot({path:OUT+'\\46-appearance.png'});
 // geser slider ukuran -> dirty, tombol simpan aktif
 await page.locator('[data-edit130="size"]').fill('140');
 await page.waitForTimeout(400);
 await page.screenshot({path:OUT+'\\47-appearance-dirty.png'});
 console.log('shots done');
 await b.close();srv.kill();
})().catch(e=>{console.error(e);process.exit(1)});
