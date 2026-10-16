/* v1.1 dev.6 — detail kaca (gaya di glass131.css).
   1. Segitiga isi pada pil persentase (referensi).
   2. Nominal ringkas di kartu metrik: tooltip kaca berisi angka lengkap.
   3. Penanda ujung batang progress + tooltip "75,6% · Rp 75.000.000 dibayarkan".
   4. Chip status dipindah tepat setelah nama pekerjaan (daftar Dashboard).
   5. Seal label terverifikasi muncul di mana pun nama label tampil.
   6. Rincian metrik buka/tutup dengan animasi (grid-rows + konten bertahap +
      batang menggambar diri); tutup cepat, buka lebih lambat. */
'use strict';
Object.assign(deltaArrow131,{
  up:'<path d="M6 2.4 10.4 9.2H1.6z"/>',
  down:'<path d="M6 9.6 1.6 2.8h8.8z"/>',
  flat:'<rect x="1.6" y="5.2" width="8.8" height="1.6" rx=".8"/>',
});

/* 2–3. tooltip nilai lengkap & penanda progress */
function glassDetails131(root=document){
  root.querySelectorAll('.metric124 .value-row131>strong[title]').forEach(v=>{
    v.dataset.tip131=v.title;v.setAttribute('aria-label',v.title);v.removeAttribute('title');
  });
  const meter=root.querySelector('.withdrawal127 .withdrawal-meter127');
  if(!meter)return;
  const track=meter.querySelector('.payout-track'),fill=track&&track.querySelector('i');
  if(!track||!fill||track.querySelector('.payout-mark131'))return;
  const pct=(meter.querySelector(':scope>div:first-child strong')||{}).textContent||'';
  const paid=(root.querySelector('.withdrawal127 .withdrawal-part127 strong')||{}).textContent||'';
  const tip=`${pct.trim()} · ${paid.trim()} ${T('dibayarkan','paid')}`.trim();
  track.insertAdjacentHTML('beforeend',`<b class="payout-mark131" style="--x:${E(fill.style.width||'0%')}" data-tip131="${E(tip)}" aria-hidden="true"></b>`);
}

/* 4. chip status tepat setelah nama pekerjaan */
function relocateChips131(root=document){
  root.querySelectorAll('.work-row9 .work-top9').forEach(top=>{
    const title=top.querySelector(':scope>div:first-child>strong'),badges=top.querySelector(':scope>.work-badges9');
    if(title&&badges&&!title.contains(badges))title.append(badges);
  });
  root.querySelectorAll('.action-row').forEach(row=>{
    const title=row.querySelector(':scope>.grow>strong');if(!title)return;
    row.querySelectorAll(':scope>.states108,:scope>.badge').forEach(el=>{if(!title.contains(el))title.append(el);});
  });
}

/* 5. seal label terverifikasi di mana pun nama label tampil */
const sealCache131=new Map();
function sealNode131(label){
  if(!sealCache131.has(label.id)){
    const t=document.createElement('template');t.innerHTML=verificationMark9(label);
    const seal=t.content.querySelector('.verify9');if(seal)seal.classList.add('inline131');
    sealCache131.set(label.id,seal);
  }
  const seal=sealCache131.get(label.id);return seal?seal.cloneNode(true):null;
}
function verifiedLabels131(){
  try{return ((data.v9&&data.v9.labels)||[]).filter(l=>!l.master&&l.name&&verification9(l).status==='verified');}catch{return [];}
}
const sealSkip131='script,style,svg,select,option,textarea,input,.verify9,.label-name9,#dialog.preview-studio,.studio-scene,.version-pill,.floating107';
function sealEverywhere131(root=document.body){
  const labels=verifiedLabels131();if(!labels.length||!root)return;
  const byName=new Map(labels.map(l=>[l.name,l]));
  const names=[...byName.keys()].sort((a,b)=>b.length-a.length).map(n=>n.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'));
  const re=new RegExp('(?<![\\w])('+names.join('|')+')(?![\\w])');
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode:n=>{
    if(!n.data||n.data.length<4)return NodeFilter.FILTER_SKIP;
    const p=n.parentElement;if(!p||p.closest(sealSkip131))return NodeFilter.FILTER_REJECT;
    const next=n.nextSibling;if(next&&next.nodeType===1&&next.classList.contains('inline131'))return NodeFilter.FILTER_SKIP;
    return re.test(n.data)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_SKIP;}});
  const hits=[];let n;while((n=walker.nextNode()))hits.push(n);
  for(let node of hits){
    while(node&&node.data){
      const m=re.exec(node.data);if(!m)break;
      const rest=node.splitText(m.index+m[0].length),nameNode=node.splitText(m.index);
      const seal=sealNode131(byName.get(m[1]));if(seal)nameNode.after(seal);
      node=rest;
    }
  }
}

