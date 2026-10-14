/* Setelah tampil: simpan yang dipicu render digabung.
   Satu render menjalankan puluhan pembungkus yang masing-masing bisa memanggil
   save10() — tiap simpan men-serialisasi & menggandakan seluruh data. Saat
   render berlangsung, simpan ditunda lalu dijalankan sekali setelah jeda
   singkat. Simpan dari aksi pengguna (di luar render) tetap langsung —
   termasuk penanganan galat/konflik penyimpanannya. */
'use strict';
let renderDepth131=0,pendingSave131=0;
const saveNow131=save10;
function flushSave131(){
  if(!pendingSave131)return;
  clearTimeout(pendingSave131);pendingSave131=0;
  try{saveNow131();}catch(error){console.warn('Simpan tertunda gagal',error);}
}
save10=function(){
  if(renderDepth131>0){
    if(!pendingSave131)pendingSave131=setTimeout(flushSave131,400);
    return;
  }
  flushSave131();
  return saveNow131.apply(this,arguments);
};
const renderBefore131p=render;
render=function(){
  renderDepth131++;
  try{return renderBefore131p.apply(this,arguments);}finally{renderDepth131--;}
};
addEventListener('pagehide',flushSave131);
document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')flushSave131();});
