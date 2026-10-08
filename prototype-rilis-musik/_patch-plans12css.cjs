const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Bingkai gradasi: kartu ikut tema, tepi gradasi kelas — adaptif light & dark */
.package-card122{background:linear-gradient(var(--surface),var(--surface)) padding-box,linear-gradient(155deg,var(--package-dark),var(--package-light)) border-box;border:2px solid transparent;color:var(--text);box-shadow:0 14px 34px -20px color-mix(in srgb,var(--package-dark) 70%,transparent)}
.package-card122.current122{box-shadow:0 0 0 1.5px color-mix(in srgb,var(--package-light) 60%,transparent),0 20px 42px -20px color-mix(in srgb,var(--package-dark) 80%,transparent)}
.plan-eyebrow122{color:var(--muted)}
.package-head122>h2{color:var(--package-dark)!important}
.package-head122>h2::after{background:linear-gradient(90deg,var(--package-dark),var(--package-light))}
.package-head122>p{color:var(--muted)}
.plan-inc122{color:var(--muted)}
.package-card122 li{color:var(--text)}
.package-card122 li svg{color:var(--package-dark)}
.pay-as-you-go122{color:var(--muted)}
.offer-price122>strong{color:var(--text)}
.offer-price122>small{color:var(--muted)}
.offer-price122>strong.price-pending122{color:var(--text)}
.package-card122 footer>small{color:var(--muted)}
.offer-savings122{color:var(--green)}
.package-cta122{background:linear-gradient(120deg,var(--package-dark),var(--package-light))!important;color:#fff!important;box-shadow:0 10px 22px -12px var(--package-dark)}
.package-card122 .current-cta122{background:transparent!important;color:var(--package-dark)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-dark) 55%,transparent)!important}
.package-head122 .your-plan122{background:color-mix(in srgb,var(--package-dark) 10%,transparent)!important;color:var(--package-dark)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-dark) 30%,transparent)!important}
.package-card122 .plan-period122{background:var(--soft);box-shadow:inset 0 1px 3px #0c324818}
.package-card122 .plan-period122>i{background:linear-gradient(135deg,var(--package-dark),var(--package-light));box-shadow:0 2px 6px #0a2f4430}
.package-card122 .plan-period122>button{color:var(--muted)}
.package-card122 .plan-period122>button[aria-pressed=true],.package-card122 .plan-period122>button.selected{color:#fff}
[data-theme=dark] .package-head122>h2{color:var(--package-light)!important}
[data-theme=dark] .package-card122 li svg{color:var(--package-light)}
[data-theme=dark] .package-card122 .current-cta122{color:var(--package-light)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-light) 55%,transparent)!important}
[data-theme=dark] .package-head122 .your-plan122{color:var(--package-light)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-light) 42%,transparent)!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
