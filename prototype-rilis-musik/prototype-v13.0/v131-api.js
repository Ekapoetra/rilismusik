/* V13.1 bridge API: menghubungkan prototype ke service /api (database salinan).
   Tanpa API — misalnya `npm run preview` lokal — file ini diam dan perilaku
   localStorage V13.0 tidak berubah. */
(function(){
 'use strict';
 const BASE='/api',KEY='rm-v11-1-journey';
 const api=window.RMAPI={online:false,busy:false,lastError:null};
 const T=(a,b)=>(typeof ten!=='undefined'&&ten.lang==='en')?b:a;
 const call=(path,opt={})=>fetch(BASE+path,{credentials:'same-origin',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});
 const localDoc=()=>{try{const r=localStorage.getItem(KEY);return r?JSON.parse(r):null}catch{return null}};
 const rev=d=>Number.isSafeInteger(d?.storageRevision116)?d.storageRevision116:-1;
 const withShared=d=>{if(!d.legacyShared117&&typeof sharedSnapshot117==='function')d.legacyShared117=sharedSnapshot117();return d;};
 const canAdopt=d=>typeof Persistence117!=='undefined'&&Persistence117.validateJourney&&Persistence117.validateJourney(withShared(d));
 /* Dokumen hasil bootstrap database diberi tanda; state simulasi lokal yang
    lama tidak boleh menimpa atau menghalangi data asli. */
 const real=d=>d&&d.dataSource==='production-copy';
 /* Tempelkan antrean kerja & feed produksi ke shared doc bawaan klien
    (sharedSnapshot117) supaya tetap lolos validasi shared(). */
 const applySharedPatch=(j,patch)=>{
  if(!patch)return;
  const sh=withShared(j).legacyShared117;
  if(!sh?.data)return;
  if(Array.isArray(patch.tasks))sh.data.tasks=patch.tasks;
  if(Array.isArray(patch.events)&&patch.events.length)sh.data.events=patch.events;
 };

 function loginScreen(){
  if(document.getElementById('rm-api-login'))return;
  const box=document.createElement('div');box.id='rm-api-login';
  box.style.cssText='position:fixed;inset:0;z-index:400;display:grid;place-items:center;background:rgba(15,15,18,.55);backdrop-filter:blur(10px)';
  box.innerHTML=`<form style="background:var(--surface,#fff);color:var(--text,#222);border-radius:16px;padding:28px;min-width:280px;box-shadow:0 20px 60px #0004"><h2 style="font-size:16px;font-weight:600;margin:0 0 6px">Rilis Musik · Preview</h2><p style="font-size:12px;color:var(--muted,#777);margin:0 0 16px">${T('Masukkan kata sandi preview untuk melihat data.','Enter the preview password to view data.')}</p><input type="password" name="pw" autocomplete="current-password" placeholder="${T('Kata sandi','Password')}" style="width:100%;box-sizing:border-box;padding:10px;border:1px solid var(--line,#ddd);border-radius:9px;font:inherit"><div id="rm-api-login-err" style="font-size:11px;color:var(--red,#b23e4e);margin-top:8px;min-height:14px"></div><button type="submit" class="btn primary" style="margin-top:6px;width:100%">${T('Masuk','Sign in')}</button></form>`;
  document.body.appendChild(box);
  box.querySelector('form').addEventListener('submit',async e=>{
   e.preventDefault();const err=box.querySelector('#rm-api-login-err');err.textContent='';
   try{
    const r=await call('/auth/login',{method:'POST',body:JSON.stringify({password:e.target.pw.value})});
    if(!r.ok){err.textContent=T('Kata sandi salah.','Wrong password.');return;}
    location.reload();
   }catch{err.textContent=T('Gagal menghubungi server.','Could not reach the server.');}
  });
 }

 async function push(){
  const doc=localDoc();
  if(!doc)return;
  const r=await call('/proto/state',{method:'PUT',body:JSON.stringify({journey:doc})});
  if(r.status===401){api.online=false;loginScreen();return;}
  if(r.status===409){api.lastError='stale';if(!push._retry){push._retry=true;return hydrate(true);}return;}
  if(!r.ok)api.lastError='push_'+r.status;
  else push._retry=false;
 }

 let timer=null;
 function schedulePush(){clearTimeout(timer);timer=setTimeout(()=>{push().catch(e=>{api.lastError=String(e&&e.code||e)});},800);}

 async function hydrate(force){
  const st=await (await call('/proto/state')).json().catch(()=>({}));
  const server=st.journey||null,local=localDoc();
  const serverOk=server&&canAdopt(server);
  /* 1. Dokumen server yang asli menang bila lebih baru, atau lokal masih dummy. */
  if(serverOk&&real(server)&&(rev(server)>rev(local)||!real(local)||force&&rev(server)>=rev(local))){
   try{Persistence117.replace(server);return;}catch{api.lastError='adopt_failed';}
  }
  /* 2. Dokumen lokal yang asli menang bila server kosong, dummy, atau usang. */
  if(real(local)&&(!serverOk||!real(server)||rev(local)>rev(server))){await push().catch(()=>{});return;}
  /* 3. Sisanya (server kosong/dummy + lokal kosong/dummy): bangun ulang dari
        koleksi produksi, bukan dari data dummy browser. */
  if(!serverOk||!real(server)){
   const b=await (await call('/proto/bootstrap')).json().catch(()=>({}));
   if(b.journey&&canAdopt(b.journey)){applySharedPatch(b.journey,b.sharedPatch);try{Persistence117.replace(b.journey);return;}catch{api.lastError='adopt_failed';}}
   api.lastError=api.lastError||'bootstrap_invalid';
  }
 }

 function wrapSave(){
  if(typeof save10!=='function'||save10.__api131)return;
  const original=save10;
  save10=function(){const result=original.apply(this,arguments);if(api.online)schedulePush();return result;};
  save10.__api131=true;
 }

 function pill(state,msg){
  let el=document.getElementById('rm-api-pill');
  if(!el){el=document.createElement('button');el.id='rm-api-pill';el.type='button';el.style.cssText='position:fixed;right:14px;bottom:14px;z-index:390;display:flex;align-items:center;gap:7px;padding:6px 11px;border-radius:20px;border:1px solid var(--line,#ddd);background:var(--surface,#fff);color:var(--muted,#777);font-size:10px;font-family:inherit;cursor:default';document.body.appendChild(el);}
  const color=state==='on'?'var(--green,#217659)':state==='warn'?'var(--amber,#946219)':'var(--muted,#777)';
  el.innerHTML=`<i style="width:7px;height:7px;border-radius:50%;background:${color};display:inline-block"></i>${msg}`;
 }

 async function boot(){
  let health;
  try{health=await fetch(BASE+'/health',{signal:AbortSignal.timeout(3000)});}catch{return;}
  if(!health.ok)return;
  api.online=true;
  try{
   const st=await (await fetch(BASE+'/auth/status')).json();
   if(st.required&&!st.session){api.online=false;pill('warn',T('Simulasi lokal','Local simulation'));loginScreen();return;}
   await hydrate();
   if(api.online)wrapSave();
   pill(api.lastError?'warn':'on',api.lastError?T('Simulasi lokal — API menolak','Local simulation — API refused'):T('Terhubung database','Database connected'));
  }catch(e){api.lastError=String(e&&e.code||e);pill('warn',T('Simulasi lokal','Local simulation'));}
 }

 api.push=push;api.hydrate=hydrate;api.loginScreen=loginScreen;
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
})();
