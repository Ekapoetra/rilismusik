const fs = require('fs');
const f = 'prototype-v13.0/v122-packages.js';
let s = fs.readFileSync(f, 'utf8');
const R = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.split(a).join(b); };

// a) Eyebrow: sentence case + badge paket kecil
R(`<small class="plan-eyebrow122">\${p.id==='Business'?T('Multi Label','Multi Label'):T('Satu Label','Single Label')}</small>`,
  `<div class="plan-eyebrow122"><span>\${p.id==='Business'?'Multi Label':'Single Label'}</span>\${badge104(p.id)}</div>`);

// b) Reset ke 1 Label saat panel dibuka baru (dialog belum menampilkan plans)
R(`plans10=function(){if(!isLabel10())return;modelPackages122();`,
  `plans10=function(){if(!isLabel10())return;const dlg=document.getElementById('dialog');if(!(dlg&&dlg.open&&dlg.classList.contains('plans-dialog122')))ui122.group='single';modelPackages122();`);

// c) Animasi keluar: geser kanan + fade
R(`bizEl.animate([{transform:'none',opacity:1},{transform:'translateY(16px) scale(.92)',opacity:0}],{duration:420,easing:'cubic-bezier(.22,.75,.15,1)'})`,
  `bizEl.animate([{transform:'none',opacity:1},{transform:'translateX(64px)',opacity:0}],{duration:440,easing:'cubic-bezier(.22,.75,.15,1)'})`);

fs.writeFileSync(f, s);
console.log('js ok');
