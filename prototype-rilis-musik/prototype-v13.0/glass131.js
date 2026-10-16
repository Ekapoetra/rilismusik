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

/* dev.18 — "Penarikan periode ini" disederhanakan (muatan sama, dibaca sekali lirik):
   kiri  = satu kalimat utama: diajukan dari maksimal bulan ini (saldo ≥ Rp 1 jt);
   kanan = dua angka yang perlu tindakan: belum dibayar (tenggat) & tidak diajukan (→ pemantauan);
   tengah= satu batang tiga warna (dibayar · diajukan belum dibayar · tidak diajukan) + legenda satu baris;
   bawah = satu baris konteks laporan (sumber, total royalti, di bawah ambang yang bergulir, tanggal penting).
   Siklus pemilik: laporan Believe awal bulan → saldo ≥ Rp 1 jt bisa dicairkan → pengajuan s.d. tgl 14 →
   bayar s.d. tgl 20 → sisa tidak diajukan menjadi kewajiban yang dipantau. */
const wdStatus131={'WD-091':'review','WD-092':'pay'};
const cycle131={report:'Believe Agustus',uploaded:'2 Sep',reportTotal:131640000,eligible:{labels:48,amount:118900000},below:{labels:312,amount:12740000},requestedLabels:31,threshold:1000000,windowEnd:14,payDue:20,today:18};
const wdBefore131=withdrawalCard124;
withdrawalCard124=function(card){
  wdBefore131(card);
  const c=cycle131,d=withdrawalTotals7(),nf=n=>new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1}).format(n);
  const jt=n=>`Rp ${nf(Math.round(n/1e5)/10)} ${T('jt','M')}`;
  const paidIds=new Set((data.ops||[]).filter(x=>x.status==='paid').map(x=>x.id));
  const open=Object.keys(withdrawalAmount7).filter(id=>!paidIds.has(id));
  const max=Math.max(c.eligible.amount,d.total),notReq=Math.max(0,max-d.total),closed=c.today>c.windowEnd,notLabels=Math.max(0,c.eligible.labels-c.requestedLabels);
  const pct=v=>max>0?v/max*100:0,reqPct=pct(d.total),daysPay=c.payDue-c.today;
  const head=card.querySelector('.withdraw-heading124');
  card.querySelectorAll(':scope>:not(.withdraw-heading124)').forEach(e=>e.remove());
  if(head){const p=head.querySelector('p');if(p)p.textContent=closed?T(`Pengajuan ditutup 14 Sep · bayar s.d. 20 Sep`,`Requests closed Sep 14 · pay by Sep 20`):T(`Pengajuan dibuka s.d. 14 Sep`,`Requests open until Sep 14`);}
  card.insertAdjacentHTML('beforeend',
    `<div class="pc131"><div class="pc-main131"><small>${T('Diajukan','Requested')}</small><strong>${jt(d.total)} <em>/ ${jt(max)}</em></strong><span>${nf(reqPct)}% ${T('dari yang bisa dicairkan bulan ini','of what can be withdrawn this month')} · ${c.requestedLabels} ${T('dari','of')} ${c.eligible.labels} label</span></div>`
   +`<div class="pc-acts131">${d.unpaid>0?`<button type="button" class="pc-act131" data-action="v6-metric" data-id="withdraw"><small>${T('Belum dibayar','Unpaid')}</small><b>${jt(d.unpaid)}</b><span>${open.length} ${T('pengajuan','requests')} · ${T(`${daysPay} hari lagi`,`${daysPay} days left`)}</span></button>`:''}`
   +`${notReq>0?`<button type="button" class="pc-act131 left" data-action="payable131-open"><small>${closed?T('Tidak diajukan','Not requested'):T('Belum diajukan','Not yet requested')}</small><b>${jt(notReq)}</b><span>${notLabels} label${closed?' → '+T('pemantauan','monitoring'):''}</span></button>`:''}</div></div>`
   +`<div class="withdrawal-meter127 wb131 pc-bar131"><div class="wb131-pct"><span></span><strong>${nf(pct(d.paid))}%</strong></div><div class="payout-track" role="progressbar" aria-label="${T('Bagian yang telah dibayar dari potensi bulan ini','Share of this month’s potential already paid')}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct(d.paid).toFixed(1)}" aria-valuetext="${nf(pct(d.paid))}% ${T('telah dibayarkan','paid')}"><i style="width:${pct(d.paid)}%"></i><s class="seg131 pay" style="left:${pct(d.paid)}%;width:${pct(d.unpaid)}%"></s><s class="seg131 left" style="left:${reqPct}%;width:${pct(notReq)}%"></s></div></div>`
   +`<div class="pc-legend131"><span><i class="wb131-dot paid"></i>${T('Dibayar','Paid')} ${jt(d.paid)}</span><span><i class="wb131-dot pay"></i>${T('Diajukan, belum dibayar','Requested, unpaid')} ${jt(d.unpaid)}</span><span><i class="wb131-dot left"></i>${closed?T('Tidak diajukan','Not requested'):T('Belum diajukan','Not yet requested')} ${jt(notReq)}</span></div>`
   +`<p class="pc-ctx131">${T(`Laporan ${c.report} diunggah ${c.uploaded} · royalti ${jt(c.reportTotal)} · ${jt(c.below.amount)} di bawah ambang Rp 1 jt bergulir ke bulan depan (${c.below.labels} label)`,`${c.report} report uploaded ${c.uploaded} · royalties ${jt(c.reportTotal)} · ${jt(c.below.amount)} below the Rp 1M threshold rolls over (${c.below.labels} labels)`)}</p>`);
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
