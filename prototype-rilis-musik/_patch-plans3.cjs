const fs = require('fs');
const R = (f, a, b) => { let s = fs.readFileSync(f, 'utf8'); if (!s.includes(a)) throw new Error(f + ' NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); fs.writeFileSync(f, s); };

const JS = 'prototype-v13.0/v122-packages.js';

// 1) Card: nama paket jadi judul besar + subjudul pendukung; hapus badge chip & tagline; hapus locked
R(JS, `,locked=ui122.group==='single'&&p.id==='Business'`, ``);
R(JS, ` ${'${'}locked?'locked122':''}`, ``);
R(JS, `<div class="package-head122"><header>\${badge104(p.id)}\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}</header><h2>\${taglines[p.id]?.[0]||E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p></div>`,
      `<div class="package-head122">\${current?\`<span class="your-plan122">\${T('Paketmu','Your plan')}</span>\`:''}<h2>\${E(p.name)}</h2><p>\${taglines[p.id]?.[1]||E(p.notes)}</p></div>`);
R(JS, `<footer>\${locked?B122(T('Lihat di Multi Label','See under Multi Label'),'plan-group','multi','package-cta122 locked-cta122'):B122(`,
      `<footer>\${B122(`);

// 2) Filter: Business hanya di Multi Label
R(JS, `p.id==='Business':true));`, `p.id==='Business':p.id!=='Business'));`);

// 3) Heading dipusatkan; paket aktif jadi chip di bawah subjudul
R(JS, `<header class="plans-heading122"><div><small>RILIS MUSIK / \${T('PAKET LAYANAN','SERVICE PLANS')}</small><h1>\${T('Ruang untuk setiap langkahmu.','Room for every step.')}</h1><p>\${T('Pilih alat dan layanan yang paling sesuai dengan cara labelmu bekerja.','Choose the tools and services that fit the way your label works.')}</p></div><div class="current-package122">`,
      `<header class="plans-heading122"><small>RILIS MUSIK / \${T('PAKET LAYANAN','SERVICE PLANS')}</small><h1>\${T('Ruang untuk setiap langkahmu.','Room for every step.')}</h1><p>\${T('Pilih alat dan layanan yang paling sesuai dengan cara labelmu bekerja.','Choose the tools and services that fit the way your label works.')}</p><div class="current-package122">`);

// 4) Toolbar: hanya pill Kelola di tengah; buang label & catatan desain
R(JS, `<div class="plans-toolbar122"><div class="toolbar-fields122"><div class="toolbar-field122"><small>\${T('Kelola','Manage')}</small><div class="plan-period122`,
      `<div class="plans-toolbar122"><div class="plan-period122`);
{
  const s = fs.readFileSync(JS, 'utf8');
  const a = `</div></div><span class="design-note122">`;
  const i = s.indexOf(a);
  if (i < 0) throw new Error('design-note anchor missing');
  const j = s.indexOf('</span></div>', i + a.length);
  if (j < 0) throw new Error('design-note end missing');
  fs.writeFileSync(JS, s.slice(0, i) + `</div>` + s.slice(j + '</span></div>'.length));
}

// 5) Grid: kelas jumlah kolom
R(JS, `package-grid122 \${plans.length<4?'few122':''}`, `package-grid122 cols-\${plans.length}`);

// 6) Palet identitas kelas + migrasi warna default lama
const MODEL = 'prototype-v13.0/packages122-model.js';
R(MODEL, `function init(s,old){if(s.packages122)return s.packages122;
 const colors=[['#36576e','#7094ad'],['#096b80','#25b9a5'],['#075697','#19b6bd'],['#343587','#7876dc']];`,
 `function init(s,old){const DEF=[['#36576e','#7094ad'],['#096b80','#25b9a5'],['#075697','#19b6bd'],['#343587','#7876dc']],colors=[['#36576e','#7094ad'],['#0d4f3c','#2ea36b'],['#0b2f6e','#4f8ef7'],['#3d1673','#9761e8']];
 if(s.packages122){s.packages122.plans.forEach(p=>{const j=names.indexOf(p.id);if(j>=0&&JSON.stringify(p.colors)===JSON.stringify(DEF[j]))p.colors=colors[j].slice()});return s.packages122}`);

console.log('js patched');
