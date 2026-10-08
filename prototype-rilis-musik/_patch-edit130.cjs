const fs = require('fs');
const f = 'prototype-v13.0/v130.js';
let s = fs.readFileSync(f, 'utf8');
const rep = (a, b) => { if (!s.includes(a)) throw new Error('NOT FOUND: ' + a.slice(0, 90)); s = s.replace(a, b); };

// 1) dirty flag di state editor
rep(`const editor130={owner:null,base:0,draft:null,drag:null,token:0,busy:false,error:'',status:''};`,
    `const editor130={owner:null,base:0,draft:null,drag:null,token:0,busy:false,error:'',status:'',dirty:false};`);

// 2) draft baru -> bersih
rep(`editor130.error='';editor130.status='';}\n return editor130.draft;`,
    `editor130.error='';editor130.status='';editor130.dirty=false;}\n return editor130.draft;`);

// 3) active130: tunjukkan draft juga saat dirty (pratinjau belum tersimpan tetap terlihat)
rep(`function active130(){return editor130.drag&&editor130.owner===state.user?editor130.draft:config130();}`,
    `function active130(){return editor130.owner===state.user&&editor130.draft&&(editor130.drag||editor130.dirty)?editor130.draft:config130();}`);

// 4) finishEdit130: bersihkan dirty setelah simpan / batal
rep(`editor130.error='';editor130.status=T('Perubahan tersimpan.','Changes saved.');}`,
    `editor130.error='';editor130.status=T('Perubahan tersimpan.','Changes saved.');editor130.dirty=false;}`);
rep(`editor130.error=error.message;editor130.status='';}\n editor130.drag=null;decorate129();editorGeometry130();`,
    `editor130.error=error.message;editor130.status='';editor130.dirty=false;}\n editor130.drag=null;decorate129();editorGeometry130();`);

// 5) markup: tambah bilah kontrol (slider presisi + peredupan + Simpan/Atur ulang)
const controls = `<div class="design-controls130"><div class="design-sliders130">\${[['size',T('Ukuran','Size'),50,220],['x',T('Posisi horizontal','Horizontal position'),-50,50],['y',T('Posisi vertikal','Vertical position'),-50,50]].map(([k,l,min,max])=>'<label class="design-slider130"><span>'+l+'</span><input type="range" min="'+min+'" max="'+max+'" step="1" data-edit130="'+k+'"><output data-out130="'+k+'"></output></label>').join('')}<label class="design-slider130 shade130"><span>\${T('Peredupan gambar','Image dimming')}</span><input type="range" min="14" max="66" step="1" data-edit130="shade"><output data-out130="shade"></output></label></div><div class="design-actions130"><button type="button" class="btn" data-edit130-reset>\${T('Atur ulang','Reset')}</button><button type="button" class="btn primary" data-edit130-save>\${T('Simpan tampilan','Save appearance')}</button></div></div>`;
rep(`}</div><p id="design-status130" class="design-status130" role="status" aria-live="polite">\${T('Tarik desain untuk memindahkan. Tarik sudut untuk mengubah ukuran.','Drag the design to move it. Drag a corner to resize.')}</p></section>`,
    `}</div>${controls}<p id="design-status130" class="design-status130" role="status" aria-live="polite">\${T('Tarik desain atau atur penggeser, lalu Simpan.','Drag the design or adjust the sliders, then Save.')}</p></section>`);

// 6) editorGeometry130: sinkronkan slider + status tombol + teks default
rep(`if(status){status.textContent=editor130.error||editor130.status||T('Tarik desain untuk memindahkan. Tarik sudut untuk mengubah ukuran.','Drag the design to move it. Drag a corner to resize.');status.classList.toggle('is-error130',!!editor130.error);}\n document.querySelector('[data-upload130]')?.toggleAttribute('disabled',editor130.busy);`,
    `if(status){status.textContent=editor130.error||editor130.status||(editor130.dirty?T('Belum tersimpan — pilih Simpan untuk menerapkan.','Unsaved — choose Save to apply.'):T('Tarik desain atau atur penggeser, lalu Simpan.','Drag the design or adjust the sliders, then Save.'));status.classList.toggle('is-error130',!!editor130.error);status.classList.toggle('is-dirty130',!editor130.error&&editor130.dirty);}\n document.querySelector('[data-upload130]')?.toggleAttribute('disabled',editor130.busy);\n document.querySelectorAll('[data-edit130]').forEach(el=>{const k=el.dataset.edit130;el.value=k==='shade'?Math.round((draft.asset.shade??.3)*100):draft.value[k];});\n document.querySelectorAll('[data-out130]').forEach(el=>{const k=el.dataset.out130;el.textContent=k==='shade'?Math.round((draft.asset.shade??.3)*100)+'%':(k==='size'?'':(draft.value[k]>0?'+':''))+draft.value[k]+'%';});\n document.querySelector('.shade130')?.classList.toggle('is-hidden130',draft.asset.kind!=='image');\n document.querySelector('[data-edit130-save]')?.toggleAttribute('disabled',!editor130.dirty);\n document.querySelector('[data-edit130-reset]')?.toggleAttribute('disabled',!editor130.dirty);`);

