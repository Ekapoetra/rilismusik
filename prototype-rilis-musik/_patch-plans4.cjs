const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// Struktur kartu ala Genesis: eyebrow kelas -> nama besar -> subjudul | Termasuk + benefit | footer(periode+harga+CTA)
R(`<div class="package-head122">\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}<h2>\${E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p></div><div class="package-body122">\${p.id==='Basic'?\`<div class="pay-as-you-go122">\${T('Layanan sesuai kebutuhan','Pay as you go')}</div>\`:planPeriod122(p.id,period)}<div class="offer-price122">\${offerPrice122(p,period)}</div><ul>\${featureRows122(p).map(x=>\`<li>\${icon('check')}<span>\${E(x)}</span></li>\`).join('')}</ul><footer>`,
  `<div class="package-head122">\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}<small class="plan-eyebrow122">\${p.id==='Business'?T('Multi Label','Multi Label'):T('Satu Label','Single Label')}</small><h2>\${E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p></div><div class="package-body122"><small class="plan-inc122">\${T('Termasuk','Includes')}</small><ul>\${featureRows122(p).map(x=>\`<li>\${icon('check')}<span>\${E(x)}</span></li>\`).join('')}</ul><footer>\${p.id==='Basic'?\`<div class="pay-as-you-go122">\${T('Layanan sesuai kebutuhan','Pay as you go')}</div>\`:planPeriod122(p.id,period)}<div class="offer-price122">\${offerPrice122(p,period)}</div>`);

fs.writeFileSync(f, s);
console.log('card restructured');
