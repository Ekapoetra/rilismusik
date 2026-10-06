/* V12.7: centred global controls, atmospheric masthead, and shared progress. */
const controlIcons127 = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  finance: '<path d="M4 20V9m5 11V5m5 15v-7m5 7V3"/><path d="M2 21h20"/>',
  access: '<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3m2-17a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 4v3"/>',
  settings: '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3"/><circle cx="15" cy="17" r="3"/>'
};
const headerControls127 = [{id:'home',label:['Home','Home']}, ...controls126];
const activeBefore127 = controlActive126;
controlActive126 = function (id) {
  if (id === 'home') return state.mode === 'staff' ? state.page === 'overview' : state.page === 'dashboard';
  return activeBefore127(id);
};
function iconControl127(c) {
  const label = T(...c.label), active = controlActive126(c.id);
  return `<button type="button" class="control-pill126 control-icon127 ${active?'active':''}" data-control126="${c.id}" aria-label="${E(label)}" title="${E(label)}" ${active?'aria-current="page"':''}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${controlIcons127[c.id]}</svg><span class="control-label127">${E(label)}</span></button>`;
}
mountControls126 = function () {
  const header = document.querySelector('.header.header124');
  if (!header || !super114()) return;
  header.querySelector('.header-controls126')?.remove();
  const nav = document.createElement('nav');
  nav.className = 'header-controls126 header-controls127';
  nav.setAttribute('aria-label', T('Navigasi utama Super Admin','Super Admin primary navigation'));
  nav.innerHTML = `<div class="control-links126">${headerControls127.map(iconControl127).join('')}</div>`;
  header.append(nav); header.classList.add('has-controls126');
};
const controlRouteBefore127 = goControl126;
goControl126 = function (id) {
  if (!super114()) return controlRouteBefore127(id);
  if (id !== 'home') return controlRouteBefore127(id);
  closePop(); closeModal(); close114(); close115(true);
  ui124.expanded = true;
  go(state.mode === 'staff' ? 'overview' : 'dashboard', state.mode);
  window.scrollTo({top:0,behavior:'instant'});
};

// Vector noise stays self-contained in the downloaded HTML. No reference text
// or screenshot UI is included in the background.
const grain127 = `<svg class="masthead-grain127" width="100%" height="100%" aria-hidden="true" focusable="false"><filter id="grain127"><feTurbulence type="fractalNoise" baseFrequency=".86" numOctaves="3" seed="27" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#grain127)" opacity=".5"/></svg>`;
let particles127 = '';
let seed127 = 127;
function random127() { seed127 = (seed127 * 16807) % 2147483647; return (seed127 - 1) / 2147483646; }
for (let i=0;i<70;i++) particles127 += `<circle cx="${Math.round(random127()*1440)}" cy="${Math.round(random127()*340)}" r="${(.45+random127()*.65).toFixed(2)}" opacity="${(.13+random127()*.3).toFixed(2)}"/>`;
const atmospheric127 = `<div class="masthead-atmosphere127" aria-hidden="true"><svg class="masthead-lights127" viewBox="0 0 1440 340" preserveAspectRatio="none" focusable="false"><defs><linearGradient id="light127" x2="0" y2="1"><stop stop-color="#83caff" stop-opacity="0"/><stop offset=".5" stop-color="#a6daff" stop-opacity=".5"/><stop offset="1" stop-color="#80c8ff" stop-opacity="0"/></linearGradient></defs><g fill="#d9ecff">${particles127}</g><g fill="url(#light127)"><rect x="230" y="7" width="1" height="48"/><rect x="520" y="44" width="1" height="79"/><rect x="755" y="0" width="1" height="65"/><rect x="1080" y="48" width="1.5" height="85"/><rect x="1270" y="147" width="1" height="73"/></g></svg>${grain127}</div>`;

const stepsBefore127 = steps9;
steps9 = function (x) {
  const box = document.createElement('div'); box.innerHTML = stepsBefore127(x);
  const rail = box.querySelector('.steps9');
  if (x.stage === 'done') rail?.querySelectorAll('.step9').forEach(s=>{s.classList.remove('current');s.classList.add('done');});
  decorateSteps127(box);
  return box.innerHTML;
};
function decorateSteps127(root=document) {
  root.querySelectorAll('.steps9,.steps11,.steps111').forEach(rail=>{
    const steps = [...rail.children].filter(e=>e.matches('.step9,li'));
    if (!steps.length) return;
    const hasWorkState = rail.classList.contains('steps9');
    let current = hasWorkState ? steps.findIndex(s=>s.classList.contains('current')) : steps.findIndex(s=>!s.classList.contains('done'));
    const finished = steps.every(s=>s.classList.contains('done'));
    if (finished) current = -1;
    const complete = current < 0 ? (finished ? 1 : 0) : current/Math.max(1,steps.length-1);
    rail.classList.add('progress-rail127'); rail.style.setProperty('--step-count127',steps.length);
    rail.style.setProperty('--fraction127',complete); rail.setAttribute('role','list');
    rail.setAttribute('aria-label',T('Tahapan proses','Process stages'));
    steps.forEach((s,i)=>{
      s.classList.add('progress-step127');s.classList.toggle('current',i===current);
      s.setAttribute('role','listitem');
      if(i===current)s.setAttribute('aria-current','step');else s.removeAttribute('aria-current');
      const marker=s.querySelector(':scope>i');if(!marker)return;
      marker.classList.remove('processing');marker.setAttribute('aria-hidden','true');
      const expected=s.classList.contains('done')?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" aria-hidden="true"><path d="m6 12 4 4 8-8"></path></svg>':'<span class="step-dot127"></span>';
      if(marker.innerHTML!==expected)marker.innerHTML=expected;
    });
  });
}

