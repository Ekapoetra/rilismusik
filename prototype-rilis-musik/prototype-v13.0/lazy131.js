/* Muat-belakangan untuk berkas besar yang tidak dibutuhkan tampilan pertama:
   data bank/wilayah (RMDirectory) dan pembuat PDF (PDFLib) — ±1,4 MB dari
   ±4,1 MB. Peta (map-data.js) tetap dimuat awal karena dipakai Dashboard
   Super Admin. Setelah aplikasi tampil, keduanya diunduh di latar
   belakang (prefetchLazy131). Bila sebuah menu membutuhkannya lebih dulu,
   akses pertama memuatnya saat itu juga (sinkron) agar kode lama yang
   memakainya tanpa await tetap berjalan. Build standalone menyisipkan
   keduanya langsung (lihat build.cjs). */
'use strict';
const lazyFiles131={"RMDirectory":"directories-data.js","PDFLib":"pdf-lib.min.js"};
const lazyLog131={};

function lazyLoaded131(name){
  const d=Object.getOwnPropertyDescriptor(window,name);
  return !!d&&'value' in d;
}
function loadLazySync131(name){
  const file=lazyFiles131[name],x=new XMLHttpRequest();
  x.open('GET',file,false);x.send();
  if(x.status!==200&&x.status!==0)throw new Error('Gagal memuat '+file);
  (0,eval)(x.responseText+'\n//# sourceURL='+file);
}
for(const name of Object.keys(lazyFiles131)){
  Object.defineProperty(window,name,{
    configurable:true,enumerable:true,
    get(){
      lazyLog131[name]='on-demand';
      loadLazySync131(name);
      return lazyLoaded131(name)?Object.getOwnPropertyDescriptor(window,name).value:undefined;
    },
    // The real file assigns window.<name>=…; turn the accessor into plain data.
    set(value){Object.defineProperty(window,name,{value,writable:true,configurable:true,enumerable:true});},
  });
}
function prefetchLazy131(){
  for(const [name,file] of Object.entries(lazyFiles131)){
    if(lazyLoaded131(name))continue;
    const s=document.createElement('script');
    s.src=file;s.async=true;s.onload=()=>{lazyLog131[name]=lazyLog131[name]||'background';};
    document.head.append(s);
  }
}
