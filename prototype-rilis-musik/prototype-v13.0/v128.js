/* V12.8: quiet controls, transparent insights and consistent process geometry. */
const normalizeStatusBefore128=normalizeStatus111;
const statusWords128=/^(aktif|active|nonaktif|inactive|menunggu aktivasi|awaiting activation|dalam pemeriksaan|under review|menunggu pembayaran|awaiting payment|berhasil|successful|paid|dibayarkan|gagal|failed|kedaluwarsa|expired|approved|disetujui|pending|draf|draft|ditampilkan|shown|disembunyikan|hidden|tersembunyi|draf berubah|draft changed|siap dikirim|ready to deliver|distribusi|distribution|tayang|live|ditunda|delayed|ditahan|held|perlu pemeriksaan|review required|perlu informasi|information needed|belum lengkap|incomplete|siap dikembalikan|ready to refund|pengembalian diproses|refund processing|dana dikembalikan|refunded|pemeriksaan selesai|review completed)$/i;
normalizeStatus111=function(root=document){
 normalizeStatusBefore128(root);
 root.querySelectorAll('.badge,.pill107,.ten-chip,.work-badge104,.task-badge,.condition8,.review-status-ui,.task-status,.module-status,.profile-status103').forEach(el=>{
  if(el.matches('.status111')||el.closest('.package104,.plan9,.coin104')||el.querySelector('.status111'))return;
  const label=el.textContent.trim();
  const explicit=el.matches('.pill107,.work-badge104,.task-badge,.condition8,.review-status-ui,.task-status,.module-status');
  if(!label||!explicit&&!statusWords128.test(label))return;
  el.classList.add('status111');
  el.dataset.tone=/^(aktif|active|berhasil|successful|paid|dibayarkan|approved|disetujui|tayang|live|dana dikembalikan|refunded|pemeriksaan selesai|review completed)$/i.test(label)?'green':/gagal|failed|kedaluwarsa|expired/i.test(label)?'red':/ditunda|delayed|ditahan|held|perlu|needed|incomplete|belum lengkap|draf berubah|draft changed/i.test(label)?'mustard':/nonaktif|inactive|draft|draf|hidden|disembunyikan|tersembunyi/i.test(label)?'neutral':badgeTone111(label,el);
 });
 root.querySelectorAll('.status111').forEach(el=>{
  const pulse=/^(prioritas|priority|lewat tenggat|overdue)$/i.test(el.textContent.trim());
  if(el.dataset.pulse126!==String(pulse))el.dataset.pulse126=String(pulse);
 });
};

// Preserve each workflow's own stages. Only terminal records complete the last
// station; a delivered release remains in Distribution until it is live.
const stepsBefore128=steps9;
steps9=function(x){
 const box=document.createElement('div');box.innerHTML=stepsBefore128(x);
 const release=RM10.getRelease(ten,x.id);
 if(x.stage==='done'||release&&['live','partial_closed'].includes(release.status))box.querySelectorAll('.step9').forEach(s=>{s.classList.remove('current');s.classList.add('done');});
 decorateSteps128(box);return box.innerHTML;
};
const decorateStepsBefore128=decorateSteps127;
const railResize128=new ResizeObserver(entries=>entries.forEach(({target})=>measureRail128(target)));
const observedRails128=new Set();
const shortStages128={Pemeriksaan:'Diperiksa','Siap dikirim':'Siap kirim','Menunggu pemeriksaan':'Antrean','Pemeriksaan berlangsung':'Diperiksa','Menunggu persetujuan':'Persetujuan','Menunggu respons Believe':'Believe','Ready to deliver':'Ready','Awaiting review':'Queued','Under review':'Review'};
function measureRail128(rail){
 if(!rail.isConnected)return;
 const style=getComputedStyle(rail),count=rail.querySelectorAll(':scope>.progress-step127').length;
 const inset=parseFloat(style.getPropertyValue('--rail-inset128'))||0,marker=parseFloat(style.getPropertyValue('--marker128'))||24;
 const track=Math.max(0,rail.getBoundingClientRect().width-2*inset-marker);
 const caption=Math.max(36,Math.min(160,track/Math.max(1,count-1)-10,2*inset+marker));
 const value=caption.toFixed(2)+'px';if(rail.style.getPropertyValue('--caption128')!==value)rail.style.setProperty('--caption128',value);
}
function decorateSteps128(root=document){
 decorateStepsBefore128(root);
 root.querySelectorAll('.progress-rail127').forEach(rail=>{
  rail.classList.add('progress-rail128');
  if(rail.matches('.steps9'))rail.querySelectorAll(':scope>.progress-step127').forEach(step=>{
   const caption=step.querySelector(':scope>small');if(!caption||caption.querySelector('.step-label-full128'))return;
   const full=caption.textContent.trim(),short=shortStages128[full];if(!short)return;
   step.setAttribute('aria-label',full);caption.title=full;
   const original=document.createElement('span');original.className='step-label-full128';original.textContent=full;
   const compact=document.createElement('span');compact.className='step-label-short128';compact.setAttribute('aria-hidden','true');compact.textContent=short;
   caption.replaceChildren(original,compact);
  });
  if(rail.isConnected){if(!observedRails128.has(rail)){observedRails128.add(rail);railResize128.observe(rail);}measureRail128(rail);}
 });
 for(const rail of observedRails128)if(!rail.isConnected){railResize128.unobserve(rail);observedRails128.delete(rail);}
}
decorateSteps127=decorateSteps128;

