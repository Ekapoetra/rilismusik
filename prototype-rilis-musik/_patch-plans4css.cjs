const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
fs.appendFileSync(f, `
.package-card122{background:linear-gradient(165deg,color-mix(in srgb,var(--package-light) 13%,var(--surface)),color-mix(in srgb,var(--package-dark) 9%,var(--surface)))}
[data-theme=dark] .package-card122{background:linear-gradient(165deg,color-mix(in srgb,var(--package-dark) 38%,var(--surface)),color-mix(in srgb,var(--package-light) 16%,var(--surface)))}
.package-head122{background:none;color:inherit;padding:30px 26px 14px}
.package-head122>h2{font-size:clamp(34px,2.6vw,44px);font-weight:600;letter-spacing:-.02em;text-transform:none;line-height:1.05;color:var(--package-dark);margin-bottom:10px;min-height:0}
.package-head122>p{color:color-mix(in srgb,var(--package-dark) 68%,var(--muted));font-size:12.5px;line-height:1.6;min-height:0}
[data-theme=dark] .package-head122>h2{color:var(--package-light)}
[data-theme=dark] .package-head122>p{color:color-mix(in srgb,var(--package-light) 62%,var(--muted))}
.plan-eyebrow122{display:block;font-size:10px;letter-spacing:.15em;text-transform:uppercase;font-weight:600;color:color-mix(in srgb,var(--package-dark) 72%,var(--muted));margin-bottom:12px}
[data-theme=dark] .plan-eyebrow122{color:color-mix(in srgb,var(--package-light) 78%,var(--muted))}
.package-head122 .your-plan122{top:20px;right:20px;background:color-mix(in srgb,var(--package-dark) 10%,transparent);color:var(--package-dark);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-dark) 30%,transparent)}
[data-theme=dark] .package-head122 .your-plan122{color:var(--package-light);background:color-mix(in srgb,var(--package-dark) 25%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-light) 45%,transparent)}
.plan-inc122{display:block;font-size:10px;letter-spacing:.12em;text-transform:uppercase;font-weight:600;color:var(--muted);margin-bottom:8px}
.package-card122 li{font-size:13px}
.package-card122 ul{gap:12px;margin-bottom:20px}
.package-body122{padding:8px 26px 26px}
.package-card122 footer{gap:11px;padding-top:8px}
.offer-price122{min-height:0;margin-top:12px}
.offer-price122>strong{font-size:31px}
.package-cta122{min-height:52px;border-radius:30px;font-size:13px;font-weight:600}
`);
console.log('css appended');
