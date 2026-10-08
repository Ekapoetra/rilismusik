const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Slab pekat: kartu penuh gradasi kelas, teks putih, CTA pil putih */
.package-card122{background:linear-gradient(155deg,var(--package-dark),var(--package-light));border:0;color:#f4f8fb;box-shadow:0 20px 40px -22px var(--package-dark),0 2px 6px #0a2f4414}
.package-card122.current122{box-shadow:0 0 0 2.5px #fff,0 24px 46px -20px var(--package-dark)}
.plan-eyebrow122{color:#ffffff9e}
.package-head122>h2{color:#fff!important}
.package-head122>h2::after{background:#ffffff73}
.package-head122>p{color:#ffffffc9}
.plan-inc122{color:#ffffff8a}
.package-card122 li{color:#eef4f9}
.package-card122 li svg{color:#fff}
.pay-as-you-go122{color:#ffffffb0}
.offer-price122>strong{color:#fff}
.offer-price122>small{color:#ffffffa8}
.offer-price122>strong.price-pending122{color:#ffffffe6}
.package-card122 footer>small{color:#ffffff96}
.offer-savings122{color:#c8f2d6}
.package-cta122{background:#fff!important;color:var(--package-dark)!important;box-shadow:0 10px 20px -10px #0009}
.package-cta122:hover{filter:none;transform:translateY(-1px);box-shadow:0 14px 24px -10px #000a}
.package-card122 .current-cta122{background:#ffffff21!important;color:#fff!important;box-shadow:inset 0 0 0 1.5px #ffffff8c!important}
.package-head122 .your-plan122{background:#ffffff22!important;color:#fff!important;box-shadow:inset 0 0 0 1px #ffffff52!important}
.plan-period122{background:#ffffff26;box-shadow:inset 0 1px 3px #0003,inset 0 -1px 1px #ffffff2a}
.plan-period122>i{background:#fff;box-shadow:0 2px 6px #0004}
.plan-period122>button{color:#ffffffad}
.plan-period122>button[aria-pressed=true],.plan-period122>button.selected{color:var(--package-dark)}
.package-ghost122{overflow:hidden;border-radius:23px}
`;

fs.writeFileSync(f, s);
console.log('css ok');
