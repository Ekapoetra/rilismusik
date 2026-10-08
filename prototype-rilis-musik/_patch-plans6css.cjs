const fs = require('fs');
const f = 'prototype-v13.0/v122.css';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// Kartu setinggi isinya (Basic tidak punya lubang kosong) + kedalaman halus
R('.package-grid122{display:grid;gap:16px;grid-template-columns:repeat(3,minmax(0,1fr))}',
  '.package-grid122{display:grid;gap:16px;grid-template-columns:repeat(3,minmax(0,1fr));align-items:start}');
R('.package-card122{border:1px solid var(--line);border-radius:23px;padding:0;overflow:hidden;display:flex;flex-direction:column;background:color-mix(in srgb,var(--surface) 92%,var(--soft));min-width:0;transition:transform .3s,box-shadow .3s;position:relative}',
  '.package-card122{border:1px solid var(--line);border-radius:23px;padding:0;overflow:hidden;display:flex;flex-direction:column;background:var(--surface);min-width:0;position:relative;box-shadow:0 1px 2px #0a2f440e,0 16px 34px -20px #0a2f4430}');

// Heading dirapatkan — space atas dimaksimalkan untuk kartu
R('.plans-heading122{display:flex;justify-content:space-between;align-items:center;gap:30px;margin-bottom:25px}',
  '.plans-heading122{display:flex;justify-content:space-between;align-items:center;gap:30px;margin-bottom:16px}');
R('.plans-heading122 h1{font-weight:500;font-size:34px;letter-spacing:-1.3px;margin:7px 0 9px}',
  '.plans-heading122 h1{font-weight:500;font-size:30px;letter-spacing:-1.1px;margin:5px 0 6px}');
R('.plans-toolbar122{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:22px}',
  '.plans-toolbar122{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:20px}');

// CTA paket aktif selalu terbaca (selector lebih kuat, posisi akhir file)
s += `
.plans-heading122 p{max-width:520px}
.current-package122{margin-top:10px}
.package-card122 .current-cta122{background:transparent!important;color:var(--package-dark)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-dark) 55%,transparent)!important}
[data-theme=dark] .package-card122 .current-cta122{color:var(--package-light)!important;box-shadow:inset 0 0 0 1.5px color-mix(in srgb,var(--package-light) 55%,transparent)!important}
`;

fs.writeFileSync(f, s);
console.log('css ok');
