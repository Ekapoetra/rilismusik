const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Light mode: kartu non-aktif gradasi abu-abu (slate), bukan hitam */
:root:not([data-theme=dark]) .package-card122:not(.current122){background:linear-gradient(168deg,#5d6775,#3a424d);border-color:#ffffff22;box-shadow:0 18px 40px -26px #3a424d73}
`;

fs.writeFileSync(f, s);
console.log('css ok');
