const fs = require('fs');

// 1. v9.js: ganti "✓" di .verify9 dengan SVG segel verifikasi gaya Instagram
const f9 = 'prototype-v13.0/v9.js';
let js = fs.readFileSync(f9, 'utf8');
const oldMark = `title="${'${'}t('Terverifikasi','Verified')}" aria-label="${'${'}t('Terverifikasi','Verified')}">✓</span>`;
const seal = `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m23 12-2.44-2.79.34-3.69-3.61-.82-1.89-3.2L12 2.96 8.6 1.5 6.71 4.69 3.1 5.5l.34 3.7L1 12l2.44 2.79-.34 3.7 3.61.82L8.6 22.5l3.4-1.47 3.4 1.46 1.89-3.19 3.61-.82-.34-3.69L23 12zm-9.16 3.57-4.24-4.24 1.41-1.41 2.83 2.83 5.66-5.66 1.41 1.41-7.07 7.07z"/></svg></span>`;
if (!js.includes(oldMark)) throw new Error('verify mark not found');
js = js.replace(oldMark, `title="${'${'}t('Terverifikasi','Verified')}" aria-label="${'${'}t('Terverifikasi','Verified')}">${seal}`);
fs.writeFileSync(f9, js);
console.log('v9.js ok');

// 2. v9.css: .verify9 -> segel biru dengan centang bolong (bukan lingkaran polos)
const fc = 'prototype-v13.0/v9.css';
let css = fs.readFileSync(fc, 'utf8');
const oldRule = '.verify9{display:inline-grid;place-items:center;background:#2377dc;color:white;border-radius:50%;width:16px;height:16px;font-size:10px}';
if (!css.includes(oldRule)) throw new Error('verify9 css not found');
css = css.replace(oldRule, '.verify9{display:inline-flex;align-items:center;color:#2377dc;vertical-align:middle}.verify9 svg{width:17px;height:17px;display:block}');
fs.writeFileSync(fc, css);
console.log('v9.css ok');

// 3. v122.css: your-plan122 -> seukuran & semodel badge paket (gradient pill kecil)
const f122 = 'prototype-v13.0/v122.css';
let c122 = fs.readFileSync(f122, 'utf8');
c122 += `
/* your-plan122: samakan dengan badge paket — pill gradient warna kelas, ukuran kecil */
.package-card122 .your-plan122{top:20px;right:20px;height:22px;padding:0 10px;display:inline-flex!important;align-items:center;justify-content:center;background:linear-gradient(125deg,var(--package-dark),var(--package-light))!important;color:#fff!important;box-shadow:0 4px 10px -4px color-mix(in srgb,var(--package-dark) 55%,transparent)!important;font-size:9.5px;font-weight:600;letter-spacing:.07em;line-height:1;border-radius:8px}
`;
fs.writeFileSync(f122, c122);
console.log('v122.css ok');
