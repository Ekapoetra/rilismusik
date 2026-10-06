/* Shared browser capabilities for localhost, LAN HTTP, and HTTPS. */
function browserId120(){
 if(typeof crypto.randomUUID==='function')return crypto.randomUUID();
 const bytes=crypto.getRandomValues(new Uint8Array(16));
 bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
 const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
 return [hex.slice(0,8),hex.slice(8,12),hex.slice(12,16),hex.slice(16,20),hex.slice(20)].join('-');
}
async function copyText120(value){
 const text=String(value);
 if(navigator.clipboard?.writeText&&window.isSecureContext){try{await navigator.clipboard.writeText(text);return;}catch{/* A denied clipboard can still support a user-initiated copy. */}}
 const active=document.activeElement,selection=active&&typeof active.selectionStart==='number'?{start:active.selectionStart,end:active.selectionEnd}:null;
 const range=window.getSelection()?.rangeCount?window.getSelection().getRangeAt(0).cloneRange():null;
 const field=document.createElement('textarea');field.value=text;field.readOnly=true;field.setAttribute('aria-label',typeof T==='function'?T('Teks untuk disalin','Text to copy'):'Text to copy');
 field.style.cssText='position:fixed;left:0;top:0;width:1px;height:1px;opacity:0;pointer-events:none;';
 (document.querySelector('dialog[open]')||document.body).append(field);
 let copied=false;
 try{field.focus({preventScroll:true});field.select();field.setSelectionRange(0,text.length);copied=!!document.execCommand('copy');}catch{/* Report a readable failure below. */}
 finally{field.remove();if(active?.isConnected){active.focus({preventScroll:true});if(selection)active.setSelectionRange(selection.start,selection.end);}if(range&&!selection){const current=window.getSelection();current.removeAllRanges();current.addRange(range);}}
 if(!copied)throw Error(typeof T==='function'?T('Teks belum disalin. Pilih dan salin teks secara manual.','Text was not copied. Select and copy it manually.'):'Text was not copied. Select and copy it manually.');
}
