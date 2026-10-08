// D13/D14 functional check — temporary QA script
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch();
 const page=await browser.newPage();
 const ok=[],fail=[];const t=(n,c)=>c?ok.push(n):fail.push(n);
 const errs=[];page.on('pageerror',e=>{errs.push(e.message);console.log('PAGEERR:',e.message.slice(0,200))});
 page.on('framenavigated',f=>{if(f===p_main(f))return;function p_main(x){return x===page.mainFrame()}if(p_main(f))console.log('NAV →',f.url())});
 page.on('response',r=>{if(r.url().includes('v131'))console.log('RESP',r.status(),r.url())});
 page.on('console',m=>{if(m.type()==='error'||m.type()==='warning')console.log('CONSOLE',m.type()+':',m.text().slice(0,300))});
 await page.goto('http://localhost:8123/index.html',{waitUntil:'load'});
 await page.waitForTimeout(800);
 console.log('typeof check:',await page.evaluate(()=>[typeof maintenancePage115,typeof updatesPage131,typeof windowEditor131].join(',')));
 if(errs.length)console.log('early PAGE ERRORS:',errs);

 // === D13: super membuka tab Pemeliharaan ===
 await page.evaluate(()=>{role102('super');route115('maintenance')});
 await page.waitForTimeout(400);
 t('tab pemeliharaan terbuka',await page.locator('.system-page115').count()===1&&await page.locator('.tabs115 button.active').textContent()==='Pemeliharaan');
 t('jendela MW-01 terdaftar',await page.locator('.list115 .row115').count()>=1);
 t('durasi tampil',(await page.locator('.row-copy115 small').first().textContent()).includes('jam'));

 // === editor jendela baru ===
 await page.click('[data-s115=window-new]');
 await page.waitForSelector('#system-drawer115 [data-editor115]');
 await page.fill('#system-drawer115 [name=title]','Uji pemeliharaan QA');
 const s=new Date(Date.now()+24*3600000),e=new Date(Date.now()+26*3600000);
 const iso=d=>new Date(d.getTime()+7*3600000).toISOString().slice(0,16);
 await page.fill('#system-drawer115 [name=startAt]',iso(s));
 await page.fill('#system-drawer115 [name=endAt]',iso(e));
 await page.check('#system-drawer115 [name=modules][value=payments]');
 await page.fill('#system-drawer115 [name=message]','Pembayaran ditutup sementara.');
 await page.click('#system-drawer115 button[type=submit]');
 await page.waitForTimeout(400);
 t('draf tersimpan + status draf',await page.locator('.config-status115').textContent().then(x=>x.includes('Draf tersimpan')));
 t('jendela baru di daftar',(await page.locator('.list115').textContent()).includes('Uji pemeliharaan QA'));

 // === tinjau & terapkan ===
 await page.click('[data-s115=review][data-id=maintenance]');
 await page.waitForSelector('[data-review115]');
 t('review menghitung perubahan',(await page.locator('.review-hero115 h3').textContent()).includes('perubahan'));
 await page.fill('[data-review115] [name=note]','Jadwal QA untuk verifikasi.');
 await page.click('[data-review115] button[type=submit]');
 await page.waitForTimeout(400);
 t('versi naik ke 2',(await page.locator('.config-status115').textContent()).includes('Versi 2'));

 // === aktifkan MW-01 manual → banner member ===
 await page.click('.list115 .row115[data-id="MW-01"]');
 await page.waitForSelector('#system-drawer115 [name=status]');
 await page.selectOption('#system-drawer115 [name=status]','active');
 await page.click('#system-drawer115 button[type=submit]');
 await page.waitForTimeout(300);
 await page.click('[data-s115=review][data-id=maintenance]');
 await page.fill('[data-review115] [name=note]','Mulai lebih awal untuk uji banner.');
 await page.click('[data-review115] button[type=submit]');
 await page.waitForTimeout(400);
 t('status berjalan di daftar',(await page.locator('.list115').textContent()).includes('Berjalan'));

 // === label melihat banner + menu Pembaruan ===
 await page.evaluate(()=>role102('label','embun'));
 await page.waitForTimeout(500);
 await page.evaluate(()=>{closeModal()});
 console.log('DBG windows:',await page.evaluate(()=>JSON.stringify(system115().areas.maintenance.published.windows.map(w=>({id:w.id,st:w.status,ms:maintState131(w)})))),'active:',await page.evaluate(()=>maintActive131().length),'bannerCount:',await page.locator('.maint-banner131').count());
 t('banner pemeliharaan tampil untuk label',await page.locator('.maint-banner131').count()>=1);
 const bc=await page.locator('.maint-banner131').count();
 t('pesan banner benar',bc>0&&(await page.locator('.maint-banner131').first().textContent()).includes('Peningkatan sistem pembayaran'));

 await page.click('[data-ten=page][data-id=updates]');
 await page.waitForTimeout(400);
 t('halaman Pembaruan terbuka',(await page.locator('#app').textContent()).includes('V1.0'));
 t('badge Baru/Berubah/Dihapus ada',(await page.locator('.status111').allTextContents()).join(' ').includes('Baru'));
 const updText=(await page.locator('#app').textContent()).toLowerCase();
 t('tidak menyebut fitur batal',!updText.includes('office')&&!updText.includes('3d'));

 // === bahasa Inggris ===
 await page.evaluate(()=>{ten.lang='en';state.lang='en';render()});
 await page.waitForTimeout(300);
 t('EN: judul Updates',(await page.locator('.pagehead, #app').first().textContent()).includes('Updates'));

 // === admin tidak bisa ke Sistem ===
 await page.evaluate(()=>{ten.lang='id';state.lang='id';role102('admin');module102('cms');render()});
 await page.waitForTimeout(400);
 t('admin ditolak dari Sistem',(await page.locator('#app').textContent()).includes('tidak tersedia')||await page.locator('.system-page115').count()===0);

 // === pratinjau tidak bermutasi ===
 const pubBefore=await page.evaluate(()=>JSON.stringify(system115().areas.maintenance.published.windows.length));
 await page.evaluate(()=>{role102('super');ui114.preview=true;route115('maintenance')});
 await page.waitForTimeout(300);
 await page.click('[data-s115=window-new]').catch(()=>{});
 const drawerOpen=await page.locator('#system-drawer115 [data-editor115]').count();
 if(drawerOpen){await page.fill('#system-drawer115 [name=title]','Preview coba');const s2=new Date(Date.now()+24*3600000),e2=new Date(Date.now()+26*3600000);await page.fill('#system-drawer115 [name=startAt]',iso(s2));await page.fill('#system-drawer115 [name=endAt]',iso(e2));await page.check('#system-drawer115 [name=modules][value=releases]');await page.fill('#system-drawer115 [name=message]','x');await page.click('#system-drawer115 button[type=submit]');await page.waitForTimeout(300);}
 const pubAfter=await page.evaluate(()=>JSON.stringify(system115().areas.maintenance.published.windows.length));
 t('preview tidak mengubah konfigurasi aktif',pubBefore===pubAfter);

 console.log('PASS:',ok.length,'/',ok.length+fail.length);
 ok.forEach(x=>console.log('  ✓',x));
 fail.forEach(x=>console.log('  ✗',x));
 if(errs.length)console.log('PAGE ERRORS:',errs.slice(0,5));
 await browser.close();
 process.exit(fail.length||errs.length?1:0);
})().catch(e=>{console.error('FATAL',e);process.exit(1)});
