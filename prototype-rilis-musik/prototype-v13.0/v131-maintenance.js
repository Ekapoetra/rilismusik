/* V13.0 · D13 — Jadwal pemeliharaan sistem untuk Super Admin.
   Konfigurasi disimpan di area 'maintenance' pada System115 (draft → tinjau → terapkan, berversi & teraudit). */

const maintModules131=[['all','Seluruh sistem','Entire system'],['releases','Rilisan','Releases'],['payments','Pembayaran & layanan','Payments & services'],['royalty','Royalti & penarikan','Royalties & payouts'],['tickets','Tiket bantuan','Support tickets'],['wami','WAMI','WAMI'],['addons','Layanan tambahan','Add-on services'],['account','Akun & aktivasi','Account & activation']];
const maintKinds131={scheduled:['Terjadwal','Scheduled'],emergency:['Darurat','Emergency']};
const maintModes131={info:['Pengumuman','Announcement'],readonly:['Baca-saja','Read-only']};
const maintStatus131={scheduled:['Terjadwal','Scheduled'],active:['Berjalan','Active'],completed:['Selesai','Completed'],cancelled:['Dibatalkan','Cancelled']};
const maintNotify131={none:['Tanpa pengumuman','No announcement'],start:['Saat mulai','At start'],'1h':['1 jam sebelum','1 hour before'],'24h':['24 jam sebelum','24 hours before']};

function maintState131(w,now=ten.now){if(['cancelled','completed','active'].includes(w.status))return w.status;const s=Date.parse(w.startAt),e=Date.parse(w.endAt);if(now>=s&&now<=e)return 'active';if(now>e)return 'completed';return 'scheduled'}
function maintDuration131(w){const ms=Date.parse(w.endAt)-Date.parse(w.startAt);if(!Number.isFinite(ms)||ms<=0)return '—';const h=Math.floor(ms/3600000),m=Math.round(ms%3600000/60000);return h&&m?`${h} jam ${m} menit`:h?`${h} jam`:`${m} menit`}
function maintLocal131(iso){const d=Date.parse(iso);return Number.isFinite(d)?new Date(d+7*3600000).toISOString().slice(0,16):''}
function maintIso131(v){v=String(v||'').trim();if(!v)return '';if(v.length===16)v+=':00';return new Date(v+'+07:00').toISOString()}
function maintModsLabel131(w){const list=w.modules.includes('all')?[maintModules131[0]]:w.modules.map(m=>maintModules131.find(x=>x[0]===m)).filter(Boolean);return list.map(m=>T(m[1],m[2])).join(' · ')}

function maintenancePage115(){const v=draft115('maintenance'),a=area115('maintenance');
 const rank=w=>({active:0,scheduled:1}[maintState131(w)]??2);
 const rows=[...v.windows].sort((x,y)=>rank(x)-rank(y)||Date.parse(x.startAt)-Date.parse(y.startAt));
 return `<div class="section-head115"><div><h2>${T('Jadwal pemeliharaan','Maintenance windows')}</h2><p>${T('Rencanakan jeda layanan: jadwal, durasi, modul terdampak, dan pesan untuk member. Berlaku setelah diterapkan.','Plan service pauses: schedule, duration, affected modules, and the member-facing message. Applied after publish.')}</p></div>${B115(T('+ Jadwalkan','+ Schedule'),'window-new','','small')}</div><section class="list115">${rows.map(w=>{const s=maintState131(w),pub=a.published.windows.find(p=>p.id===w.id),diff=!pub||JSON.stringify(pub)!==JSON.stringify(w);return row115(w.title,`${fmt115(w.startAt)} – ${fmt115(w.endAt)} · ${maintDuration131(w)} · ${maintModsLabel131(w)}`,statusBadge111(T(...maintStatus131[s]),s==='active'?'red':s==='scheduled'?'blue':'neutral')+(diff?' '+statusBadge111(T('Draf berubah','Draft changed'),'mustard'):''),'window',w.id)}).join('')||`<p class="empty115">${T('Belum ada jadwal pemeliharaan.','No maintenance windows yet.')}</p>`}</section><section class="linked115"><div>${icon('clock')}<h3>${T('Apa yang terjadi saat pemeliharaan','What happens during maintenance')}</h3><p>${T('Mode pengumuman menampilkan pesan kepada member mulai dari waktu pengingat yang dipilih. Mode baca-saja menandai modul terdampak sebaiknya tidak mengubah data selama jendela berjalan. Status berjalan/selesai dihitung otomatis dari rentang waktu; pembatalan dicatat dalam riwayat versi.','Announcement mode shows the message to members from the chosen reminder time. Read-only mode marks affected modules as best kept unchanged during the window. Running/completed status follows the time range automatically; cancellations are recorded in version history.')}</p></div>${B115(T('Riwayat versi','Version history'),'versions','maintenance','small')}</section>`}