// The dedicated heading contains only its title and sections. Context actions
// stay with their content, retaining the same handlers and permissions.
function centerControl128(){
 if(!document.body.classList.contains('focus-controls127'))return;
 const main=document.querySelector('#main');if(!main||main.querySelector('.control-heading128'))return;
 const id=controls126.find(c=>controlActive126(c.id))?.id;
 const selectors=id==='access'?['.heading114','.tabs114']:id==='settings'?['.heading115','.tabs115']:['.pagehead','.tabs121'];
 const old=main.querySelector(selectors[0]),tabs=main.querySelector(selectors[1]);
 if(!old||!tabs)return;
 const title=old.querySelector('h1');if(!title)return;
 const actions=[...old.querySelectorAll('button')];
 const heading=document.createElement('header');heading.className='control-heading128';
 if(id==='finance')title.textContent=T('Pemantauan Keuangan','Financial Monitoring');
 heading.append(title,tabs);
 if(id==='finance'&&old.closest('.legacy-monitor121')){
  main.querySelector('.legacy-monitor121').before(heading);old.remove();
 }else old.replaceWith(heading);
 if(id==='access'){
  const filters=main.querySelector('.filters114');actions.forEach(b=>{b.classList.add('control-action128');filters?.append(b);});
 }else if(actions.length){
  const context=main.querySelector('.config-status115')||main.querySelector('.tab-body115');
  const group=document.createElement('div');group.className='control-context-actions128';group.append(...actions);context?.append(group);
 }
}
function fitSearch128(){
 const header=document.querySelector('.header.header124'),trigger=header?.querySelector('[data-action=search]');
 trigger?.querySelectorAll('kbd').forEach(e=>e.remove());
 const panel=header?.querySelector('.search-popover');if(!panel||!trigger)return;
 const h=header.getBoundingClientRect(),t=trigger.getBoundingClientRect(),left=Math.max(12,Math.min(t.left-h.left,h.width-280));
 panel.style.setProperty('--search-left128',left+'px');
 panel.style.setProperty('--search-width128',Math.min(520,h.width-left-16)+'px');
}
function decorate128(root=document){
 if(state.page==='dashboard'||state.page==='overview')root.querySelectorAll('#main [data-card="progress"]').forEach(card=>card.remove());
 fitSearch128();normalizeStatus111(root);decorateSteps128(root);centerControl128();stamp128();
}
function stamp128(){
 document.title='Rilis Musik · V12.8';document.documentElement.dataset.release='12.8';
 document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>{if(e.textContent!=='V12.8')e.textContent='V12.8';});
 const f=document.querySelector('.footer span');if(f&&f.textContent!=='RILIS MUSIK · V12.8')f.textContent='RILIS MUSIK · V12.8';
}
stamp124=stamp128;stamp125=stamp128;stamp126=stamp128;stamp127=stamp128;
const enhanceBefore128=enhanceUI124;
enhanceUI124=function(root=document){enhanceBefore128(root);decorate128(root);};
const renderBefore128=render;
render=function(){document.body.classList.add('release128');renderBefore128();decorate128();syncMasthead124();};
window.addEventListener('resize',fitSearch128,{passive:true});
const scenarios128=[['super','Header & dashboard · Super Admin','Header & dashboard · Super Admin'],['staff','Kendali & ruang Staff','Controls & Staff workspace'],['admin','Progress seragam · Admin','Consistent progress · Admin'],['label','Wawasan kaca · Label','Glass insights · Label']];
studioCatalog.unshift(...scenarios128.map(([id,a,b])=>({id:'v128-'+id,role:id==='staff'?'super':id,version:'12.8',title:[a,b],description:['Ikon ringkas, Wawasan transparan, indikator seragam dan progress dengan panjang tetap.','Compact icons, transparent Insights, consistent indicators and fixed-length progress.']})));
const studioBefore128=studioStart;
studioStart=async function(id){const s=scenarios128.find(s=>'v128-'+s[0]===id);if(!s)return studioBefore128(id);await studioBefore128('v127-'+s[0]);studioSelected=id;decorate128();};
render();
