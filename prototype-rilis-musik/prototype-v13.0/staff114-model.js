/* Prototype account governance. No invitation email or authentication service is called. */
(function(root){
'use strict';
const copy=x=>JSON.parse(JSON.stringify(x)),need=(c,m)=>{if(!c)throw Error(m)};
const groups=[
 ['releases','Rilisan','release',['claim','Ambil pekerjaan'],['review','Periksa materi'],['request','Minta perbaikan'],['approve','Setujui hasil pemeriksaan'],['deliver','Teruskan pengiriman'],['finish','Catat hasil tayang'],['assign','Alihkan penanganan']],
 ['labels','Identitas Label','claim',['review','Periksa identitas'],['request','Minta perbaikan'],['document','Buka dokumen identitas'],['bank','Lihat rekening lengkap'],['export','Ekspor data']],
 ['tickets','Tiket Bantuan','support',['claim','Ambil pekerjaan'],['handle','Tangani permintaan'],['request','Minta kelengkapan'],['send','Teruskan ke distributor'],['finish','Catat hasil'],['assign','Alihkan penanganan']],
 ['services','Layanan Tambahan','support',['claim','Ambil pekerjaan'],['handle','Tangani layanan'],['request','Minta bahan'],['finish','Kirim hasil'],['assign','Alihkan penanganan']],
 ['wami','Registrasi WAMI','support',['claim','Mulai pemeriksaan'],['handle','Siapkan pendaftaran'],['request','Minta perbaikan'],['send','Catat pengiriman'],['finish','Catat hasil']],
 ['transactions','Transaksi','finance',['check','Periksa pembayaran'],['handle','Tangani pemeriksaan'],['fulfill','Selesaikan pembelian'],['refund','Ajukan pengembalian dana'],['assign','Alihkan penanganan'],['bank','Lihat rekening lengkap'],['export','Ekspor data']],
 ['royalty','Royalti','finance',['import','Impor laporan'],['review','Periksa laporan'],['export','Ekspor data']],
 ['withdraw','Pembayaran Royalti','finance',['review','Periksa permintaan'],['handle','Catat pelaksanaan pembayaran'],['bank','Lihat rekening lengkap'],['export','Ekspor data']],
 ['claims','Migrasi & Klaim','claim',['handle','Tangani pencocokan'],['request','Minta informasi']],
 ['team','Ringkasan Tim','team',['view-personal','Lihat profil kerja tim']]
];
const catalog=groups.flatMap(([id,label,legacy,...actions])=>[{id:id+'.view',group:id,label:'Lihat daftar dan detail',groupLabel:label,legacy,deps:[]},...actions.map(([action,text])=>({id:id+'.'+action,group:id,label:text,groupLabel:label,legacy,deps:[id+'.view']}))]);
const user=(s,id)=>s.users.find(u=>u.id===id),role=(s,id)=>s.roles.find(r=>r.id===id);
const normalize=ids=>{const out=new Set;for(const id of ids||[]){const p=catalog.find(p=>p.id===id);need(p,'Izin tidak dikenal: '+id);out.add(id);p.deps.forEach(x=>out.add(x))}return [...out]};
function seed(people,legacyRoles,assignments,at){
 const roles=legacyRoles.map(r=>({id:r.id,name:String(r.name).split(' / ')[0],description:'Akses bawaan dari pengaturan sebelumnya; tinjau sebelum mengubah.',permissions:normalize(catalog.filter(p=>r.rules[p.legacy]==='direct'||p.id.endsWith('.view')&&r.rules[p.legacy]&&r.rules[p.legacy]!=='none').map(p=>p.id)),legacy:copy(r.rules),archived:false,version:1}));
 const users=people.map(p=>({id:p.id,name:p.name,email:p.email.toLowerCase(),super:!!p.super,status:'active',role:p.super?null:assignments[p.id]||null,scope:'all',labels:[],version:1,joined:p.joined,session:1}));
 for(const u of users.filter(u=>!u.super&&!u.role)){const id='legacy-'+u.id;roles.push({id,name:'Akses lama · '+u.name,description:'Belum ada peran operasional pada akun sebelumnya.',permissions:[],legacy:{},archived:false,version:1});u.role=id}
 return {schema:1,users,roles,serial:0,revision:1,audit:[],notifications:[],handoffs:[],known:catalog.map(p=>p.id),reviewed:catalog.map(p=>p.id),at,migration:{at,note:'Akun lama mempertahankan izin yang dapat dipetakan. Tidak ada pemindahan akun otomatis.'}};
}
function can(s,id,permission,member){const u=user(s,id);if(!u||u.status!=='active')return false;if(u.super)return true;const r=role(s,u.role);if(!r||r.archived||!r.permissions.includes(permission))return false;return !member||u.scope==='all'||u.labels.includes(member)}
function effective(s,u){return u.super?catalog.map(p=>p.id):role(s,u.role)?.permissions||[]}
function impact(s,u,proposal,jobs){return jobs.filter(j=>j.handler===u.id&&!j.closed&&!((proposal.status||u.status)==='active'&&(u.super||proposal.permissions.includes(j.permission))&&((proposal.scope||u.scope)==='all'||(proposal.labels||u.labels).includes(j.member))))}
function eligible(s,jobs,id){return jobs.every(j=>can(s,id,j.permission,j.member))}
function audit(s,a,kind,target,before,after,note,at){s.audit.unshift({id:'AUD-'+(++s.serial),actor:a.id,kind,target,before:copy(before),after:copy(after),note:note||'',at});s.revision++;}
function act(s,a,k,p={},jobs=[],at=Date.now()){
 const admin=user(s,a.id);need(admin?.super&&admin.status==='active'&&!a.preview,'Pengelolaan akses khusus Super Admin aktif.');
 const u=p.user?user(s,p.user):null,r=p.role?role(s,p.role):null;
 const expected=()=>need(p.version===(u||r)?.version,'Pengaturan telah berubah. Tinjau versi terbaru sebelum menyimpan.');
 const note=()=>need(String(p.note||'').trim(),'Tuliskan alasan perubahan.');
 function move(affected,emergency=false,futureRole=null){
  const out=[];for(const j of affected){const to=p.transfers?.[j.key]||null;need(emergency||to!==null||p.queueConfirmed,'Pilih pengganti atau konfirmasikan daftar Perlu pengalihan.');if(to){const dest=user(s,to);const futureOk=!futureRole||dest.super||dest.role!==futureRole.id||futureRole.permissions.includes(j.permission);need(to!==j.handler&&eligible(s,[j],to)&&futureOk,'Pengganti tidak memiliki akses yang diperlukan setelah perubahan.');}}
  for(const j of affected){const to=p.transfers?.[j.key]||null,h={id:'HO-'+(++s.serial),key:j.key,title:j.title,member:j.member,permission:j.permission,from:j.handler,to,status:to?'assigned':'pending',at,actor:a.id};s.handoffs.unshift(h);out.push(h)}return out;
 }
 if(k==='invite'){
  const email=String(p.email||'').trim().toLowerCase(),name=String(p.name||'').trim(),selected=role(s,p.role);
  need(name&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email),'Isi nama dan email yang valid.');
  const old=s.users.find(u=>u.email===email);if(old)return {existing:old.id};
  need(selected&&!selected.archived,'Pilih peran aktif.');need(p.scope==='all'||p.labels?.length,'Pilih minimal satu label.');
  const id='staff-'+(++s.serial),u={id,name,email,super:false,status:'invited',role:p.role,scope:p.scope==='all'?'all':'selected',labels:[...new Set(p.labels||[])],version:1,joined:null,session:0,invite:{generation:1,status:'valid',at}};
  s.users.push(u);audit(s,a,k,id,{},u,'Undangan simulasi; masa berlaku produksi belum ditetapkan.',at);return {id};
 }
 if(['resend','revoke-invite'].includes(k)){need(u?.status==='invited','Akun tidak sedang menunggu aktivasi.');expected();const before=copy(u);u.invite.generation++;u.invite.status=k==='resend'?'valid':'revoked';u.invite.at=at;u.version++;audit(s,a,k,u.id,before,u,p.note,at);return {id:u.id}}
 if(k==='save-access'){
  need(u&&!u.super,'Kewenangan Super Admin tidak diubah melalui peran staff.');expected();note();need(r&&!r.archived,'Pilih peran aktif.');need(p.scope==='all'||p.labels?.length,'Pilih minimal satu label.');
  const proposal={permissions:r.permissions,scope:p.scope,labels:p.labels||[]},affected=impact(s,u,proposal,jobs),moves=move(affected),before=copy(u);
  u.role=r.id;u.scope=p.scope;u.labels=[...new Set(p.labels||[])];u.version++;u.session++;audit(s,a,k,u.id,before,u,p.note,at);s.notifications.unshift({target:u.id,kind:k,at,text:'Akses kerjamu diperbarui. Periksa kewenangan terbaru.'});return {id:u.id,moves};
 }
 if(k==='save-role'){
  need(p.name?.trim(),'Isi nama peran.');need(!/^super\s*admin$/i.test(p.name.trim()),'Nama Super Admin digunakan untuk kewenangan akun khusus.');
  const permissions=normalize(p.permissions),other=s.roles.find(x=>x.id!==r?.id&&!x.archived&&x.name.toLowerCase()===p.name.trim().toLowerCase());need(!other,'Nama peran sudah digunakan.');
  if(r){need(!r.archived,'Peran telah diarsipkan.');expected();note()}
  const users=r?s.users.filter(u=>u.role===r.id&&!u.super):[],affected=users.flatMap(u=>impact(s,u,{permissions},jobs)),moves=move(affected,false,r?{id:r.id,permissions}:null),before=r?copy(r):{};
  const next=r||{id:'role-'+(++s.serial),version:0,archived:false};Object.assign(next,{name:p.name.trim(),description:String(p.description||'').trim(),permissions,version:next.version+1});if(!r)s.roles.push(next);
  for(const u of users){u.version++;u.session++;s.notifications.unshift({target:u.id,kind:k,at,text:'Izin peranmu diperbarui. Periksa kewenangan terbaru.'})}audit(s,a,k,next.id,before,next,p.note,at);s.audit[0].staffTargets=users.map(u=>u.id);return {id:next.id,moves};
 }
 if(k==='archive-role'){need(r&&!r.archived,'Peran tidak tersedia.');expected();note();need(!s.users.some(u=>u.role===r.id),'Pindahkan seluruh akun pengguna peran ini terlebih dahulu.');const before=copy(r);r.archived=true;r.version++;audit(s,a,k,r.id,before,r,p.note,at);return {id:r.id}}
 if(k==='disable'){
  need(u?.status==='active','Akun tidak aktif.');expected();note();need(!u.super||s.users.filter(u=>u.super&&u.status==='active').length>1,'Super Admin aktif terakhir tidak dapat dinonaktifkan.');
  const affected=jobs.filter(j=>j.handler===u.id&&!j.closed),moves=move(affected,!!p.emergency),before=copy(u);u.status='inactive';u.session++;u.version++;audit(s,a,k,u.id,before,u,p.note,at);return {id:u.id,moves};
 }
 if(k==='reactivate'){need(u?.status==='inactive','Akun bukan akun nonaktif.');expected();note();if(!u.super){need(r&&!r.archived,'Tinjau peran aktif sebelum mengaktifkan akun.');need(p.scope==='all'||p.labels?.length,'Pilih cakupan label.')}const before=copy(u);if(!u.super){u.role=r.id;u.scope=p.scope;u.labels=p.labels||[]}u.status='active';u.session++;u.version++;audit(s,a,k,u.id,before,u,p.note,at);return {id:u.id}}
 if(k==='handoff'){const h=s.handoffs.find(h=>h.id===p.id);need(h?.status==='pending','Pengalihan telah berubah.');const j=jobs.find(j=>j.key===h.key);need(j&&!j.closed&&!j.handler,'Pekerjaan telah selesai atau memiliki penanggung jawab baru.');need(eligible(s,[j],p.to),'Pengganti tidak memiliki izin dan cakupan yang sesuai.');const before=copy(h);h.to=p.to;h.status='assigned';h.actor=a.id;h.assignedAt=at;audit(s,a,k,h.key,before,h,p.note,at);return {moves:[h]}}
 if(k==='review-new'){const ids=(p.ids||[]).filter(x=>catalog.some(c=>c.id===x));s.reviewed=[...new Set([...s.reviewed,...ids])];audit(s,a,k,'catalog',{},ids,p.note,at);return {ids}}
 throw Error('Tindakan tidak dikenal.');
}
function activate(s,id,generation,profile,at=Date.now()){const u=user(s,id);need(u?.status==='invited'&&u.invite.status==='valid'&&u.invite.generation===generation,'Undangan ini sudah diganti atau dicabut.');need(role(s,u.role)&&!role(s,u.role).archived,'Peran undangan perlu ditinjau Super Admin.');need(profile.name?.trim()&&String(profile.password||'').length>=8&&profile.password===profile.confirm,'Periksa nama dan kata sandi minimal 8 karakter.');const before=copy(u);u.name=profile.name.trim();u.status='active';u.joined=new Date(at).toISOString().slice(0,10);u.invite.status='used';u.version++;u.session++;audit(s,{id:u.id},'activate',u.id,before,u,'Aktivasi simulasi; kata sandi tidak disimpan.',at);return u.id}
const API={catalog,groups,seed,user,role,normalize,can,effective,impact,eligible,act,activate};if(typeof module!=='undefined')module.exports=API;root.Staff114=API;
})(typeof window!=='undefined'?window:globalThis);
