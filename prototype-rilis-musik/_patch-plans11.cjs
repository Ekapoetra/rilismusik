const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// Judul bilingual (brand — sama dua bahasa, tapi tetap lewat T())
R(`fullscreen103('Rilis Musik Service Plans'`, `fullscreen103(T('Rilis Musik Service Plans','Rilis Musik Service Plans')`);

// Ghost Business harus masuk top-layer: tempel ke #dialog, bukan body
R(`document.body.appendChild(bizEl);bizEl.animate([{transform:'none',opacity:1},{transform:'translateX(56px)',opacity:0}],{duration:480,easing:'cubic-bezier(.22,.75,.15,1)'}).onfinish=()=>bizEl.remove()}`,
  `const dlg=document.getElementById('dialog')||document.body;dlg.appendChild(bizEl);bizEl.animate([{transform:'none',opacity:1},{transform:'translateX(56px)',opacity:0}],{duration:480,easing:'cubic-bezier(.22,.75,.15,1)'}).onfinish=()=>bizEl.remove()}`);

fs.writeFileSync(f, s);
console.log('js ok');

// Reset ke 1 Label setiap kali panel dibuka dari menu / studio
const f2 = 'prototype-v13.0/v122.js';
let s2 = fs.readFileSync(f2, 'utf8');
const a2 = `if(a==='plans'){plans10();return}`;
if (!s2.includes(a2)) throw new Error('NOT FOUND plans action');
s2 = s2.split(a2).join(`if(a==='plans'){ui122.group='single';plans10();return}`);
fs.writeFileSync(f2, s2);

let s3 = fs.readFileSync(f, 'utf8');
const a3 = `if(id==='v122-label')plans10();`;
if (!s3.includes(a3)) throw new Error('NOT FOUND studio plans');
s3 = s3.split(a3).join(`if(id==='v122-label'){ui122.group='single';plans10()}`);
fs.writeFileSync(f, s3);
console.log('reset ok');
