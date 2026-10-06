/* V13.0: one continuous masthead, direct artwork editing and a centred team selector. */
const Header130={defaults:{size:100,x:0,y:0},bounds:{size:[50,220],x:[-50,50],y:[-50,50]},maxData:1200000};
const editor130={owner:null,base:0,draft:null,drag:null,token:0,busy:false,error:'',status:''};
function geometryValue130(value){
 if(!value||Object.keys(value).length!==3||!Object.keys(Header130.bounds).every(k=>Number.isInteger(value[k])&&value[k]>=Header130.bounds[k][0]&&value[k]<=Header130.bounds[k][1]))throw Error(T('Ukuran atau posisi berada di luar jangkauan.','Size or position is outside the allowed range.'));
 return {size:value.size,x:value.x,y:value.y};
}
function assetValue130(asset){
 if(asset?.kind==='builtin')return {kind:'builtin'};
 if(asset?.kind!=='image'||!['image/png','image/jpeg','image/webp'].includes(asset.mime)||typeof asset.data!=='string'||asset.data.length>Header130.maxData||!asset.data.startsWith('data:'+asset.mime+';base64,')||!/^[A-Za-z0-9+/]+=*$/.test(asset.data.slice(asset.data.indexOf(',')+1))||!Number.isInteger(asset.width)||!Number.isInteger(asset.height)||asset.width<1||asset.height<1||asset.width>2400||asset.height>2400||typeof asset.name!=='string'||asset.name.length>160)throw Error(T('Desain belum dapat dibaca. Gunakan gambar PNG, JPG, atau WebP.','The design could not be read. Use a PNG, JPG, or WebP image.'));
 const shade=Number.isFinite(asset.shade)&&asset.shade>=.14&&asset.shade<=.66?asset.shade:.66;
 return {kind:'image',mime:asset.mime,data:asset.data,width:asset.width,height:asset.height,name:asset.name,shade};
}
function config130(){
 const saved=system115().header130;
 try{if(saved?.schema===1&&Number.isSafeInteger(saved.version)&&saved.version>0)return {version:saved.version,value:geometryValue130(saved.value),asset:assetValue130(saved.asset)};}catch{}
 return {version:0,value:headerConfig129().value,asset:{kind:'builtin'}};
}
function summary130(config){return {size:config.value.size,x:config.value.x,y:config.value.y,design:config.asset.kind==='builtin'?'builtin':config.asset.name,width:config.asset.width||null,height:config.asset.height||null};}
function save130(next,version){
 const value=geometryValue130(next.value),asset=assetValue130(next.asset);
 return atomic10(()=>{
  headerGuard129();const previous=config130();
  if(previous.version!==version)throw Error(T('Desain telah berubah. Buka ulang Tampilan untuk memakai versi terbaru.','The design has changed. Reopen Appearance to use the latest version.'));
  if(JSON.stringify(previous.value)===JSON.stringify(value)&&JSON.stringify(previous.asset)===JSON.stringify(asset))return false;
  const config={schema:1,version:previous.version+1,value,asset};system115().header130=config;
  System115.log(system115(),actor115(),'header-design','header',summary130(previous),summary130(config),'Desain, ukuran, dan penempatan kartu header diperbarui.',now115());
  return true;
 });
}
events115['header-design']='Desain kartu header diperbarui';
function draft130(){
 if(editor130.owner!==state.user||!editor130.draft){const current=config130();editor130.owner=state.user;editor130.base=current.version;editor130.draft={value:{...current.value},asset:{...current.asset}};editor130.error='';editor130.status='';}
 return editor130.draft;
}
function active130(){return editor130.drag&&editor130.owner===state.user?editor130.draft:config130();}
function art130(element,config){
 if(!element)return;
 geometry129(element,config.value);
 element.classList.toggle('has-image130',config.asset.kind==='image');
 let image=element.querySelector(':scope>.header-image130');
 if(config.asset.kind==='image'){
  if(!image){image=document.createElement('img');image.className='header-image130';image.alt='';image.draggable=false;element.prepend(image);}
  if(image.getAttribute('src')!==config.asset.data)image.src=config.asset.data;
  element.style.setProperty('--image-shade130',config.asset.shade);
 }else image?.remove();
}
function editorGeometry130(){
 const stage=document.querySelector('.design-stage130'),draft=draft130();if(!stage)return;
 art130(stage.querySelector('.masthead-atmosphere127'),draft);
 const box=stage.querySelector('.design-selection130');
 for(const [key,value] of Object.entries(draft.value))box.style.setProperty('--design-'+key+'130',value);
 box.setAttribute('aria-label',T('Desain header. Gunakan tombol arah untuk memindahkan; Shift dan atas atau bawah untuk mengubah ukuran.','Header design. Use arrow keys to move; Shift and up or down to resize.'));
 stage.querySelectorAll('.design-handle130').forEach(handle=>{
  const [sx,sy]=handle.dataset.corner.split(',').map(Number),v=draft.value;
  handle.style.left=Math.max(2,Math.min(98,50+v.x+sx*v.size/2))+'%';
  handle.style.top=Math.max(4,Math.min(96,50+v.y+sy*v.size/2))+'%';
 });
 const status=document.querySelector('.design-status130');
 if(status){status.textContent=editor130.error||editor130.status||T('Tarik desain untuk memindahkan. Tarik sudut untuk mengubah ukuran.','Drag the design to move it. Drag a corner to resize.');status.classList.toggle('is-error130',!!editor130.error);}
 document.querySelector('[data-upload130]')?.toggleAttribute('disabled',editor130.busy);
}
appearancePage129=function(){
 const draft=draft130(),scene=hero122().replace('dashboard-hero122 hero124','design-content130').replace('<section ','<section inert ');
 const uploadIcon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></svg>';
 const homeIcon=`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">${controlIcons127.home}</svg>`;
 return `<section class="appearance130"><header class="design-heading130"><h2>${T('Kartu header saat ini','Current header card')}</h2><button type="button" class="btn" data-upload130>${uploadIcon}${T('Unggah desain baru','Upload new design')}</button><input type="file" data-file130 accept="image/png,image/jpeg,image/webp" hidden></header><div class="design-stage130" aria-describedby="design-status130">${atmospheric127}<div class="design-nav130" inert><span class="design-brand130">RM <b>RILIS MUSIK</b></span><span>${homeIcon}${icon('people')}${icon('settings')}</span><i>JR</i></div>${scene}<div class="design-selection130" tabindex="0" role="group" aria-describedby="design-status130"></div>${[[-1,-1],[1,-1],[-1,1],[1,1]].map(([sx,sy])=>`<button type="button" class="design-handle130" data-corner="${sx},${sy}" aria-label="${T('Ubah ukuran dari sudut','Resize from corner')} ${sx<0?T('kiri','left'):T('kanan','right')} ${sy<0?T('atas','top'):T('bawah','bottom')}"></button>`).join('')}</div><p id="design-status130" class="design-status130" role="status" aria-live="polite">${T('Tarik desain untuk memindahkan. Tarik sudut untuk mengubah ukuran.','Drag the design to move it. Drag a corner to resize.')}</p></section>`;
};
function finishEdit130(){
 try{save130(editor130.draft,editor130.base);const saved=config130();editor130.base=saved.version;editor130.draft={value:{...saved.value},asset:{...saved.asset}};editor130.error='';editor130.status=T('Perubahan tersimpan.','Changes saved.');}
 catch(error){const current=config130();editor130.draft={value:{...current.value},asset:{...current.asset}};editor130.base=current.version;editor130.error=error.message;editor130.status='';}
 editor130.drag=null;decorate129();editorGeometry130();
}
async function readDesign130(file){
 if(!file||!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>12*1024*1024||!file.size)throw Error(T('Pilih gambar PNG, JPG, atau WebP hingga 12 MB.','Choose a PNG, JPG, or WebP image up to 12 MB.'));
 const url=URL.createObjectURL(file),image=new Image();
 try{
  image.src=url;await image.decode();
  if(image.naturalWidth*image.naturalHeight>40000000)throw Error(T('Gambar terlalu besar. Gunakan desain dengan resolusi lebih kecil.','The image is too large. Use a smaller resolution.'));
  const factor=Math.min(1,2400/image.naturalWidth,2400/image.naturalHeight),canvas=document.createElement('canvas');
  canvas.width=Math.max(1,Math.round(image.naturalWidth*factor));canvas.height=Math.max(1,Math.round(image.naturalHeight*factor));
  const context=canvas.getContext('2d');context.drawImage(image,0,0,canvas.width,canvas.height);
  const sample=document.createElement('canvas');sample.width=40;sample.height=20;const sampleContext=sample.getContext('2d');sampleContext.drawImage(canvas,0,0,40,20);const pixels=sampleContext.getImageData(0,0,40,20).data;
  const linear=n=>{const value=n/255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;};let luminance=0;
  for(let i=0;i<pixels.length;i+=4)luminance=Math.max(luminance,(.2126*linear(pixels[i])+.7152*linear(pixels[i+1])+.0722*linear(pixels[i+2]))*pixels[i+3]/255);
  const shade=luminance>.4?.66:luminance>.15?.45:.18;
  let data=canvas.toDataURL('image/webp',.9);
  if(data.length>Header130.maxData)data=canvas.toDataURL('image/webp',.7);
  if(data.length>Header130.maxData){const smaller=document.createElement('canvas');smaller.width=Math.round(canvas.width*.67);smaller.height=Math.round(canvas.height*.67);smaller.getContext('2d').drawImage(canvas,0,0,smaller.width,smaller.height);data=smaller.toDataURL('image/webp',.7);canvas.width=smaller.width;canvas.height=smaller.height;}
  const mime=data.slice(5,data.indexOf(';'));
  return assetValue130({kind:'image',mime,data,width:canvas.width,height:canvas.height,name:file.name.slice(0,160),shade});
 }catch(error){if(error.message.startsWith('Gambar ')||error.message.startsWith('The image '))throw error;throw Error(T('Desain belum dapat dibaca. Coba gambar PNG, JPG, atau WebP lain.','The design could not be read. Try another PNG, JPG, or WebP image.'));}
 finally{URL.revokeObjectURL(url);}
}
window.addEventListener('change',async event=>{
 if(!event.target.matches('[data-file130]'))return;
 const file=event.target.files[0];event.target.value='';if(!file)return;
 const token=++editor130.token,owner=state.user,version=editor130.base,input=event.target;
 editor130.busy=true;editor130.error='';editor130.status=T('Membaca desain…','Reading the design…');editorGeometry130();
 try{
  headerGuard129();const asset=await readDesign130(file);
  if(token!==editor130.token||owner!==state.user||!input.isConnected)return;
  headerGuard129();save130({value:draft130().value,asset},version);
  editor130.draft=null;editor130.busy=false;render();editor130.status=T('Desain baru tersimpan.','New design saved.');editorGeometry130();
 }catch(error){if(token===editor130.token&&owner===state.user){editor130.error=error.message;editor130.status='';}}
 finally{if(token===editor130.token){editor130.busy=false;if(owner===state.user)editorGeometry130();}}
},true);
window.addEventListener('pointerdown',event=>{
 const stage=event.target.closest('.design-stage130');if(!stage||event.button>0||editor130.busy)return;
 const handle=event.target.closest('.design-handle130'),selection=stage.querySelector('.design-selection130');
 if(!handle&&!selection.contains(event.target))return;
 try{headerGuard129();}catch(error){editor130.error=error.message;editorGeometry130();return;}
 event.preventDefault();const draft=draft130();
 editor130.drag={pointer:event.pointerId,target:handle||selection,owner:state.user,x:event.clientX,y:event.clientY,rect:stage.getBoundingClientRect(),value:{...draft.value},corner:handle?.dataset.corner.split(',').map(Number)||null};
 editor130.error='';editor130.status='';editor130.drag.target.setPointerCapture(event.pointerId);stage.classList.add('is-editing130');
},true);
window.addEventListener('pointermove',event=>{
 const drag=editor130.drag;if(!drag||event.pointerId!==drag.pointer||drag.owner!==state.user)return;
 event.preventDefault();const dx=(event.clientX-drag.x)/drag.rect.width*100,dy=(event.clientY-drag.y)/drag.rect.height*100,v=drag.value;
 if(drag.corner){const [sx,sy]=drag.corner,size=Math.round(Math.max(50,Math.min(220,v.size+(sx*dx+sy*dy)/2))),change=size-v.size;editor130.draft.value={size,x:Math.round(Math.max(-50,Math.min(50,v.x+sx*change/2))),y:Math.round(Math.max(-50,Math.min(50,v.y+sy*change/2)))};}
 else editor130.draft.value={size:v.size,x:Math.round(Math.max(-50,Math.min(50,v.x+dx))),y:Math.round(Math.max(-50,Math.min(50,v.y+dy)))};
 editorGeometry130();art130(document.querySelector('.masthead124 .masthead-atmosphere127'),editor130.draft);
},true);
function endPointer130(event,cancel){
 const drag=editor130.drag;if(!drag||drag.pointer!==event.pointerId)return;
 if(drag.target.hasPointerCapture(event.pointerId))drag.target.releasePointerCapture(event.pointerId);
 document.querySelector('.design-stage130')?.classList.remove('is-editing130');
 if(cancel||drag.owner!==state.user){editor130.drag=null;editor130.draft=null;decorate129();editorGeometry130();return;}
 finishEdit130();
}
window.addEventListener('pointerup',event=>endPointer130(event,false),true);
window.addEventListener('pointercancel',event=>endPointer130(event,true),true);

