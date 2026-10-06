/* V12.9: a stable top bar, deliberate navigation and header geometry only. */
const Header129={defaults:{size:100,x:0,y:0},bounds:{size:[80,160],x:[-15,15],y:[-15,15]}};
function headerValue129(value){
 if(!value||Object.keys(value).length!==3||!Object.keys(Header129.bounds).every(k=>Number.isInteger(value[k])&&value[k]>=Header129.bounds[k][0]&&value[k]<=Header129.bounds[k][1]))throw Error(T('Ukuran atau posisi berada di luar jangkauan.','Size or position is outside the allowed range.'));
 return {size:value.size,x:value.x,y:value.y};
}
function headerConfig129(){
 const saved=system115().header129;
 try{if(saved?.schema===1&&Number.isSafeInteger(saved.version)&&saved.version>0)return {version:saved.version,value:headerValue129(saved.value)};}catch{}
 return {version:0,value:{...Header129.defaults}};
}
function headerGuard129(){
 staffGuard117();
 if(ten.role!=='super'||!super114()||ui114.preview||state.preview)throw Error(T('Tampilan hanya dapat diatur oleh Super Admin aktif.','Only an active Super Admin can change the appearance.'));
}
function saveHeader129(value,version){
 const next=headerValue129(value);
 return atomic10(()=>{
  headerGuard129();const previous=headerConfig129();
  if(previous.version!==version)throw Error(T('Pengaturan telah berubah. Muat ulang sebelum menerapkan.','Settings have changed. Reload before applying.'));
  if(JSON.stringify(previous.value)===JSON.stringify(next))return false;
  system115().header129={schema:1,version:previous.version+1,value:next};
  System115.log(system115(),actor115(),'header-layout','header',previous.value,next,'Ukuran dan posisi latar header diperbarui.',now115());
  return true;
 });
}
events115['header-layout']='Ukuran dan posisi header diperbarui';
Object.assign(fields115,{size:'Ukuran latar',x:'Posisi horizontal',y:'Posisi vertikal'});
const appearance129={draft:null,base:0,owner:null};
function appearanceDraft129(){
 const config=headerConfig129();
 if(!appearance129.draft||appearance129.owner!==state.user){appearance129.draft={...config.value};appearance129.base=config.version;appearance129.owner=state.user;}
 return appearance129.draft;
}
function geometry129(element,value){
 const props={'--header-scale129':String(value.size/100),'--header-x129':value.x+'%','--header-y129':value.y+'%'};
 for(const [key,v] of Object.entries(props))if(element.style.getPropertyValue(key)!==v)element.style.setProperty(key,v);
}
function appearancePage129(){
 const draft=appearanceDraft129();
 const scene=hero122().replace('dashboard-hero122 hero124','header-preview-content129').replace('<section ','<section inert ');
 return `<section class="appearance129"><div class="appearance-preview129"><div class="header-preview129" aria-label="${T('Pratinjau latar header','Header background preview')}">${atmospheric127}${scene}</div></div><form class="appearance-form129" data-appearance129><h2>${T('Latar header','Header background')}</h2>${[['size',T('Ukuran','Size')],['x',T('Posisi horizontal','Horizontal position')],['y',T('Posisi vertikal','Vertical position')]].map(([key,label])=>`<label for="header-${key}129"><span>${label}<output for="header-${key}129" data-output129="${key}">${draft[key]}%</output></span><input id="header-${key}129" name="${key}" type="range" min="${Header129.bounds[key][0]}" max="${Header129.bounds[key][1]}" step="1" value="${draft[key]}"></label>`).join('')}<p class="appearance-note129">${T('Berlaku untuk latar header seluruh akun, pada light dan dark mode.','Applies to the header background for all accounts, in light and dark mode.')}</p><p class="appearance-error129" role="alert" hidden></p><div class="appearance-actions129"><button type="button" class="btn" data-appearance-reset129>${T('Kembalikan isian','Reset entries')}</button><button type="submit" class="btn primary">${T('Terapkan','Apply')}</button></div></form></section>`;
}

