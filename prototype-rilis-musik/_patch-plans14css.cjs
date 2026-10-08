const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
s += `
.package-card122 .package-cta122.current-cta122{background:transparent!important;color:var(--text)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--text) 45%,transparent)!important}
.package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-cta122.current-cta122{background:transparent!important;color:#fff!important;box-shadow:inset 0 0 0 1.5px #ffffff4d!important}
[data-theme=dark] .package-card122 .package-cta122.current-cta122{color:var(--text)!important}
[data-theme=dark] .package-card122:is([data-package122="Pro"],[data-package122="Business"]) .package-cta122.current-cta122{color:#fff!important}
`;
fs.writeFileSync(f, s);
console.log('ok');
