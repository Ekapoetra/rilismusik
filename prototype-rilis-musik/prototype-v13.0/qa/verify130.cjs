const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib'),assert=require('node:assert/strict');
const source=path.resolve(__dirname,'../Rilis-Musik-V13.0.html'),checks=[],views=[],errors=[];
const check=(name,pass,detail)=>{checks.push({name,pass,detail});assert.ok(pass,name+' '+JSON.stringify(detail||''));};
function png(buffer){let offset=8,w,h,bpp;const chunks=[];while(offset<buffer.length){const len=buffer.readUInt32BE(offset),name=buffer.toString('ascii',offset+4,offset+8),chunk=buffer.subarray(offset+8,offset+8+len);if(name==='IHDR'){w=chunk.readUInt32BE(0);h=chunk.readUInt32BE(4);bpp=chunk[9]===6?4:3;}if(name==='IDAT')chunks.push(chunk);offset+=len+12;}const raw=zlib.inflateSync(Buffer.concat(chunks)),stride=w*bpp,p=Buffer.alloc(stride*h),paeth=(a,b,c)=>{const n=a+b-c,da=Math.abs(n-a),db=Math.abs(n-b),dc=Math.abs(n-c);return da<=db&&da<=dc?a:db<=dc?b:c;};for(let y=0;y<h;y++)for(let x=0;x<stride;x++){const filter=raw[y*(stride+1)],a=x>=bpp?p[y*stride+x-bpp]:0,b=y?p[(y-1)*stride+x]:0,c=y&&x>=bpp?p[(y-1)*stride+x-bpp]:0,v=raw[y*(stride+1)+1+x];p[y*stride+x]=(v+(filter===1?a:filter===2?b:filter===3?Math.floor((a+b)/2):filter===4?paeth(a,b,c):0))&255;}return {w,h,bpp,p};}
function diff(a,b){const x=png(a),y=png(b);assert.equal(x.w,y.w);assert.equal(x.h,y.h);let sum=0,count=0,changed=0;for(let r=12;r<x.h-12;r++)for(let c=12;c<x.w-12;c++){const i=(r*x.w+c)*x.bpp;let d=0;for(let k=0;k<3;k++)d+=Math.abs(x.p[i+k]-y.p[i+k]);sum+=d/3;changed+=d>30;count++;}return {mean:sum/count,changed:changed/count};}
(async()=>{
 const browser=await chromium.launch({headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}});
 page.on('pageerror',e=>errors.push(e.stack));
 const scene=async(role='super',theme='light',width=1440)=>{await page.setViewportSize({width,height:1000});await page.evaluate(async({role,theme})=>{await studioStart('v130-'+role);themeMode105(theme);state.lang=ten.lang='id';closeModal();render();scrollTo({top:0,behavior:'instant'});},{role,theme});await page.waitForTimeout(650);};
 const navigate=async(selector)=>{await page.locator(selector).click();await page.waitForTimeout(430);};
 const fingerprint=()=>page.evaluate(()=>JSON.stringify({members:ten.members,releases:ten.releases,royalty:ten.royalty107,orders:ten.commerce113?.orders,credit:ten.credit11}));
 const header=()=>page.evaluate(()=>{const frame=document.querySelector('.masthead124'),bar=frame.querySelector('.header.header124'),art=frame.querySelector('.masthead-atmosphere127'),r=bar.getBoundingClientRect();return {expanded:ui124.expanded,height:frame.getBoundingClientRect().height,barHeight:r.height,background:getComputedStyle(bar).backgroundColor,ink:getComputedStyle(bar.querySelector('.header-brand122 strong')).color,frameShadow:getComputedStyle(frame).boxShadow,artParent:art?.parentElement.className,rounded:getComputedStyle(frame.querySelector('.masthead-backdrop130')).borderBottomLeftRadius,overflow:document.documentElement.scrollWidth-innerWidth};});
 try{
  await page.goto('file:///'+source.replaceAll('\\','/'));
  for(const role of ['super','admin','label'])for(const theme of ['light','dark'])for(const width of [1440,820,390]){
   await scene(role,theme,width);const m=await header();views.push({role,theme,width,...m});
   check(role+'/'+theme+'/'+width+' uses one continuous readable masthead',m.expanded&&m.background==='rgba(0, 0, 0, 0)'&&m.ink==='rgb(245, 249, 255)'&&m.artParent==='masthead-backdrop130'&&m.frameShadow==='none'&&m.overflow<=1&&m.rounded==='18px',m);
   const boxes=await page.evaluate(()=>[...document.querySelectorAll('.header.header124 .header-controls127,.header.header124 .tools,.header.header124 [data-action=search]')].map(e=>e.getBoundingClientRect().toJSON()));
   const overlap=boxes.some((a,i)=>boxes.slice(i+1).some(b=>Math.min(a.right,b.right)>Math.max(a.left,b.left)+1&&Math.min(a.bottom,b.bottom)>Math.max(a.top,b.top)+1));
   check(role+'/'+theme+'/'+width+' controls do not overlap',!overlap,boxes);
   if(role==='super'&&width===1440)await page.screenshot({path:path.join(__dirname,'dashboard-'+theme+'130.png')});
  }
  await scene();
  const blue=await page.locator('.hero-insight122').screenshot();await page.evaluate(()=>document.querySelector('.masthead-atmosphere127').style.setProperty('background','#b53587','important'));await page.waitForTimeout(120);const magenta=await page.locator('.hero-insight122').screenshot(),glass=diff(blue,magenta);
  check('Glass responds to its actual backdrop after the masthead is reunited',glass.mean>25&&glass.changed>.8,glass);
  await scene();const expanded=await header();
  await page.locator('.workspace-switch122 [data-id=staff]').click();await page.waitForTimeout(65);const switched=await header();
  check('Platform to Staff preserves the expanded header without folding',switched.expanded&&switched.height===expanded.height&&!await page.locator('.masthead124.is-folding129').count()&&await page.evaluate(()=>!navigation129.pending),switched);
  await page.waitForTimeout(450);const centre=await page.evaluate(()=>{const main=document.querySelector('#main').getBoundingClientRect(),selector=document.querySelector('.staff-carousel122').getBoundingClientRect();return {main:(main.left+main.right)/2,selector:(selector.left+selector.right)/2};});
  check('Team profile selector is centred in the menu',Math.abs(centre.main-centre.selector)<1,centre);
  const beforeStaff=await page.evaluate(()=>({id:selectedStaff122().id,name:selectedStaff122().name}));await page.locator('[data-u122=staff-next]').click();await page.waitForTimeout(70);
  check('Changing profiles slides the card group and keeps the header still',await page.evaluate(before=>ui122.staff!==before&&document.querySelector('.staff-board122').getAnimations().length>0&&document.querySelectorAll('.staff-snapshot130').length===1&&ui124.expanded,beforeStaff.id));
  await page.waitForTimeout(430);
  check('Selected profile updates every card without leaving an overlay',await page.evaluate(()=>{const selected=selectedStaff122();return document.querySelector('.staff-board122').dataset.staff122===selected.id&&document.querySelector('.staff-person122 h2').textContent===selected.name&&document.querySelector('.staff-activity122>header>span').textContent===selected.name&&document.querySelectorAll('.staff-snapshot130').length===0&&document.querySelector('.staff-slide130').style.height==='';}));
  await page.locator('[data-u122=staff-prev]').click();await page.waitForTimeout(430);check('Previous profile works in the opposite direction',await page.evaluate(id=>ui122.staff===id,beforeStaff.id));
  await page.locator('.staff-choice122.selected').focus();await page.keyboard.press('ArrowRight');await page.waitForTimeout(430);check('Profile selector is keyboard operable',await page.evaluate(id=>ui122.staff!==id,beforeStaff.id));
  for(let i=0;i<3;i++)await page.locator('[data-u122=staff-next]').click();await page.waitForTimeout(430);check('Rapid profile changes leave only the final card group',await page.locator('.staff-board122').count()===1&&await page.locator('.staff-snapshot130').count()===0);
  const beforeSwipe=await page.evaluate(()=>ui122.staff),touch=await page.context().newCDPSession(page),touchBoard=await page.locator('.staff-work122').boundingBox();
  const touchX=touchBoard.x+touchBoard.width*.7,touchY=touchBoard.y+touchBoard.height*.5;
  await touch.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:touchX,y:touchY}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:touchX-90,y:touchY+2}]});
  await touch.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.waitForTimeout(430);await touch.detach();
  check('A horizontal touch gesture changes the profile',await page.evaluate(id=>ui122.staff!==id,beforeSwipe));
  await page.screenshot({path:path.join(__dirname,'staff-light130.png')});
  await page.mouse.move(1050,700);await page.mouse.wheel(0,150);await page.waitForTimeout(400);const collapsed=await header();
  check('Collapsed header remains readable and plain',!collapsed.expanded&&collapsed.background!=='rgba(0, 0, 0, 0)'&&collapsed.frameShadow==='none',collapsed);
  await page.locator('.workspace-switch122 [data-id=platform]').click();await page.waitForTimeout(80);const closedSwitch=await header();
  check('Staff to Platform preserves the collapsed header',!closedSwitch.expanded&&closedSwitch.height===collapsed.height&&!await page.locator('.masthead124.is-folding129').count(),closedSwitch);
  await page.evaluate(()=>scrollTo({top:0,behavior:'instant'}));await page.mouse.move(1000,500);await page.mouse.wheel(0,-120);await page.waitForTimeout(400);check('Top gesture can still reopen the greeting',await page.evaluate(()=>ui124.expanded));
  await page.locator('[data-control126=settings]').click();await page.waitForTimeout(70);check('Ordinary menu navigation retains the smooth fold',await page.evaluate(()=>state.page==='dashboard'&&!ui124.expanded));await page.waitForTimeout(380);
  check('Appearance shows the current card and upload, without sliders or an Apply form',await page.locator('.design-stage130').count()===1&&await page.locator('[data-upload130]').count()===1&&await page.locator('.appearance130 input[type=range],.appearance130 form,.appearance-form129').count()===0&&await page.locator('.appearance130 input').count()===1);
  check('Preview does not become the actual dashboard header',await page.locator('.masthead124 .hero-clip124').count()===0&&await page.locator('.design-content130').count()===1);
  check('Company identity remains accessible and public content stays hidden',await page.locator('.tabs115 [data-id=company]').count()===1&&await page.locator('.tabs115 [data-id=content]').count()===0);
  const finance=await fingerprint(),initial=await page.evaluate(()=>config130());
  const stage=await page.locator('.design-stage130').boundingBox();await page.mouse.move(stage.x+100,stage.y+80);await page.mouse.down();await page.mouse.move(stage.x+160,stage.y+110,{steps:8});
  check('Dragging changes the preview immediately before release',await page.evaluate(()=>editor130.draft.value.x!==config130().value.x&&document.querySelector('.design-selection130').style.getPropertyValue('--design-x130')!==String(config130().value.x)));
  await page.mouse.up();check('Releasing a drag saves the new position directly',await page.evaluate(version=>config130().version===version+1&&config130().value.x!==0&&config130().value.y!==0&&!editor130.error,initial.version));
  const oldSize=await page.evaluate(()=>config130().value.size),corner=await page.locator('.design-handle130[data-corner="1,1"]').boundingBox();await page.mouse.move(corner.x+corner.width/2,corner.y+corner.height/2);await page.mouse.down();await page.mouse.move(corner.x+corner.width/2-90,corner.y+corner.height/2-30,{steps:8});await page.mouse.up();
  check('Corner resizing changes the actual artwork scale without a slider',await page.evaluate(size=>config130().value.size<size&&!editor130.error,oldSize));
  const saved=await page.evaluate(()=>config130());await page.locator('.design-selection130').focus();await page.keyboard.press('ArrowLeft');check('Direct manipulation supports keyboard movement',await page.evaluate(value=>config130().value.x===value-1,saved.value.x));
  const cancel=await page.evaluate(()=>JSON.stringify(config130()));const selection=await page.locator('.design-selection130').boundingBox();await page.mouse.move(selection.x+80,selection.y+60);await page.mouse.down();await page.mouse.move(selection.x+120,selection.y+60);await page.keyboard.press('Escape');await page.mouse.up();check('Escape cancels an unfinished drag',await page.evaluate(()=>JSON.stringify(config130()))===cancel);
  await page.evaluate(()=>{window.savedSet130=Storage.prototype.setItem;Storage.prototype.setItem=function(key,value){if(key===V10KEY)throw Error('Simulated storage failure');return savedSet130.call(this,key,value);};});
  await page.locator('.design-selection130').focus();await page.keyboard.press('ArrowRight');check('A failed save preserves the applied artwork and shows a useful error',await page.evaluate(()=>JSON.stringify(config130()))===cancel&&await page.locator('.design-status130.is-error130').count()===1);
  await page.evaluate(()=>Storage.prototype.setItem=savedSet130);await page.keyboard.press('ArrowRight');check('Editing can continue after storage recovers',await page.evaluate(before=>!editor130.error&&config130().value.x===JSON.parse(before).value.x+1,cancel));
  const image=await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=400;const ctx=canvas.getContext('2d'),gradient=ctx.createLinearGradient(0,0,1600,400);gradient.addColorStop(0,'#121d4c');gradient.addColorStop(.55,'#7730bd');gradient.addColorStop(1,'#ffdbee');ctx.fillStyle=gradient;ctx.fillRect(0,0,1600,400);return canvas.toDataURL('image/png').split(',')[1];});
  const chooserPromise=page.waitForEvent('filechooser');await page.locator('[data-upload130]').click();const chooser=await chooserPromise;
  await chooser.setFiles({name:'design-example.png',mimeType:'image/png',buffer:Buffer.from(image,'base64')});await page.waitForFunction(()=>!editor130.busy);
  check('Uploading valid artwork replaces the current design directly',await page.evaluate(()=>config130().asset.kind==='image'&&config130().asset.name==='design-example.png'&&!editor130.error&&document.querySelector('.design-stage130 .header-image130').complete));
  const uploaded=await page.evaluate(()=>config130()),uploadVersion=uploaded.version;await page.locator('[data-file130]').setInputFiles({name:'broken.png',mimeType:'image/png',buffer:Buffer.from('not a real image')});await page.waitForFunction(()=>!editor130.busy);
  check('Unreadable uploads leave the current design intact',await page.evaluate(version=>config130().version===version&&!!editor130.error,uploadVersion));
  await page.locator('[data-file130]').setInputFiles({name:'unsafe.svg',mimeType:'image/svg+xml',buffer:Buffer.from('<svg></svg>')});await page.waitForFunction(()=>!editor130.busy);
  check('Unsupported image formats cannot overwrite the design',await page.evaluate(version=>config130().version===version&&!!editor130.error,uploadVersion));
  check('Artwork editing leaves financial and operational data intact',finance===await fingerprint());
  check('Activity records contain metadata rather than copies of the image',await page.evaluate(()=>{const events=system115().audit.filter(e=>e.kind==='header-design');return events.length>0&&!JSON.stringify(events).includes('data:image');}));
  await page.reload();await page.waitForTimeout(450);check('Uploaded design and geometry survive reload',await page.evaluate(before=>JSON.stringify(config130())===JSON.stringify(before),uploaded));
  await navigate('[data-control126=home]');await page.waitForTimeout(150);
  check('Saved artwork is used behind both navigation and greeting',await page.evaluate(()=>{const art=document.querySelector('.masthead-backdrop130>.masthead-atmosphere127'),image=art.querySelector('.header-image130');return image?.src===config130().asset.data&&getComputedStyle(document.querySelector('.header.header124')).backgroundColor==='rgba(0, 0, 0, 0)'&&art.style.getPropertyValue('--header-scale129')===String(config130().value.size/100);}));
  await page.screenshot({path:path.join(__dirname,'dashboard-upload130.png')});
  const accounts=await page.evaluate(()=>{const results=[],expected=config130();for(const role of ['admin','label','super']){role102(role);if(role!=='label')state.user=role==='super'?'jeck':'adovi';state.mode='platform';state.page='dashboard';render();const art=document.querySelector('.masthead-atmosphere127');results.push({role,same:art.querySelector('.header-image130')?.getAttribute('src')===expected.asset.data&&art.style.getPropertyValue('--header-x129')===expected.value.x+'%'});}return results;});
  check('The same design and position apply to all account views',accounts.every(r=>r.same),accounts);
  const denied=await page.evaluate(()=>{const results=[];for(const role of ['admin','label']){role102(role);if(role==='admin')state.user='adovi';const before=JSON.stringify(config130());try{save130({value:{size:120,x:0,y:0},asset:{kind:'builtin'}},config130().version);results.push(false);}catch{results.push(before===JSON.stringify(config130()));}}role102('super');state.user='jeck';state.preview=true;try{save130({value:{size:120,x:0,y:0},asset:{kind:'builtin'}},config130().version);results.push(false);}catch{results.push(true);}state.preview=false;state.page='dashboard';render();return results;});
  check('Admin, Label and preview cannot replace the shared design',denied.every(Boolean),denied);
  const invalid=await page.evaluate(()=>{const before=JSON.stringify(config130());let count=0;for(const [value,version] of [[{size:999,x:0,y:0},config130().version],[{size:120,x:0,y:0},0]])try{save130({value,asset:{kind:'builtin'}},version);}catch{count++;}return count===2&&before===JSON.stringify(config130());});check('Invalid geometry and stale changes cannot overwrite the saved design',invalid);
  await navigate('[data-control126=settings]');
  for(const width of [1280,1100,820,620,390]){
   await page.setViewportSize({width,height:1000});await page.evaluate(()=>{scrollTo({top:0,behavior:'instant'});render();});await page.waitForTimeout(150);
   const bounds=await page.evaluate(()=>{const stage=document.querySelector('.design-stage130').getBoundingClientRect(),upload=document.querySelector('[data-upload130]').getBoundingClientRect();return {overflow:document.documentElement.scrollWidth-innerWidth,stage:stage.toJSON(),upload:upload.toJSON()};});
   check('Appearance editing fits width '+width,bounds.overflow<=1&&bounds.stage.width>0&&bounds.upload.right<=width+1,bounds);
   if(width===390)await page.screenshot({path:path.join(__dirname,'appearance-phone130.png')});
  }
  await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>{themeMode105('dark');render();});await page.waitForTimeout(650);await page.screenshot({path:path.join(__dirname,'appearance-dark130.png')});
  await navigate('[data-control126=home]');await page.locator('.workspace-switch122 [data-id=staff]').click();await page.waitForTimeout(430);
  await page.emulateMedia({reducedMotion:'reduce'});await page.locator('[data-u122=staff-next]').click();check('Reduced motion skips profile sliding',await page.locator('.staff-snapshot130').count()===0&&await page.locator('.staff-board122').evaluate(e=>e.getAnimations().length===0));
  await page.locator('.workspace-switch122 [data-id=platform]').click();check('Reduced motion keeps workspace changes immediate without folding',await page.evaluate(()=>ui124.expanded&&state.mode==='platform'&&!navigation129.pending));
  await page.emulateMedia({reducedMotion:'no-preference'});await page.evaluate(()=>{state.lang=ten.lang='en';render();});await navigate('[data-control126=settings]');check('Appearance uses the matching English labels',await page.locator('.design-heading130 h2').textContent()==='Current header card'&&await page.locator('[data-upload130]').textContent()==='Upload new design');
  for(const id of ['finance','access','settings']){await navigate('[data-control126='+id+']');check('Dedicated '+id+' layout remains centred with sidebar hidden',await page.locator('.control-heading128').count()===1&&!await page.locator('.side5').isVisible());}
  check('No runtime errors',errors.length===0,errors);
  const report={version:'13.0',hash:crypto.createHash('sha256').update(fs.readFileSync(source)).digest('hex').toUpperCase(),checkedAt:new Date().toISOString(),checks,views,errors};fs.writeFileSync(path.join(__dirname,'acceptance130.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({checks:checks.length,views:views.length,errors,hash:report.hash}));
 }catch(error){fs.writeFileSync(path.join(__dirname,'failure130.json'),JSON.stringify({checks,views,errors,failure:error.stack},null,2));await page.screenshot({path:path.join(__dirname,'failure130.png')});throw error;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