// 7) upload: tahapkan sebagai draft (bukan auto-save) — user bisa atur peredupan dulu
rep(`headerGuard129();save130({value:draft130().value,asset},version);\n  editor130.draft=null;editor130.busy=false;render();editor130.status=T('Desain baru tersimpan.','New design saved.');editorGeometry130();`,
    `headerGuard129();const draft=draft130();draft.asset=asset;editor130.dirty=true;editor130.status=T('Desain baru dimuat — atur lalu Simpan.','New design loaded — adjust, then Save.');art130(document.querySelector('.design-stage130 .masthead-atmosphere127'),draft);art130(document.querySelector('.masthead124 .masthead-atmosphere127'),draft);editorGeometry130();`);

// 8) lepas drag: jangan simpan — tandai dirty
rep(` if(cancel||drag.owner!==state.user){editor130.drag=null;editor130.draft=null;decorate129();editorGeometry130();return;}\n finishEdit130();`,
    ` if(cancel||drag.owner!==state.user){editor130.drag=null;editor130.draft=null;editor130.dirty=false;decorate129();editorGeometry130();return;}\n editor130.drag=null;editor130.dirty=true;editor130.status=T('Belum tersimpan — pilih Simpan untuk menerapkan.','Unsaved — choose Save to apply.');decorate129();editorGeometry130();`);

// 9) tombol arah: pratinjau saja, tidak auto-save; Escape juga bersihkan dirty
rep(`  if(event.key==='Escape'){if(editor130.drag){editor130.drag=null;editor130.draft=null;decorate129();editorGeometry130();}return;}`,
    `  if(event.key==='Escape'){if(editor130.drag){editor130.drag=null;editor130.draft=null;editor130.dirty=false;decorate129();editorGeometry130();}return;}`);
rep(`   editor130.draft.value=value;finishEdit130();`,
    `   editor130.draft.value=value;editor130.dirty=true;editor130.status=T('Belum tersimpan — pilih Simpan untuk menerapkan.','Unsaved — choose Save to apply.');decorate129();editorGeometry130();`);

// 10) peredupan default lebih ringan — gambar tidak lagi digelapkan berlebihan
rep(`  const shade=luminance>.4?.66:luminance>.15?.45:.18;`,
    `  const shade=luminance>.45?.4:luminance>.2?.26:.14;`);

// 11) handler slider + tombol simpan/reset
rep(`window.addEventListener('pointerdown',event=>{\n const stage=event.target.closest('.design-stage130');`,
    `window.addEventListener('input',event=>{\n const input=event.target.closest?.('[data-edit130]');if(!input)return;\n try{headerGuard129();const draft=draft130(),k=input.dataset.edit130,v=Number(input.value);\n  if(k==='shade'){if(draft.asset.kind==='image')draft.asset={...draft.asset,shade:Math.max(.14,Math.min(.66,v/100))};}\n  else{const b=Header130.bounds[k];draft.value[k]=Math.round(Math.max(b[0],Math.min(b[1],v)));}\n  editor130.dirty=true;editor130.error='';editor130.status='';editorGeometry130();art130(document.querySelector('.masthead124 .masthead-atmosphere127'),draft);\n }catch(error){editor130.error=error.message;editorGeometry130();}\n},true);\nwindow.addEventListener('pointerdown',event=>{\n const stage=event.target.closest('.design-stage130');`);

rep(` const button=event.target.closest('[data-u122="staff-select"],[data-u122="staff-prev"],[data-u122="staff-next"]');if(!button)return;`,
    ` if(event.target.closest('[data-edit130-save]')){event.preventDefault();event.stopImmediatePropagation();try{headerGuard129();finishEdit130();}catch(error){editor130.error=error.message;editorGeometry130();}return;}\n if(event.target.closest('[data-edit130-reset]')){event.preventDefault();event.stopImmediatePropagation();const saved=config130();editor130.draft={value:{...saved.value},asset:{...saved.asset}};editor130.base=saved.version;editor130.dirty=false;editor130.error='';editor130.status=T('Perubahan dibatalkan.','Changes reverted.');decorate129();editorGeometry130();return;}\n const button=event.target.closest('[data-u122="staff-select"],[data-u122="staff-prev"],[data-u122="staff-next"]');if(!button)return;`);

fs.writeFileSync(f, s);
console.log('v130.js ok');

// CSS
const fc = 'prototype-v13.0/v130.css';
let c = fs.readFileSync(fc, 'utf8');
c += `
/* Panel kontrol desain header: slider presisi + aksi simpan */
.design-controls130{display:flex;justify-content:space-between;align-items:flex-end;gap:18px 24px;margin-top:14px;flex-wrap:wrap}
.design-sliders130{display:flex;gap:20px;flex-wrap:wrap;flex:1;min-width:0}
.design-slider130{display:grid;grid-template-columns:1fr auto;gap:4px 10px;min-width:160px;flex:1;max-width:230px;align-items:center}
.design-slider130>span{font-size:11px;color:var(--muted)}
.design-slider130>output{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums;text-align:right}
.design-slider130>input[type=range]{grid-column:1/-1;width:100%;height:22px;margin:0;accent-color:var(--blue)}
.shade130.is-hidden130{visibility:hidden}
.design-actions130{display:flex;align-items:center;gap:10px}
.design-status130{margin-top:10px}
.design-status130.is-dirty130{color:var(--copper)}
@media(max-width:760px){.design-controls130{flex-direction:column;align-items:stretch}.design-actions130{justify-content:flex-end}}
`;
fs.writeFileSync(fc, c);
console.log('v130.css ok');