// Keep the artwork behind both the navigation and the greeting, in one frame.
decorate129=function(){
 const frame=document.querySelector('.masthead124'),art=frame?.querySelector('.masthead-atmosphere127');
 if(frame&&art){let backdrop=frame.querySelector(':scope>.masthead-backdrop130');if(!backdrop){backdrop=document.createElement('div');backdrop.className='masthead-backdrop130';backdrop.setAttribute('aria-hidden','true');frame.prepend(backdrop);}if(art.parentElement!==backdrop)backdrop.append(art);art130(art,active130());}
 stamp130();fitSearch128();if(document.querySelector('.design-stage130'))editorGeometry130();
};
const routeBefore130=routeClick129;
routeClick129=function(event){
 const button=event.target.closest('button');
 if(button?.matches('[data-u122="mode"],[data-action="mode"]')){clearTimeout(navigation129.timer);navigation129.timer=0;navigation129.pending=null;return;}
 return routeBefore130(event);
};
function staffWrap130(){
 const board=document.querySelector('#main .staff-board122');if(!board)return null;
 if(!board.parentElement.classList.contains('staff-slide130')){const wrap=document.createElement('div');wrap.className='staff-slide130';board.before(wrap);wrap.append(board);}
 return board;
}
function selectStaff130(id,direction){
 if(!super114()||state.mode!=='staff'||state.page!=='overview')return;
 const users=staffList122(),current=selectedStaff122(),from=users.findIndex(u=>u.id===current?.id),to=users.findIndex(u=>u.id===id);if(to<0||to===from)return;
 const old=staffWrap130(),snapshot=old?.cloneNode(true),height=old?.getBoundingClientRect().height;
 ui122.staff=id;v7.staff=id;render();
 const board=staffWrap130();if(!board||!snapshot||matchMedia('(prefers-reduced-motion:reduce)').matches)return;
 const wrap=board.parentElement,sign=direction||Math.sign(to-from),duration=380,easing='cubic-bezier(.22,.75,.15,1)';
 snapshot.classList.add('staff-snapshot130');snapshot.setAttribute('aria-hidden','true');snapshot.inert=true;snapshot.querySelectorAll('[id]').forEach(e=>e.removeAttribute('id'));wrap.append(snapshot);
 const nextHeight=board.getBoundingClientRect().height;wrap.style.height=height+'px';wrap.dataset.sliding='true';
 const incoming=board.animate([{transform:`translateX(${sign*32}px)`,opacity:.1},{transform:'translateX(0)',opacity:1}],{duration,easing});
 const outgoing=snapshot.animate([{transform:'translateX(0)',opacity:1},{transform:`translateX(${-sign*32}px)`,opacity:0}],{duration:300,easing,fill:'forwards'});
 const size=wrap.animate([{height:height+'px'},{height:nextHeight+'px'}],{duration,easing,fill:'forwards'});
 Promise.allSettled([incoming.finished,outgoing.finished,size.finished]).then(()=>{snapshot.remove();if(wrap.isConnected){wrap.style.height='';delete wrap.dataset.sliding;size.cancel();}});
}
function cycleStaff130(direction){const users=staffList122(),current=selectedStaff122(),index=users.findIndex(u=>u.id===current?.id);if(users.length)selectStaff130(users[(index+direction+users.length)%users.length].id,direction);}
function interaction130(event){
 const upload=event.target.closest('[data-upload130]');
 if(upload){event.preventDefault();event.stopImmediatePropagation();try{headerGuard129();document.querySelector('[data-file130]')?.click();}catch(error){editor130.error=error.message;editorGeometry130();}return;}
 const button=event.target.closest('[data-u122="staff-select"],[data-u122="staff-prev"],[data-u122="staff-next"]');if(!button)return;
 event.preventDefault();event.stopImmediatePropagation();
 if(button.dataset.u122==='staff-select')selectStaff130(button.dataset.id);else cycleStaff130(button.dataset.u122==='staff-next'?1:-1);
}
function key130(event){
 if(event.altKey||event.ctrlKey||event.metaKey)return;
 const selection=event.target.closest('.design-selection130,.design-handle130');
 if(selection&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Escape'].includes(event.key)){
  event.preventDefault();event.stopImmediatePropagation();
  if(event.key==='Escape'){if(editor130.drag){editor130.drag=null;editor130.draft=null;decorate129();editorGeometry130();}return;}
  if(editor130.busy)return;
  try{headerGuard129();const draft=draft130(),value={...draft.value};
   if(event.shiftKey||selection.matches('.design-handle130'))value.size=Math.max(50,Math.min(220,value.size+(['ArrowUp','ArrowRight'].includes(event.key)?2:-2)));
   else if(event.key==='ArrowLeft'||event.key==='ArrowRight')value.x=Math.max(-50,Math.min(50,value.x+(event.key==='ArrowRight'?1:-1)));
   else value.y=Math.max(-50,Math.min(50,value.y+(event.key==='ArrowDown'?1:-1)));
   editor130.draft.value=value;finishEdit130();
  }catch(error){editor130.error=error.message;editorGeometry130();}
  return;
 }
 if(event.target.closest('.staff-carousel122')&&['ArrowLeft','ArrowRight'].includes(event.key)){
  event.preventDefault();event.stopImmediatePropagation();cycleStaff130(event.key==='ArrowRight'?1:-1);
  document.querySelector('.staff-choice122.selected')?.focus();
 }
}
let swipe130=null;
window.addEventListener('pointerdown',event=>{if(event.pointerType==='mouse'||!event.target.closest('.staff-slide130')||event.target.closest('button,input,select,a'))return;swipe130={id:event.pointerId,x:event.clientX,y:event.clientY};},{passive:true});
window.addEventListener('pointerup',event=>{if(!swipe130||swipe130.id!==event.pointerId)return;const dx=event.clientX-swipe130.x,dy=event.clientY-swipe130.y;swipe130=null;if(Math.abs(dx)>48&&Math.abs(dx)>Math.abs(dy)*1.5)cycleStaff130(dx<0?1:-1);},{passive:true});
window.addEventListener('pointercancel',()=>swipe130=null,{passive:true});

