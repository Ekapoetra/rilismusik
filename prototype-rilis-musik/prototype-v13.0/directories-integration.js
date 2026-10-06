const directoryActBase=RM10.act;
RM10.act=function(s,action,p={}){const member=RM10.getMember(s,p.member||s.member);let params=p;
 if(action==='contract'&&member?.identity.location&&!member.identity.location.complete)throw Error('location');
 if(action==='bank_submit'){const bank=directoryBank(p.bank);params={...p,bank:bank?.name||String(p.bank||'').trim(),holder:directoryTitle(p.holder)};}
 if(['profile','profile_edit'].includes(action)){params={...p};if(p.email!==undefined)params.email=String(p.email).trim().toLowerCase();if(p.identity)params.identity={...p.identity,person:p.identity.person===undefined?member.identity.person:directoryTitle(p.identity.person)};}
 const result=directoryActBase(s,action,params);
 if(action==='bank_submit')member.bank.pending.directoryBankId=directoryBank(params.bank)?.id||null;
 if(['profile','profile_edit'].includes(action)&&params.identity?.location)Object.assign(member.identity,{location:params.identity.location,legacyAddress:params.identity.legacyAddress||member.identity.legacyAddress||''});
 return result;
};
const directoryErrorBase=error10;
error10=function(code){return code==='location'?T('Pilih provinsi, kabupaten/kota, dan kecamatan yang sesuai, lalu lengkapi kode pos.','Choose a matching province, regency/city and district, then complete the postal code.'):directoryErrorBase(code);};
const directoryDetailsBase=identityDetails102;
identityDetails102=function(m){const l=m.identity.location;if(!l)return directoryDetailsBase(m);const body=directoryDetailsBase(m),dom=document.createElement('template');dom.innerHTML=body;const rows=dom.content.querySelectorAll('dl>div');for(const row of rows){if(row.querySelector('dt')?.textContent===T('Alamat','Address')&&l.complete)row.remove();}const list=dom.content.querySelector('dl');for(const [title,value] of [[T('Provinsi','Province'),l.province],[T('Kabupaten/kota','Regency/city'),l.regency],[T('Kecamatan','District'),l.district]])list.insertAdjacentHTML('beforeend',`<div><dt>${title}</dt><dd>${E(value||'—')}</dd></div>`);return dom.innerHTML;};
const directoryDraftBase=restoreDrafts10;
restoreDrafts10=function(){directoryDraftBase();for(const f of document.querySelectorAll('[data-ten-form=profile]'))if(f.elements.province)directoryRefresh(f,null);};