/* 6. animasi buka/tutup rincian metrik */
let metricAnimate131=false;
const metricDetailBase131=metricDetail131;
metricDetail131=function(id){
  const html=metricDetailBase131(id);if(!html)return html;
  return html.replace(/^(\s*<div class="metric-detail131"[^>]*>)/,'$1<div class="md-inner131">').replace(/<\/div>\s*$/,'</div></div>');
};
placeMetricDetail131=function(root=document){
  const grid=root.querySelector?root.querySelector('.platform6-grid'):null;if(!grid)return;
  grid.querySelectorAll('.metric124').forEach(card=>{
    const want=String(card.dataset.id===metricOpen131);
    if(card.getAttribute('aria-expanded')!==want)card.setAttribute('aria-expanded',want);
  });
  const parent=grid.parentElement,panels=[...parent.querySelectorAll(':scope>.metric-detail131')];
  const valid=metricOpen131&&grid.querySelector(`.metric124[data-id="${metricOpen131}"]`);
  const current=panels.find(p=>p.dataset.metric===metricOpen131&&!p.classList.contains('out'));
  for(const p of panels){
    if(p===current||p.classList.contains('out'))continue;
    p.classList.remove('in');p.classList.add('out');
    const done=()=>p.remove();p.addEventListener('transitionend',done,{once:true});setTimeout(done,260);
  }
  if(valid&&!current){
    grid.insertAdjacentHTML('afterend',metricDetail131(metricOpen131));
    const panel=grid.nextElementSibling;
    if(metricAnimate131){metricAnimate131=false;requestAnimationFrame(()=>requestAnimationFrame(()=>panel.classList.add('in')));}
    else panel.classList.add('in');
  }
};
const actionBeforeGlass131=handleAction;
handleAction=async function(b){
  if(b.dataset.action==='v6-metric'&&b.dataset.id!=='withdraw')metricAnimate131=true;
  return actionBeforeGlass131(b);
};

function glassPass131(root){
  glassDetails131(root);relocateChips131(root);sealEverywhere131(root===document?document.body:root);
}
const renderBeforeGlass131=render;
render=function(){renderBeforeGlass131();glassPass131(document);};
if(typeof enhanceUI124==='function'){
  const enhanceBeforeGlass131=enhanceUI124;
  enhanceUI124=function(root=document){enhanceBeforeGlass131(root);glassPass131(root);};
}
/* Dialog (detail label, dsb.) dibangun di luar render — seal ikut dipasang. */
(function(){
  const dialog=document.getElementById('dialog');if(!dialog)return;
  let busy=false;
  new MutationObserver(()=>{if(busy)return;busy=true;try{sealEverywhere131(dialog);}finally{busy=false;}}).observe(dialog,{childList:true,subtree:true});
})();

/* dev.9 — warna penanda mengikuti Kamus Penanda (Standar & Penanda):
   biru = menunggu/diproses, oranye = perlu tindakan, merah = lewat tenggat,
   hijau = selesai/terkonfirmasi, netral = ditutup/kedaluwarsa. Temuan audit:
   "Baru" dan "Diajukan" (tiket) dipetakan netral padahal keduanya antrean
   → biru; penanda akses di halaman Label (Normal/Dibatasi/Ditangguhkan) belum
   masuk sistem status111 (warna & titik berbeda) → dinormalkan. */
const toneMap131=[
  [/^(baru|new|diajukan|submitted)$/i,'blue'],
  [/^(normal)$/i,'neutral'],
  [/^(dibatasi|limited)$/i,'mustard'],
  [/^(ditangguhkan|suspended)$/i,'red'],
  [/^(aktif|active)$/i,'green'],
  [/^(belum aktif|not yet active)$/i,'blue'],
  [/^(lama tidak beraktivitas|inactive for a while|nonoperasional|nonoperational)$/i,'neutral'],
];
function fixTones131(root=document){
  root.querySelectorAll('.badge,.pill107,.status111,.ten-chip').forEach(el=>{
    if(el.closest('.package104,.plan9'))return;
    const txt=el.textContent.trim();
    const hit=toneMap131.find(([re])=>re.test(txt));if(!hit)return;
    el.classList.add('status111');el.dataset.tone=hit[1];
  });
}
const passBeforeTones131=glassPass131;
glassPass131=function(root=document){passBeforeTones131(root);fixTones131(root===document?document:root);};

/* dev.14: zona hover panah kartu metrik — hanya panah yang berubah warna saat di-hover. */
function arrowZones131(root=document){root.querySelectorAll('.metric124:not(:has(> .mk131))').forEach(c=>c.insertAdjacentHTML('beforeend','<span class="mk131" aria-hidden="true"></span>'));}
const passBeforeArrow131=glassPass131;
glassPass131=function(root=document){passBeforeArrow131(root);arrowZones131(root===document?document:root);};

