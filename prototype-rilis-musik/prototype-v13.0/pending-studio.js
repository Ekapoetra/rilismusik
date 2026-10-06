const pendingScenes=[
 ['pending-bonus','super','Buat dan pratinjau bonus','Create and preview a bonus'],
 ['pending-claim','label','Bonus menunggu klaim','Bonus waiting to be claimed'],
 ['pending-expired','label','Batas klaim bonus terlewati','Bonus claim deadline passed'],
 ['pending-level','label','Pencapaian baru dan kredit hadiah','New achievement and reward credits'],
 ['pending-monitor','super','Saldo kredit dan kabar pencapaian','Credit balances and achievement news'],
 ['pending-cleanup','super','Perbarui data label lama','Update legacy label data'],
 ['pending-proposal','label','Konfirmasi koreksi rekening','Confirm a bank correction'],
 ['pending-document','label','Penyesuaian gambar identitas','Prepare an identity image'],
 ['pending-map','super','Sebaran wilayah member','Member locations'],
 ['pending-stale','super','Identitas berubah saat rekening diperiksa','Identity changed during bank review']
];
studioCatalog.unshift(...pendingScenes.map(([id,role,a,b])=>({id,role,version:'10.3',title:[a,b],description:['Coba alur baru pada akun yang sesuai.','Try the new flow with the relevant account.']})));
const pendingStudioBase=studioStart;
studioStart=async function(id){const scene=pendingScenes.find(x=>x[0]===id);if(!scene)return pendingStudioBase(id);await pendingStudioBase('overview');studioSelected=id;pendingInit();studioAccount(scene[1]);let open=()=>{};
 const m=member10();
 if(['pending-bonus','pending-claim','pending-expired'].includes(id)){ten.role='super';const bonusId=RM10.act(ten,'bonus_send',{member:m.id,amount:5,type:'temporary',message:'Ada 5 kredit untuk rilisanmu berikutnya.',requestId:'scene-'+id});ten.role=scene[1];if(id==='pending-bonus'){module102('monitor-pending');pendingUI.tab='bonuses';open=bonusForm;}else{if(id==='pending-expired')ten.now+=49*RM10.H;open=()=>bonusPopup(bonusId);}}
 if(['pending-level','pending-monitor'].includes(id)){ten.role='super';m.achievement={paid:34000000,earned:RM10.pending.levels.filter(l=>l.threshold<=34000000).map(l=>l.id),baseline:true,owner:m.id};RM10.act(ten,'emblem_update',{paid:35000000});ten.role=scene[1];if(id==='pending-monitor'){pendingUI.tab='achievements';module102('monitor-pending');}else open=()=>document.querySelector('[data-pending=achievement-popup]')?.click();}
 if(id==='pending-cleanup'){module102('cleanup-pending');open=()=>cleanupOpen(m.id);}
 if(id==='pending-proposal'){ten.role='super';RM10.act(ten,'cleanup_save',{base:RM10.pending.bankFingerprint(m),mode:'proposal',bank:{bank:'Bank Central Asia',holder:'Nara Pradana Putra',directoryBankId:'ojk-014'}});ten.role='label';open=cleanupProposalPending;}
 if(id==='pending-document'){m.active=false;m.application=null;open=()=>{documentBase106();document.querySelector('[data-pending=document-sample]').click();};}
 if(id==='pending-map'){const ids=['32','31','35','51','61'];ten.members.slice(0,5).forEach((m,i)=>{const p=RMDirectory.provinces.find(p=>p.id===ids[i]),r=RMDirectory.regencies.find(r=>r.parent===p.id),d=RMDirectory.districts.find(d=>d.parent===r.id);m.identity.location={provinceId:p.id,province:directoryTitle(p.name),regencyId:r.id,regency:directoryTitle(r.name),districtId:d.id,district:directoryTitle(d.name),complete:true};});}
 if(id==='pending-stale'){ten.role='label';RM10.act(ten,'bank_submit',{bank:'Bank Central Asia',number:'0007654321',holder:m.identity.person});ten.role='super';open=()=>{bankModal10(m.id);m.identity.person='Nara Pradana Putra';m.version++;};}
 save10();render();open();
};
const pendingStudioUIBase=studio8;
studio8=function(){pendingStudioUIBase();document.querySelector('.studio-pending')?.remove();};studio10=studio8;guide=studio8;
render();
