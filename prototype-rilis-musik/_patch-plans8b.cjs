const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// Scope switch kaca hanya di dalam kartu (switch grup di header tetap terang)
R('.plan-period122{background:#ffffff26;box-shadow:inset 0 1px 3px #0003,inset 0 -1px 1px #ffffff2a}',
  '.package-card122 .plan-period122{background:#ffffff26;box-shadow:inset 0 1px 3px #0003,inset 0 -1px 1px #ffffff2a}');
R('.plan-period122>i{background:#fff;box-shadow:0 2px 6px #0004}',
  '.package-card122 .plan-period122>i{background:#fff;box-shadow:0 2px 6px #0004}');
R('.plan-period122>button{color:#ffffffad}',
  '.package-card122 .plan-period122>button{color:#ffffffad}');
R('.plan-period122>button[aria-pressed=true],.plan-period122>button.selected{color:var(--package-dark)}',
  '.package-card122 .plan-period122>button[aria-pressed=true],.package-card122 .plan-period122>button.selected{color:var(--package-dark)}');

fs.writeFileSync(f, s);
console.log('css ok');
