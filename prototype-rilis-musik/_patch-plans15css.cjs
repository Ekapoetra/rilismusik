const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');

s += `
/* Penyesuaian material: eyebrow netral + badge, aksen atas pada kartu aktif, hover kontras tanpa gerak */
.plan-eyebrow122{display:inline-flex;align-items:center;gap:8px;text-transform:none;letter-spacing:.02em;font-size:11.5px;font-weight:500;color:var(--muted)}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .plan-eyebrow122{color:#79838f}
.package-card122.current122{box-shadow:0 18px 40px -26px #0a2f442e}
.package-card122[data-package122="Pro"].current122,.package-card122[data-package122="Business"].current122{box-shadow:0 24px 46px -24px #000a}
.package-card122.current122::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,var(--package-dark),var(--package-light));z-index:1}
.package-cta122:hover{transform:none!important;filter:brightness(1.13)!important;box-shadow:0 10px 20px -14px #0a2f4460}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-cta122:hover{background:#e7ebf0!important;filter:none!important}
.package-card122 .package-cta122.current-cta122:hover{background:color-mix(in srgb,var(--text) 8%,transparent)!important;filter:none!important}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-cta122.current-cta122:hover{background:#ffffff14!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