withdrawalCard124 = function (card) {
  const d=withdrawalTotals7(),fraction=d.total>0?Math.min(100,Math.max(0,d.paid/d.total*100)):0;
  const percent=new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1}).format(fraction);
  card.classList.add('withdraw124','withdrawal127');
  card.innerHTML=`<header class="withdraw-heading124"><div><h2>${T('Penarikan periode ini','Period Withdrawals')}</h2><p>${T('1–18 September 2026 · Data pratinjau','September 1–18, 2026 · Preview data')}</p></div><button type="button" class="detail-arrow124" data-action="v6-metric" data-id="withdraw" aria-label="${T('Buka rincian penarikan','Open withdrawal details')}">${arrowSVG124('right')}</button></header><div class="withdrawal-facts127"><div class="withdrawal-total127"><span>${T('Total pengajuan','Total requested')}</span><strong>${money(d.total)}</strong></div><div class="withdrawal-part127"><span><i class="withdrawal-dot127 paid"></i>${T('Dibayarkan','Paid')}</span><strong>${money(d.paid)}</strong></div><div class="withdrawal-part127"><span><i class="withdrawal-dot127 remaining"></i>${T('Belum dibayarkan','Not yet paid')}</span><strong>${money(d.unpaid)}</strong></div></div><div class="withdrawal-meter127"><div><span>${T('Penyelesaian pembayaran','Payment completion')}</span><strong>${percent}%</strong></div><div class="payout-track" role="progressbar" aria-label="${T('Bagian penarikan yang telah dibayar','Share of withdrawals paid')}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${fraction.toFixed(1)}" aria-valuetext="${percent}% ${T('telah dibayarkan','paid')}"><i style="width:${fraction}%"></i></div></div>`;
  return card;
};
function syncFocus127() {
  const focused=super114()&&controls126.some(c=>controlActive126(c.id));
  document.body.classList.toggle('focus-controls127',focused);
  const side=document.querySelector('.side5');
  if(side){side.inert=focused;side.setAttribute('aria-hidden',String(focused));}
}
function decorate127(root=document) {
  const frame=root.querySelector('.masthead124.has-hero124');
  if(frame&&!frame.querySelector('.masthead-atmosphere127'))frame.insertAdjacentHTML('afterbegin',atmospheric127);
  root.querySelectorAll('.platform124>.section-head124').forEach(e=>e.remove());
  root.querySelectorAll('[data-card="queue"] .panel-head p,[data-card="mywork"] .panel-head p,[data-card="progress"] .panel-head p,.geography124 .map-header106 p').forEach(e=>e.remove());
  decorateSteps127(root);syncFocus127();stamp127();
}
function stamp127() {
  document.title='Rilis Musik · V12.7';document.documentElement.dataset.release='12.7';
  document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>{if(e.textContent!=='V12.7')e.textContent='V12.7';});
  const f=document.querySelector('.footer span');if(f&&f.textContent!=='RILIS MUSIK · V12.7')f.textContent='RILIS MUSIK · V12.7';
}
stamp124=stamp127;stamp125=stamp127;stamp126=stamp127;
const enhanceBefore127=enhanceUI124;
enhanceUI124=function(root=document){enhanceBefore127(root);decorate127(root);};
const renderBefore127=render;
render=function(){document.body.classList.add('release127');renderBefore127();decorate127();syncMasthead124();};

const scenarios127=[['super','v126-super','super','Header atmosfer & empat ikon','Atmospheric header & four icons'],['staff','v126-staff','super','Home & kendali dari ruang Staff','Home & controls from Staff'],['admin','v126-admin','admin','Progress & dashboard Admin','Admin progress & dashboard'],['label','v126-label','label','Dashboard Label · kedua tema','Label dashboard · both themes']];
studioCatalog.unshift(...scenarios127.map(([id,,role,a,b])=>({id:'v127-'+id,role,version:'12.7',title:[a,b],description:['Empat ikon terpusat, menu khusus tanpa sidebar, progress bertahap dan kartu penarikan baru.','Four centred icons, focused controls without a sidebar, shared progress and new withdrawal card.']})));
const studioBefore127=studioStart;
studioStart=async function(id){const s=scenarios127.find(s=>'v127-'+s[0]===id);if(!s)return studioBefore127(id);await studioBefore127(s[1]);studioSelected=id;decorate127();};
render();
