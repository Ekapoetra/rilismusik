/* v1.1 dev — Studio Pratinjau dengan satu sumber catatan perubahan.
   Data: release/changelog.json → release-data131.js (scripts/sync-release.cjs).
   Entri baru tampil paling atas dengan status (prototype / aplikasi asli /
   keduanya); kondisi V1–V13.0 dikelompokkan sebagai riwayat prototype lama.
   Label versi layar mengikuti release/release.json (mis. "v1.1 · dev 1"). */
'use strict';
const release131=window.RM_RELEASE||{version:'0.0.0'};
const changelog131=Array.isArray(window.RM_CHANGELOG)?window.RM_CHANGELOG:[];
const entries131=changelog131.flatMap(v=>(v.entries||[]).map(e=>({...e,version:v.version})));
function releaseLabel131(version){
  const m=/^(\d+)\.(\d+)\.(\d+)(?:-([a-z]+)\.(\d+))?$/.exec(version||'')||[];
  const short=m[3]==='0'?`${m[1]}.${m[2]}`:`${m[1]}.${m[2]}.${m[3]}`;
  return m[1]?`v${short}${m[4]?` · ${m[4]} ${m[5]}`:''}`:`v${version}`;
}
const currentLabel131=releaseLabel131(release131.version);
const pick131=o=>o?(state.lang==='en'?(o.en||o.id):(o.id||o.en)):'';
const statusText131={
  prototype:['Prototype','Prototype'],
  app:['Aplikasi asli','Real app'],
  both:['Prototype + aplikasi','Prototype + app'],
};

/* Version stamp: replaces V13.0 everywhere the shell shows the release. */
stamp130=function(){
  const title='Rilis Musik · '+currentLabel131;
  if(document.title!==title)document.title=title;
  document.documentElement.dataset.release=release131.version;
  document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>{if(e.textContent!==currentLabel131)e.textContent=currentLabel131;});
  const footer=document.querySelector('.footer span'),text='RILIS MUSIK · '+currentLabel131.toUpperCase();
  if(footer&&footer.textContent!==text)footer.textContent=text;
};
stamp124=stamp125=stamp126=stamp127=stamp128=stamp129=stamp130;

/* Scenario runner for changelog entries: open the role's clean base scene,
   then land on the menu the entry points to. */
const studioBefore131=studioStart;
studioStart=async function(id){
  const entry=entries131.find(e=>e.id===id);
  if(!entry)return studioBefore131(id);
  if(!entry.where)return;
  await studioBefore131('v130-'+(entry.where.role||'super'));
  studioSelected=id;
  if(entry.where.page)state.page=entry.where.page;
  render();window.scrollTo(0,0);
};

function card131(e){
  const [sid,sen]=statusText131[e.status]||[e.status,e.status];
  const status=`<span class="studio-status131 ${E(e.status)}">${T(sid,sen)}</span>`;
  const menu=e.where&&e.where.menu?`<span class="studio-menu131">${T('Menu','Menu')}: ${E(pick131(e.where.menu))}</span>`:'';
  const body=`<strong>${E(pick131(e.title))}</strong><small>${E(pick131(e.detail))}</small><span class="studio-foot131">${status}${menu}</span>`;
  return e.where
    ?`<button type="button" data-studio-scene="${E(e.id)}" class="studio-scene ${studioSelected===e.id?'selected':''}"><span class="studio-scene-meta">${E(studioRoleLabel(e.where.role||'super'))}</span>${body}</button>`
    :`<div class="studio-scene studio-info131" title="${T('Belum bisa dicoba di preview prototype','Not available in the prototype preview')}"><span class="studio-scene-meta">${T('Hanya di aplikasi asli','Real app only')}</span>${body}</div>`;
}

function decorateStudio131(){
  const body=document.querySelector('#dialog .dialog-body');
  if(!body||body.querySelector('.studio-current131'))return;
  const legacy=[...body.querySelectorAll(':scope > .studio-version')];
  legacy.forEach(s=>s.querySelector('.studio-version-title span')?.remove());
  const sections=changelog131.map((v,i)=>`<section class="studio-version studio-current131" data-version="${E(v.version)}"><div class="studio-version-title"><h3>${E(releaseLabel131(v.version))}</h3>${i===0?`<span>${T('Versi terbaru','Latest version')}</span>`:''}<time>${E(v.date||'')}</time></div>${v.summary?`<p class="studio-summary131">${E(pick131(v.summary))}</p>`:''}<div class="studio-scenes">${(v.entries||[]).map(card131).join('')}</div></section>`).join('');
  if(legacy[0])legacy[0].insertAdjacentHTML('beforebegin',sections);else body.insertAdjacentHTML('beforeend',sections);
  if(legacy.length){
    const details=document.createElement('details');
    details.className='studio-legacy131';
    details.innerHTML=`<summary>${T('Riwayat prototype lama (V1–V13.0)','Earlier prototype history (V1–V13.0)')}<small>${T('Penanda iterasi sebelum penomoran v1.1','Iteration markers before v1.1 numbering')}</small></summary>`;
    legacy[0].before(details);legacy.forEach(s=>details.append(s));
  }
}
const studioUI131=studio8;
studio8=function(){studioUI131();decorateStudio131();};
studio10=studio8;guide=studio8;
