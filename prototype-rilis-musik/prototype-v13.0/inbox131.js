/* v1.1 dev.11–13 — Kotak Masuk: notifikasi + percakapan dalam SATU tata letak tiga kolom
   (pola kotak masuk bersama ala Front/Zendesk):
     kiri   = navigasi: Notifikasi (per jenis) · Percakapan (Semua · Tiket & label · Internal)
     tengah = daftar item tampilan terpilih
     kanan  = detail: notifikasi → isi + objek terkait; tiket → percakapan dengan label DAN
              catatan internal dalam satu linimasa (catatan bergaris putus-putus + gembok);
              ruang internal → percakapan staf dengan pita "tidak terlihat oleh label".
   Pembeda jenis tanpa memakai warna Kamus: tiket = avatar label + ID tiket + chip status;
   internal = ikon gembok + tag "Internal"; notifikasi = ikon jenis dalam kotak bulat.
   Lonceng & ikon chat tetap membuka popover ringkas dengan tautan "Buka Kotak Masuk".
   Halaman memakai mekanisme modul v4 (v4.module) agar tidak menyentuh peta halaman app.js. */
'use strict';
const inbox131={view:'c:all',sel:null,search:'',waiting:false,mode:'reply'};
modules.push({id:'inbox131',group:'ops',title:['Kotak Masuk','Inbox'],desc:['Notifikasi dan percakapan dalam satu pintu.','Notifications and conversations in one place.'],actions:['',''],note:['',''],access:''});
const allowedBeforeInbox131=allowedModule;
allowedModule=function(m){if(m&&(m.id==='inbox131'||m.id==='profile131'))return true;return allowedBeforeInbox131(m);};

