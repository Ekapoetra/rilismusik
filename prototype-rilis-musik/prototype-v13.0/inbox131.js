/* v1.1 dev.11 — Kotak Masuk: satu halaman, dua tab.
   Notifikasi = sesuatu TERJADI (pembayaran masuk, rilisan tayang) — dikelompokkan per hari,
   difilter per jenis, "tandai semua dibaca", setiap baris mengarah ke objeknya.
   Percakapan = seseorang BICARA dan menunggu balasan — chat label, chat internal, tiket.
   Lonceng dan ikon chat di header kini membuka halaman ini (bukan popover); popover lama
   tetap dipakai sebagai tampilan thread saat sebuah percakapan dibuka.
   Halaman memakai mekanisme modul v4 (v4.module) agar tidak menyentuh peta halaman app.js. */
'use strict';
const inbox131={tab:'notif',filter:'all'};
modules.push({id:'inbox131',group:'ops',title:['Kotak Masuk','Inbox'],desc:['Notifikasi dan percakapan dalam satu pintu.','Notifications and conversations in one place.'],actions:['',''],note:['',''],access:''});
const allowedBeforeInbox131=allowedModule;
allowedModule=function(m){if(m&&(m.id==='inbox131'||m.id==='profile131'))return true;return allowedBeforeInbox131(m);};

/* Jenis notifikasi: dari izin yang terkait (permission) atau halaman tujuan. */
const inboxKinds131=[['all',['Semua','All']],['finance',['Pembayaran','Payments']],['release',['Rilisan','Releases']],['support',['Tiket & chat','Tickets & chat']],['personal',['Personal','Personal']],['system',['Sistem','System']]];
function kindOf131(n){if(n.permission==='finance')return 'finance';if(n.permission==='release'||n.permission==='claim')return 'release';if(n.permission==='support')return 'support';if(n.page==='attendance'||n.page==='profile'||n.target!=='all')return 'personal';return 'system';}
const isUnread131=n=>!n.read.includes(me().id);
function dayOf131(n){return /^\d{1,2}\.\d{2}$/.test(n.time)?t('Hari ini','Today'):n.time;}

function openInbox131(tab){inbox131.tab=tab||inbox131.tab;try{closeModal();}catch{}try{closePop();}catch{}module102('inbox131');render();window.scrollTo(0,0);}
function markAllRead131(){visibleNotifications().forEach(n=>{if(isUnread131(n))n.read.push(me().id);});if(typeof save10==='function')save10();render();}

