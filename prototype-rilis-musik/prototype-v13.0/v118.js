/* B22–B31: complete Staff safeguards without finalizing KPI or compensation policy. */
function id118(){return 'SL-'+browserId120();}
const errors118={
 staff_structure:['Data Staff perlu diperiksa sebelum perubahan dilanjutkan.','Staff data needs review before changes can continue.'],
 staff_not_found:['Akun Staff atau periode tidak tersedia.','The Staff account or period is unavailable.'],
 payroll_period:['Periode kompensasi tidak valid.','The compensation period is invalid.'],
 payroll_amount:['Nominal kompensasi tidak valid atau melampaui batas perhitungan.','The compensation amount is invalid or exceeds the calculation limit.'],
 payroll_unavailable:['Rincian periode belum lengkap. Lengkapi data sebelum membuat slip atau mencatat pembayaran.','Period details are incomplete. Complete the data before creating a payslip or recording payment.'],
 revenue_missing:['Data pendapatan periode belum tersedia.','Revenue for this period is not yet available.'],
 compensation_midmonth:['Perubahan di tengah bulan memerlukan ketentuan perhitungan yang belum ditetapkan. Gunakan tanggal 1 untuk perubahan satu periode penuh.','Mid-month changes require a calculation policy that has not been defined. Use the first day for a full-period change.'],
 compensation_historical:['Perubahan ini memengaruhi periode dengan slip yang sudah diterbitkan. Catatan historis harus tetap dipertahankan.','This change affects a period with an issued payslip. Historical records must be preserved.'],
 compensation_missing:['Versi kompensasi untuk periode ini belum tersedia.','The compensation version for this period is unavailable.'],
 slip_missing:['Dokumen slip tidak ditemukan.','The payslip document was not found.'],
 slip_identity:['Identitas dokumen belum unik. Tinjau dokumen sebelum melanjutkan.','The document identity is not unique. Review the document before continuing.'],
 slip_origin:['Koreksi harus tetap menggunakan Staff dan periode dokumen asal.','A correction must retain the Staff member and period of the original document.'],
 slip_stale:['Versi slip sudah berubah atau memerlukan peninjauan. Buka versi aktif terbaru sebelum menerbitkan koreksi.','The payslip version has changed or needs review. Open the latest active version before issuing a correction.'],
 slip_amount:['Total dokumen harus berupa nominal yang valid dan tidak negatif.','The document total must be a valid, non-negative amount.'],
 policy_invalid:['Periksa jadwal, tanggal berlaku, jatah, dan hari kerja.','Check the schedule, effective date, allowance, and working days.'],
 policy_reserved:['Jatah baru lebih kecil dari cuti yang sudah digunakan atau dicadangkan. Sesuaikan aturan tanpa mengurangi hak tersebut.','The new allowance is below used or reserved leave. Adjust the policy without reducing those entitlements.'],
 correction_stale:['Catatan kehadiran sudah berubah atau permintaan telah diputuskan. Tinjau catatan terbaru.','The attendance record has changed or the request has been decided. Review the latest record.'],
 correction_invalid:['Periksa tanggal serta jam masuk dan pulang.','Check the date and arrival and departure times.']
};
const message118=code=>errors118[code]?T(...errors118[code]):code;
function saveMessage118(err){return err.name==='QuotaExceededError'?T('Pembayaran belum dicatat. Penyimpanan browser penuh; coba kembali setelah ruang tersedia.','Payment was not recorded. Browser storage is full; retry after space is available.'):errors118[err.code]?message118(err.code):err.message;}
const toastBefore118=toast;toast=function(message){return toastBefore118(message118(message));};
const saveErrorBefore118=saveError117;saveError117=function(form,err){
 if(!form.isConnected){const live=[...document.querySelectorAll('form')].find(x=>x.dataset.form===form.dataset.form&&x.dataset.id===form.dataset.id);if(live){const seen={};for(const field of form.elements){if(!field.name||['file','submit','button'].includes(field.type))continue;const index=seen[field.name]||0;seen[field.name]=index+1;const target=[...live.elements].filter(x=>x.name===field.name)[index];if(!target)continue;if(['checkbox','radio'].includes(field.type))target.checked=field.checked;else target.value=field.value;}form=live;}}
 if(errors118[err.code])err=Object.assign(Error(message118(err.code)),{code:err.code});return saveErrorBefore118(form,err);
};
function ensureStaff118(){return Staff118.ensure(data,people.map(p=>p.id),id118,day());}
function saveCompensation118(id,values){ensureStaff118();return Staff118.schedule(data,id,values,id118,day());}
function saveQuota118(id,n){const year=Number(day().slice(0,4)),candidate={...data,quotaAdjust:{...data.quotaAdjust,[`${id}:${year}`]:n}},reserved=data.leaves.filter(x=>x.staff===id&&x.type==='annual'&&x.start.startsWith(String(year))&&['used','approved','pending'].includes(x.status)).reduce((sum,x)=>sum+x.days,0);if(Staff118.quota(candidate,person(id),year)<reserved)throw Object.assign(Error('policy_reserved'),{code:'policy_reserved'});data.quotaAdjust[`${id}:${year}`]=n;}
payments=function(id,m=state.period){
 ensureStaff118();const rows=Staff118.rows(data,id,m,{salary:t('Gaji tetap','Base salary'),allowance:t('Tunjangan','Allowance'),sales:t('Bonus penjualan','Sales bonus')});
 return rows.concat(data.surprises.filter(x=>x.staff===id&&x.month===m&&(me().super||x.published)).map(x=>({key:x.id,label:t('Bonus Apresiasi','Appreciation bonus'),amount:Number.isSafeInteger(x.amount)&&x.amount>=0?x.amount:null,available:Number.isSafeInteger(x.amount)&&x.amount>=0,paid:Number.isSafeInteger(x.amount)&&x.amount>=0&&!!x.paid,scheduledDate:m+'-29',date:x.paidDate||m+'-29',published:x.published,note:x.note})));
};
function recordPayment118(id,m,key){
 if(!user114(id))throw Error(message118('staff_not_found'));
 const row=payments(id,m).find(r=>r.key===key);if(!row||!row.available)throw Error(message118('payroll_unavailable'));
 if(row.paid)return false;
 const bonus=data.surprises.find(x=>x.id===key);
 if(bonus){if(bonus.staff!==id||bonus.month!==m)throw Error(message118('staff_not_found'));bonus.paid=true;bonus.paidDate=day();}
 else{data.paid[`${id}:${m}:${key}`]=true;data.paymentDates[`${id}:${m}:${key}`]=day();}
 return true;
}
// All mutation dispatchers use the same active-actor check and one storage commit.
superForms117.delete('v5-time');
for(const kind of ['payroll-payment','payroll-bonus','attendance-approval','slip-active118'])superForms117.add(kind);
for(const [action,kind]of [['pay-component','payroll-payment'],['pay-bonus','payroll-payment'],['publish-bonus','payroll-bonus'],['v5-time-approve','attendance-approval'],['correction-approve','attendance-approval']])writeActions117.set(action,kind);
const guardBefore118=staffGuard117;
staffGuard117=function(kind,target){guardBefore118(kind,target);if(kind==='v5-time'){const u=user114();if(!user114(target)||target!==u.id&&!u.super)throw Error(T('Koreksi hanya dapat diajukan untuk catatanmu sendiri.','Corrections can only be requested for your own records.'));}};
const submitBefore118=handleSubmit;
handleSubmit=async function(form){
 if(form.dataset.form==='v5-time')form.dataset.id=String(new FormData(form).get('staff')||'');
 if(form.dataset.form==='slip-active118'){
  if(!form.reportValidity())return;
  try{return await legacyCommit117(()=>{const v=new FormData(form),s=Staff118.chooseActive(data,String(v.get('slip')),String(v.get('reason')),day(),me().id);log(t('Versi slip aktif ditetapkan','Active payslip version selected'),s.id+' · '+v.get('reason'));closeModal();render();},()=>staffGuard117('slip-active118'));}catch(err){saveError117(form,err);return;}
 }
 return submitBefore118(form);
};
timeCorrectionForm=function(id,d=day()){
 try{staffGuard117('v5-time',id);if(!Staff118.date(d)||d>day())throw Error(message118('correction_invalid'));}catch(err){return toast(err.message);}
 const r=data.timeRecords[id+':'+d]||{},p=Staff118.policyForDate(data,id,d);
 modal(t('Ajukan koreksi waktu','Request a time correction'),`<p class="sub">${E(person(id).name)}</p><form data-form="v5-time" data-id="${E(id)}"><input type="hidden" name="staff" value="${E(id)}">${field('date',t('Tanggal catatan','Record date'),d,'date',`required max="${day()}"`)}<div class="form-grid space">${field('in',t('Jam masuk','Arrival'),r.in||p.start,'time','required')}${field('out',t('Jam pulang','Departure'),r.out||p.end,'time','required')}</div>${reasonField()}<p class="scope-note">${t('Pengajuan tidak langsung mengubah kehadiran. Koreksi akan ditinjau terlebih dahulu.','A request does not immediately change attendance. The correction will be reviewed first.')}</p>${formEnd(t('Ajukan koreksi','Request correction'))}</form>`);
};
const actionBefore118=handleAction;
handleAction=async function(b){
 const a=b.dataset.action,id=b.dataset.id;
 if(a==='attendance-correction')return timeCorrectionForm(me().id,b.dataset.date||day());
 if(a==='slip-review118')return reviewSlips118(id);
 if(['slip-new','slip-edit','salary','quota','staff-pay','v5-time-correct','v8-attendance'].includes(a)){
  try{staffGuard117(['slip-new','slip-edit'].includes(a)?'slip':['salary','quota','staff-pay'].includes(a)?a==='staff-pay'?'salary':a:a==='v5-time-correct'?'v5-time':'personal',id||me().id);}catch(err){return toast(err.message);}
 }
 return actionBefore118(b);
};
const compensationPageBefore118=compensationPage;
compensationPage=function(){
 const box=document.createElement('div');box.innerHTML=compensationPageBefore118();
 const team=me().super&&state.comp==='team',pending=t('Data belum lengkap','Incomplete data');
 if(team){for(const row of box.querySelectorAll('tbody tr')){const id=row.querySelector('[data-action=staff-pay]')?.dataset.id;if(id&&payments(id).some(x=>!x.available)){row.cells[1].textContent=pending;row.cells[3].textContent=pending;}}}
 else{const rows=payments(me().id);if(rows.some(x=>!x.available)){for(const selector of ['.reconcile>div:first-child strong','.reconcile>div:last-child strong','.earnings6>strong']){const el=box.querySelector(selector);if(el)el.textContent=pending;}const caption=box.querySelector('.earnings6>p');if(caption)caption.textContent=t('Total periode menunggu kelengkapan data pendapatan.','The period total is awaiting complete revenue data.');}
 const lines=box.querySelector('.grid .panel')?.querySelectorAll('.row')||[];rows.forEach((x,i)=>{const row=lines[i];if(!row)return;if(!x.available){row.querySelector('.num strong').textContent=t('Belum tersedia','Not available');row.querySelector('small').textContent=message118(x.reason||'payroll_unavailable');row.querySelector('.num').querySelector('.badge')?.replaceWith(dom118(badge(pending)));}else if(x.key==='sales')row.querySelector('small').textContent=date(x.date)+' · '+x.percent+'% × '+money(data.revenue[state.period]);});}
 return box.innerHTML;
};
function dom118(html){const box=document.createElement('div');box.innerHTML=html;return box.firstElementChild;}
const downloadBefore118=downloadDocument;
downloadDocument=function(id,kind,period){if(kind==='payslip'&&payments(id,period||state.period).some(x=>!x.available))return toast(message118('payroll_unavailable'));return downloadBefore118(id,kind,period);};
staffPayModal=function(id){
 try{staffGuard117('salary',id);}catch(err){return toast(err.message);}
 const next=data.nextComp?.[id],rows=payments(id),scheduled=next&&next.effective>day();
 modal(t('Kompensasi','Compensation')+' · '+person(id).name,`${next?`<div class="notice">${scheduled?t('Perubahan terjadwal','Scheduled change'):t('Versi kompensasi berlaku','Effective compensation version')} · ${date(next.effective)}<br>${t('Gaji tetap','Base salary')} ${money(next.salary)} · ${t('Tunjangan','Allowance')} ${money(next.allowance)} · ${t('Bonus penjualan','Sales bonus')} ${next.percent}%</div>`:''}${rows.map(x=>`<div class="row"><div><strong>${x.label}</strong><small>${x.available?money(x.amount):t('Belum tersedia','Not available')} · ${x.key==='sales'?x.percent+'% · ':''}${x.paid?date(x.date):t('Belum ada pembayaran tercatat','No payment recorded')}${!x.available?'<br>'+E(message118(x.reason||'payroll_unavailable')):''}</small></div>${x.paid?badge(t('Dibayar','Paid'),'green'):x.available?btn(t('Catat pembayaran','Record payment'),'pay-component',`data-id="${id}" data-month="${state.period}" data-key="${x.key}"`,'small'):badge(t('Data belum lengkap','Incomplete data'))}</div>`).join('')}<div class="inline space">${btn(t('Atur gaji & bonus','Edit salary & bonus'),'salary',`data-id="${id}"`,'small')}${btn(t('Unduh slip','Download payslip'),'payslip',`data-id="${id}"`,'small')}</div>`);
};
slipForm=function(id){
 try{staffGuard117('slip',id);}catch(err){return toast(err.message);}
 const x=id?Staff118.slip(data,id):null;if(x&&x.status!=='draft')return;
 const locked=!!x?.previous;
 const identity=locked?`<input type="hidden" name="staff" value="${E(x.staff)}"><input type="hidden" name="month" value="${E(x.month)}"><div class="field"><label>Staff</label><strong class="locked118">${E(person(x.staff).name)}</strong></div><div class="field"><label>${t('Periode','Period')}</label><strong class="locked118">${month(x.month)}</strong></div>`:`${selectField('staff','Staff',people.map(p=>[p.id,p.name]),x?.staff||'adovi')}${selectField('month',t('Periode','Period'),[['2026-08',month('2026-08')],['2026-07',month('2026-07')]],x?.month||state.period)}`;
 modal(locked?t('Koreksi slip','Correct payslip'):t('Draf slip gaji','Payslip draft'),`<form data-form="slip" data-id="${E(id||'new')}"><div class="form-grid">${identity}${field('adjust',t('Koreksi nominal dokumen (IDR)','Document amount correction (IDR)'),x?.adjust||0,'number','step="1" min="-100000000" max="100000000" required')}${field('note',t('Catatan / alasan','Note / reason'),x?.note||'','text','required maxlength="300"')}</div><p class="scope-note">${locked?t('Penerima dan periode mengikuti dokumen asal. Koreksi tidak mengubah catatan pembayaran.','The recipient and period follow the original document. Corrections do not change payment records.'):t('Rincian mengikuti periode terpilih. Dokumen tidak mengubah catatan pembayaran.','Details follow the selected period. The document does not change payment records.')}</p>${x?.review118==='origin_ambiguous'?`<p class="save-error117">${t('Hubungan dokumen asal perlu ditinjau. Pertahankan dokumen ini, lalu buat koreksi dari versi aktif yang sudah dipastikan.','The original document link needs review. Retain this document, then create a correction from the confirmed active version.')}</p>`:formEnd(t('Simpan draf','Save draft'))}</form>`);
};
function reviewSlips118(id){
 try{staffGuard117('slip');const s=Staff118.slip(data,id),rows=Staff118.active(data,s.staff,s.month);modal(t('Tinjau versi slip','Review payslip versions'),`<p class="sub">${E(person(s.staff).name)} · ${month(s.month)}</p><form data-form="slip-active118"><p>${t('Tentukan dokumen yang tetap menjadi versi aktif. Dokumen lainnya disimpan dalam riwayat sebagai digantikan; catatan pembayaran tetap sama.','Choose the document that remains active. Other documents remain in history as replaced; payment records stay unchanged.')}</p><div class="slip-review118">${rows.map(x=>`<label class="check"><input type="radio" name="slip" value="${E(x.id)}" required><span><strong>${E(x.id)} · v${x.version}</strong><small>${money(Staff118.sum(x.rows)+(x.adjust||0))} · ${E(x.note||'')}</small></span></label>`).join('')}</div>${reasonField()}${formEnd(t('Tetapkan versi aktif','Set active version'))}</form>`);}catch(err){toast(err.message);}
}
function slipLabel118(s){return /^SL-(?:[a-f0-9]{32}|[a-f0-9-]{36})$/.test(s.id)?`SL-${s.month.replace('-','')}-${s.id.slice(-8).toUpperCase()}`:s.id;}
const slipsBefore118=compensationSlips;
compensationSlips=function(){const html=slipsBefore118(),team=me().super&&state.comp==='team',box=document.createElement('div');box.innerHTML=html;for(const row of box.querySelectorAll('tbody tr')){const button=row.querySelector('[data-action]'),id=button?.dataset.id,s=data.slips.find(x=>x.id===id);if(!s)continue;const caption=row.querySelector('td small');if(caption)caption.textContent=slipLabel118(s)+' · v'+s.version;if(s.status==='void'&&s.replacedBy118)row.querySelector('td:nth-child(3)').innerHTML=badge(t('Digantikan','Replaced'));if(team&&s.review118==='duplicate_active'){row.querySelector('td:nth-child(3)').innerHTML=badge(t('Tinjau versi','Review versions'),'amber');row.querySelector('.team-actions').innerHTML=btn118('slip-review118',id);}}return box.innerHTML;};
function btn118(a,id){return btn(t('Tinjau dokumen','Review documents'),a,`data-id="${E(id)}"`,'small');}
attendanceToday=function(p){
 const d=day(),policy=Staff118.policyForDate(data,p.id,d);
 if(!policy.days.includes(new Date(d+'T12:00Z').getUTCDay())||data.holidays.includes(d))return {label:t('Libur','Day off'),time:'—',color:''};
 if(data.leaves.some(l=>l.staff===p.id&&['approved','used'].includes(l.status)&&l.start<=d&&l.end>=d))return {label:t('Cuti','On leave'),time:'—',color:'blue'};
 const r=data.timeRecords[p.id+':'+d];if(!r?.in)return {label:t('Belum tercatat','Not recorded'),time:'—',color:''};
 const late=clockMinutes(r.in)>clockMinutes(policy.start)+policy.grace;return {label:late?t('Terlambat','Late'):t('Tepat waktu','On time'),time:r.in,color:late?'amber':'green'};
};
const timeBefore118=timeSummary;
timeSummary=function(id,d=day()){const current=data.policy;try{data.policy=Staff118.policyForDate(data,id,d);return timeBefore118(id,d);}finally{data.policy=current;}};
const attendanceBefore118=attendancePage;
attendancePage=function(){const box=document.createElement('div');box.innerHTML=attendanceBefore118();if(!me().super)box.querySelector('.pagehead')?.insertAdjacentHTML('beforeend',btn(t('Rincian kehadiran','Attendance details'),'v8-attendance',`data-id="${me().id}"`,'small'));return box.innerHTML;};
const renderBefore118=render;
function stamp118(){document.title='Rilis Musik · V11.8';document.querySelectorAll('.version-pill,.floating107>strong').forEach(x=>x.textContent='V11.8');const f=document.querySelector('.footer span');if(f)f.textContent='RILIS MUSIK · V11.8';}
render=function(){if(Persistence117.blocked)return;renderBefore118();stamp118();};
const scenes118=[
 ['v118-time','admin','Koreksi waktu milik Staff','Staff time correction','Ajukan koreksi tanpa mengubah catatan final; keputusan tetap ditinjau.','Request a correction without changing the final record; the decision is reviewed.'],
 ['v118-policy','super','Kebijakan dan hak cuti','Policy and leave entitlements','Buka aturan; kuota yang sudah digunakan atau dicadangkan tetap dilindungi.','Open the policy; used or reserved leave remains protected.'],
 ['v118-payroll','super','Kompensasi dan versi slip','Compensation and payslip versions','Periksa jadwal kompensasi, tanggal pembayaran, dan koreksi dokumen.','Review compensation schedules, payment dates, and document corrections.']
];
studioCatalog.unshift(...scenes118.map(([id,role,a,b,c,d])=>({version:'11.8',id,role,title:[a,b],description:[c,d]})));
const studioBefore118=studioStart;
studioStart=async function(id){if(!id.startsWith('v118-')){const result=await studioBefore118(id);ensureStaff118();stamp118();return result;}await studioBefore118('v107-dashboard');document.querySelectorAll('dialog[open]').forEach(d=>d.close());role102(id==='v118-time'?'admin':'super');state.user=id==='v118-time'?'adovi':'jeck';state.mode='staff';state.page=id==='v118-payroll'?'compensation':'attendance';state.comp='team';v3.attendanceTab=id==='v118-policy'?'policy':'records';ensureStaff118();render();studioSelected=id;save10();stamp118();};
if(!Persistence117.blocked){try{atomic10(()=>ensureStaff118());render();}catch(err){toast(message118(err.code)||err.message);}}
