/* v1.1 dev.5 — detail kaca (gaya di glass131.css).
   1. Segitiga isi pada pil persentase (referensi) menggantikan panah diagonal.
   2. Nominal ringkas di kartu metrik: tooltip kaca berisi angka lengkap.
   3. Penanda ujung batang progress + tooltip "75,6% · Rp 75.000.000 dibayarkan". */
'use strict';
Object.assign(deltaArrow131,{
  up:'<path d="M6 2.4 10.4 9.2H1.6z"/>',
  down:'<path d="M6 9.6 1.6 2.8h8.8z"/>',
  flat:'<rect x="1.6" y="5.2" width="8.8" height="1.6" rx=".8"/>',
});

function glassDetails131(root=document){
  root.querySelectorAll('.metric124 .value-row131>strong[title]').forEach(v=>{
    v.dataset.tip131=v.title;v.setAttribute('aria-label',v.title);v.removeAttribute('title');
  });
  const meter=root.querySelector('.withdrawal127 .withdrawal-meter127');
  if(!meter)return;
  const track=meter.querySelector('.payout-track'),fill=track&&track.querySelector('i');
  if(!track||!fill||track.querySelector('.payout-mark131'))return;
  const pct=(meter.querySelector(':scope>div:first-child strong')||{}).textContent||'';
  const paid=(root.querySelector('.withdrawal127 .withdrawal-part127 strong')||{}).textContent||'';
  const tip=`${pct.trim()} · ${paid.trim()} ${T('dibayarkan','paid')}`.trim();
  track.insertAdjacentHTML('beforeend',`<b class="payout-mark131" style="--x:${E(fill.style.width||'0%')}" data-tip131="${E(tip)}" aria-hidden="true"></b>`);
}
const renderBeforeGlass131=render;
render=function(){renderBeforeGlass131();glassDetails131();};
if(typeof enhanceUI124==='function'){
  const enhanceBeforeGlass131=enhanceUI124;
  enhanceUI124=function(root=document){enhanceBeforeGlass131(root);glassDetails131(root===document?document:root);};
}