function inboxPage131(){
  const all=visibleNotifications(),unread=all.filter(isUnread131).length;
  const tabs=`<div class="tabs inbox-tabs131" role="tablist">${[['notif',t('Notifikasi','Notifications'),unread],['chat',t('Percakapan','Conversations'),0]].map(([id,label,n])=>`<button type="button" role="tab" aria-selected="${inbox131.tab===id}" class="${inbox131.tab===id?'active':''}" data-action="inbox131-tab" data-id="${id}">${label}${n?`<span class="count131">${n}</span>`:''}</button>`).join('')}</div>`;
  return pageHead(t('Kotak Masuk','Inbox'),t('Notifikasi memberi tahu sesuatu terjadi; percakapan menunggu balasanmu.','Notifications tell you something happened; conversations wait for your reply.'))+tabs+(inbox131.tab==='chat'?chatTab131():notifTab131(all,unread));
}
function notifTab131(all,unread){
  const list=all.filter(n=>inbox131.filter==='all'||kindOf131(n)===inbox131.filter);
  const groups=[];for(const n of list){const d=dayOf131(n);let g=groups.find(x=>x.day===d);if(!g){g={day:d,items:[]};groups.push(g);}g.items.push(n);}
  const filters=`<div class="inbox-filters131">${inboxKinds131.map(([id,label])=>`<button type="button" class="pill107 ${inbox131.filter===id?'active':''}" aria-pressed="${inbox131.filter===id}" data-action="inbox131-filter" data-id="${id}">${L(label)}</button>`).join('')}<span class="grow"></span>${btn(t('Tandai semua dibaca','Mark all read'),'inbox131-read',unread?'':'disabled','small')}</div>`;
  if(!list.length)return `<section class="panel pad inbox131">${filters}${empty(t('Tidak ada notifikasi','No notifications'),t('Kejadian baru akan muncul di sini.','New events will appear here.'))}</section>`;
  return `<section class="panel pad inbox131">${filters}${groups.map(g=>`<h3 class="inbox-day131">${g.day}</h3>${g.items.map(n=>`<div class="inbox-row131 ${isUnread131(n)?'unread':''}"><span class="eventdot" aria-hidden="true"></span><button type="button" data-action="notification-open" data-id="${n.id}"><strong>${L(n.title)}</strong><p>${L(n.body)}</p><small>${n.time} · ${L(inboxKinds131.find(k=>k[0]===kindOf131(n))[1])}${n.obj?` · ${E(n.obj)}`:''}</small></button>${isUnread131(n)?`<span class="badge status111" data-tone="blue">${t('Baru','New')}</span>`:''}</div>`).join('')}`).join('')}</section>`;
}
/* Percakapan: chat label (jika punya izin dukungan), chat internal, dan tiket bantuan. */
function ticketStatusLabel131(s){return ({submitted:['Diajukan','Submitted'],handling:['Dalam Penanganan','In Handling'],awaiting_label:['Perlu Tanggapan Label','Needs Label Response'],awaiting_distributor:['Menunggu Distributor','Awaiting Distributor'],completed:['Selesai','Completed'],closed:['Ditutup','Closed']})[s]||[s,s];}
function threads131(){
  const out=[];const chats=data.chats||{};
  if(chats.label&&permission('support')!=='none'){const last=chats.label[chats.label.length-1];out.push({id:'label',kind:t('Chat label','Label chat'),title:chats.label[0]?.who||'Label',last:last?`${last.who}: ${L(last.text)}`:'',count:chats.label.length,status:['Menunggu tanggapan','Awaiting response']});}
  if(chats.internal){const last=chats.internal[chats.internal.length-1];out.push({id:'internal',kind:t('Chat internal','Internal chat'),title:t('Tim internal','Internal team'),last:last?`${last.who}: ${L(last.text)}`:'',count:chats.internal.length,status:['Dalam Penanganan','In Handling']});}
  const store=(typeof ten!=='undefined'&&ten.tickets112)||{};const tickets=Array.isArray(store)?store:(store.tickets||store.list||[]);
  for(const tk of tickets.slice(0,12)){const msgs=tk.messages||[],last=msgs[msgs.length-1];out.push({id:'ticket:'+tk.id,kind:t('Tiket bantuan','Support ticket'),title:`${tk.id}${tk.release?` · ${tk.release}`:''}`,last:last?(last.text?L(last.text):''):t('Belum ada pesan','No messages yet'),count:msgs.length,status:ticketStatusLabel131(tk.status)});}
  return out;
}
function chatTab131(){
  const th=threads131();
  if(!th.length)return `<section class="panel pad inbox131">${empty(t('Belum ada percakapan','No conversations yet'))}</section>`;
  return `<section class="panel pad inbox131">${th.map(x=>`<div class="inbox-row131 thread131"><button type="button" data-action="inbox131-open" data-id="${E(x.id)}"><strong>${E(x.title)} <small class="kind131">${x.kind}</small></strong><p>${E(x.last)}</p><small>${x.count} ${t('pesan','messages')}</small></button>${statusBadge111(L(x.status))}</div>`).join('')}</section>`;
}
function openThread131(id){
  if(id==='label'||id==='internal'){state.chat=id;return chatModalBase131();}
  if(id.startsWith('ticket:')){if(typeof route102==='function')return route102('tickets');}
}
/* Lonceng & chat membuka halaman; popover lama disimpan untuk tampilan thread. */
const chatModalBase131=chatModal,notificationModalBase131=notificationModal;
chatModal=function(){if(document.querySelector('#header-popover.chat'))return chatModalBase131();openInbox131('chat');};
notificationModal=function(){if(document.querySelector('#header-popover.notifications'))return notificationModalBase131();openInbox131('notif');};
document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='inbox131-tab'){inbox131.tab=id;render();}
  else if(a==='inbox131-filter'){inbox131.filter=id;render();}
  else if(a==='inbox131-read')markAllRead131();
  else if(a==='inbox131-open')openThread131(id);
  else return;
  e.preventDefault();e.stopImmediatePropagation();
},true);
const modulePageBeforeInbox131=modulePage;
modulePage=function(){if(v4.module==='inbox131')return inboxPage131();return modulePageBeforeInbox131();};
