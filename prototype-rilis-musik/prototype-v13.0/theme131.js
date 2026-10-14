/* v1.1 dev.3 — persentase metrik sebaris di samping angka.
   Kartu .metric124 menyimpan arah tren di .metric-trend125[data-trend]
   (up/down/flat, dihitung v125.js dari platformData6). Lapisan ini memindahkan
   persentasenya ke samping angka sebagai "+12% ↗" / "−8,1% ↘" / "0% →";
   gaya ada di theme131.css. */
'use strict';
try{localStorage.removeItem('rm-accent131');}catch{} // sisa eksplorasi warna (dihapus dev.5)
const deltaArrow131={
  up:'<path d="M3.5 8.5l5-5M4.5 3.5h4v4"/>',
  down:'<path d="M3.5 3.5l5 5M8.5 4.5v4h-4"/>',
  flat:'<path d="M2.5 6h7M7 3.5 9.5 6 7 8.5"/>',
};
function compactMoney131(v){
  const id=state.lang==='id',nf=new Intl.NumberFormat(id?'id-ID':'en-US',{maximumFractionDigits:1});
  if(Math.abs(v)>=1e9)return 'Rp '+nf.format(v/1e9)+(id?' M':'B');
  if(Math.abs(v)>=1e6)return 'Rp '+nf.format(v/1e6)+(id?' jt':'M');
  return money(v);
}
function compactMoneyHTML131(v){
  // 'Rp 151,6 jt' → mata uang & satuan kecil-redup, angka tetap besar.
  const m=/^Rp (.+?)( jt| M|M|B)?$/.exec(compactMoney131(v));
  if(!m)return E(compactMoney131(v));
  return '<span class="cur131">Rp</span>'+E(m[1])+(m[2]?'<span class="unit131">'+E(m[2].trim())+'</span>':'');
}
function decorate131(root=document){
  root.querySelectorAll('.metric124').forEach(card=>{
    if(card.querySelector('.delta131'))return;
    const trend=card.querySelector('.metric-trend125'),value=card.querySelector(':scope>strong');
    if(!trend||!value)return;
    const dir=['up','down','flat'].includes(trend.dataset.trend)?trend.dataset.trend:'flat';
    const pct=[...trend.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join('').trim().replace(/^[+−-]\s*/,'');
    if(!pct)return;
    const sign=dir==='up'?'+':dir==='down'?'−':'';
    // Nominal besar diringkas di kartu (Rp 151,6 jt) agar persentase muat sebaris;
    // angka lengkap tetap di tooltip dan panel rincian.
    const data=platformData6.find(r=>r[0]===card.dataset.id);
    if(data&&data[5]&&Math.abs(data[3])>=1e6){value.title=value.textContent;value.innerHTML=compactMoneyHTML131(data[3]);}
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

/* Kartu metrik: rincian buka/tutup di bawah deretan kartu (menggantikan popup).
   Isi sama dengan popup lama (nilai periode ini vs sebelumnya + perubahan),
   ditambah selisih nominal dan batang perbandingan CSS. */
let metricOpen131=null;
function metricDetail131(id){
  const x=platformData6.find(r=>r[0]===id);if(!x)return '';
  const cur=x[3],prev=x[4],diff=cur-prev,pct=prev?diff/prev*100:0,max=Math.max(cur,prev)||1;
  const f=v=>x[5]?money(v):fmt(v),nf=new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1});
  const dir=diff>0?'up':diff<0?'down':'flat',sign=dir==='up'?'+':dir==='down'?'−':'';
  return `<div class="metric-detail131" data-metric="${E(id)}" role="region" aria-label="${E(T(x[1],x[2]))}">
    <div class="md-head131"><span>${E(T(x[1],x[2]))}</span><small>${E(T(x[6],x[7]))}</small></div>
    <div class="md-row131"><span>${T('Periode saat ini','Current period')}</span><i style="--w:${(cur/max*100).toFixed(1)}%"></i><strong>${f(cur)}</strong></div>
    <div class="md-row131 prev"><span>${T('Periode sebelumnya','Previous period')}</span><i style="--w:${(prev/max*100).toFixed(1)}%"></i><strong>${f(prev)}</strong></div>
    <p class="md-note131"><span class="delta131" data-trend="${dir}">${sign}${nf.format(Math.abs(pct))}%<svg viewBox="0 0 12 12" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${deltaArrow131[dir]}</svg></span><span>${T('Selisih','Difference')} ${sign}${f(Math.abs(diff))} · ${T('perbandingan dua periode, data simulasi.','comparison of two periods, preview data.')}</span></p>
  </div>`;
}
function placeMetricDetail131(root=document){
  // Idempoten: dipanggil dari render/enhance (termasuk via MutationObserver);
  // hanya mengubah DOM bila keadaannya memang berbeda, agar tidak memicu loop
  // pasang-copot yang mengulang animasi tanpa henti.
  const grid=root.querySelector?.('.platform6-grid');if(!grid)return;
  for(const card of grid.querySelectorAll('.metric124')){
    const want=String(card.dataset.id===metricOpen131);
    if(card.getAttribute('aria-expanded')!==want)card.setAttribute('aria-expanded',want);
  }
  const panels=[...grid.parentElement.querySelectorAll(':scope>.metric-detail131')];
  const valid=metricOpen131&&grid.querySelector(`.metric124[data-id="${metricOpen131}"]`);
  const current=panels.find(p=>p.dataset.metric===metricOpen131&&p.previousElementSibling===grid);
  if(valid&&current&&panels.length===1)return;
  panels.forEach(p=>p.remove());
  if(valid)grid.insertAdjacentHTML('afterend',metricDetail131(metricOpen131));
}
const decorateBefore131=decorate131;
decorate131=function(root=document){decorateBefore131(root);placeMetricDetail131(root===document?document:root);};
const actionBefore131=handleAction;
handleAction=async function(b){
  if(b.dataset.action==='v6-metric'&&b.dataset.id!=='withdraw'){
    const id=b.dataset.id;
    if(id==='royalty'&&!(ten.role==='super'&&typeof super114==='function'&&super114()))return;
    metricOpen131=metricOpen131===id?null:id;
    placeMetricDetail131();
    return;
  }
  return actionBefore131(b);
};
