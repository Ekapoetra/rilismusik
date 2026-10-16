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
const inbox131={view:'n:all',sel:null,search:'',waiting:false,mode:'reply'};
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

function threads131(){
  const st=threadStore131(),out=[];
  if(permission('support')!=='none')for(const tk of st.tickets){
    const label=tk.chat?(data.chats[tk.chat]||[]):tk.msgs;
    const items=[...label.map(m=>({...m,kind:'msg'})),...tk.notes.map(m=>({...m,kind:'note'}))];
    const lastLabel=label[label.length-1];
    out.push({id:'t:'+tk.id,type:'ticket',tk,title:tk.label,sub:L(tk.subject),code:tk.id,items,labelCount:label.length,noteCount:tk.notes.length,
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

function inboxPage131(){
  const notes=visibleNotifications(),th=threads131();
  const navItem=(view,icon,label,count,extra='')=>`<button type="button" class="nav131 ${inbox131.view===view?'active':''}" data-action="inbox131-view" data-id="${view}" aria-current="${inbox131.view===view}">${svg131(icon)}<span>${label}</span>${count?`<b>${count}</b>`:''}${extra}</button>`;
  const nav=`<nav class="inbox-nav131" aria-label="${t('Kotak Masuk','Inbox')}">
    <h3>${t('Notifikasi','Notifications')}</h3>
    ${kinds131.map(([k,l])=>navItem('n:'+k,k==='all'?'bell':k,L(l),notes.filter(n=>isUnread131(n)&&(k==='all'||kindOf131(n)===k)).length)).join('')}
    <h3>${t('Percakapan','Conversations')}</h3>
    ${navItem('c:all','chat',t('Semua percakapan','All conversations'),th.filter(x=>x.waiting).length)}
    ${th.some(x=>x.type==='ticket')?navItem('c:ticket','ticket',t('Tiket & label','Tickets & labels'),th.filter(x=>x.type==='ticket'&&x.waiting).length):''}
    ${navItem('c:internal','lock',t('Internal','Internal'),th.filter(x=>x.type==='internal'&&x.waiting).length)}
  </nav>`;
  const isNotif=inbox131.view.startsWith('n:');
  return pageHead(t('Kotak Masuk','Inbox'),t('Notifikasi memberi tahu sesuatu terjadi; percakapan menunggu balasanmu.','Notifications tell you something happened; conversations wait for your reply.'))
    +`<section class="panel inbox3-131">${nav}${isNotif?notifColumns131(notes):chatColumns131(th)}</section>`;
}
function notifColumns131(all){
  const k=inbox131.view.slice(2),q=inbox131.search.toLowerCase();
  const list=all.filter(n=>(k==='all'||kindOf131(n)===k)&&(!q||(L(n.title)+' '+L(n.body)+' '+(n.obj||'')).toLowerCase().includes(q)));
  if(!list.some(n=>n.id===inbox131.sel))inbox131.sel=list[0]?.id||null;
  const cur=list.find(n=>n.id===inbox131.sel);const unread=list.filter(isUnread131).length;
  let day='';
  const rows=list.map(n=>{const d=dayOf131(n),head=d!==day?`<h4 class="day131">${d}</h4>`:'';day=d;const kk=kindOf131(n);
    return head+`<button type="button" class="row131 ${n.id===inbox131.sel?'active':''} ${isUnread131(n)?'unread':''}" data-action="inbox131-sel" data-id="${n.id}"><span class="kind-ico131">${svg131(kk)}</span><span class="row-main131"><span class="row-top131"><strong>${L(n.title)}</strong><time>${n.time}</time></span><span class="row-sub131">${L(n.body)}</span></span>${isUnread131(n)?'<i class="udot131" aria-label="'+t('Belum dibaca','Unread')+'"></i>':''}</button>`;}).join('');
  const listCol=`<div class="list131"><header class="list-head131"><div><h2>${kindName131(k)}</h2><small>${list.length} ${t('notifikasi','notifications')}${unread?` · ${unread} ${t('belum dibaca','unread')}`:''}</small></div>${btn(t('Tandai semua dibaca','Mark all read'),'inbox131-read',unread?'':'disabled','small text')}</header>${searchBox131()}<div class="rows131i">${rows||`<p class="hint131 pad131">${t('Tidak ada notifikasi.','No notifications.')}</p>`}</div></div>`;
  const detail=cur?`<article class="detail131"><div class="eyebrow131">${svg131(kindOf131(cur))}<span>${kindName131(kindOf131(cur))}</span><span>·</span><time>${dayOf131(cur)}${/^\d/.test(cur.time)&&dayOf131(cur)!==cur.time?' '+cur.time:''}</time></div><h2 class="detail-title131">${L(cur.title)}</h2><p class="detail-body131">${L(cur.body)}</p>${cur.obj||cur.page?`<div class="obj131"><span class="obj-ico131">${svg131(kindOf131(cur)==='personal'?'personal':'release')}</span><div><small>${t('Objek terkait','Related item')}</small><strong>${E(cur.obj||pages()[cur.page]||cur.page)}</strong></div>${btn(t('Buka','Open'),'notification-open',`data-id="${cur.id}"`,'small primary')}</div>`:''}<p class="hint131">${t('Membaca notifikasi tidak menyelesaikan pekerjaan terkait.','Reading a notification does not complete the related work.')}</p></article>`:`<article class="detail131 empty131">${empty(t('Pilih notifikasi','Pick a notification'))}</article>`;
  return listCol+detail;
}
function searchBox131(){return `<div class="search131">${svg131('all')}<input type="search" data-input="inbox131-search" value="${E(inbox131.search)}" placeholder="${t('Cari…','Search…')}" aria-label="${t('Cari','Search')}"></div>`;}
function chatColumns131(all){
  const v=inbox131.view.slice(2),q=inbox131.search.toLowerCase();
  let th=all.filter(x=>v==='all'||x.type===v);
  if(q)th=th.filter(x=>(x.title+' '+x.sub+' '+x.code+' '+x.last).toLowerCase().includes(q));
  if(inbox131.waiting)th=th.filter(x=>x.waiting);
  if(!th.some(x=>x.id===inbox131.sel))inbox131.sel=th[0]?.id||null;
  const cur=th.find(x=>x.id===inbox131.sel);
  const lead=x=>x.type==='ticket'?`<span class="avatar lead131">${initials131(x.title)}</span>`:`<span class="kind-ico131 lock131">${svg131('lock')}</span>`;
  const rows=th.map(x=>`<button type="button" class="row131 ${x.id===inbox131.sel?'active':''}" data-action="inbox131-sel" data-id="${x.id}">${lead(x)}<span class="row-main131"><span class="row-top131"><strong>${E(x.title)}${x.type==='ticket'&&labelVerified131(x.title)?'<span class="seal-slot131"></span>':''}</strong>${x.type==='ticket'?statusBadge111(stepName131(x.tk.status),ticketTone131[x.tk.status]):`<span class="tag131">${t('Internal','Internal')}</span>`}</span><span class="row-meta131"><span class="code131">${E(x.code)}</span>${E(x.sub)}</span><span class="row-sub131">${E(x.last)}</span></span>${x.waiting?'<i class="udot131" title="'+t('Menunggu jawabanmu','Awaiting your reply')+'"></i>':''}</button>`).join('');
  const title=v==='ticket'?t('Tiket & label','Tickets & labels'):v==='internal'?t('Internal','Internal'):t('Semua percakapan','All conversations');
  const listCol=`<div class="list131"><header class="list-head131"><div><h2>${title}</h2><small>${th.length} ${t('percakapan','conversations')}</small></div><button type="button" class="chip-toggle131 ${inbox131.waiting?'on':''}" aria-pressed="${inbox131.waiting}" data-action="inbox131-waiting">${t('Menunggu jawabanku','Awaiting my reply')}</button></header>${searchBox131()}<div class="rows131i">${rows||`<p class="hint131 pad131">${t('Tidak ada percakapan yang cocok.','No matching conversation.')}</p>`}</div></div>`;
  return listCol+(cur?(cur.type==='ticket'?ticketDetail131(cur):roomDetail131(cur)):`<article class="detail131 empty131">${empty(t('Pilih percakapan','Pick a conversation'))}</article>`);
}
function bubble131(m){
  const mine=isMine131(m.who),note=m.kind==='note',staff=isStaff131(m.who);
  return `<div class="msg131 ${mine?'mine':''} ${note?'note':''}"><span class="msg-who131">${note?svg131('lock'):''}${E(whoName131(m.who))}${note?` · ${t('catatan internal','internal note')}`:staff?'':` · ${t('label','label')}`}${m.at?` · ${E(m.at)}`:''}</span><p>${E(msgText131(m))}</p></div>`;
}
function ticketDetail131(x){
  const tk=x.tk,idx=ticketSteps131.findIndex(s=>s[0]===tk.status);
  const steps=`<ol class="steps131">${ticketSteps131.map(([k,l],i)=>`<li class="${i<idx?'done':i===idx?'now':''}"><i></i><span>${L(l)}</span></li>`).join('')}</ol>`;
  const note=inbox131.mode==='note';
  return `<article class="detail131 thread131d"><header class="thread-head131"><span class="avatar lead131 big">${initials131(x.title)}</span><div class="th-id131"><h2>${E(x.title)}${labelVerified131(x.title)?'<span class="seal-slot131"></span>':''}</h2><small><span class="code131">${E(tk.id)}</span>${E(x.sub)} · ${E(tk.obj)}</small></div><div class="th-ctl131">${statusBadge111(stepName131(tk.status),ticketTone131[tk.status])}${btn(t('Buka tiket','Open ticket'),'inbox131-ticket',`data-id="${E(tk.id)}"`,'small')}</div></header>${steps}
  <div class="legend131"><span><i class="lg-msg"></i>${t('Dengan label','With label')} · ${x.labelCount}</span><span><i class="lg-note"></i>${t('Catatan internal','Internal notes')} · ${x.noteCount}</span></div>
  <div class="msgs131">${x.items.map(bubble131).join('')||`<p class="hint131">${t('Belum ada pesan.','No messages yet.')}</p>`}</div>
  <form class="composer131 ${note?'note':''}" data-form="inbox131-send"><div class="mode131" role="tablist"><button type="button" role="tab" aria-selected="${!note}" class="${!note?'on':''}" data-action="inbox131-mode" data-id="reply">${t('Balas ke label','Reply to label')}</button><button type="button" role="tab" aria-selected="${note}" class="${note?'on':''}" data-action="inbox131-mode" data-id="note">${svg131('lock')}${t('Catatan internal','Internal note')}</button></div><div class="compose-row131"><textarea name="text" rows="2" placeholder="${note?t('Catatan untuk staf — tidak terlihat oleh label','Note for staff — not visible to the label'):t(`Balas ke ${x.title}…`,`Reply to ${x.title}…`)}" aria-label="${t('Pesan','Message')}"></textarea><button type="submit" class="btn primary small">${note?t('Simpan catatan','Save note'):t('Kirim','Send')}</button></div></form></article>`;
}
function roomDetail131(x){
  const who=[...new Set(x.items.map(m=>m.who))].map(w=>personOf131(w)).filter(Boolean);
  return `<article class="detail131 thread131d"><header class="thread-head131"><span class="kind-ico131 lock131 big">${svg131('lock')}</span><div class="th-id131"><h2>${E(x.title)}</h2><small><span class="code131">${E(x.code)}</span>${E(x.sub)}</small></div><div class="th-ctl131"><span class="faces131">${who.map(p=>`<span class="avatar" title="${E(p.name)}">${p.initials}</span>`).join('')}</span>${btn(x.code,'task',`data-id="${E(x.code)}"`,'small')}</div></header>
  <div class="banner131">${svg131('lock')}${t('Ruang internal staf — tidak terlihat oleh label.','Staff-only room — not visible to labels.')}</div>
  <div class="msgs131">${x.items.map(bubble131).join('')}</div>
  <form class="composer131 note" data-form="inbox131-send"><div class="compose-row131"><textarea name="text" rows="2" placeholder="${t('Tulis ke tim internal…','Write to the internal team…')}" aria-label="${t('Pesan','Message')}"></textarea><button type="submit" class="btn primary small">${t('Kirim','Send')}</button></div></form></article>`;
}
function sendMessage131(form){
  const text=form.elements.text.value.trim();if(!text)return;const id=inbox131.sel;if(!id)return;
  const msg={who:me().id,text:[text,text],at:t('baru saja','just now')};
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
  if(a==='inbox131-view'){inbox131.view=id;inbox131.sel=null;inbox131.search='';render();}
  else if(a==='inbox131-sel'){inbox131.sel=id;const n=visibleNotifications().find(x=>x.id===id);if(n&&isUnread131(n)){n.read.push(me().id);if(typeof save10==='function')save10();}render();}
  else if(a==='inbox131-read')markAllRead131();
  else if(a==='inbox131-waiting'){inbox131.waiting=!inbox131.waiting;render();}
  else if(a==='inbox131-mode'){inbox131.mode=id;render();const ta=document.querySelector('.composer131 textarea');if(ta)ta.focus();}
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
