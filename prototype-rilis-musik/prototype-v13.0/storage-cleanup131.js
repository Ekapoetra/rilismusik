/* Pembersih transisi: eksperimen hidrasi database (V13.1, dicabut) pernah
   menulis dokumen bertanda dataSource 'production-copy' ke localStorage.
   Dokumen itu tidak kompatibel dengan simulasi V13.0 — buang sebelum
   storage117 membacanya, pulihkan cadangan simulasi terakhir bila ada. */
(function(){
 'use strict';
 const journeyKey='rm-v11-1-journey',backupKey='rm-v11-7-last-good';
 const parse=k=>{try{return JSON.parse(localStorage.getItem(k))}catch{return null}};
 const foreign=d=>!!d&&typeof d==='object'&&d.dataSource==='production-copy';
 try{
  if(!foreign(parse(journeyKey)))return;
  const backup=parse(backupKey);
  if(backup&&!foreign(backup))localStorage.setItem(journeyKey,JSON.stringify(backup));
  else localStorage.removeItem(journeyKey);
  if(foreign(backup))localStorage.removeItem(backupKey);
 }catch{}
})();
