const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Gelap netral + aksen: kartu charcoal seragam, kelas lewat aksen warna */
.package-card122{background:linear-gradient(168deg,#1d242d,#10151b);border:1px solid #ffffff12;color:#e8edf2;box-shadow:0 22px 42px -24px #000c,0 2px 6px #0a2f4420}
.package-card122.current122{box-shadow:0 0 0 2px color-mix(in srgb,var(--package-light) 70%,transparent),0 24px 46px -22px #000c}
.plan-eyebrow122{color:#8b96a3}
.package-head122>h2{color:var(--package-light)!important}
.package-head122>h2::after{background:linear-gradient(90deg,var(--package-dark),var(--package-light))}
.package-head122>p{color:#9aa7b4}
.plan-inc122{color:#79838f}
.package-card122 li{color:#d3dbe4}
.package-card122 li svg{color:var(--package-light)}
.pay-as-you-go122{color:#8b96a3}
.offer-price122>strong{color:#fff}
.offer-price122>small{color:#8b96a3}
.offer-price122>strong.price-pending122{color:#c3ccd6}
.package-card122 footer>small{color:#6d7885}
.offer-savings122{color:#9fd8ae}
.package-cta122{background:linear-gradient(120deg,var(--package-dark),var(--package-light))!important;color:#fff!important;box-shadow:0 10px 22px -10px color-mix(in srgb,var(--package-dark) 85%,#000)}
.package-card122 .current-cta122{background:#ffffff08!important;color:var(--package-light)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-light) 60%,transparent)!important}
.package-head122 .your-plan122{background:color-mix(in srgb,var(--package-light) 15%,transparent)!important;color:var(--package-light)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-light) 42%,transparent)!important}
.package-card122 .plan-period122{background:#ffffff0f;box-shadow:inset 0 1px 3px #0007}
.package-card122 .plan-period122>i{background:linear-gradient(135deg,var(--package-dark),var(--package-light));box-shadow:0 2px 6px #0008}
.package-card122 .plan-period122>button{color:#8b96a3}
.package-card122 .plan-period122>button[aria-pressed=true],.package-card122 .plan-period122>button.selected{color:#fff}
[data-theme=dark] .package-card122 .current-cta122{color:var(--package-light)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-light) 60%,transparent)!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
