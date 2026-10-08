const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };
const D = (a) => { if (!s.includes(a)) throw new Error('NOT FOUND del: ' + a.slice(0, 90)); s = s.split(a).join(''); };

// 1) Buang animasi hover kartu
D('.package-card122:hover{transform:translateY(-3px);box-shadow:0 12px 26px #04374b0b}');

// 2) Grid 3 kolom dasar + kelas kolom
R('.package-grid122{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}',
  '.package-grid122{display:grid;gap:16px;grid-template-columns:repeat(3,minmax(0,1fr))}');

// 3) Aturan head lama yang sudah tidak relevan (tidak ada <header> lagi) dibuang
D('.package-head122>header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:23px;min-height:28px}');
D('.package-head122>header{margin-bottom:16px}');
D('.package-head122 .package104{background:#ffffff30!important;color:#fff!important;box-shadow:inset 0 0 0 1px #ffffff50!important}');

// 4) Head: posisi relatif untuk pill Paketmu + ruang nama besar
R('.package-head122{background:linear-gradient(135deg,var(--package-dark),var(--package-light));color:#fff;padding:22px 22px 20px}',
  '.package-head122{position:relative;background:linear-gradient(135deg,var(--package-dark),var(--package-light));color:#fff;padding:26px 22px 24px}');
R('.package-head122>h2{color:#fff}',
  '.package-head122>h2{font-size:26px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;min-height:0;margin-bottom:9px;color:#fff}');
R('.package-head122>p{color:#ffffffd4;margin-bottom:0}',
  '.package-head122>p{color:#ffffffd4;font-size:12px;line-height:1.6;min-height:38px;margin-bottom:0}');
R('.package-head122 .your-plan122{background:#ffffff30;color:#fff;box-shadow:inset 0 0 0 1px #ffffff50}',
  '.package-head122 .your-plan122{position:absolute;top:16px;right:16px;background:#ffffff30;color:#fff;box-shadow:inset 0 0 0 1px #ffffff50}');

// 5) Buang aturan locked/few yang tidak dipakai lagi
D('.locked122{opacity:.55}');
D('.locked122:hover{transform:none;box-shadow:none}');
D('.locked-cta122{background:var(--soft)!important;color:var(--muted)!important;box-shadow:inset 0 0 0 1px var(--line)!important}');
R('.package-grid122.few122{grid-template-columns:repeat(auto-fit,minmax(270px,360px));justify-content:start}',
  '.package-grid122.cols-1{grid-template-columns:minmax(0,460px);justify-content:center}.package-grid122.cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}');

// 6) Heading + toolbar dipusatkan
s += `
.plans-heading122{flex-direction:column;align-items:center;text-align:center}
.plans-heading122 p{margin-left:auto;margin-right:auto}
.current-package122{flex-direction:row;align-items:center;justify-content:center;gap:10px;margin-top:15px}
.current-package122>span:last-child{text-align:left;max-width:none}
.plans-toolbar122{justify-content:center;align-items:center}
@media(max-width:1250px){.package-grid122.cols-3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:580px){.package-grid122.cols-3,.package-grid122.cols-2{grid-template-columns:1fr}}
`;

fs.writeFileSync(f, s);
console.log('css patched');