// Public-page drafts stay stored. Company identity remains available separately
// because new invoices use it; applying identity never publishes other blocks.
tabs115.appearance=['Tampilan','Appearance'];tabs115.company=['Identitas Perusahaan','Company Identity'];
heading115=function(){
 const entries=[['appearance',tabs115.appearance],['company',tabs115.company],...Object.entries(tabs115).filter(([key])=>!['appearance','company','content','activity'].includes(key)),['activity',tabs115.activity]];
 const history=['navigation','procedures'].includes(ui115.tab)?B115(T('Riwayat versi','Version history'),'versions',ui115.tab,'small'):'';
 return `<header class="heading115"><h1>${T('Pengaturan Platform','Platform Settings')}</h1>${history}</header><nav class="switch104 tabs115" role="tablist" aria-label="${T('Bagian Pengaturan Platform','Platform Settings sections')}">${entries.map(([key,label])=>`<button type="button" role="tab" class="${key===ui115.tab?'active':''}" aria-selected="${key===ui115.tab}" data-s115="tab" data-id="${key}">${T(...label)}</button>`).join('')}</nav>`;
};
function companyPage129(){
 const area=area115('content'),company=area.published.company,draft=area.draft?.company,changed=draft&&JSON.stringify(company)!==JSON.stringify(draft);
 return `<section class="company129"><header><h2>${T('Identitas perusahaan','Company identity')}</h2>${B115(T('Ubah identitas','Edit identity'),'company','','small')}</header><dl>${[['name',T('Nama badan usaha','Company name')],['email','Email'],['phone',T('Telepon','Phone')],['address',T('Alamat','Address')]].map(([key,label])=>`<div><dt>${label}</dt><dd>${E(company[key]||'—')}</dd></div>`).join('')}</dl>${changed?`<div class="company-draft129"><span>${T('Perubahan identitas tersimpan sebagai draf.','Identity changes are saved as a draft.')}</span><button type="button" class="btn primary" data-company-review129>${T('Tinjau identitas','Review identity')}</button></div>`:''}<footer><p>${T('Dipakai pada dokumen baru. Dokumen yang telah diterbitkan tetap menggunakan identitas sebelumnya.','Used on new documents. Issued documents retain their original identity.')}</p>${B115(T('Riwayat versi','Version history'),'versions','content','text')}</footer></section>`;
}
const pageBefore129=page115;
page115=function(){
 if(!super114())return denied9();
 if(ui115.tab==='content')ui115.tab='appearance';
 if(!['appearance','company'].includes(ui115.tab))return pageBefore129();
 return `<div class="system-page115">${heading115()}<section class="tab-body115" role="tabpanel">${ui115.tab==='appearance'?appearancePage129():companyPage129()}</section></div>`;
};
const routeBefore129=route115;
route115=function(tab='appearance'){return routeBefore129(tab==='content'?'appearance':tab);};
function reviewCompany129(){
 headerGuard129();const area=area115('content');
 if(!area.draft)return;
 ui115.editor=null;ui115.dirty=false;
 drawer115(T('Tinjau identitas perusahaan','Review company identity'),`<form data-company-apply129 data-version="${area.version}" data-draft="${area.draftVersion}">${diffHtml115(System115.changed(area.published.company,area.draft.company))}<p>${T('Perubahan berlaku untuk dokumen baru.','Changes apply to new documents.')}</p><p class="appearance-error129" role="alert" hidden></p><div class="form-foot115"><button type="submit" class="btn primary">${T('Terapkan identitas','Apply identity')}</button></div></form>`);
}
window.addEventListener('input',event=>{
 const form=event.target.closest('[data-appearance129]');if(!form)return;
 const key=event.target.name;if(!Header129.bounds[key])return;
 appearanceDraft129()[key]=Number(event.target.value);
 form.querySelector(`[data-output129="${key}"]`).textContent=event.target.value+'%';
 geometry129(document.querySelector('.header-preview129'),appearance129.draft);
 form.querySelector('.appearance-error129').hidden=true;
},true);
window.addEventListener('click',event=>{
 const reset=event.target.closest('[data-appearance-reset129]'),company=event.target.closest('[data-company-review129]');
 if(!reset&&!company)return;event.preventDefault();event.stopImmediatePropagation();
 if(company){try{reviewCompany129();}catch(error){toast(error.message);}return;}
 const current=headerConfig129();appearance129.draft={...current.value};appearance129.base=current.version;render();
},true);
window.addEventListener('submit',event=>{
 const form=event.target;if(!form.matches('[data-appearance129],[data-company-apply129]'))return;
 event.preventDefault();event.stopImmediatePropagation();
 try{
  if(form.matches('[data-appearance129]')){
   const value=Object.fromEntries([...new FormData(form)].map(([key,v])=>[key,Number(v)]));
   saveHeader129(value,appearance129.base);appearance129.draft=null;render();toast(T('Ukuran dan posisi header diterapkan.','Header size and position applied.'));
  }else{
   headerGuard129();atomic115('publish',{area:'content',version:Number(form.dataset.version),draftVersion:Number(form.dataset.draft),blocks:['company'],note:'Identitas perusahaan diperbarui untuk dokumen baru.'});close115(true);render();toast(T('Identitas perusahaan diterapkan.','Company identity applied.'));
  }
 }catch(error){const message=form.querySelector('.appearance-error129');message.textContent=error.message;message.hidden=false;}
},true);

