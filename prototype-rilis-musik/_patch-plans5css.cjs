const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };
const D = (a) => { if (!s.includes(a)) throw new Error('DEL NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(''); };

// Buang tint penuh -> kartu netral (editorial minimal)
D('.package-card122{background:linear-gradient(165deg,color-mix(in srgb,var(--package-light) 17%,var(--surface)),color-mix(in srgb,var(--package-dark) 12%,var(--surface)))}');
D('[data-theme=dark] .package-card122{background:linear-gradient(165deg,color-mix(in srgb,var(--package-dark) 38%,var(--surface)),color-mix(in srgb,var(--package-light) 16%,var(--surface)))}');
D('[data-theme=dark] .package-head122>h2{color:var(--package-light)}');
D('[data-theme=dark] .package-head122>p{color:color-mix(in srgb,var(--package-light) 62%,var(--muted))}');
D('[data-theme=dark] .plan-eyebrow122{color:color-mix(in srgb,var(--package-light) 78%,var(--muted))}');
D('.package-head122 .your-plan122{top:20px;right:20px;background:color-mix(in srgb,var(--package-dark) 10%,transparent);color:var(--package-dark);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-dark) 30%,transparent)}');
D('[data-theme=dark] .package-head122 .your-plan122{color:var(--package-light);background:color-mix(in srgb,var(--package-dark) 25%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-light) 45%,transparent)}');

// Pengetatan proporsi & kunci tinggi harga
R('.package-head122{position:relative;background:linear-gradient(135deg,var(--package-dark),var(--package-light));color:#fff;padding:26px 22px 24px}',
  '.package-head122{position:relative;color:inherit;padding:26px 24px 12px}');
R('.package-head122>h2{font-size:26px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;min-height:0;margin-bottom:9px;color:#fff}',
  '.package-head122>h2{font-size:clamp(30px,2.2vw,36px);font-weight:600;letter-spacing:-.02em;min-height:0;margin-bottom:0;color:var(--text)}');
R('.package-head122>p{color:#ffffffd4;font-size:12px;line-height:1.6;min-height:38px;margin-bottom:0}',
  '.package-head122>p{color:var(--muted);font-size:12px;line-height:1.6;min-height:0;margin-bottom:0}');
R('.offer-price122{min-height:0;margin-top:12px}',
  '.offer-price122{min-height:58px;margin-top:10px;justify-content:flex-start}');
R('.offer-price122>strong{font-size:31px}', '.offer-price122>strong{font-size:27px}');
R('.package-cta122{min-height:52px;border-radius:30px;font-size:13px;font-weight:600}',
  '.package-cta122{min-height:48px;border-radius:26px;font-size:13px;font-weight:600;background:var(--package-dark)!important}');
R('.package-body122{padding:8px 26px 26px}', '.package-body122{padding:6px 24px 24px}');
R('.plans122{max-width:1420px!important;margin:0 auto}', '.plans122{max-width:1160px!important;margin:0 auto}');

// Editorial: garis aksen di bawah nama + pill netral + animasi masuk Business
s += `
.package-head122>h2::after{content:'';display:block;width:38px;height:3px;border-radius:2px;background:linear-gradient(90deg,var(--package-dark),var(--package-light));margin-top:13px}
.package-head122 .your-plan122{top:22px;right:22px;background:color-mix(in srgb,var(--package-dark) 9%,transparent);color:var(--package-dark);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-dark) 28%,transparent)}
[data-theme=dark] .package-head122 .your-plan122{color:var(--package-light);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--package-light) 40%,transparent)}
.package-grid122.cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}
@keyframes card-enter122{from{opacity:0;transform:translateX(34px) scale(.97)}to{opacity:1;transform:none}}
.package-card122.enter122{animation:card-enter122 .5s var(--motion122) both}
@media(max-width:1250px){.package-grid122.cols-4{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:580px){.package-grid122.cols-4{grid-template-columns:1fr}}
`;

fs.writeFileSync(f, s);
console.log('css ok');