/* dev.17 — kartu "Penarikan periode ini" mengikuti SIKLUS BULANAN pemilik:
   1) awal bulan laporan Believe (CSV) diunggah → total royalti periode;
   2) hanya label dengan saldo ≥ Rp 1 juta yang bisa mencairkan → POTENSI MAKSIMAL pencairan bulan ini;
   3) pengajuan label (1–14) mengisi batang menuju potensi maksimal; dibayar/menunggu bayar/diperiksa;
   4) setelah tgl 14, sisa yang TIDAK diajukan menjadi saldo yang dipantau (Pemantauan Royalti);
      saldo < Rp 1 juta bergulir ke bulan berikutnya.
   Angka laporan/potensi adalah data pratinjau (cycle131); pengajuan memakai withdrawalTotals7 & WD-091/092. */
const wdStatus131={'WD-091':'review','WD-092':'pay'};
const cycle131={report:'Believe_Agustus_2026.csv',uploaded:'2026-09-02',reportTotal:131640000,eligible:{labels:48,amount:118900000},below:{labels:312,amount:12740000},requestedLabels:31,threshold:1000000,windowEnd:14,payDue:20,today:18,nextReport:'1 Okt'};
const wdBefore131=withdrawalCard124;
withdrawalCard124=function(card){
  wdBefore131(card);
  const c=cycle131,d=withdrawalTotals7(),fmt=n=>new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1}).format(n);
  const short=n=>{const v=n/1e6;return 'Rp '+fmt(v>=100?Math.round(v):Math.round(v*10)/10)+T(' jt',' M');};
  const paidIds=new Set((data.ops||[]).filter(x=>x.status==='paid').map(x=>x.id));
  const open=Object.entries(withdrawalAmount7).filter(([id])=>!paidIds.has(id)).map(([id,amount])=>({id,amount,st:wdStatus131[id]||'pay'}));
  const sum=a=>a.reduce((n,x)=>n+x.amount,0),pay=open.filter(x=>x.st==='pay'),rev=open.filter(x=>x.st==='review');
  const max=Math.max(c.eligible.amount,d.total),notReq=Math.max(0,max-d.total),closed=c.today>c.windowEnd,daysPay=c.payDue-c.today;
  const notLabels=Math.max(0,c.eligible.labels-c.requestedLabels);
  const pct=v=>max>0?v/max*100:0,reqPct=pct(d.total);
  const segs=[['paid',d.paid,T('Dibayarkan','Paid'),null],['pay',sum(pay),T('Menunggu pembayaran','Awaiting payment'),pay.length],['review',sum(rev),T('Menunggu pemeriksaan','Awaiting review'),rev.length],['left',notReq,closed?T('Tidak diajukan','Not requested'):T('Belum diajukan','Not yet requested'),notLabels]].filter(s=>s[1]>0);
  let at=0;const extra=segs.map(s=>{const h=s[0]==='paid'?'':`<s class="seg131 ${s[0]}" style="left:${at}%;width:${pct(s[1])}%"></s>`;at+=pct(s[1]);return h;}).join('');
  const day=n=>`${n} Sep`;
  const steps=[[2,T('Laporan diunggah','Report uploaded')],[c.windowEnd,T('Pengajuan ditutup','Requests close')],[c.payDue,T('Batas bayar','Payment due')],[30,T('Laporan berikutnya','Next report')]];
  const pos=n=>Math.min(100,Math.max(0,(n-1)/29*100));
  const head=card.querySelector('.withdraw-heading124');
  card.querySelectorAll(':scope>:not(.withdraw-heading124)').forEach(e=>e.remove());
  if(head){const p=head.querySelector('p');if(p)p.textContent=T(`Laporan Believe Agustus · diunggah 2 Sep 2026 · data pratinjau`,`Believe August report · uploaded Sep 2, 2026 · preview data`);
    if(!head.querySelector('.cy-phase131'))head.querySelector('div')?.insertAdjacentHTML('beforeend',`<span class="cy-phase131">${closed?T(`Pengajuan ditutup · bayar s.d. ${day(c.payDue)}`,`Requests closed · pay by ${day(c.payDue)}`):T(`Pengajuan dibuka s.d. ${day(c.windowEnd)}`,`Requests open until ${day(c.windowEnd)}`)}</span>`);}
  card.insertAdjacentHTML('beforeend',
    `<div class="cy-top131"><div class="cy-main131"><div><small>${T('Diajukan','Requested')}</small><strong>${money(d.total)}</strong><span>${T('dari maksimal','of a maximum of')} ${money(max)} · ${c.requestedLabels} label</span></div></div><div class="cy-facts131"><div><small>${T('Royalti laporan','Report royalties')}</small><b>${money(c.reportTotal)}</b></div><div><small>${T('Bisa dicairkan · ≥ Rp 1 jt','Withdrawable · ≥ Rp 1M')}</small><b>${money(c.eligible.amount)}</b><span>${c.eligible.labels} label</span></div><div><small>${T('Di bawah ambang · bergulir','Below threshold · carried over')}</small><b>${money(c.below.amount)}</b><span>${c.below.labels} label</span></div></div></div>`
   +`<div class="withdrawal-meter127 wb131"><div class="wb131-pct"><span>${T('Pengajuan terhadap potensi maksimal','Requests vs maximum potential')}</span><strong>${fmt(reqPct)}%</strong></div>`
   +`<div class="payout-track" role="progressbar" aria-label="${T('Bagian potensi yang telah dibayar','Share of potential paid')}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct(d.paid).toFixed(1)}" aria-valuetext="${fmt(pct(d.paid))}% ${T('telah dibayarkan','paid')}"><i style="width:${pct(d.paid)}%"></i>${extra}<em class="cy-cap131" style="left:${reqPct}%" title="${T('Batas pengajuan','Requested so far')}"></em></div></div>`
   +`<div class="wb131-cols cy-cols131">${segs.map(s=>`<div class="wb131-col ${s[0]}"><span><i class="wb131-dot ${s[0]}"></i>${s[2]}</span><strong>${short(s[1])}</strong><small>${s[0]==='paid'?fmt(pct(s[1]))+'%':s[0]==='left'?`${s[3]} label${closed?' → '+T('pemantauan','monitoring'):''}`:`${s[3]} ${T('pengajuan','request'+(s[3]===1?'':'s'))}`}</small></div>`).join('')}</div>`
   +`<div class="cy-time131"><i class="cy-line131"><b style="width:${pos(c.today)}%"></b></i>${steps.map(([n,l],i)=>`<span class="cy-step131 ${n<=c.today?'done':''} ${i===0?'first':i===steps.length-1?'last':''}" style="left:${pos(n)}%"><i></i><small>${day(n)}</small><em>${l}</em></span>`).join('')}<span class="cy-today131" style="left:${pos(c.today)}%"><small>${T('Hari ini','Today')} · ${day(c.today)}</small></span></div>`
   +`<div class="cy-calls131">${d.unpaid>0?`<div class="wb131-call"><span><b>${money(d.unpaid)}</b> ${T('belum dibayar','unpaid')} · ${T(`selesaikan sebelum 21 Sep (${daysPay+1} hari lagi)`,`settle before Sep 21 (${daysPay+1} days left)`)}</span>${btn(T(`Lihat ${open.length} pengajuan`,`View ${open.length} requests`),'v6-metric','data-id="withdraw"','small')}</div>`:''}${closed&&notReq>0?`<div class="wb131-call cy-left131"><span><b>${money(notReq)}</b> ${T(`dari ${notLabels} label tidak diajukan s.d. 14 Sep → masuk Pemantauan Royalti`,`from ${notLabels} labels not requested by Sep 14 → moved to Royalty Monitoring`)}</span>${btn(T('Buka pemantauan','Open monitoring'),'nav','data-page="liability9"','small')}</div>`:''}</div>`);
  return card;
};

