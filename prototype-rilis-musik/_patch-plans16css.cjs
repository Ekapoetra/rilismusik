const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Genesis: semua kartu slab gelap; kartu "Paketmu" mutiara iridescent */
.package-card122{background:linear-gradient(168deg,#1c232c,#0e1319);border:1px solid #ffffff12;color:#e8edf2;box-shadow:0 18px 40px -26px #0a2f4459}
.package-card122 .plan-eyebrow122{color:#79838f}
.package-card122 .package-head122>h2{color:#fff!important}
.package-card122 .package-head122>p{color:#93a0ad}
.package-card122 .plan-inc122{color:#79838f}
.package-card122 li{color:#d3dbe4}
.package-card122 li svg{color:#fff}
.package-card122 :is(.offer-price122>small,.pay-as-you-go122){color:#8b96a3}
.package-card122 .offer-price122>strong{color:#fff}
.package-card122 .offer-price122>strong.price-pending122{color:#c9d2dc}
.package-card122 footer>small{color:#6d7885}
.package-card122 .package-cta122{background:#fff!important;color:#13181f!important;box-shadow:0 10px 20px -10px #0007}
.package-card122 .package-cta122:hover{background:#e7ebf0!important;filter:none!important}
.package-card122 .plan-period122{background:#ffffff12;box-shadow:inset 0 1px 3px #0007}
.package-card122 .plan-period122>button{color:#8b96a3}
.package-card122 .plan-period122>button[aria-pressed=true],.package-card122 .plan-period122>button.selected{color:#13181f}
.package-card122 .your-plan122{position:absolute;top:22px;right:22px;background:#fff!important;color:#13181f!important;box-shadow:none!important;font-weight:600;letter-spacing:.04em}

/* Kartu aktif: mutiara iridescent (dua tema) */
.package-card122.current122{background:linear-gradient(152deg,#e9eef7 0%,#faf0e8 34%,#eceefb 62%,#f6eaf3 100%);border:1px solid #ffffff;color:#161b22;box-shadow:0 24px 50px -22px #5a6b8c59,0 0 0 1px #ffffffb8}
.package-card122.current122::before{content:none}
.package-card122.current122 .plan-eyebrow122{color:#5b6673}
.package-card122.current122 .package-head122>h2{color:#13181f!important}
.package-card122.current122 .package-head122>h2::after{background:#13181f;opacity:.2}
.package-card122.current122 .package-head122>p{color:#5b6673}
.package-card122.current122 .plan-inc122{color:#7c8590}
.package-card122.current122 li{color:#2c343e}
.package-card122.current122 li svg{color:#13181f}
.package-card122.current122 :is(.offer-price122>small,.pay-as-you-go122){color:#5b6673}
.package-card122.current122 .offer-price122>strong{color:#13181f}
.package-card122.current122 .offer-price122>strong.price-pending122{color:#3a434f}
.package-card122.current122 footer>small{color:#7c8590}
.package-card122.current122 .package-cta122{background:#13181f!important;color:#fff!important;box-shadow:0 10px 20px -10px #13181f55}
.package-card122.current122 .package-cta122:hover{background:#2a323d!important;filter:none!important}
.package-card122.current122 .package-cta122.current-cta122{background:transparent!important;color:#13181f!important;box-shadow:inset 0 0 0 1.5px #13181f59!important}
.package-card122.current122 .package-cta122.current-cta122:hover{background:#13181f12!important}
.package-card122.current122 .plan-period122{background:#0c152226;box-shadow:inset 0 1px 3px #0c15221f}
.package-card122.current122 .plan-period122>button{color:#4c5663}
.package-card122.current122 .plan-period122>button[aria-pressed=true],.package-card122.current122 .plan-period122>button.selected{color:#fff}
.package-card122.current122 .plan-period122>i{background:#13181f}
.package-card122.current122 .your-plan122{background:#13181f!important;color:#fff!important;box-shadow:0 6px 14px -6px #13181f66!important}
[data-theme=dark] .package-card122.current122 .package-head122>h2{color:#13181f!important}
[data-theme=dark] .package-card122.current122 li{color:#2c343e}
[data-theme=dark] .package-card122.current122 li svg{color:#13181f}
[data-theme=dark] .package-card122.current122 .package-head122>p{color:#5b6673}
[data-theme=dark] .package-card122.current122 .offer-price122>strong{color:#13181f}
[data-theme=dark] .package-card122.current122 .package-cta122{background:#13181f!important;color:#fff!important}
[data-theme=dark] .package-card122.current122 .package-cta122.current-cta122{background:transparent!important;color:#13181f!important;box-shadow:inset 0 0 0 1.5px #13181f59!important}
[data-theme=dark] .package-card122.current122 .plan-period122>button[aria-pressed=true]{color:#fff}
[data-theme=dark] .package-card122.current122 .plan-period122>i{background:#13181f}
[data-theme=dark] .package-card122.current122 .your-plan122{background:#13181f!important;color:#fff!important;box-shadow:0 6px 14px -6px #13181f66!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
