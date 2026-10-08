const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// plan-group: jaga posisi scroll + animasi FLIP semua kartu saat jumlah kolom berubah
R(`if(a==='plan-group'){if(!isLabel10())return;ui122.group=id;plans10();return}`,
  `if(a==='plan-group'){if(!isLabel10())return;const grid=document.querySelector('.package-grid122'),body=document.querySelector('#dialog .dialog-body'),sc=body?.scrollTop||0,rects=grid?[...grid.children].map(c=>c.getBoundingClientRect()):[];ui122.group=id;plans10();const nb=document.querySelector('#dialog .dialog-body');if(nb)nb.scrollTop=sc;if(!matchMedia('(prefers-reduced-motion:reduce)').matches)document.querySelectorAll('.package-card122').forEach((c,i)=>{if(i>=rects.length)return;const r=c.getBoundingClientRect(),dx=rects[i].left-r.left,dy=rects[i].top-r.top;if(dx||dy)c.animate([{transform:\`translate(\${dx}px,\${dy}px)\`},{transform:'none'}],{duration:520,easing:'cubic-bezier(.22,.75,.15,1)'})});return}`);

fs.writeFileSync(f, s);
console.log('js ok');
