const fs = require('fs');

// 1. v9.js: ganti gelombang bulat -> segel oktagram (8 titik tajam, tepi cekung) persis contoh IG
const f9 = 'prototype-v13.0/v9.js';
let js = fs.readFileSync(f9, 'utf8');
const oldSeal = /function sealPath9\(\)\{[^}]*\}/;
if (!oldSeal.test(js)) throw new Error('seal fn not found');
const newSeal = `function sealPath9(){const N=8,R=11.5,V=8.7,P=(a,r)=>[(12+r*Math.cos(a)).toFixed(2),(12+r*Math.sin(a)).toFixed(2)];let d='M'+P(-Math.PI/2,R);for(let i=1;i<=N;i++){const t=-Math.PI/2+i*Math.PI/4,dip=t-Math.PI/8,[cx,cy]=P(dip,V*0.86),[vx,vy]=P(dip,V),[x,y]=P(t,R);d+='Q'+cx+' '+cy+' '+vx+' '+vy+'Q'+cx+' '+cy+' '+x+' '+y;}return d+'Z';}`;
js = js.replace(oldSeal, newSeal);
fs.writeFileSync(f9, js);
console.log('v9.js ok');

// 2. v122.css: badge Paket Anda -> uppercase + kontras netral kuat (slate solid)
const f122 = 'prototype-v13.0/v122.css';
let c122 = fs.readFileSync(f122, 'utf8');
const oldPill = /\[data-theme\] \.package-card122\.current122 \.your-plan122\{[^}]*\}(\[data-theme=dark\] \.package-card122\.current122 \.your-plan122\{[^}]*\})?/;
if (!oldPill.test(c122)) throw new Error('pill rule not found');
c122 = c122.replace(oldPill, `[data-theme] .package-card122.current122 .your-plan122{top:32px;right:26px;height:19px;padding:0 8px;display:inline-flex!important;align-items:center;justify-content:center;background:#3d4652!important;color:#fff!important;box-shadow:0 3px 8px -3px #3d465280!important;font-size:8.5px;font-weight:600;letter-spacing:.05em;line-height:1;border-radius:7px;text-transform:uppercase}`);
fs.writeFileSync(f122, c122);
console.log('v122.css ok');
