/* Simpan ditunda (dev.6): setiap save10() men-serialisasi ±7 MB data + dua
   structuredClone, dan dipanggil di hampir semua aksi — termasuk klik menu
   (save8 → save10), yang membuat INP 400–540 ms. Kini simpan ditunda 300 ms
   setelah aksi terakhir dan digabung; aksi di dalam atomic10 (transaksi
   dengan deteksi konflik + rollback) tetap menyimpan seketika. Simpan selalu
   dipaksa saat tab disembunyikan/ditutup. Galat simpan yang tertunda tetap
   diberitahukan lewat toast. */
'use strict';
let pendingSave131=0,syncSave131=0,flushing131=false;
const saveNow131=save10;
function flushSave131(){
  if(!pendingSave131)return;
  clearTimeout(pendingSave131);pendingSave131=0;
  // Lapisan lama dapat memanggil save10() lagi dari dalam rantai simpan —
  // selama flush, panggilan itu bagian dari simpan yang sama (bukan simpan baru).
  flushing131=true;
  try{saveNow131();}
  catch(error){
    console.warn('Simpan tertunda gagal',error);
    if(typeof toast==='function')toast(error&&error.message?error.message:T('Perubahan tidak tersimpan','Changes were not saved'));
  }finally{flushing131=false;}
}
save10=function(){
  if(flushing131)return;
  if(syncSave131>0){flushSave131();return saveNow131.apply(this,arguments);}
  if(pendingSave131)clearTimeout(pendingSave131);
  pendingSave131=setTimeout(flushSave131,300);
};
if(typeof atomic10==='function'){
  const atomicBase131=atomic10;
  atomic10=function(fn){syncSave131++;try{return atomicBase131(fn);}finally{syncSave131--;}};
}
const flushEvents131=()=>flushSave131();
addEventListener('pagehide',flushEvents131);
addEventListener('beforeunload',flushEvents131);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')flushSave131();});