/* ---------- ikon kecil ---------- */
const ico131={
  finance:'<path d="M3 7h18v12H3z"/><path d="M3 10h18M16 15h2"/>',
  release:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
  support:'<path d="M4 5h16v11H9l-5 4z"/>',
  personal:'<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
  system:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2m10-10 2-2"/>',
  ticket:'<path d="M3 8a2 2 0 0 0 0 4v0a2 2 0 0 1 0 4v2h18v-2a2 2 0 0 1 0-4 2 2 0 0 0 0-4V6H3z"/><path d="M14 6v12" stroke-dasharray="2 2"/>',
  lock:'<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  all:'<path d="M4 6h16M4 12h16M4 18h10"/>',
  bell:'<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
  chat:'<path d="M4 5h16v11H9l-5 4z"/>',
};
const svg131=k=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ico131[k]||''}</svg>`;

/* ---------- notifikasi ---------- */
const kinds131=[['all',['Semua notifikasi','All notifications']],['finance',['Pembayaran','Payments']],['release',['Rilisan','Releases']],['support',['Tiket & chat','Tickets & chat']],['personal',['Personal','Personal']],['system',['Sistem','System']]];
function kindOf131(n){if(n.permission==='finance')return 'finance';if(n.permission==='release'||n.permission==='claim')return 'release';if(n.permission==='support')return 'support';if(n.page==='attendance'||n.page==='profile'||n.target!=='all')return 'personal';return 'system';}
const isUnread131=n=>!n.read.includes(me().id);
const dayOf131=n=>/^\d{1,2}\.\d{2}$/.test(n.time)?t('Hari ini','Today'):n.time;
const kindName131=k=>L((kinds131.find(x=>x[0]===k)||kinds131[0])[1]);

/* ---------- percakapan ----------
   Tiket menyatukan percakapan label (data.chats.label untuk T-318 — sama dengan popover) dan
   catatan internal. Tiket contoh tambahan hanya untuk tampilan dan disimpan di data.inbox131
   (tidak mengubah berkas data contoh). */
function threadStore131(){
  if(!data.inbox131){data.inbox131={tickets:[
    {id:'T-318',label:'Senja Records',subject:['Metadata · Kumari','Metadata · Kumari'],obj:'R-1048',status:'handling',chat:'label',notes:[{who:'adovi',text:['Believe belum membalas; jadwalkan tindak lanjut Jumat.','Believe has not replied; follow up on Friday.'],at:'09.12'}]},
    {id:'T-322',label:'Awan Records',subject:['Takedown · Langit Biru','Takedown · Langit Biru'],obj:'R-1031',status:'awaiting_distributor',msgs:[{who:'Awan Records',text:['Mohon takedown rilisan Langit Biru di semua platform.','Please take down Langit Biru on all platforms.'],at:'Kem 14.20'},{who:'cantika',text:['Sudah kami teruskan ke distributor. Estimasi 3–5 hari kerja.','Forwarded to the distributor. Estimated 3–5 working days.'],at:'Kem 15.02'}],notes:[{who:'cantika',text:['Tiket distributor #88213.','Distributor ticket #88213.'],at:'Kem 15.03'}]},
    {id:'T-325',label:'Utara Music',subject:['Ubah metadata · Biru Kembali','Metadata change · Biru Kembali'],obj:'R-1061',status:'awaiting_label',msgs:[{who:'eka',text:['Mohon kirim surat persetujuan dari pemegang hak untuk perubahan nama artis.','Please send the rights-holder approval letter for the artist name change.'],at:'08.40'}],notes:[]},
  ]};}
  return data.inbox131;
}
const ticketSteps131=[['submitted',['Diajukan','Submitted']],['handling',['Dalam penanganan','In progress']],['awaiting_label',['Perlu tanggapan label','Needs label response']],['awaiting_distributor',['Menunggu distributor','Awaiting distributor']],['completed',['Selesai','Completed']]];
const ticketTone131={submitted:'blue',handling:'blue',awaiting_label:'mustard',awaiting_distributor:'blue',completed:'green',closed:'neutral'};
const stepName131=s=>L((ticketSteps131.find(x=>x[0]===s)||[s,[s,s]])[1]);
const personOf131=w=>{try{return typeof person==='function'?person(w):null;}catch{return null;}};
const whoName131=w=>personOf131(w)?.name||w;
const isStaff131=w=>!!personOf131(w);
const isMine131=w=>w===me().id||w===me().name;
const msgText131=m=>Array.isArray(m.text)?L(m.text):String(m.text||m.note||'');
const initials131=n=>String(n||'').split(/\s+/).filter(Boolean).slice(0,2).map(s=>s[0]).join('').toUpperCase();
const labelVerified131=name=>{try{const l=(data.v9.labels||[]).find(x=>x.name===name);return !!(l&&verification9(l).status==='verified');}catch{return false;}};

/* urutan linimasa: waktu "HH.MM" (Kem = kemarin), pesan baru (ts) paling akhir; tanpa waktu → urutan asli */
function key131(at,i){if(typeof at==='number')return at;const m=/(Kems)?(d{1,2}).(d{2})/.exec(at||'');if(m)return (m[1]?-1440:0)+(+m[2])*60+(+m[3]);return /baru|just/.test(at||'')?1e7+i:i;}
function threads131(){
  const st=threadStore131(),out=[];
  if(permission('support')!=='none')for(const tk of st.tickets){
    const label=tk.chat?(data.chats[tk.chat]||[]):tk.msgs;
    const defAt=tk.chat==='label'?['09.02','09.10']:[];const items=[...label.map((m,i)=>({...m,at:m.at||defAt[i],kind:'msg',k:key131(m.ts||m.at||defAt[i],i)})),...tk.notes.map((m,i)=>({...m,kind:'note',k:key131(m.ts||m.at,100+i)}))].sort((a,b)=>a.k-b.k);
    const lastLabel=label[label.length-1];
    out.push({id:'t:'+tk.id,type:'ticket',tk,time:(label[label.length-1]||{}).at||(tk.id==='T-318'?'10.45':''),title:tk.label,sub:L(tk.subject),code:tk.id,items,labelCount:label.length,noteCount:tk.notes.length,
      last:items.length?msgText131(items[items.length-1]):'',waiting:!!lastLabel&&!isStaff131(lastLabel.who)});
  }
  const room=data.chats.internal||[],lastRoom=room[room.length-1];
  out.push({id:'i:room',type:'internal',title:t('Koordinasi internal','Internal coordination'),sub:t('Catatan terkait R-1055','Notes about R-1055'),code:'R-1055',items:room.map(m=>({...m,kind:'msg'})),
    last:lastRoom?msgText131(lastRoom):'',waiting:!!lastRoom&&!isMine131(lastRoom.who)});
  return out;
}

/* ---------- halaman ---------- */
function openInbox131(view){if(view)inbox131.view=view;try{closeModal();}catch{}try{closePop();}catch{}module102('inbox131');render();window.scrollTo(0,0);}
function markAllRead131(){visibleNotifications().forEach(n=>{if(isUnread131(n))n.read.push(me().id);});if(typeof save10==='function')save10();render();}

function searchBox131(){return `<div class="search131">${svg131('all')}<input type="search" data-input="inbox131-search" value="${E(inbox131.search)}" placeholder="${t('Cari…','Search…')}" aria-label="${t('Cari','Search')}"></div>`;}
function bubble131(m){
  const mine=isMine131(m.who),note=m.kind==='note',staff=isStaff131(m.who);
  return `<div class="msg131 ${mine?'mine':''} ${note?'note':''}"><span class="msg-who131">${note?svg131('lock'):''}${E(whoName131(m.who))}${note?` · ${t('catatan internal','internal note')}`:staff?'':` · ${t('label','label')}`}${m.at?` · ${E(m.at)}`:''}</span><p>${E(msgText131(m))}</p></div>`;
}
/* ---------- dev.18: CH-A (pilihan pemilik) — chat lebih dulu ----------
   Tata letak: daftar (kiri) · percakapan (tengah) · konteks (kanan), tanpa judul halaman.
   Notification Center TIDAK jadi menu terpisah: pengalih "Percakapan | Notifikasi" di kepala daftar;
   popover lonceng "Buka Kotak Masuk" membuka mode Notifikasi; notifikasi yang terkait objek tiket
   juga tampil di panel konteks sebagai "Aktivitas terkait". */
const ticketMeta131={'T-318':{cat:['Metadata','Metadata'],opened:'16 Sep · 09.02',owner:'adovi'},'T-322':{cat:['Takedown','Takedown'],opened:'17 Sep · 14.20',owner:'cantika'},'T-325':{cat:['Ubah metadata','Metadata change'],opened:'18 Sep · 08.31',owner:'eka'}};
const quick131=[['Terima kasih, kami cek dulu.','Thanks, we will check.'],['Mohon lengkapi dokumen pendukung.','Please complete the supporting documents.'],['Sudah kami teruskan ke distributor.','We have forwarded it to the distributor.']];
const modeOf131=()=>inbox131.view.startsWith('n:')?'notif':'chat';
function inboxPage131(){
  const notes=visibleNotifications(),th=threads131(),unread=notes.filter(isUnread131).length,waiting=th.filter(x=>x.waiting).length,mode=modeOf131();
  const sw=`<div class="cha-switch131" role="tablist">${[['c:all',t('Percakapan','Conversations'),waiting,'chat'],['n:all',t('Notifikasi','Notifications'),unread,'notif']].map(([v,l,n,m])=>`<button type="button" role="tab" aria-selected="${mode===m}" class="${mode===m?'on':''}" data-action="inbox131-view" data-id="${v}">${l}${n?`<b>${n}</b>`:''}</button>`).join('')}</div>`;
  return `<section class="cha131">${mode==='chat'?chatA131(th,sw):notifA131(notes,sw)}</section>`;
}
function rowThread131(x){
  const lead=x.type==='ticket'?`<span class="avatar lead131">${initials131(x.title)}</span>`:`<span class="kind-ico131 lock131">${svg131('lock')}</span>`;
  return `<button type="button" class="row131 ${x.id===inbox131.sel?'active':''}" data-action="inbox131-sel" data-id="${x.id}">${lead}<span class="row-main131"><span class="row-top131"><strong>${E(x.title)}</strong><time>${E(x.time||'')}</time></span><span class="row-meta131"><span class="code131">${E(x.code)}</span>${E(x.sub)}</span><span class="row-sub131">${E(x.last)}</span></span>${x.waiting?'<i class="udot131" title="'+t('Menunggu jawabanmu','Awaiting your reply')+'"></i>':''}</button>`;
}
function chatA131(all,sw){
  const v=inbox131.view.slice(2),q=inbox131.search.toLowerCase();
  let th=all.filter(x=>v==='all'||x.type===v);
  if(q)th=th.filter(x=>(x.title+' '+x.sub+' '+x.code+' '+x.last).toLowerCase().includes(q));
  if(inbox131.waiting)th=th.filter(x=>x.waiting);
  if(!th.some(x=>x.id===inbox131.sel))inbox131.sel=th[0]?.id||null;
  const cur=th.find(x=>x.id===inbox131.sel);
  const tabs=`<div class="cha-tabs131">${[['all',t('Semua','All'),all.filter(x=>x.waiting).length],['ticket',t('Label & tiket','Labels & tickets'),all.filter(x=>x.type==='ticket'&&x.waiting).length],['internal',t('Internal','Internal'),0]].map(([id,l,n])=>`<button type="button" class="${v===id?'on':''}" data-action="inbox131-view" data-id="c:${id}">${l}${n?` <b>${n}</b>`:''}</button>`).join('')}<button type="button" class="cha-wait131 ${inbox131.waiting?'on':''}" aria-pressed="${inbox131.waiting}" data-action="inbox131-waiting" title="${t('Hanya yang menunggu jawabanku','Only awaiting my reply')}">${svg131('chat')}</button></div>`;
  const list=`<aside class="cha-list131"><header class="cha-lhead131">${sw}</header>${tabs}${searchBox131()}<div class="rows131i">${th.map(rowThread131).join('')||`<p class="hint131 pad131">${t('Tidak ada percakapan yang cocok.','No matching conversation.')}</p>`}</div></aside>`;
  if(!cur)return list+`<article class="cha-mid131">${empty(t('Pilih percakapan','Pick a conversation'))}</article><aside class="cha-ctx131"></aside>`;
  return list+chatMid131(cur)+chatCtx131(cur);
}
function chatMid131(x){
  const tk=x.tk,note=inbox131.mode==='note'||x.type==='internal';
  const head=x.type==='ticket'
    ?`<header class="thread-head131"><span class="avatar lead131 big">${initials131(x.title)}</span><div class="th-id131"><h2>${E(x.title)}</h2><small><span class="code131">${E(tk.id)}</span>${E(x.sub)} · ${E(tk.obj)}</small></div><div class="th-ctl131">${statusBadge111(stepName131(tk.status),ticketTone131[tk.status])}${btn(t('Buka tiket','Open ticket'),'inbox131-ticket',`data-id="${E(tk.id)}"`,'small')}</div></header>`
    :`<header class="thread-head131"><span class="kind-ico131 lock131 big">${svg131('lock')}</span><div class="th-id131"><h2>${E(x.title)}</h2><small><span class="code131">${E(x.code)}</span>${E(x.sub)}</small></div><div class="th-ctl131"><span class="tag131">${t('Hanya staf','Staff only')}</span></div></header>`;
  const composer=`<form class="composer131 ${note?'note':''}" data-form="inbox131-send">${x.type==='ticket'&&!note?`<div class="quick131">${quick131.map((q,i)=>`<button type="button" data-action="inbox131-quick" data-id="${i}">${L(q)}</button>`).join('')}</div>`:''}${x.type==='ticket'?`<div class="mode131" role="tablist"><button type="button" role="tab" aria-selected="${!note}" class="${!note?'on':''}" data-action="inbox131-mode" data-id="reply">${t('Balas ke label','Reply to label')}</button><button type="button" role="tab" aria-selected="${note}" class="${note?'on':''}" data-action="inbox131-mode" data-id="note">${svg131('lock')}${t('Catatan internal','Internal note')}</button></div>`:''}<div class="compose-row131"><textarea name="text" rows="2" placeholder="${x.type==='internal'?t('Tulis ke tim internal…','Write to the internal team…'):note?t('Catatan untuk staf — tidak terlihat oleh label','Note for staff — not visible to the label'):t(`Balas ke ${x.title}…`,`Reply to ${x.title}…`)}" aria-label="${t('Pesan','Message')}"></textarea><button type="submit" class="btn primary small">${note&&x.type==='ticket'?t('Simpan catatan','Save note'):t('Kirim','Send')}</button></div></form>`;
  return `<article class="cha-mid131">${head}${x.type==='internal'?`<div class="banner131">${svg131('lock')}${t('Ruang internal staf — tidak terlihat oleh label.','Staff-only room — not visible to labels.')}</div>`:''}<div class="msgs131"><span class="day131c">${t('Hari ini','Today')}</span>${x.items.map(bubble131).join('')||`<p class="hint131">${t('Belum ada pesan.','No messages yet.')}</p>`}</div>${composer}</article>`;
}
function relatedNotes131(obj){return obj?visibleNotifications().filter(n=>n.obj===obj):[];}
function chatCtx131(x){
  if(x.type==='internal'){const who=[...new Set(x.items.map(m=>m.who))].map(w=>personOf131(w)).filter(Boolean);
    return `<aside class="cha-ctx131"><section class="ctx-sec131"><h4>${t('Ruang','Room')}</h4><div class="kv131c"><span>${t('Terkait','Related')}</span><b>${E(x.code)}</b><span>${t('Anggota','Members')}</span><b>${who.length}</b></div><div class="faces131 ctx-faces131">${who.map(p=>`<span class="avatar" title="${E(p.name)}">${p.initials}</span>`).join('')}</div></section><section class="ctx-sec131"><h4>${t('Tindakan','Actions')}</h4><div class="ctx-acts131">${btn(t(`Buka ${x.code}`,`Open ${x.code}`),'task',`data-id="${E(x.code)}"`,'small')}</div></section>${ctxNotes131(relatedNotes131(x.code))}</aside>`;}
  const tk=x.tk,meta=ticketMeta131[tk.id]||{},idx=ticketSteps131.findIndex(s=>s[0]===tk.status),lab=(ten.members||[]).find(m=>m.name===tk.label);
  return `<aside class="cha-ctx131">
    <section class="ctx-sec131"><h4>${t('Tiket','Ticket')}</h4><div class="kv131c"><span>${t('Kategori','Category')}</span><b>${meta.cat?L(meta.cat):'—'}</b><span>${t('Rilisan','Release')}</span><b>${E(L(tk.subject).split('·').pop().trim())} · ${E(tk.obj)}</b><span>${t('Dibuka','Opened')}</span><b>${E(meta.opened||'—')}</b><span>${t('Penanggung','Owner')}</span><b>${E(whoName131(meta.owner||'')||'—')}</b></div></section>
    <section class="ctx-sec131"><h4>${t('Tahapan','Stages')}</h4><ol class="vsteps131">${ticketSteps131.map(([k,l],i)=>`<li class="${i<idx?'d':i===idx?'n':''}"><i></i>${L(l)}</li>`).join('')}</ol></section>
    <section class="ctx-sec131"><h4>${t('Tindakan','Actions')}</h4><div class="ctx-acts131">${idx<ticketSteps131.length-1?btn(t(`Lanjut ke "${L(ticketSteps131[idx+1][1])}"`,`Move to "${L(ticketSteps131[idx+1][1])}"`),'inbox131-advance',`data-id="${E(tk.id)}"`,'small'):''}${tk.status!=='awaiting_distributor'&&tk.status!=='completed'?btn(t('Teruskan ke distributor','Forward to distributor'),'inbox131-forward',`data-id="${E(tk.id)}"`,'small'):''}${btn(t(`Buka rilisan ${tk.obj}`,`Open release ${tk.obj}`),'task',`data-id="${E(tk.obj)}"`,'small')}</div></section>
    <section class="ctx-sec131"><h4>Label</h4><div class="kv131c"><span>${t('Paket','Plan')}</span><b>${E(lab?.plan||'—')}${lab?.active?' · '+t('aktif','active'):''}</b><span>${t('Tiket terbuka','Open tickets')}</span><b>${threadStore131().tickets.filter(z=>z.label===tk.label&&z.status!=='completed').length}</b><span>Email</span><b>${E(lab?.email||'—')}</b></div></section>
    ${ctxNotes131(relatedNotes131(tk.obj))}</aside>`;
}
function ctxNotes131(list){return `<section class="ctx-sec131"><h4>${t('Aktivitas terkait','Related activity')}</h4>${list.length?list.map(n=>`<button type="button" class="ctx-note131" data-action="inbox131-noteopen" data-id="${n.id}"><span class="kind-ico131 sm">${svg131(kindOf131(n))}</span><span><b>${L(n.title)}</b><small>${n.time}</small></span></button>`).join(''):`<p class="hint131">${t('Belum ada notifikasi terkait.','No related notifications.')}</p>`}</section>`;}
function notifA131(all,sw){
  const k=inbox131.view.slice(2),q=inbox131.search.toLowerCase();
  const list=all.filter(n=>(k==='all'||kindOf131(n)===k)&&(!q||(L(n.title)+' '+L(n.body)+' '+(n.obj||'')).toLowerCase().includes(q)));
  if(!list.some(n=>n.id===inbox131.sel))inbox131.sel=list[0]?.id||null;
  const cur=list.find(n=>n.id===inbox131.sel),unread=all.filter(isUnread131).length;
  const chips=`<div class="cha-chips131">${kinds131.map(([id,l])=>`<button type="button" class="${k===id?'on':''}" data-action="inbox131-view" data-id="n:${id}">${id==='all'?t('Semua','All'):L(l)}</button>`).join('')}</div>`;
  let day='';const rows=list.map(n=>{const d=dayOf131(n),head=d!==day?`<h4 class="day131">${d}</h4>`:'';day=d;return head+`<button type="button" class="row131 ${n.id===inbox131.sel?'active':''} ${isUnread131(n)?'unread':''}" data-action="inbox131-sel" data-id="${n.id}"><span class="kind-ico131">${svg131(kindOf131(n))}</span><span class="row-main131"><span class="row-top131"><strong>${L(n.title)}</strong><time>${n.time}</time></span><span class="row-sub131">${L(n.body)}</span></span>${isUnread131(n)?'<i class="udot131"></i>':''}</button>`;}).join('');
  const left=`<aside class="cha-list131"><header class="cha-lhead131">${sw}</header>${chips}<div class="cha-subhead131"><small>${list.length} ${t('notifikasi','notifications')}</small>${btn(t('Tandai semua dibaca','Mark all read'),'inbox131-read',unread?'':'disabled','small text')}</div>${searchBox131()}<div class="rows131i">${rows||`<p class="hint131 pad131">${t('Tidak ada notifikasi.','No notifications.')}</p>`}</div></aside>`;
  if(!cur)return left+`<article class="cha-mid131">${empty(t('Pilih notifikasi','Pick a notification'))}</article><aside class="cha-ctx131"></aside>`;
  const kk=kindOf131(cur),conv=threads131().find(x=>x.type==='ticket'&&x.tk.obj&&x.tk.obj===cur.obj);
  const mid=`<article class="cha-mid131 nmid131"><div class="eyebrow131">${svg131(kk)}<span>${kindName131(kk)}</span><span>·</span><time>${dayOf131(cur)}${/^\d/.test(cur.time)&&dayOf131(cur)!==cur.time?' '+cur.time:''}</time></div><h2 class="detail-title131">${L(cur.title)}</h2><p class="detail-body131">${L(cur.body)}</p><p class="hint131">${t('Membaca notifikasi tidak menyelesaikan pekerjaan terkait.','Reading a notification does not complete the related work.')}</p></article>`;
  const ctx=`<aside class="cha-ctx131">${cur.obj||cur.page?`<section class="ctx-sec131"><h4>${t('Objek terkait','Related item')}</h4><div class="obj131"><span class="obj-ico131">${svg131(kk==='personal'?'personal':'release')}</span><div><strong>${E(cur.obj||pages()[cur.page]||cur.page)}</strong></div>${btn(t('Buka','Open'),'notification-open',`data-id="${cur.id}"`,'small primary')}</div></section>`:''}${conv?`<section class="ctx-sec131"><h4>${t('Percakapan terkait','Related conversation')}</h4><button type="button" class="ctx-note131" data-action="inbox131-goconv" data-id="${conv.id}"><span class="avatar lead131">${initials131(conv.title)}</span><span><b>${E(conv.title)}</b><small>${E(conv.code)} · ${E(conv.sub)}</small></span></button></section>`:''}<section class="ctx-sec131"><h4>${t('Tindakan','Actions')}</h4><div class="ctx-acts131">${btn(t('Tandai belum dibaca','Mark unread'),'inbox131-unread',`data-id="${cur.id}"`,'small')}</div></section></aside>`;
  return left+mid+ctx;
}
function sendMessage131(form){
  const text=form.elements.text.value.trim();if(!text)return;const id=inbox131.sel;if(!id)return;
  const msg={who:me().id,text:[text,text],at:t('baru saja','just now'),ts:Date.now()};
  if(id==='i:room')(data.chats.internal=data.chats.internal||[]).push(msg);
  else if(id.startsWith('t:')){const tk=threadStore131().tickets.find(x=>x.id===id.slice(2));if(!tk)return;
    if(inbox131.mode==='note')tk.notes.push(msg);else if(tk.chat)(data.chats[tk.chat]=data.chats[tk.chat]||[]).push(msg);else tk.msgs.push(msg);}
  if(typeof save10==='function')save10();render();
  const box=document.querySelector('.msgs131');if(box)box.scrollTop=box.scrollHeight;
}

/* Popover ringkas tetap; tambahkan tautan ke halaman penuh di judulnya. */
const chatModalBase131=chatModal,notificationModalBase131=notificationModal;
function inboxLink131(view){const head=document.querySelector('#header-popover .popover-title>div');if(!head||head.querySelector('[data-action=inbox131-page]'))return;head.insertAdjacentHTML('afterbegin',btn(t('Buka Kotak Masuk','Open Inbox'),'inbox131-page',`data-id="${view}"`,'text'));}
chatModal=function(){chatModalBase131();inboxLink131('c:all');};
notificationModal=function(){notificationModalBase131();inboxLink131('n:all');};

document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='inbox131-view'){if(id[0]!==inbox131.view[0])inbox131.sel=null;inbox131.view=id;inbox131.search='';render();}
  else if(a==='inbox131-sel'){inbox131.sel=id;const n=visibleNotifications().find(x=>x.id===id);if(n&&isUnread131(n)){n.read.push(me().id);if(typeof save10==='function')save10();}if(id.startsWith('i:'))inbox131.mode='reply';render();}
  else if(a==='inbox131-read')markAllRead131();
  else if(a==='inbox131-waiting'){inbox131.waiting=!inbox131.waiting;render();}
  else if(a==='inbox131-mode'){inbox131.mode=id;render();document.querySelector('.composer131 textarea')?.focus();}
  else if(a==='inbox131-quick'){const ta=document.querySelector('.composer131 textarea');if(ta){ta.value=L(quick131[+id]);ta.focus();}}
  else if(a==='inbox131-advance'||a==='inbox131-forward'){const tk=threadStore131().tickets.find(x=>x.id===id);if(!tk)return;const i=ticketSteps131.findIndex(s=>s[0]===tk.status);tk.status=a==='inbox131-forward'?'awaiting_distributor':ticketSteps131[Math.min(i+1,ticketSteps131.length-1)][0];tk.notes.push({who:me().id,text:[`Status diubah ke "${L(ticketSteps131.find(s=>s[0]===tk.status)[1])}".`,`Status changed to "${L(ticketSteps131.find(s=>s[0]===tk.status)[1])}".`],at:t('baru saja','just now'),ts:Date.now()});if(typeof save10==='function')save10();render();toast(t('Status tiket diperbarui (simulasi).','Ticket status updated (simulation).'));}
  else if(a==='inbox131-noteopen'){inbox131.view='n:all';inbox131.sel=id;const n=visibleNotifications().find(x=>x.id===id);if(n&&isUnread131(n))n.read.push(me().id);render();}
  else if(a==='inbox131-goconv'){inbox131.view='c:all';inbox131.sel=id;render();}
  else if(a==='inbox131-unread'){const n=visibleNotifications().find(x=>x.id===id);if(n)n.read=n.read.filter(r=>r!==me().id);if(typeof save10==='function')save10();render();}
  else if(a==='inbox131-page')openInbox131(id);
  else if(a==='inbox131-ticket'){if(typeof route102==='function')route102('tickets');}
  else return;
  e.preventDefault();e.stopImmediatePropagation();
},true);
document.addEventListener('input',e=>{const i=e.target.closest('[data-input="inbox131-search"]');if(!i)return;inbox131.search=i.value;clearTimeout(inbox131._t);inbox131._t=setTimeout(()=>{const pos=i.selectionStart;render();const n=document.querySelector('[data-input="inbox131-search"]');if(n){n.focus();n.setSelectionRange(pos,pos);}},180);});
document.addEventListener('submit',e=>{const f=e.target.closest('form[data-form="inbox131-send"]');if(!f)return;e.preventDefault();e.stopImmediatePropagation();sendMessage131(f);},true);
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&e.target.closest('.composer131 textarea')){e.preventDefault();sendMessage131(e.target.form);}});
const modulePageBeforeInbox131=modulePage;
modulePage=function(){if(v4.module==='inbox131')return inboxPage131();return modulePageBeforeInbox131();};

/* dev.15: ikon Kotak Masuk di menu header, tepat setelah Home (kontrol Super Admin v127).
   Aktif saat halaman Kotak Masuk terbuka; titik kecil bila ada notifikasi belum dibaca atau
   percakapan yang menunggu jawaban. */
if(typeof headerControls127!=='undefined'&&!headerControls127.some(c=>c.id==='inbox')){
  headerControls127.splice(1,0,{id:'inbox',label:['Kotak Masuk','Inbox']});
  controlIcons127.inbox='<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5.5 5h13L21 13v6H3v-6z"/>';
  const activeBeforeInbox131=controlActive126;
  controlActive126=function(id){if(id==='inbox')return v4.module==='inbox131'&&!!document.querySelector('#main .cha131');if(id==='home'&&v4.module==='inbox131'&&document.querySelector('#main .cha131'))return false;return activeBeforeInbox131(id);};
  const goBeforeInbox131=goControl126;
  goControl126=function(id){if(id==='inbox')return openInbox131();return goBeforeInbox131(id);};
}
function markInboxIcon131(){
  const b=document.querySelector('.header [data-control126="inbox"]');if(!b)return;
  const on=v4.module==='inbox131'&&!!document.querySelector('#main .inbox3-131,#main .cha131');
  b.classList.toggle('active',on);if(on)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');
  if(on)document.querySelectorAll('.header [data-control126="home"]').forEach(h=>{h.classList.remove('active');h.removeAttribute('aria-current');});
  let n=0;try{n=visibleNotifications().filter(isUnread131).length+threads131().filter(x=>x.waiting).length;}catch{}
  b.classList.toggle('has-dot131',n>0);b.title=b.getAttribute('aria-label')+(n?` · ${n}`:'');
}
const renderBeforeInboxIcon131=render;
render=function(){renderBeforeInboxIcon131();markInboxIcon131();};
