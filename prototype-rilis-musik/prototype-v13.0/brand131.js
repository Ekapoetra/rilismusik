/* Eksplorasi warna merek (dev). Palet dipilih di Studio Pratinjau dan disimpan
   per-browser (localStorage, kenyamanan pratinjau saja). Tanpa pilihan, tampilan
   tetap seperti sekarang. Gaya di brand131.css. */
'use strict';
const brandKey131='rm-accent131';
const brandPalettes131=[
  ['', 'Bawaan saat ini','Current default','linear-gradient(135deg,#0c4e7c,#087aa0 56%,#11b8af)'],
  ['blue','Biru','Blue','linear-gradient(135deg,#002658,#0873fb 56%,#87c4ff)'],
  ['violet','Violet','Violet','linear-gradient(135deg,#1e0b4f,#6d28d9 56%,#c4b5fd)'],
  ['lime','Lime','Lime','linear-gradient(135deg,#132b05,#65a30d 56%,#d9f99d)'],
  ['coral','Coral','Coral','linear-gradient(135deg,#45110a,#f04e2f 56%,#ffc4b0)'],
  ['teal','Teal','Teal','linear-gradient(135deg,#043a36,#0d9488 56%,#99f6e4)'],
  ['graphite','Grafit','Graphite','linear-gradient(135deg,#09090b,#52525b 56%,#e4e4e7)'],
];
function applyBrand131(id){
  const valid=brandPalettes131.some(p=>p[0]===id)?id:'';
  if(valid)document.documentElement.dataset.accent131=valid;else delete document.documentElement.dataset.accent131;
  try{valid?localStorage.setItem(brandKey131,valid):localStorage.removeItem(brandKey131);}catch{}
  document.querySelectorAll('.brand131-swatches button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.accent131===valid)));
}
try{applyBrand131(localStorage.getItem(brandKey131)||'');}catch{applyBrand131('');}

function brandPicker131(){
  const current=document.documentElement.dataset.accent131||'';
  return `<section class="brand131" aria-label="${T('Eksplorasi warna merek','Brand colour exploration')}"><h3>${T('Eksplorasi warna merek','Brand colour exploration')}</h3><p>${T('Coba palet untuk header, logo, progress dan aksen. Tersimpan di browser ini saja.','Try a palette for the header, logo, progress and accent. Saved in this browser only.')}</p><div class="brand131-swatches">${brandPalettes131.map(([id,a,b,sw])=>`<button type="button" data-accent131="${id}" aria-pressed="${id===current}" style="--sw:${sw}"><i aria-hidden="true"></i>${T(a,b)}</button>`).join('')}</div></section>`;
}
const studioBrand131=studio8;
studio8=function(){
  studioBrand131();
  const body=document.querySelector('#dialog .dialog-body');
  if(body&&!body.querySelector('.brand131'))(body.querySelector('.studio-current131')||body.firstElementChild)?.insertAdjacentHTML('beforebegin',brandPicker131());
};
studio10=studio8;guide=studio8;
document.addEventListener('click',e=>{
  const b=e.target.closest('.brand131-swatches button');if(!b)return;
  e.preventDefault();e.stopImmediatePropagation();
  applyBrand131(b.dataset.accent131);
},true);
