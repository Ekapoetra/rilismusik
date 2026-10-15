/* v1.1 dev.11–12 — Kotak Masuk: satu halaman, dua tab.
   Notifikasi = sesuatu TERJADI (pembayaran masuk, rilisan tayang) — dikelompokkan per hari,
   difilter per jenis, "tandai semua dibaca", setiap baris mengarah ke objeknya.
   Percakapan (Chat Center, dev.12) = seseorang BICARA dan menunggu balasan — daftar thread di
   kiri (chat label, chat internal, tiket) dengan pencarian & saringan "menunggu jawabanku",
   thread terpilih di kanan dengan gelembung pesan dan kotak balasan.
   Lonceng dan ikon chat di header tetap membuka popover ringkas (permintaan pemilik); popover
   diberi tautan "Buka Kotak Masuk" ke halaman ini.
   Halaman memakai mekanisme modul v4 (v4.module) agar tidak menyentuh peta halaman app.js. */
'use strict';
const inbox131={tab:'notif',filter:'all',thread:null,search:'',waiting:false};
modules.push({id:'inbox131',group:'ops',title:['Kotak Masuk','Inbox'],desc:['Notifikasi dan percakapan dalam satu pintu.','Notifications and conversations in one place.'],actions:['',''],note:['',''],access:''});
const allowedBeforeInbox131=allowedModule;
allowedModule=function(m){if(m&&(m.id==='inbox131'||m.id==='profile131'))return true;return allowedBeforeInbox131(m);};

/* ---------- Notifikasi ---------- */
const inboxKinds131=[['all',['Semua','All']],['finance',['Pembayaran','Payments']],['release',['Rilisan','Releases']],['support',['Tiket & chat','Tickets & chat']],['personal',['Personal','Personal']],['system',['Sistem','System']]];
function kindOf131(n){if(n.permission==='finance')return 'finance';if(n.permission==='release'||n.permission==='claim')return 'release';if(n.permission==='support')return 'support';if(n.page==='attendance'||n.page==='profile'||n.target!=='all')return 'personal';return 'system';}
const isUnread131=n=>!n.read.includes(me().id);
function dayOf131(n){return /^\d{1,2}\.\d{2}$/.test(n.time)?t('Hari ini','Today'):n.time;}
function openInbox131(tab){inbox131.tab=tab||inbox131.tab;try{closeModal();}catch{}try{closePop();}catch{}module102('inbox131');render();window.scrollTo(0,0);}
function markAllRead131(){visibleNotifications().forEach(n=>{if(isUnread131(n))n.read.push(me().id);});if(typeof save10==='function')save10();render();}

function inboxPage131(){
  const all=visibleNotifications(),unread=all.filter(isUnread131).length,waiting=threads131().filter(x=>x.waiting).length;
  const tabs=`<div class="tabs inbox-tabs131" role="tablist">${[['notif',t('Notifikasi','Notifications'),unread],['chat',t('Percakapan','Conversations'),waiting]].map(([id,label,n])=>`<button type="button" role="tab" aria-selected="${inbox131.tab===id}" class="${inbox131.tab===id?'active':''}" data-action="inbox131-tab" data-id="${id}">${label}${n?`<span class="count131">${n}</span>`:''}</button>`).join('')}</div>`;
  return pageHead(t('Kotak Masuk','Inbox'),t('Notifikasi memberi tahu sesuatu terjadi; percakapan menunggu balasanmu.','Notifications tell you something happened; conversations wait for your reply.'))+tabs+(inbox131.tab==='chat'?chatCenter131():notifTab131(all,unread));
}
function notifTab131(all,unread){
  const list=all.filter(n=>inbox131.filter==='all'||kindOf131(n)===inbox131.filter);
  const groups=[];for(const n of list){const d=dayOf131(n);let g=groups.find(x=>x.day===d);if(!g){g={day:d,items:[]};groups.push(g);}g.items.push(n);}
  const filters=`<div class="inbox-filters131">${inboxKinds131.map(([id,label])=>`<button type="button" class="pill107 ${inbox131.filter===id?'active':''}" aria-pressed="${inbox131.filter===id}" data-action="inbox131-filter" data-id="${id}">${L(label)}</button>`).join('')}<span class="grow"></span>${btn(t('Tandai semua dibaca','Mark all read'),'inbox131-read',unread?'':'disabled','small')}</div>`;
  if(!list.length)return `<section class="panel pad inbox131">${filters}${empty(t('Tidak ada notifikasi','No notifications'),t('Kejadian baru akan muncul di sini.','New events will appear here.'))}</section>`;
  return `<section class="panel pad inbox131">${filters}${groups.map(g=>`<h3 class="inbox-day131">${g.day}</h3>${g.items.map(n=>`<div class="inbox-row131 ${isUnread131(n)?'unread':''}"><span class="eventdot" aria-hidden="true"></span><button type="button" data-action="notification-open" data-id="${n.id}"><strong>${L(n.title)}</strong><p>${L(n.body)}</p><small>${n.time} · ${L(inboxKinds131.find(k=>k[0]===kindOf131(n))[1])}${n.obj?` · ${E(n.obj)}`:''}</small></button>${isUnread131(n)?`<span class="badge status111" data-tone="blue">${t('Baru','New')}</span>`:''}</div>`).join('')}`).join('')}</section>`;
}

