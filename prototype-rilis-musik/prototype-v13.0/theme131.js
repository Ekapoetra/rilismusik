/* v1.1 dev.3 — persentase metrik sebaris di samping angka.
   Kartu .metric124 menyimpan arah tren di .metric-trend125[data-trend]
   (up/down/flat, dihitung v125.js dari platformData6). Lapisan ini memindahkan
   persentasenya ke samping angka sebagai "+12% ↗" / "−8,1% ↘" / "0% →";
   gaya ada di theme131.css. */
'use strict';
const deltaArrow131={
  up:'<path d="M3.5 8.5l5-5M4.5 3.5h4v4"/>',
  down:'<path d="M3.5 3.5l5 5M8.5 4.5v4h-4"/>',
  flat:'<path d="M2.5 6h7M7 3.5 9.5 6 7 8.5"/>',
};
function decorate131(root=document){
  root.querySelectorAll('.metric124').forEach(card=>{
    if(card.querySelector('.delta131'))return;
    const trend=card.querySelector('.metric-trend125'),value=card.querySelector(':scope>strong');
    if(!trend||!value)return;
    const dir=['up','down','flat'].includes(trend.dataset.trend)?trend.dataset.trend:'flat';
    const pct=[...trend.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim().replace(/^[+−-]\s*/,'');
    if(!pct)return;
    const sign=dir==='up'?'+':dir==='down'?'−':'';
    const row=document.createElement('span');
    row.className='value-row131';
    value.before(row);row.append(value);
    row.insertAdjacentHTML('beforeend',`<span class="delta131" data-trend="${dir}" title="${T('Dibanding periode sebelumnya','Compared with the previous period')}">${sign}${E(pct)}<svg viewBox="0 0 12 12" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${deltaArrow131[dir]}</svg></span>`);
  });
}
/* v124-ui normalizeType124 membulatkan berat ke 300/400/600 lewat gaya inline
   !important — skala baru memakai 500 untuk angka, jadi 500 diterima apa adanya. */
normalizeType124=function(root=document){
  const targets=root.querySelectorAll('h1,h2,h3,h4,h5,h6,p,small,span,strong,b,label,button,a,th,td,dt,dd,legend,input,select,textarea,kbd,time,li,summary,figcaption');
  for(const el of targets){
    if(!el.isConnected||el.closest('svg,.coin104,.coin-face106,.coin-layer106'))continue;
    const style=getComputedStyle(el),weight=Number(style.fontWeight);
    const value=weight<350?300:weight<450?400:weight<575?500:600;
    if(weight!==value)el.style.setProperty('font-weight',String(value),'important');
    const badge=el.closest('.status111,.work-badge104,.condition8,.task-badge'),size=parseFloat(style.fontSize);
    if(size<12&&!badge&&!el.closest('.avatar,.mark,.profile-photo103,.notification-count,.package104,.plan9'))el.style.setProperty('font-size','12px','important');
  }
};
const renderBefore131=render;
render=function(){renderBefore131();decorate131();};
if(typeof enhanceUI124==='function'){
  const enhanceBefore131=enhanceUI124;
  enhanceUI124=function(root=document){enhanceBefore131(root);decorate131(root);};
}
