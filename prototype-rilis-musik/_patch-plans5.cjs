const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// 1) Multi Label: Business masuk sebagai kartu ke-4 (bukan mengganti tampilan)
R(`p.id==='Business':p.id!=='Business'))`, `true:p.id!=='Business'))`);

// 2) Business dapat kelas animasi masuk saat multi aktif
R(`class="package-card122 \${current?'current122':''}"`,
  `class="package-card122 \${current?'current122':''} \${ui122.group==='multi'&&p.id==='Business'?'enter122':''}"`);

fs.writeFileSync(f, s);
console.log('js ok');
