/* V12.6: global Super Admin controls and one visual state for the masthead. */
const controls126 = [
  { id: 'finance', old: 'monitor', label: ['Pemantauan Keuangan', 'Financial Monitoring'], aliases: 'royalti royalty funds cash kas keuangan pemantauan' },
  { id: 'access', old: 'access', label: ['Staff & Akses', 'Staff & Access'], aliases: 'staff tim team peran roles izin permissions akses' },
  { id: 'settings', old: 'system', label: ['Pengaturan Platform', 'Platform Settings'], aliases: 'sistem system website navigasi navigation prosedur pengingat history riwayat' }
];
const movedNav126 = new Set(['monitor', 'access', 'system', 'plans']);
function controlActive126(id) {
  return id === 'finance' ? state.page === 'liability9' : id === 'access' ? state.page === 'access' :
    state.page === 'module' && ['cms', 'appearance', 'auditlog', 'catalogue104'].includes(v4.module);
}
function controlButton126(c, compact = false) {
  return `<button type="button" class="control-pill126 ${controlActive126(c.id) ? 'active' : ''}" data-control126="${c.id}" ${controlActive126(c.id) ? 'aria-current="page"' : ''}>${T(...c.label)}</button>`;
}
function mountControls126() {
  const header = document.querySelector('.header.header124'), left = header?.querySelector('.header-left');
  if (!left || !super114()) return;
  const nav = document.createElement('nav');
  nav.className = 'header-controls126';
  nav.setAttribute('aria-label', T('Kendali Super Admin', 'Super Admin controls'));
  nav.innerHTML = `<div class="control-links126">${controls126.map(c => controlButton126(c)).join('')}</div><button type="button" class="control-menu-toggle126" data-control126="menu" aria-expanded="false" aria-controls="control-menu126" aria-label="${T('Kendali Super Admin', 'Super Admin controls')}" title="${T('Kendali Super Admin', 'Super Admin controls')}">${icon('settings')}<span>${T('Kendali', 'Controls')}</span></button>`;
  left.append(nav);
  header.classList.add('has-controls126');
}
function removeMovedLinks126() {
  if (!super114()) return;
  const definitions = navSeed115().targets['super-platform'].items.concat(navSeed115().targets['super-staff'].items);
  document.querySelectorAll('.side-scroll button').forEach(b => {
    if (definitions.some(x => movedNav126.has(x.id) && matchNav115(b, x))) b.remove();
  });
}
function navView126(n) {
  const items = n.items.filter(x => !movedNav126.has(x.id)).map(x => ({ ...x, parent: movedNav126.has(x.parent) ? '' : x.parent }));
  return { ...n, items };
}
// Presentation migration only: keep published navigation, drafts and financial
// records intact. Operational children of a relocated parent remain reachable.
const sidebarBefore126 = sidebar5;
sidebar5 = function () {
  const html = sidebarBefore126();
  if (!super114()) return html;
  const box = document.createElement('div'); box.innerHTML = html;
  const definitions = navSeed115().targets['super-platform'].items.concat(navSeed115().targets['super-staff'].items);
  box.querySelectorAll('.side-scroll button').forEach(b => {
    if (definitions.some(x => movedNav126.has(x.id) && matchNav115(b, x))) b.remove();
  });
  return box.innerHTML;
};
const applyNavBefore126 = applyNav115;
applyNav115 = function () {
  if (!super114()) return applyNavBefore126();
  const original = navSession115 || System115.cp(area115('navigation').published);
  const view = { ...original, targets: { ...original.targets } };
  for (const key of ['super-platform', 'super-staff']) if (view.targets[key]) view.targets[key] = navView126(view.targets[key]);
  navSession115 = view;
  try { return applyNavBefore126(); } finally { navSession115 = original; }
};
const previewNavBefore126 = previewNav115;
previewNav115 = function (n) { return previewNavBefore126(ui115.target.startsWith('super-') ? navView126(n) : n); };
const navigationPageBefore126 = navigationPage115;
navigationPage115 = function () {
  const html = navigationPageBefore126();
  if (!ui115.target.startsWith('super-')) return html;
  const box = document.createElement('div'); box.innerHTML = html;
  box.querySelectorAll('[data-drag115]').forEach(row => { if (movedNav126.has(row.dataset.drag115)) row.remove(); });
  box.insertAdjacentHTML('afterbegin', `<p class="control-navigation-note126">${T('Pemantauan Keuangan, Staff & Akses, dan Pengaturan Platform tersedia di header Super Admin. Paket & Layanan dikelola melalui Pengaturan Platform.', 'Financial Monitoring, Staff & Access, and Platform Settings are in the Super Admin header. Plans & Services are managed through Platform Settings.')}</p>`);
  return box.innerHTML;
};