/* dev.16 — Geografi: konteks "x/y lokasi lengkap" + "Lihat & lengkapi" (disukai pemilik dari G-A/G-C)
   menggantikan tautan polos "Lokasi belum lengkap · n" di kaki kartu. */
function geoCoverage131(root=document){
  const card=root.querySelector&&root.querySelector('.geography124');if(!card||card.querySelector('.geo-cov131'))return;
  let groups=[];try{groups=mapGroups106();}catch{return;}
  const total=groups.reduce((n,g)=>n+g.members.length,0),unknown=(groups.find(g=>g.id==='unknown')||{members:[]}).members.length,done=total-unknown;
  if(!total)return;
  const C=2*Math.PI*15,frac=done/total;
  let foot=card.querySelector(':scope>footer');if(!foot){card.insertAdjacentHTML('beforeend','<footer></footer>');foot=card.querySelector(':scope>footer');}
  foot.querySelector('[data-ui106="region"][data-id="unknown"]')?.remove();
  foot.insertAdjacentHTML('afterbegin',`<div class="geo-cov131"><svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15" class="trk"/>${done?`<circle cx="18" cy="18" r="15" class="val" stroke-dasharray="${(C*frac).toFixed(1)} ${C.toFixed(1)}"/>`:""}</svg><div><strong>${done}/${total}</strong><span>${T('lokasi lengkap','complete locations')}</span></div>${unknown?`<button type="button" class="btn small" data-ui106="region" data-id="unknown">${T('Lihat & lengkapi','View & complete')} · ${unknown}</button>`:''}</div>`);
}
const passBeforeGeo131=glassPass131;
glassPass131=function(root=document){passBeforeGeo131(root);geoCoverage131(root===document?document:root);};