function stamp130(){
 document.title='Rilis Musik · V13.0';document.documentElement.dataset.release='13.0';
 document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>{if(e.textContent!=='V13.0')e.textContent='V13.0';});
 const footer=document.querySelector('.footer span');if(footer&&footer.textContent!=='RILIS MUSIK · V13.0')footer.textContent='RILIS MUSIK · V13.0';
}
stamp124=stamp130;stamp125=stamp130;stamp126=stamp130;stamp127=stamp130;stamp128=stamp130;stamp129=stamp130;
const renderBefore130=render;
render=function(){
 document.body.classList.add('release130');
 const frame=document.querySelector('.masthead124.has-hero124'),wasMode=document.body.classList.contains('staff-workspace122')?'staff':'platform';
 const switchWorkspace=!!frame&&wasMode!==state.mode&&['dashboard','overview'].includes(state.page)&&ui124.route?.startsWith(ten.role+'|');
 if(switchWorkspace){clearTimeout(foldTimer129);frame.classList.remove('is-folding129');ui124.route=ten.role+'|'+state.mode+'|'+state.page;}
 renderBefore130();decorate129();staffWrap130();syncMasthead124();
 if(switchWorkspace&&!matchMedia('(prefers-reduced-motion:reduce)').matches)document.querySelector('#main')?.animate([{transform:`translateX(${state.mode==='staff'?18:-18}px)`,opacity:.55},{transform:'translateX(0)',opacity:1}],{duration:320,easing:'cubic-bezier(.22,.75,.15,1)'});
};
const scenes130=[['super','Desain header langsung · Super Admin','Direct header design · Super Admin'],['staff','Pilihan profil tim terpusat','Centred team profile selector'],['admin','Header menyatu · Admin','Continuous header · Admin'],['label','Header menyatu · Label','Continuous header · Label']];
studioCatalog.unshift(...scenes130.map(([id,a,b])=>({id:'v130-'+id,role:id==='staff'?'super':id,version:'13.0',title:[a,b],description:['Unggah desain, tarik posisi dan ukuran, serta perpindahan ruang kerja dan profil yang halus.','Upload artwork, move and resize it directly, with smooth workspace and profile changes.']})));
const studioBefore130=studioStart;
studioStart=async function(id){const scene=scenes130.find(s=>'v130-'+s[0]===id);if(!scene)return studioBefore130(id);editor130.token++;editor130.busy=false;editor130.owner=null;editor130.draft=null;editor130.drag=null;await studioBefore130('v129-'+scene[0]);studioSelected=id;render();};
render();