tabs115.packages = ['Paket & Layanan', 'Plans & Services'];
heading115 = function () {
  const tabs = Object.entries(tabs115).filter(([k]) => k !== 'activity').concat([['activity', tabs115.activity]]);
  return `<header class="heading115"><div><h1>${T('Pengaturan Platform', 'Platform Settings')}</h1><p>${T('Kelola konten, navigasi, layanan, dan prosedur platform.', 'Manage platform content, navigation, services, and procedures.')}</p></div>${!['activity', 'packages'].includes(ui115.tab) ? B115(T('Riwayat versi', 'Version history'), 'versions', ui115.tab, 'small') : ''}</header><nav class="switch104 tabs115" role="tablist" aria-label="${T('Bagian Pengaturan Platform', 'Platform Settings sections')}">${tabs.map(([k, n]) => `<button type="button" role="tab" aria-selected="${k === ui115.tab}" class="${k === ui115.tab ? 'active' : ''}" data-s115="tab" data-id="${k}">${T(...n)}</button>`).join('')}</nav>`;
};
const pageSystemBefore126 = page115;
page115 = function () {
  if (ui115.tab !== 'packages') return pageSystemBefore126();
  if (!super114()) return denied9();
  const box = document.createElement('div'); box.innerHTML = cataloguePage104();
  box.querySelector('.pagehead')?.remove();
  return `<div class="system-page115">${heading115()}<section class="tab-body115 settings-packages126" role="tabpanel">${box.innerHTML}</section></div>`;
};
function goControl126(id) {
  if (!super114()) { toast(T('Akses tidak tersedia.', 'Access unavailable.')); return; }
  const workspace = state.mode;
  closePop(); closeModal(); close114(); close115(true);
  if (id === 'finance') { financialGuard121(); state.page = 'liability9'; }
  else if (id === 'access') { state.page = 'access'; }
  else { ui115.tab = id === 'packages' ? 'packages' : 'content'; state.page = 'module'; v4.module = 'cms'; }
  state.mode = workspace;
  window.scrollTo({ top: 0, behavior: 'instant' }); render();
}
const closePopBefore126 = closePop;
closePop = function () {
  closePopBefore126();
  const button = document.querySelector('.control-menu-toggle126');
  if (button?.getAttribute('aria-expanded') !== 'false') button?.setAttribute('aria-expanded', 'false');
};
function toggleControls126() {
  if (!super114()) return;
  if (document.querySelector('#control-menu126')) { closePop(); return; }
  closePop();
  const header = document.querySelector('.header.header124'), toggle = header?.querySelector('.control-menu-toggle126');
  if (!header || !toggle) return;
  const width = Math.min(310, header.clientWidth - 24), relative = toggle.getBoundingClientRect().left - header.getBoundingClientRect().left;
  const left = Math.max(12, Math.min(relative, header.clientWidth - width - 12));
  header.insertAdjacentHTML('beforeend', `<section id="header-popover" class="header-popover control-menu126" style="--control-left126:${left}px;--control-width126:${width}px" aria-label="${T('Kendali Super Admin', 'Super Admin controls')}"><div id="control-menu126">${controls126.map(c => controlButton126(c, true)).join('')}</div></section>`);
  v5.pop = 'controls126'; toggle.setAttribute('aria-expanded', 'true');
  header.querySelector('.control-menu126 button')?.focus();
}
window.addEventListener('click', e => {
  const button = e.target.closest('[data-control126],[data-v104="catalogue-open"],[data-s115="source"][data-id="plans"]');
  if (!button) return;
  e.preventDefault(); e.stopImmediatePropagation();
  if (button.dataset.control126 === 'menu') toggleControls126(); else goControl126(button.dataset.control126 || 'packages');
}, true);
window.addEventListener('keydown', e => {
  const menu = document.querySelector('#control-menu126');
  if (!menu) {
    if (e.key === 'Home' && !e.altKey && !e.ctrlKey && !e.metaKey && !innerScroll124(e.target) && atTop125() && !ui124.expanded) setHero124(true);
    return;
  }
  if (e.key === 'Escape') { e.preventDefault(); e.stopImmediatePropagation(); closePop(); document.querySelector('.control-menu-toggle126')?.focus(); }
  else if (['ArrowDown', 'ArrowUp'].includes(e.key) && menu.contains(e.target)) {
    e.preventDefault(); e.stopImmediatePropagation();
    const buttons = [...menu.querySelectorAll('button')], i = buttons.indexOf(document.activeElement);
    buttons[(i + (e.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length]?.focus();
  }
}, true);
const searchBefore126 = searchResults;
searchResults = function (q) {
  const html = searchBefore126(q);
  const box = document.querySelector('#search-results');
  if (!super114() || !box) return html;
  const definitions = navSeed115().targets['super-platform'].items.concat(navSeed115().targets['super-staff'].items);
  box.querySelectorAll('button').forEach(b => { if ((b.dataset.action === 'search-nav' && b.dataset.page === 'liability9') || definitions.some(x => movedNav126.has(x.id) && matchNav115(b, x))) b.remove(); });
  const term = String(q || '').trim().toLowerCase();
  const choices = controls126.concat([{ id: 'packages', label: ['Paket & Layanan', 'Plans & Services'], aliases: 'paket layanan plans services kredit credit' }]).filter(c => !term || (c.label.join(' ') + ' ' + c.aliases).toLowerCase().includes(term));
  if (choices.length) { box.querySelector('.empty')?.remove(); box.insertAdjacentHTML('beforeend', `<section class="control-search126"><small>${T('Kendali Super Admin', 'Super Admin controls')}</small>${choices.map(c => `<button type="button" class="search-result" data-control126="${c.id}"><strong>${T(...c.label)}</strong>${arrowSVG124('right')}</button>`).join('')}</section>`); }
  return box.innerHTML;
};

// Direction-only icons. Preserve expansion state and real movement semantics.
const badgesBefore126 = normalizeBadges124;
normalizeBadges124 = function (root = document) {
  badgesBefore126(root);
  root.querySelectorAll('.badge,.pill107,.ten-chip').forEach(b => {
    if (b.classList.contains('status111') || b.closest('.package104,.emblem-pending,.plan9')) return;
    const text = b.textContent.trim();
    if (!/^(draft|draf|tayang|live|aktif|active|nonaktif|inactive|menunggu aktivasi|awaiting activation)$/i.test(text)) return;
    b.classList.add('status111');
    b.dataset.tone = /^(tayang|live|aktif|active)$/i.test(text) ? 'green' : /^(nonaktif|inactive)$/i.test(text) ? 'red' : /aktivasi|activation/i.test(text) ? 'blue' : 'neutral';
  });
};
Object.assign(arrowPath124, { down: 'M6 9l6 6 6-6', up: 'M6 15l6-6 6 6', right: 'M9 6l6 6-6 6', left: 'M15 6l-6 6 6 6' });
const directionBefore126 = arrowDirection124;
arrowDirection124 = function (b) {
  if (b.dataset.s115 === 'move') return b.dataset.id.endsWith(':-1') ? 'up' : 'down';
  if (b.dataset.arrow126) return b.dataset.arrow126;
  return directionBefore126(b);
};
const normalizeArrowsBefore126 = normalizeArrows124;
normalizeArrows124 = function (root = document) {
  const trends = [...root.querySelectorAll('.metric-trend125 svg')];
  trends.forEach(svg => svg.classList.remove('action-arrow124'));
  normalizeArrowsBefore126(root);
  trends.forEach(svg => svg.classList.add('action-arrow124'));
  root.querySelectorAll('button,a[role="button"],a.btn').forEach(b => {
    const walk = document.createTreeWalker(b, NodeFilter.SHOW_TEXT), nodes = [];
    for (let n; n = walk.nextNode();) if (!n.parentElement.closest('svg,.metric-trend125,.metric-foot124>span') && /[↗↘→←↑↓]/.test(n.nodeValue)) nodes.push(n);
    for (const n of nodes) {
      const direction = b.dataset.s115 === 'move' ? arrowDirection124(b) : b.hasAttribute('aria-expanded') ? arrowDirection124(b) : /←/.test(n.nodeValue) ? 'left' : /↑/.test(n.nodeValue) ? 'up' : /↓/.test(n.nodeValue) ? 'down' : 'right';
      const fragment = document.createDocumentFragment();
      for (const part of n.nodeValue.split(/([↗↘→←↑↓])/)) {
        if (/^[↗↘→←↑↓]$/.test(part)) { const span = document.createElement('span'); span.className = 'inline-chevron126'; span.innerHTML = arrowSVG124(direction); fragment.append(span); }
        else if (part) fragment.append(document.createTextNode(part));
      }
      n.replaceWith(fragment);
    }
  });
};
function decorate126(root = document) {
  root.querySelectorAll('.status111').forEach(b => {
    const pulse = /^(prioritas|priority|lewat tenggat|overdue)$/i.test(b.textContent.trim());
    if (b.dataset.pulse126 !== String(pulse)) b.dataset.pulse126 = String(pulse);
  });
  root.querySelectorAll('.metric-trend125').forEach(t => {
    const i = t.querySelector('i'), dir = t.dataset.trend === 'down' ? 'down' : 'up';
    if (i && t.dataset.trend !== 'flat' && (i.dataset.chevron126 !== dir || i.querySelector('path')?.getAttribute('d') !== arrowPath124[dir])) { i.innerHTML = arrowSVG124(dir); i.dataset.chevron126 = dir; }
  });
  // A nested inline arrow is part of its row, rather than another framed button.
  root.querySelectorAll('button').forEach(b => { if (b.querySelector('.action-arrow124') && !b.textContent.trim()) b.classList.add('arrow-circle125'); });
  if (state.page === 'liability9') {
    const h = document.querySelector('#main .pagehead h1');
    if (h && h.textContent !== T('Pemantauan Keuangan', 'Financial Monitoring')) h.textContent = T('Pemantauan Keuangan', 'Financial Monitoring');
  }
  stamp126();
}
function stamp126() {
  document.title = 'Rilis Musik · V12.6'; document.documentElement.dataset.release = '12.6';
  document.querySelectorAll('.version-pill,.floating107>strong').forEach(e => { if (e.textContent !== 'V12.6') e.textContent = 'V12.6'; });
  const f = document.querySelector('.footer span'); if (f && f.textContent !== 'RILIS MUSIK · V12.6') f.textContent = 'RILIS MUSIK · V12.6';
}
stamp125 = stamp126; stamp124 = stamp126;
const enhanceBefore126 = enhanceUI124;
enhanceUI124 = function (root = document) { enhanceBefore126(root); decorate126(root); };
const renderBefore126 = render;
render = function () { document.body.classList.add('release126'); renderBefore126(); removeMovedLinks126(); mountControls126(); decorate126(); };

const scenes126 = [
  ['super', 'v125-super', 'super', 'Kendali Super Admin & header yang konsisten', 'Super Admin controls & consistent header'],
  ['scroll', 'v125-scroll', 'super', 'Header setelah satu scroll', 'Header after one scroll'],
  ['staff', 'v124-staff', 'super', 'Kendali dari ruang Staff', 'Controls from the Staff workspace'],
  ['admin', 'v125-admin', 'admin', 'Chevron & indikator · Admin', 'Chevrons & indicators · Admin'],
  ['label', 'v125-label', 'label', 'Chevron & indikator · Label', 'Chevrons & indicators · Label']
];
studioCatalog.unshift(...scenes126.map(([id, , role, a, b]) => ({ id: 'v126-' + id, role, version: '12.6', title: [a, b], description: ['Menu kapsul, panel solid di atas Wawasan, dan pulse hanya pada bullet Prioritas dan Lewat tenggat.', 'Pill navigation, opaque panels above Insights, and pulsing dots only for Priority and Overdue.'] })));
const studioBefore126 = studioStart;
studioStart = async function (id) { const s = scenes126.find(x => 'v126-' + x[0] === id); if (!s) return studioBefore126(id); await studioBefore126(s[1]); studioSelected = id; decorate126(); };
const guideBefore126 = standardsPage9;
standardsPage9 = function () {
  const box = document.createElement('div'); box.innerHTML = guideBefore126();
  const p = box.querySelector('.guide124>p:last-child');
  if (p) p.textContent = T('Light, Regular, Semi Bold. Indikator 18 px dengan bullet solid. Pulse hanya pada bullet Prioritas dan Lewat tenggat. Chevron mengikuti arah buka, tutup, atau navigasi; tombol arah tetap bulat.', 'Light, Regular, Semi Bold. Indicators are 18 px with solid dots. Only Priority and Overdue dots pulse. Chevrons follow expansion, collapse, or navigation; direction buttons remain circular.');
  return box.innerHTML;
};
render();
