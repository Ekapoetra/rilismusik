const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Material berjenjang: permukaan membedakan kelas, bukan warna */
.package-card122{background:var(--surface);border:1px solid var(--line);color:var(--text);box-shadow:none}
.package-card122[data-package122="Studio"]{box-shadow:0 18px 40px -26px #0a2f4433}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]){background:linear-gradient(168deg,#1c232c,#0e1319);border-color:#ffffff14;color:#e8edf2}
.package-card122[data-package122="Business"]{box-shadow:inset 0 1px 0 #ffffff1f,0 24px 46px -24px #000a}
.package-card122.current122{box-shadow:0 0 0 1.5px var(--text)}
.package-card122[data-package122="Pro"].current122,.package-card122[data-package122="Business"].current122{box-shadow:0 0 0 1.5px #ffffffb0,0 24px 46px -24px #000a}
.plan-eyebrow122{color:var(--muted)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .plan-eyebrow122{color:#79838f}
.package-head122>h2{color:var(--text)!important}
.package-head122>h2::after{background:var(--text);opacity:.28}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-head122>h2{color:#fff!important}
.package-head122>p{color:var(--muted)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-head122>p{color:#93a0ad}
.plan-inc122{color:var(--muted)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .plan-inc122{color:#79838f}
.package-card122 li{color:var(--text)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) li{color:#d3dbe4}
.package-card122 li svg{color:var(--text)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) li svg{color:#fff}
.pay-as-you-go122,.offer-price122>small,.package-card122 footer>small{color:var(--muted)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) :is(.offer-price122>small,.pay-as-you-go122){color:#8b96a3}
.offer-price122>strong{color:var(--text)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .offer-price122>strong{color:#fff}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .offer-price122>strong.price-pending122{color:#c9d2dc}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) footer>small{color:#6d7885}
.package-cta122{background:var(--text)!important;color:var(--surface)!important;box-shadow:0 10px 20px -14px #0a2f4460}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-cta122{background:#fff!important;color:#13181f!important}
.package-card122 .current-cta122{background:transparent!important;color:var(--text)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--text) 45%,transparent)!important}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .current-cta122{color:#fff!important;box-shadow:inset 0 0 0 1.5px #ffffff4d!important}
.package-head122 .your-plan122{background:transparent!important;color:var(--text)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--text) 35%,transparent)!important}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .your-plan122{color:#fff!important;box-shadow:inset 0 0 0 1px #ffffff4d!important}
.package-card122 .plan-period122{background:var(--soft);box-shadow:inset 0 1px 3px #0c324818}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .plan-period122{background:#ffffff12;box-shadow:inset 0 1px 3px #0007}
.package-card122 .plan-period122>i{background:#fff;box-shadow:0 2px 6px #0a2f4433}
.package-card122 .plan-period122>button{color:var(--muted)}
.package-card122 .plan-period122>button[aria-pressed=true],.package-card122 .plan-period122>button.selected{color:#13181f}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .plan-period122>button{color:#8b96a3}
[data-theme=dark] .package-head122>h2{color:var(--text)!important}
[data-theme=dark] .package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-head122>h2{color:#fff!important}
[data-theme=dark] .package-card122 li svg{color:var(--text)}
[data-theme=dark] .package-card122:is([data-package122="Pro"],[data-package122="Business"]) li svg{color:#fff}
[data-theme=dark] .package-card122 .current-cta122{color:var(--text)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--text) 45%,transparent)!important}
[data-theme=dark] .package-card122:is([data-package122="Pro"],[data-package122="Business"]) .current-cta122{color:#fff!important;box-shadow:inset 0 0 0 1.5px #ffffff4d!important}
[data-theme=dark] .package-head122 .your-plan122{color:var(--text)!important;box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--text) 35%,transparent)!important}
[data-theme=dark] .package-card122:is([data-package122="Pro"],[data-package122="Business"]) .your-plan122{color:#fff!important;box-shadow:inset 0 0 0 1px #ffffff4d!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');

// Animasi keluar: menyusut + turun + fade (bukan terbang ke kanan)
const f2 = 'prototype-v13.0/v122-packages.js';
let s2 = fs.readFileSync(f2, 'utf8');
const a = `bizEl.animate([{transform:'none',opacity:1},{transform:'translateX(56px)',opacity:0}],{duration:480,easing:'cubic-bezier(.22,.75,.15,1)'})`;
if (!s2.includes(a)) throw new Error('NOT FOUND exit anim');
s2 = s2.split(a).join(`bizEl.animate([{transform:'none',opacity:1},{transform:'translateY(16px) scale(.92)',opacity:0}],{duration:420,easing:'cubic-bezier(.22,.75,.15,1)'})`);
fs.writeFileSync(f2, s2);
console.log('anim ok');
