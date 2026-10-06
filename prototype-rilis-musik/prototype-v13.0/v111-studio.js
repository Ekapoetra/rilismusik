const scenes111=[['catalogue','label','Layanan · katalog, satuan & benefit'],['payment','label','Layanan · pembayaran rupiah'],['materials','label','Layanan · lengkapi bahan pada pesanan'],['queue','admin','Layanan · antrean & penanganan'],['draft','admin','Layanan · draft hasil pribadi petugas'],['result','label','Layanan · terima hasil atau minta revisi'],['revision','admin','Layanan · koreksi tanpa potongan revisi'],['resolution','super','Layanan · usulan penyelesaian'],['offer','label','Layanan · tinjau usulan pengembalian'],['refund','super','Layanan · catat pengembalian'],['settings','super','Layanan · konfigurasi & ketentuan'],['ui','super','UI · tema, tipografi & indikator'],['charts','super','Grafik · ringkasan, tooltip & tren']];
studioCatalog.unshift(...scenes111.map(([id,role,title])=>({id:'v111-'+id,role,version:'11.1',title:[title,title],description:['Alur layanan terhubung dan penyempurnaan UI bersama. Akun mengikuti kondisi yang dipilih.','Connected service workflow and shared UI. Account follows the selected scenario.']})));
const studioBefore111=studioStart;
studioStart=async function(id){
 document.querySelector('#service-drawer111')?.close();
 if(!id.startsWith('v111-'))return studioBefore111(id);
 const sc=scenes111.find(s=>'v111-'+s[0]===id);if(!sc)return;
 const scene=sc[0],visual=['ui','charts'].includes(scene);
 await studioBefore111(visual?'v106-dashboard':'v11-label');
 delete ten.addons111;Addons111.init(ten);
 Object.assign(ui111,{tab:'all',q:'',status:'all',service:'promo',release:'',track:''});
 if(visual){role102('super');state.page='dashboard';state.mode=scene==='charts'?'staff':'platform';}
 else{
  role102('label','awan');const m=member10();
  Object.assign(m,{active:true,contract:true,plan:scene==='payment'||['resolution','offer','refund'].includes(scene)?'Flex':'Pro',subscriptionEnd:'2027-09-28',onboardingSeen105:true,themeChosen106:true});
  const r=ten.releases.find(r=>r.member===ten.member)||fixture105('live');ui111.release=r.id;
  const c=Addons111.init(ten).catalogue[0];
  if(!['catalogue','settings'].includes(scene)){
   const oid=act111('create',{service:c.id,release:r.id,brief:'Siapkan materi promosi untuk rilisan ini. Gunakan cover katalog, judul dan nama artis yang tersedia.',catalogueVersion:Addons111.init(ten).version,quote:JSON.stringify(quote111(c,r.id))});
   const o=Addons111.init(ten).orders.find(o=>o.id===oid);
   const action=(k,p={})=>act111(k,{id:oid,version:o.version,...p});
   if(scene!=='payment'){
    if(o.status==='unpaid')action('pay',{checked:true});
    role102('admin');action('claim');
    if(scene==='materials')action('materials',{note:'Tambahkan satu kalimat ajakan dan tanggal publikasi yang diinginkan.'});
    else if(scene!=='queue'){
     action('start',{checked:true});
     if(['draft','result','revision'].includes(scene)){
      action('draft-result',{url:'https://example.com/hasil-demo',note:'Tautan contoh untuk memeriksa alur; bukan hasil layanan nyata.'});
      if(scene!=='draft'){
       action('send-result',{checked:true});
       if(scene==='revision'){role102('label','awan');action('revision',{note:'Nama artis pada hasil belum sesuai dengan data katalog.'});}
      }
     }
     if(['resolution','offer','refund'].includes(scene)){
      action('resolution',{note:'Hasil tidak dapat diselesaikan sesuai kebutuhan. Usulkan pengembalian biaya.'});
      if(scene!=='resolution'){
       role102('super');action('offer',{kind:'refund',amount:o.amount,note:'Seluruh biaya dikembalikan karena layanan tidak dapat dipenuhi.'});
       if(scene==='refund'){role102('label','awan');action('offer-accept');}
      }
     }
    }
   }
  }
  role102(sc[1],'awan');ui111.tab=scene==='catalogue'?'catalogue':scene==='settings'?'settings':'all';module102('addons');
 }
 studioSelected=id;save10();closeModal();render();window.scrollTo(0,0);
};
render();
