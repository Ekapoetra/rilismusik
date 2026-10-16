/* v1.1 dev.18 — Pemantauan Keuangan › "Kewajiban Royalti" (royalty payable / utang royalti ke label).
   Rekap per laporan bulanan: saldo yang BISA dicairkan (≥ Rp 1 jt) tetapi tidak diajukan sampai tgl 14,
   dan saldo yang BELUM BISA dicairkan (di bawah ambang Rp 1 jt). Keduanya tetap hak label → kewajiban
   Rilis Musik yang terakumulasi dari bulan ke bulan. Halaman: ringkasan, tren per laporan, umur saldo,
   dan daftar label dengan tindakan (pengingat). Angka rekap bulanan = data pratinjau; daftar label
   memakai saldo label prototype (kredit + penyesuaian − dibayar). */
'use strict';
const payable131={filter:'all',q:''};
const payableMonths131=[
  {m:'2026-04',report:98200000,eligible:84100000,elig:39,requested:70300000,below:10900000,belowN:281},
  {m:'2026-05',report:104600000,eligible:92800000,elig:41,requested:76000000,below:11400000,belowN:290},
  {m:'2026-06',report:112300000,eligible:101500000,elig:44,requested:83900000,below:11800000,belowN:298},
  {m:'2026-07',report:121900000,eligible:108700000,elig:46,requested:90200000,below:12100000,belowN:305},
  {m:'2026-08',report:131640000,eligible:118900000,elig:48,requested:99215767,below:12740000,belowN:312},
];
const ageing131=()=>[[T('< 1 bulan','< 1 month'),14200000,21],[T('1–3 bulan','1–3 months'),9600000,58],[T('3–6 bulan','3–6 months'),5900000,96],[T('> 6 bulan','> 6 months'),2720000,154]];
const jt131=n=>`Rp ${new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1}).format(Math.round(n/1e5)/10)} ${T('jt','M')}`;
const monthLabel131=k=>{const [y,m]=k.split('-').map(Number);return new Date(y,m-1,1).toLocaleDateString(state.lang==='id'?'id-ID':'en-US',{month:'short',year:'2-digit'});};
function payableLabels131(){
  const today=Date.parse('2026-09-18');
  return ((data.v9&&data.v9.labels)||[]).filter(l=>!l.master).map(l=>{const bal=(l.credit||0)+(l.adjustment||0)-(l.paid||0);
    const months=l.lastPayment?Math.max(0,Math.floor((today-Date.parse(l.lastPayment))/(30.4*86400000))):null;
    return {l,bal,eligible:bal>=1e6,months,blocked:l.restriction==='blocked'};}).filter(x=>x.bal>0).sort((a,b)=>b.bal-a.bal);
}
function payablePage131(){
  const cur=payableMonths131[payableMonths131.length-1],notReq=cur.eligible-cur.requested,total=notReq+cur.below,prev=payableMonths131[payableMonths131.length-2],prevTotal=prev.eligible-prev.requested+prev.below;
  const delta=(total-prevTotal)/prevTotal*100;
  const tiles=`<div class="py-tiles131">
    <div class="py-tile131 main"><small>${T('Kewajiban royalti berjalan','Running royalty payable')}</small><strong>${jt131(total)}</strong><span><span class="delta131" data-trend="${delta>=0?'up':'down'}"><svg viewBox="0 0 12 12" aria-hidden="true"><path d="${delta>=0?'M6 2.4 10.4 9.2H1.6z':'M6 9.6 1.6 2.8h8.8z'}"/></svg>${delta>=0?'+':''}${new Intl.NumberFormat(state.lang==='id'?'id-ID':'en-US',{maximumFractionDigits:1}).format(delta)}%</span> ${T('dibanding laporan Juli','vs July report')}</span></div>
    <div class="py-tile131"><small><i class="py-dot131 a"></i>${T('Siap cair, tidak diajukan','Withdrawable, not requested')}</small><strong>${jt131(notReq)}</strong><span>${cur.elig-31} label · ≥ Rp 1 jt</span></div>
    <div class="py-tile131"><small><i class="py-dot131 b"></i>${T('Belum bisa dicairkan','Not yet withdrawable')}</small><strong>${jt131(cur.below)}</strong><span>${cur.belowN} label · < Rp 1 jt</span></div>
    <div class="py-tile131"><small><i class="py-dot131 c"></i>${T('Diajukan, dalam pembayaran','Requested, being paid')}</small><strong>${jt131(24215767)}</strong><span>${T('bukan bagian kewajiban mengendap','not part of the idle payable')}</span></div></div>`;
  const maxT=Math.max(...payableMonths131.map(r=>r.eligible-r.requested+r.below));
  const chart=`<div class="py-chart131">${payableMonths131.map(r=>{const a=r.eligible-r.requested,b=r.below,h=v=>v/maxT*100;return `<div class="py-col131" title="${monthLabel131(r.m)} · ${jt131(a+b)}"><b>${jt131(a+b)}</b><div class="py-stack131"><i class="b" style="height:${h(b)}%"></i><i class="a" style="height:${h(a)}%"></i></div><small>${monthLabel131(r.m)}</small></div>`;}).join('')}</div>`;
  const table=`<div class="table-wrap py-table131"><table><thead><tr><th>${T('Laporan','Report')}</th><th>${T('Royalti laporan','Report royalties')}</th><th>${T('Bisa dicairkan','Withdrawable')}</th><th>${T('Diajukan','Requested')}</th><th>${T('Tidak diajukan','Not requested')}</th><th>${T('Di bawah ambang','Below threshold')}</th><th>${T('Kewajiban','Payable')}</th></tr></thead><tbody>${payableMonths131.slice().reverse().map(r=>`<tr><td>${monthLabel131(r.m)}</td><td>${jt131(r.report)}</td><td>${jt131(r.eligible)} <small>${r.elig} label</small></td><td>${jt131(r.requested)} <small>${Math.round(r.requested/r.eligible*100)}%</small></td><td>${jt131(r.eligible-r.requested)}</td><td>${jt131(r.below)}</td><td><b>${jt131(r.eligible-r.requested+r.below)}</b></td></tr>`).join('')}</tbody></table></div>`;
  const ageMax=Math.max(...ageing131().map(a=>a[1]));
  const ageing=`<div class="py-age131">${ageing131().map(([k,v,n])=>`<div class="py-agerow131"><span>${k}</span><div class="py-agebar131"><i style="width:${v/ageMax*100}%"></i></div><b>${jt131(v)}</b><small>${n} label</small></div>`).join('')}<p class="hint131">${T('Umur dihitung dari laporan saat saldo pertama kali muncul. Saldo > 6 bulan sebaiknya dihubungi langsung.','Age counts from the report where the balance first appeared. Balances > 6 months should be contacted directly.')}</p></div>`;
  let rows=payableLabels131();
  if(payable131.filter==='eligible')rows=rows.filter(x=>x.eligible);else if(payable131.filter==='below')rows=rows.filter(x=>!x.eligible);
  if(payable131.q)rows=rows.filter(x=>x.l.name.toLowerCase().includes(payable131.q.toLowerCase()));
  const list=`<div class="py-listhead131"><div class="seg131">${[['all',T('Semua','All')],['eligible',T('Siap cair','Withdrawable')],['below',T('Di bawah ambang','Below threshold')]].map(([id,l])=>`<button type="button" class="${payable131.filter===id?'on':''}" data-action="payable131-filter" data-id="${id}">${l}</button>`).join('')}</div><input type="search" data-input="payable131-q" value="${E(payable131.q)}" placeholder="${T('Cari label…','Search labels…')}" aria-label="${T('Cari label','Search labels')}"></div>
    <div class="table-wrap py-table131"><table><thead><tr><th>Label</th><th>${T('Saldo','Balance')}</th><th>${T('Status','Status')}</th><th>${T('Pembayaran terakhir','Last payment')}</th><th></th></tr></thead><tbody>${rows.map(x=>`<tr><td>${E(x.l.name)}</td><td><b>${money(x.bal)}</b></td><td>${x.blocked?statusBadge111(T('Ditangguhkan','Suspended'),'red'):x.eligible?statusBadge111(T('Siap cair · tidak diajukan','Withdrawable · not requested'),'mustard'):statusBadge111(T(`Perlu ${jt131(1e6-x.bal)} lagi`,`Needs ${jt131(1e6-x.bal)} more`),'neutral')}</td><td>${x.l.lastPayment?new Date(x.l.lastPayment).toLocaleDateString(state.lang==='id'?'id-ID':'en-US',{day:'numeric',month:'short',year:'numeric'})+(x.months!=null?` <small>${x.months?x.months+' '+T('bln lalu','mo ago'):T('bulan ini','this month')}</small>`:''):'—'}</td><td>${x.eligible&&!x.blocked?btn(T('Kirim pengingat','Send reminder'),'payable131-remind',`data-id="${E(x.l.id)}"`,'small'):''}</td></tr>`).join('')||`<tr><td colspan="5">${T('Tidak ada label.','No labels.')}</td></tr>`}</tbody></table></div>`;
  return `<div class="py131">${tiles}
    <div class="py-grid131"><section class="panel pad py-sec131"><header><h2>${T('Kewajiban per laporan','Payable per report')}</h2><span class="py-legend131"><span><i class="py-dot131 a"></i>${T('Siap cair, tidak diajukan','Withdrawable, not requested')}</span><span><i class="py-dot131 b"></i>${T('Di bawah ambang','Below threshold')}</span></span></header>${chart}${table}</section>
    <section class="panel pad py-sec131"><header><h2>${T('Umur saldo','Balance age')}</h2></header>${ageing}</section></div>
    <section class="panel pad py-sec131"><header><h2>${T('Label dengan saldo belum dicairkan','Labels with unpaid balances')}</h2><span class="hint131">${T('Saldo = kredit + penyesuaian − dibayar','Balance = credits + adjustments − paid')}</span></header>${list}</section>
    <p class="hint131 py-note131">${T('Rekap per laporan & umur saldo: data pratinjau. Kewajiban = saldo siap cair yang tidak diajukan s.d. tgl 14 + saldo di bawah ambang Rp 1 jt; saldo yang sedang dibayar tidak dihitung.','Per-report recap & balance age: preview data. Payable = withdrawable balances not requested by the 14th + balances below the Rp 1M threshold; balances being paid are excluded.')}</p></div>`;
}
/* Tab baru di Pemantauan Keuangan, setelah "Pemantauan Dana". */
const monitorTabsBefore131=monitorTabs121;
monitorTabs121=function(){const h=monitorTabsBefore131();const btnHtml=B121(T('Kewajiban Royalti','Royalty Payable'),'monitor','payable',ui121.monitor==='payable'?'active':'text');
  const i=h.indexOf('</button>');return i<0?h:h.slice(0,i+9)+btnHtml+h.slice(i+9);};
