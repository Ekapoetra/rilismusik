/* Boot senyap — dimuat tepat setelah app.js. Judul tab ditahan selama boot
   (html.booting131) supaya tidak berganti V9 → V13.0 saat memuat; skrip
   penutup index.html memasang judul akhir. (Render tetap berjalan: sebagian
   lapisan lama langsung mengakses elemen hasil render.) */
'use strict';
const booting131=()=>document.documentElement.classList.contains('booting131');

(function(){
  const desc=Object.getOwnPropertyDescriptor(Document.prototype,'title');
  if(!desc||!desc.set)return;
  let pending=null;
  Object.defineProperty(document,'title',{configurable:true,
    get(){return desc.get.call(document);},
    set(value){if(booting131()){pending=value;return;}desc.set.call(document,value);}});
  window.flushTitle131=()=>{if(pending!==null){desc.set.call(document,pending);pending=null;}};
})();
