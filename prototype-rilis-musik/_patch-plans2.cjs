const fs = require('fs');
const file = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(file, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// 1) Kartu: header berwarna (badge+tagline+desc) + body netral; slider periode kembali ke kartu; Business dimmed saat '1 Label'
R(`<header>\${badge104(p.id)}\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}</header><h2>\${taglines[p.id]?.[0]||E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p>\${p.id==='Basic'?\`<div class="pay-as-you-go122">\${T('Layanan sesuai kebutuhan','Pay as you go')}</div>\`:\`<div class="plan-bill122">\${period==='month'?T('Tagihan per bulan','Billed monthly'):T('Tagihan per tahun','Billed annually')}</div>\`}<div class="offer-price122">\${offerPrice122(p,period)}</div><ul>\${featureRows122(p).map(x=>\`<li>\${icon('check')}<span>\${E(x)}</span></li>\`).join('')}</ul>`,
  `<div class="package-head122"><header>\${badge104(p.id)}\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}</header><h2>\${taglines[p.id]?.[0]||E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p></div><div class="package-body122">\${p.id==='Basic'?\`<div class="pay-as-you-go122">\${T('Layanan sesuai kebutuhan','Pay as you go')}</div>\`:planPeriod122(p.id,period)}<div class="offer-price122">\${offerPrice122(p,period)}</div><ul>\${featureRows122(p).map(x=>\`<li>\${icon('check')}<span>\${E(x)}</span></li>\`).join('')}</ul>`);

// 2) locked state: deklarasi + class + CTA berubah
R(`current=Packages122.tier(ten,m)===p.id,q=Packages122.quote(ten,p.id,period),`,
  `current=Packages122.tier(ten,m)===p.id,locked=ui122.group==='single'&&p.id==='Business',q=Packages122.quote(ten,p.id,period),`);

R(`class="package-card122 \${current?'current122':''}"`,
  `class="package-card122 \${current?'current122':''} \${locked?'locked122':''}"`);

// tutup package-body122 sebelum article; footer pindah ke dalam body
R(`<footer>\${B122(p.id==='Basic'?(current?T('Beli kredit','Buy credits'):T('Gunakan Basic','Use Basic')):current?T('Perpanjang paket','Renew plan'):T('Beralih ke '+p.name,'Switch to '+p.name),'plan-select',p.id,\`package-cta122 \${current?'current-cta122':''}\`)}\${p.id!=='Basic'&&!q?\`<small>\${T('Periode ini belum dapat dibeli.','This period cannot be purchased yet.')}</small>\`:''}</footer></article>`,
  `<footer>\${locked?B122(T('Lihat di Multi Label','See under Multi Label'),'plan-group','multi','package-cta122 locked-cta122'):B122(p.id==='Basic'?(current?T('Beli kredit','Buy credits'):T('Gunakan Basic','Use Basic')):current?T('Perpanjang paket','Renew plan'):T('Beralih ke '+p.name,'Switch to '+p.name),'plan-select',p.id,\`package-cta122 \${current?'current-cta122':''}\`)}\${p.id!=='Basic'&&!q?\`<small>\${T('Periode ini belum dapat dibeli.','This period cannot be purchased yet.')}</small>\`:''}</footer></div></article>`);

// 3) toolbar: buang field Periode global (kembali ke kartu), sisakan Kelola berlabel + catatan
R(`<div class="toolbar-field122"><small>\${T('Periode','Billing')}</small>\${planPeriod122('_all',period)}</div>`,
  ``);
R(`,period=ui122.periods.Pro||ui122.periods.Studio||'year';`, `;`);

fs.writeFileSync(file, s);
console.log('v122-packages.js re-patched');
