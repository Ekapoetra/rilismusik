const fs = require('fs');

// 1. v9.js: segel rosette lebih tegas — lobus lebih dalam (amp 1.35 -> 1.7), tetap solid fill biru IG
const f9 = 'prototype-v13.0/v9.js';
let js = fs.readFileSync(f9, 'utf8');
const oldSeal = `function sealPath9(){const d=[];for(let i=0;i<72;i++){const t=i/72*2*Math.PI,r=10+1.35*Math.cos(12*t);d.push((i?'L':'M')+(12+r*Math.cos(t)).toFixed(2)+' '+(12+r*Math.sin(t)).toFixed(2));}return d.join('')+'Z';}`;
if (!js.includes(oldSeal)) throw new Error('seal fn not found');
js = js.replace(oldSeal, `function sealPath9(){const d=[];for(let i=0;i<96;i++){const t=i/96*2*Math.PI,r=9.9+1.7*Math.cos(12*t);d.push((i?'L':'M')+(12+r*Math.cos(t)).toFixed(2)+' '+(12+r*Math.sin(t)).toFixed(2));}return d.join('')+'Z';}`);
fs.writeFileSync(f9, js);
console.log('v9.js ok');

// 2. v122-packages.js: Paketmu -> Paket Anda / Your plan
const fp = 'prototype-v13.0/v122-packages.js';
let pk = fs.readFileSync(fp, 'utf8');
if (!pk.includes(`T('Paketmu','Your plan')`)) throw new Error('badge text not found');
pk = pk.replace(`T('Paketmu','Your plan')`, `T('Paket Anda','Your plan')`);
fs.writeFileSync(fp, pk);
console.log('v122-packages.js ok');

// 3. v122.css: pill lebih kecil, tanpa uppercase, letter-spacing normal, tetap netral
const f122 = 'prototype-v13.0/v122.css';
let c122 = fs.readFileSync(f122, 'utf8');
const oldPill = /\[data-theme\] \.package-card122\.current122 \.your-plan122\{[^}]*\}(\[data-theme=dark\] \.package-card122\.current122 \.your-plan122\{[^}]*\})?/;
if (!oldPill.test(c122)) throw new Error('pill rule not found');
c122 = c122.replace(oldPill, `[data-theme] .package-card122.current122 .your-plan122{top:32px;right:26px;height:19px;padding:0 8px;display:inline-flex!important;align-items:center;justify-content:center;background:#56607050!important;color:#4a5462!important;box-shadow:none!important;font-size:9px;font-weight:500;letter-spacing:0;line-height:1;border-radius:7px;text-transform:none}[data-theme=dark] .package-card122.current122 .your-plan122{background:#56607044!important;color:#8a95a5!important}`);
fs.writeFileSync(f122, c122);
console.log('v122.css ok');
