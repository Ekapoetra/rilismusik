const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// Judul dialog jadi "Rilis Musik Service Plans"; eyebrow di body dihapus
R(`fullscreen103(T('Pilihan paket','Choose your plan')`, `fullscreen103('Rilis Musik Service Plans'`);
R(`<header class="plans-heading122"><small>RILIS MUSIK / \${T('PAKET LAYANAN','SERVICE PLANS')}</small><div class="plans-bar122">`,
  `<header class="plans-heading122"><div class="plans-bar122">`);

fs.writeFileSync(f, s);
console.log('js ok');
