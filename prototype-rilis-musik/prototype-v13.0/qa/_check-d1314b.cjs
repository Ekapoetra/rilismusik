/* Verifikasi perbaikan: (a) sub-tab Paket & Layanan tampil penuh dari awal;
   (b) menu Pembaruan untuk admin & super; (c) tanpa header ganda di label. */
const { chromium } = require('playwright');
const BASE = 'http://localhost:8123/index.html';
let pass = 0, fail = 0;
const ok = (cond, name) => { if (cond) { pass++; console.log('  PASS', name); } else { fail++; console.log('  FAIL', name); } };

async function role(page, who) {
  await page.evaluate(r => role102(r), who);
  await page.waitForTimeout(400);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('  [pageerror]', e.message.slice(0, 140)));
  await page.goto(BASE, { waitUntil: 'load' });
  await page.waitForSelector('#app', { timeout: 15000 });
  await page.waitForTimeout(900);

  // === A. Super → Paket & Layanan: 4 sub-tab langsung terlihat ===
  await role(page, 'super');
  await page.evaluate(() => { ui104.settings = 'plans'; route115('packages'); });
  await page.waitForTimeout(500);
  let tabs = await page.$$eval('.settings-packages126 .switch104 button', bs => bs.map(b => b.textContent.trim()));
  console.log('  tabs@plans:', JSON.stringify(tabs));
  ok(tabs.some(t => /Paket layanan|Service plans/.test(t)), 'sub-tab Paket layanan ada');
  ok(tabs.some(t => /Harga layanan|Service pricing/.test(t)), 'sub-tab Harga layanan LANGSUNG ada (bug diperbaiki)');
  ok(tabs.some(t => /Kredit rilisan|Release credits/.test(t)), 'sub-tab Kredit rilisan ada');
  ok(tabs.some(t => /Aturan Penggunaan|Usage Rules/.test(t)), 'sub-tab Aturan Penggunaan LANGSUNG ada');

  // Klik Harga layanan → tabel harga tampil
  await page.evaluate(() => { ui104.settings = 'services'; render(); });
  await page.waitForTimeout(400);
  tabs = await page.$$eval('.settings-packages126 .switch104 button, .catalogue104 .switch104 button', bs => bs.map(b => b.textContent.trim()));
  ok(tabs.length >= 4, 'tab@services tetap 4');
  const svcVisible = await page.$eval('body', b => /Harga dasar 1 token|Base price per token|svc-|layanan/i.test(b.innerText));
  ok(svcVisible, 'konten Harga layanan tampil');

  // Klik Aturan Penggunaan → creditConfig11 tampil
  await page.evaluate(() => { ui104.settings = 'rules11'; render(); });
  await page.waitForTimeout(400);
  const rulesVisible = await page.$eval('body', b => /kredit harian|daily credits|Aturan/i.test(b.innerText));
  ok(rulesVisible, 'konten Aturan Penggunaan tampil');
  tabs = await page.$$eval('.settings-packages126 .switch104 button, .catalogue104 .switch104 button', bs => bs.map(b => b.textContent.trim()));
  console.log('  tabs@rules11:', JSON.stringify(tabs));
  ok(tabs.some(t => /Harga layanan|Service pricing/.test(t)), 'Harga layanan masih ada di tab Aturan');

  // === B. Menu Pembaruan untuk super ===
  await role(page, 'super');
  await page.waitForTimeout(400);
  const superBtn = await page.$('.side-scroll [data-action="v4-module"][data-id="updates"]');
  ok(!!superBtn, 'tombol Pembaruan ada di sidebar super');
  if (superBtn) {
    await superBtn.click();
    await page.waitForTimeout(500);
    const h1 = await page.$eval('body', b => (b.querySelector('.pagehead h1,.head107 h1,.heading115 h1,h1')?.textContent || '').trim());
    const items = await page.$$eval('.update-item131', n => n.length);
    console.log('  h1:', h1, '· items:', items);
    ok(/Pembaruan|Updates/i.test(h1), 'halaman Pembaruan super terbuka (h1 benar)');
    ok(items >= 15, 'konten guide ter-render (' + items + ' butir)');
  }

  // === C. Menu Pembaruan untuk admin ===
  await role(page, 'admin');
  await page.waitForTimeout(400);
  const adminBtn = await page.$('.side-scroll [data-action="v4-module"][data-id="updates"]');
  ok(!!adminBtn, 'tombol Pembaruan ada di sidebar admin');
  if (adminBtn) {
    await adminBtn.click();
    await page.waitForTimeout(500);
    const items = await page.$$eval('.update-item131', n => n.length);
    ok(items >= 15, 'halaman Pembaruan admin ter-render (' + items + ' butir)');
  }

  // === D. Label: tidak ada header ganda ===
  await role(page, 'label');
  await page.waitForTimeout(400);
  const lb = await page.$('.side-scroll [data-ten="page"][data-id="updates"]');
  if (lb) {
    await lb.click();
    await page.waitForTimeout(400);
    const heads = await page.$$eval('.pagehead', n => n.length);
    const h1s = await page.$$eval('.pagehead h1', n => n.map(x => x.textContent.trim()));
    console.log('  pageheads:', heads, '· h1:', JSON.stringify(h1s));
    ok(heads === 1, 'tepat satu pagehead di label (tanpa header ganda)');
  } else ok(false, 'tombol Pembaruan label tidak ditemukan');

  console.log(`\n${pass} lolos · ${fail} gagal`);
  await browser.close();
  process.exit(fail ? 1 : 0);
})();
