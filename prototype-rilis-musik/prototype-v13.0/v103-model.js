/* Profile amendments keep the approved identity and subscription intact. */
(function(root){
function attach(api){const previous=api.act;
api.act=function(s,action,p={}){
 const m=api.getMember(s,p.member||s.member);
 if(action==='profile'&&m?.active)action='profile_edit';
 if(!['profile_edit','profile_approve','profile_correct','profile_photo'].includes(action))return previous(s,action,p);
 api.tick(s);if(s.failNext){s.failNext=false;throw Error('save_failed');}
 const assert=(v,e)=>{if(!v)throw Error(e);};assert(m,'invalid');
 const log=note=>s.events.unshift({id:'EV-'+(++s.serial),kind:action,target:m.id,note,actor:s.role,at:s.now});
 if(['profile_edit','profile_photo'].includes(action)){
  assert(s.role==='label'&&s.member===m.id,'permission');
  if(action==='profile_photo'){assert(typeof p.photo==='string'&&p.photo.length<2800000&&/^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/.test(p.photo),'invalid');m.avatar103=p.photo;log('');return true;}
  assert(m.active,'state');
  const clean=(v,old)=>v===undefined?old:String(v).trim();
  const after={name:clean(p.name,m.name),email:clean(p.email,m.email),person:clean(p.identity?.person,m.identity.person)};
  assert(after.name&&after.name.length<=120&&after.person&&after.person.length<=120&&/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(after.email),'identity');
  const before={name:m.name,email:m.email,person:m.identity.person};
  const changed=Object.keys(before).some(k=>before[k]!==after[k]);
  assert(!changed||m.profileChange103?.status!=='pending','pending');
  const minor={};for(const k of ['address','postal','country']){minor[k]=clean(p.identity?.[k],m.identity[k]);assert(minor[k]&&minor[k].length<=400,'identity');}
  if(changed)m.profileChange103={version:(m.profileChange103?.version||0)+1,baseVersion:m.version,status:'pending',before,after,at:s.now};
  else if(m.profileChange103?.status==='correction')m.profileChange103.status='withdrawn';
  Object.assign(m.identity,minor);log(changed?'submitted':'saved');return changed?'pending':'saved';
 }
 assert(['admin','super'].includes(s.role),'permission');
 const q=m.profileChange103;assert(q?.status==='pending'&&q.version===Number(p.version)&&q.baseVersion===m.version,'stale');
 if(action==='profile_correct'){assert(typeof p.note==='string'&&p.note.trim(),'reason');q.status='correction';q.note=p.note.trim();}
 else{Object.assign(m,{name:q.after.name,email:q.after.email});m.identity.person=q.after.person;m.version++;m.contractVersion=m.version;q.status='approved';q.resolvedAt=s.now;}
 s.notifications.unshift({member:m.id,key:action,ref:m.id,at:s.now});log(p.note||'');return true;
};return api;}
if(typeof module!=='undefined')module.exports=attach;else attach(root.RM10);
})(typeof window==='undefined'?globalThis:window);