// Keep the atmospheric backdrop in the same clipped scene as the glass. The
// retained top bar has its own opaque, shadow-free surface on every route.
function decorate129(){
 const frame=document.querySelector('.masthead124'),inner=frame?.querySelector('.hero-inner124'),art=frame?.querySelector('.masthead-atmosphere127');
 if(inner&&art&&art.parentElement!==inner)inner.prepend(art);
 if(frame)geometry129(frame,headerConfig129().value);
 const preview=document.querySelector('.header-preview129');if(preview)geometry129(preview,appearanceDraft129());
 stamp129();fitSearch128();
}
let foldTimer129=0;
const heroBefore129=setHero124;
setHero124=function(expanded){
 const frame=document.querySelector('.masthead124');if(!frame?.querySelector('.hero-clip124')||ui124.expanded===expanded)return false;
 if(expanded&&!atTop125())return false;
 clearTimeout(foldTimer129);frame.classList.add('is-folding129');
 const changed=heroBefore129(expanded);
 const finish=()=>{frame.classList.remove('is-folding129');syncMasthead124();};
 foldTimer129=setTimeout(finish,matchMedia('(prefers-reduced-motion:reduce)').matches?0:340);
 return changed;
};

// Defer genuine route clicks until the greeting is folded. Replaying the same
// button preserves existing permission checks, confirmation and route handlers.
const navigation129={timer:0,pending:null,replay:false,settled:false};
function routeKey129(){return [ten.role,state.user,state.mode,state.page,v4.module].join('|');}
function isRouteButton129(button){
 return button.matches('[data-control126]:not([data-control126="menu"]),[data-action="nav"],[data-action="search-nav"],[data-action="v4-module"],[data-action="v4-home"],[data-action="mode"],[data-ten="page"],[data-u122="mode"],[data-u122="labels"],[data-u122="mywork"],[data-u122="monitor"],[data-u122="releases"]');
}
function sameRoute129(button){
 if(button.dataset.control126==='home')return state.page===(state.mode==='staff'?'overview':'dashboard');
 if(button.dataset.action==='v4-home')return state.mode==='platform'&&state.page==='dashboard';
 if(button.dataset.action==='nav')return button.dataset.page===state.page;
 if(button.dataset.action==='mode')return button.dataset.mode===state.mode;
 if(button.dataset.ten==='page')return button.dataset.id==='home'?state.page==='dashboard':state.page==='module'&&v4.module===button.dataset.id;
 if(button.dataset.u122==='mode')return button.dataset.id===state.mode;
 return false;
}
function scheduleRoute129(pending){
 navigation129.pending=pending;
 if(navigation129.timer)return;
 gesture125.direction=0;setHero124(false);
 navigation129.timer=setTimeout(()=>{
  const next=navigation129.pending;navigation129.timer=0;navigation129.pending=null;
  if(!next||next.route!==routeKey129()||next.button&&!next.button.isConnected)return;
  navigation129.replay=true;navigation129.settled=true;
  try{if(next.run)next.run();else next.button.click();}finally{navigation129.replay=false;navigation129.settled=false;}
 },340);
}
const controlBefore129=goControl126;
goControl126=function(id){
 if(!super114()||navigation129.replay||!document.querySelector('.masthead124.has-hero124')||!ui124.expanded&&!navigation129.pending||matchMedia('(prefers-reduced-motion:reduce)').matches)return controlBefore129(id);
 if(controlActive126(id)){clearTimeout(navigation129.timer);navigation129.timer=0;navigation129.pending=null;return controlBefore129(id);}
 scheduleRoute129({route:routeKey129(),run:()=>controlBefore129(id)});
};
function routeClick129(event){
 if(navigation129.replay||event.button>0||event.ctrlKey||event.metaKey||event.altKey)return;
 const button=event.target.closest('button');if(!button||!isRouteButton129(button))return;
 if(sameRoute129(button)){clearTimeout(navigation129.timer);navigation129.pending=null;navigation129.timer=0;return;}
 const frame=document.querySelector('.masthead124.has-hero124');
 if(!frame||!ui124.expanded&&!navigation129.pending||matchMedia('(prefers-reduced-motion:reduce)').matches)return;
 event.preventDefault();event.stopImmediatePropagation();
 scheduleRoute129({button,route:routeKey129()});
}
function stamp129(){
 document.title='Rilis Musik · V12.9';document.documentElement.dataset.release='12.9';
 document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>{if(e.textContent!=='V12.9')e.textContent='V12.9';});
 const footer=document.querySelector('.footer span');if(footer&&footer.textContent!=='RILIS MUSIK · V12.9')footer.textContent='RILIS MUSIK · V12.9';
}
stamp124=stamp129;stamp125=stamp129;stamp126=stamp129;stamp127=stamp129;stamp128=stamp129;
const enhanceBefore129=enhanceUI124;
enhanceUI124=function(root=document){enhanceBefore129(root);decorate129();};
const renderBefore129=render;
render=function(){document.body.classList.add('release129');renderBefore129();decorate129();if(navigation129.settled)document.querySelector('#main')?.classList.add('route-arrival129');syncMasthead124();};
const scenarios129=[['super','super','Header & perpindahan menu','Header & navigation'],['staff','super','Ruang Staff & kendali header','Staff workspace & header controls'],['admin','admin','Header seragam · Admin','Consistent header · Admin'],['label','label','Wawasan kaca · Label','Glass Insights · Label']];
studioCatalog.unshift(...scenarios129.map(([id,role,a,b])=>({id:'v129-'+id,role,version:'12.9',title:[a,b],description:['Header polos, perpindahan lembut, Wawasan kaca serta pengaturan ukuran dan posisi.','Plain header, smooth navigation, glass Insights and size and position settings.']})));
const studioBefore129=studioStart;
studioStart=async function(id){const scene=scenarios129.find(x=>'v129-'+x[0]===id);if(!scene)return studioBefore129(id);clearTimeout(navigation129.timer);navigation129.timer=0;navigation129.pending=null;appearance129.draft=null;await studioBefore129('v128-'+scene[0]);studioSelected=id;render();};
render();