/* ---------- Percakapan (Chat Center) ---------- */
function ticketStatusLabel131(s){return ({submitted:['Diajukan','Submitted'],handling:['Dalam Penanganan','In Handling'],awaiting_label:['Perlu Tanggapan Label','Needs Label Response'],awaiting_distributor:['Menunggu Distributor','Awaiting Distributor'],completed:['Selesai','Completed'],closed:['Ditutup','Closed']})[s]||[s,s];}
const whoName131=w=>{try{const p=typeof person==='function'&&person(w);if(p&&p.name)return p.name;}catch{}return w;};
const isMine131=w=>w===me().id||w===me().name;
const msgText131=m=>Array.isArray(m.text)?L(m.text):String(m.text||'');
function threads131(){
  const out=[];const chats=data.chats||{};
  const mk=(id,kind,title,msgs,status)=>{const last=msgs[msgs.length-1];out.push({id,kind,title,msgs,status,last:last?`${whoName131(last.who)}: ${msgText131(last)}`:t('Belum ada pesan','No messages yet'),waiting:!!last&&!isMine131(last.who)});};
  if(chats.label&&permission('support')!=='none')mk('label',t('Chat label','Label chat'),chats.label[0]?.who||'Label',chats.label,['Menunggu tanggapan','Awaiting response']);
  if(chats.internal)mk('internal',t('Chat internal','Internal chat'),t('Tim internal','Internal team'),chats.internal,['Dalam Penanganan','In Handling']);
  const store=(typeof ten!=='undefined'&&ten.tickets112)||{};const tickets=Array.isArray(store)?store:(store.tickets||store.list||[]);
  for(const tk of tickets.slice(0,20))mk('ticket:'+tk.id,t('Tiket bantuan','Support ticket'),`${tk.id}${tk.release?` · ${tk.release}`:''}`,tk.messages||[],ticketStatusLabel131(tk.status));
  return out;
}
function chatCenter131(){
  let th=threads131();
  if(inbox131.search){const q=inbox131.search.toLowerCase();th=th.filter(x=>(x.title+' '+x.kind+' '+x.last).toLowerCase().includes(q));}
  if(inbox131.waiting)th=th.filter(x=>x.waiting);
  if(!th.some(x=>x.id===inbox131.thread))inbox131.thread=th[0]?.id||null;
  const cur=th.find(x=>x.id===inbox131.thread);
  const list=`<aside class="thread-list131"><div class="thread-tools131"><input type="search" data-input="inbox131-search" value="${E(inbox131.search)}" placeholder="${t('Cari percakapan…','Search conversations…')}" aria-label="${t('Cari percakapan','Search conversations')}"><button type="button" class="pill107 ${inbox131.waiting?'active':''}" aria-pressed="${inbox131.waiting}" data-action="inbox131-waiting">${t('Menunggu jawabanku','Awaiting my reply')}</button></div>${th.length?th.map(x=>`<button type="button" class="thread131 ${x.id===inbox131.thread?'active':''}" data-action="inbox131-open" data-id="${E(x.id)}" aria-current="${x.id===inbox131.thread}"><span class="thread-top131"><strong>${E(x.title)}</strong>${x.waiting?`<i class="dot131" title="${t('Menunggu jawabanmu','Awaiting your reply')}"></i>`:''}</span><small class="kind131">${x.kind}</small><p>${E(x.last)}</p></button>`).join(''):`<p class="hint131" style="padding:14px">${t('Tidak ada percakapan yang cocok.','No matching conversation.')}</p>`}</aside>`;
  const view=cur?`<section class="thread-view131"><header class="thread-head131"><div><h2>${E(cur.title)}</h2><small>${cur.kind} · ${cur.msgs.length} ${t('pesan','messages')}</small></div><div class="thread-head-ctl131">${statusBadge111(L(cur.status))}${cur.id.startsWith('ticket:')?btn(t('Buka tiket','Open ticket'),'inbox131-ticket',`data-id="${E(cur.id.slice(7))}"`,'small'):''}</div></header><div class="msgs131">${cur.msgs.length?cur.msgs.map(m=>`<div class="msg131 ${isMine131(m.who)?'mine':''}"><span class="msg-who131">${E(whoName131(m.who))}${m.at?` · ${E(m.at)}`:''}</span><p>${E(msgText131(m))}</p></div>`).join(''):`<p class="hint131">${t('Belum ada pesan di percakapan ini.','No messages in this conversation yet.')}</p>`}</div><form class="composer131" data-form="inbox131-send"><textarea name="text" rows="2" placeholder="${t('Tulis balasan…','Write a reply…')}" aria-label="${t('Balasan','Reply')}"></textarea><button type="submit" class="btn primary small">${t('Kirim','Send')}</button></form></section>`
    :`<section class="thread-view131">${empty(t('Pilih percakapan','Pick a conversation'))}</section>`;
  return `<section class="panel chat-center131">${list}${view}</section>`;
}
function sendMessage131(form){
  const ta=form.elements.text,text=ta.value.trim();if(!text)return;const id=inbox131.thread;if(!id)return;
  const msg={who:me().id,text:[text,text],at:t('baru saja','just now')};
  if(id==='label'||id==='internal'){(data.chats[id]=data.chats[id]||[]).push(msg);}
  else if(id.startsWith('ticket:')){const store=ten.tickets112||{};const tickets=Array.isArray(store)?store:(store.tickets||store.list||[]);const tk=tickets.find(x=>x.id===id.slice(7));if(!tk)return;(tk.messages=tk.messages||[]).push(msg);}
  if(typeof save10==='function')save10();render();
  const box=document.querySelector('.msgs131');if(box)box.scrollTop=box.scrollHeight;
}

/* Popover ringkas tetap; tambahkan tautan ke halaman penuh di judulnya. */
const chatModalBase131=chatModal,notificationModalBase131=notificationModal;
function inboxLink131(tab){const head=document.querySelector('#header-popover .popover-title>div');if(!head||head.querySelector('[data-action=inbox131-page]'))return;head.insertAdjacentHTML('afterbegin',btn(t('Buka Kotak Masuk','Open Inbox'),'inbox131-page',`data-id="${tab}"`,'text'));}
chatModal=function(){chatModalBase131();inboxLink131('chat');};
notificationModal=function(){notificationModalBase131();inboxLink131('notif');};

document.addEventListener('click',e=>{
  const b=e.target.closest('[data-action]');if(!b)return;const a=b.dataset.action,id=b.dataset.id;
  if(a==='inbox131-tab'){inbox131.tab=id;render();}
  else if(a==='inbox131-filter'){inbox131.filter=id;render();}
  else if(a==='inbox131-read')markAllRead131();
  else if(a==='inbox131-open'){inbox131.thread=id;render();}
  else if(a==='inbox131-waiting'){inbox131.waiting=!inbox131.waiting;render();}
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