function windowEditor131(id){const v=draft115('maintenance'),w=id?v.windows.find(x=>x.id===id):null;
 if(id&&!w)return toast(T('Jadwal tidak tersedia.','Window not found.'));
 const d=w||{kind:'scheduled',mode:'info',status:'scheduled',notify:'start',modules:[],message:'',note:''};
 editor115('maintenance','window',id||'',d.title||T('Jadwal pemeliharaan baru','New maintenance window'),`
 ${input115('title',T('Judul pemeliharaan','Maintenance title'),d.title||'','text','required maxlength="160"')}
 <div class="form-grid115"><label>${T('Jenis','Kind')}<select name="kind">${Object.entries(maintKinds131).map(([k,n])=>`<option value="${k}" ${d.kind===k?'selected':''}>${T(...n)}</option>`).join('')}</select></label><label>${T('Mode','Mode')}<select name="mode">${Object.entries(maintModes131).map(([k,n])=>`<option value="${k}" ${d.mode===k?'selected':''}>${T(...n)}</option>`).join('')}</select></label></div>
 <div class="form-grid115">${input115('startAt',T('Mulai · WIB','Starts · WIB'),maintLocal131(d.startAt),'datetime-local','required')}${input115('endAt',T('Selesai · WIB','Ends · WIB'),maintLocal131(d.endAt),'datetime-local','required')}</div>
 <fieldset class="days115"><legend>${T('Modul terdampak','Affected modules')}</legend>${maintModules131.map(([k,a,b])=>`<label class="check115"><input name="modules" type="checkbox" value="${k}" ${(d.modules||[]).includes(k)?'checked':''}>${T(a,b)}</label>`).join('')}</fieldset>
 ${textarea115('message',T('Pesan untuk member','Member-facing message'),d.message,'required maxlength="1000"')}
 <label>${T('Pengumuman mulai tampil','Announcement starts showing')}<select name="notify">${Object.entries(maintNotify131).map(([k,n])=>`<option value="${k}" ${d.notify===k?'selected':''}>${T(...n)}</option>`).join('')}</select></label>
 ${id?`<label>${T('Status','Status')}<select name="status">${Object.entries(maintStatus131).map(([k,n])=>`<option value="${k}" ${d.status===k?'selected':''}>${T(...n)}</option>`).join('')}</select></label>`:''}
 ${textarea115('note',T('Catatan internal — tidak tampil ke member','Internal note — not shown to members'),d.note,'maxlength="1000"')}
 <p class="policy-note115">${T('Durasi dihitung otomatis dari waktu mulai–selesai. Perubahan baru tampil setelah jadwal diterapkan.','Duration is calculated from the start–end range. Changes appear only after the window is applied.')}</p>`)}

const collectBefore131=collectEditor115;
collectEditor115=function(f){const e=ui115.editor;if(e?.type!=='window')return collectBefore131(f);
 const fd=new FormData(f),get=k=>String(fd.get(k)||'').trim(),v=System115.cp(e.source);
 const w={id:e.id||'MW-'+String(Math.max(0,...v.windows.map(x=>Number(String(x.id).slice(3))||0))+1).padStart(2,'0'),title:get('title'),kind:get('kind'),mode:get('mode'),status:e.id?get('status'):'scheduled',startAt:maintIso131(get('startAt')),endAt:maintIso131(get('endAt')),modules:fd.getAll('modules').map(String),message:get('message'),notify:get('notify'),note:get('note')};
 const i=v.windows.findIndex(x=>x.id===w.id);if(i>=0)v.windows[i]=w;else v.windows.push(w);return v};

/* Pengumuman pemeliharaan untuk pengguna — mengikuti konfigurasi yang sudah diterapkan, bukan draf. */
function maintBannerHtml131(w,upcoming){return `<section class="attention9 attention-shell109 maint-banner131 ${w.mode==='readonly'?'red9':''} ${upcoming?'upcoming131':''}"><div class="spread"><h2><span class="status-dot9"></span>${E(w.title)}</h2>${statusBadge111(w.mode==='readonly'?T('Baca-saja','Read-only'):T('Pengumuman','Announcement'),w.mode==='readonly'?'red':'blue')}</div><p>${E(w.message)}</p><p><small>${E(fmt115(w.startAt))} – ${E(fmt115(w.endAt))} · ${maintDuration131(w)}${w.mode==='readonly'?' · '+T('Modul terdampak: ','Affected: ')+maintModsLabel131(w):''}</small></p></section>`}
function maintActive131(now=ten.now){const pub=system115().areas.maintenance?.published;return (pub?.windows||[]).filter(w=>{if(maintState131(w,now)==='cancelled'||w.notify==='none')return false;if(w.status==='active')return true;const s=Date.parse(w.startAt),e=Date.parse(w.endAt),lead={start:0,'1h':3600000,'24h':86400000}[w.notify]??0;return now>=s-lead&&now<=e})}
const renderMaint131=render;
render=function(){renderMaint131();document.querySelectorAll('.maint-banner131').forEach(e=>e.remove());const ws=maintActive131();if(!ws.length)return;const html=ws.map(w=>maintBannerHtml131(w,maintState131(w)!=='active')).join('');const head=document.querySelector('.pagehead,.heading115');if(head)return head.insertAdjacentHTML('afterend',html);const top=document.querySelector('.workspace-body122')||document.querySelector('.shell>main')||document.querySelector('.shell');top?.insertAdjacentHTML('afterbegin',html)};
