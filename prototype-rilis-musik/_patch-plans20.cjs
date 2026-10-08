const fs = require('fs');

// 1. v9.js: ganti path lama dengan segel rosette IG-style (gelombang 12 lobus, biru, centang putih)
const f9 = 'prototype-v13.0/v9.js';
let js = fs.readFileSync(f9, 'utf8');
const oldSvg = `<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="m23 12-2.44-2.79.34-3.69-3.61-.82-1.89-3.2L12 2.96 8.6 1.5 6.71 4.69 3.1 5.5l.34 3.7L1 12l2.44 2.79-.34 3.7 3.61.82L8.6 22.5l3.4-1.47 3.4 1.46 1.89-3.19 3.61-.82-.34-3.69L23 12zm-9.16 3.57-4.24-4.24 1.41-1.41 2.83 2.83 5.66-5.66 1.41 1.41-7.07 7.07z"/></svg>`;
if (!js.includes(oldSvg)) throw new Error('old svg not found');
const newSvg = `<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#0095f6" d="${'${'}sealPath9()}"/><path d="M7.7 12.5l2.9 2.9 5.7-6.2" fill="none" stroke="#fff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
js = js.replace(oldSvg, newSvg);

// helper pembangkit path rosette — dipasang sebelum verificationMark9
const helper = `function sealPath9(){const d=[];for(let i=0;i<72;i++){const t=i/72*2*Math.PI,r=10+1.35*Math.cos(12*t);d.push((i?'L':'M')+(12+r*Math.cos(t)).toFixed(2)+' '+(12+r*Math.sin(t)).toFixed(2));}return d.join('')+'Z';}\n`;
js = js.replace('function verificationMark9(l)', helper + 'function verificationMark9(l)');
fs.writeFileSync(f9, js);
console.log('v9.js ok');

// 2. v9.css: ukuran ikon sedikit lebih besar
const fc = 'prototype-v13.0/v9.css';
let css = fs.readFileSync(fc, 'utf8');
css = css.replace('.verify9 svg{width:17px;height:17px;display:block}', '.verify9 svg{width:19px;height:19px;display:block}');
fs.writeFileSync(fc, css);
console.log('v9.css ok');

// 3. v122.css: your-plan122 -> lebih kecil + warna netral, sejajar baris badge (padding atas 30px)
const f122 = 'prototype-v13.0/v122.css';
let c122 = fs.readFileSync(f122, 'utf8');
const oldPill = /\[data-theme\] \.package-card122\.current122 \.your-plan122\{[^}]*\}/;
if (!oldPill.test(c122)) throw new Error('pill rule not found');
c122 = c122.replace(oldPill, `[data-theme] .package-card122.current122 .your-plan122{top:32px;right:26px;height:19px;padding:0 8px;display:inline-flex!important;align-items:center;justify-content:center;background:#56607050!important;color:#4a5462!important;box-shadow:none!important;font-size:8.5px;font-weight:600;letter-spacing:.08em;line-height:1;border-radius:7px}[data-theme=dark] .package-card122.current122 .your-plan122{background:#56607044!important;color:#8a95a5!important}`);
fs.writeFileSync(f122, c122);
console.log('v122.css ok');
