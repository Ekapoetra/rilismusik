const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const sel = ':root:not([data-theme=dark]) .package-card122:not(.current122)';

s += `
/* Light mode: kartu non-aktif gradasi abu terang→putih, konten gelap */
${sel}{background:linear-gradient(168deg,#f4f6f9,#dde2ea);border-color:#ffffff;box-shadow:0 18px 40px -26px #5a6b8c4d;color:#1e242c}
${sel} .plan-eyebrow122{color:#6d7885}
${sel} .package-head122>h2{color:#13181f!important}
${sel} .package-head122>p{color:#5b6673}
${sel} .plan-inc122{color:#7c8590}
${sel} li{color:#2c343e}
${sel} li svg{color:#13181f}
${sel} :is(.offer-price122>small,.pay-as-you-go122){color:#5b6673}
${sel} .offer-price122>strong{color:#13181f}
${sel} .offer-price122>strong.price-pending122{color:#3a434f}
${sel} footer>small{color:#7c8590}
${sel} .package-cta122{background:#13181f!important;color:#fff!important;box-shadow:0 10px 20px -12px #13181f55}
${sel} .package-cta122:hover{background:#2a323d!important;filter:none!important}
${sel} .plan-period122{background:#0c152214;box-shadow:inset 0 1px 3px #0c15221f}
${sel} .plan-period122>i{background:#13181f;box-shadow:0 2px 6px #13181f40}
${sel} .plan-period122>button{color:#5b6673}
${sel} .plan-period122>button[aria-pressed=true],${sel} .plan-period122>button.selected{color:#fff}
${sel} .your-plan122{background:#13181f!important;color:#fff!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