const liabilityBefore131=liabilityPage9;
liabilityPage9=function(){
  if(ui121.monitor==='payable'){if(ten.role!=='super'||!super114())return denied9();return pageHead(T('Pemantauan Royalti','Royalty Monitoring'),'')+monitorTabs121()+payablePage131();}
  return liabilityBefore131();
};
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='payable131-filter'){payable131.filter=id;render();}
  else if(a==='payable131-remind'){const l=((data.v9&&data.v9.labels)||[]).find(x=>x.id===id);toast(T(`Pengingat pengajuan dikirim ke ${l?l.name:'label'} (simulasi).`,`Request reminder sent to ${l?l.name:'label'} (simulation).`));b.disabled=true;b.textContent=T('Terkirim','Sent');}
  else if(a==='payable131-open'){ui121.monitor='payable';go('liability9','platform');}
  else return;
  e.preventDefault();e.stopImmediatePropagation();
},true);
document.addEventListener('input',e=>{const i=e.target.closest('[data-input="payable131-q"]');if(!i)return;payable131.q=i.value;clearTimeout(payable131._t);payable131._t=setTimeout(()=>{const pos=i.selectionStart;render();const n=document.querySelector('[data-input="payable131-q"]');if(n){n.focus();n.setSelectionRange(pos,pos);}},180);});
