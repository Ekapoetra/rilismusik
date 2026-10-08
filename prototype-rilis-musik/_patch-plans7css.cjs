const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

R('.plans-heading122{display:flex;justify-content:space-between;align-items:center;gap:30px;margin-bottom:16px}',
  '.plans-heading122{display:flex;flex-direction:column;align-items:center;gap:14px;margin-bottom:22px}');

s += `
.plans-bar122{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:20px;width:100%}
.plans-bar122>p{margin:0;text-align:left;max-width:none}
.plans-bar122 .current-package122{margin:0;flex-direction:row;align-items:center;justify-self:end;gap:8px}
.plans-bar122 .current-package122>span:last-child{max-width:none;text-align:right}
@media(max-width:900px){.plans-bar122{grid-template-columns:1fr;justify-items:center;gap:12px}.plans-bar122>p{text-align:center}.plans-bar122 .current-package122{justify-self:center}}
`;

fs.writeFileSync(f, s);
console.log('css ok');
