/* sample/production-sample.json → prototype-v13.0/sample131-data.js
   Mengubah cuplikan produksi (hasil preview-api/sample-export) menjadi data
   ringkas yang dipakai layer v131-sample.js sebagai skenario dummy tambahan.
   Deterministik: menjalankan ulang pada sampel yang sama menghasilkan berkas
   yang sama. Tidak ada kredensial; nomor rekening sudah disamarkan di sumber. */
const fs=require('node:fs'),path=require('node:path');
const SRC=path.join(__dirname,'sample','production-sample.json'),OUT=path.join(__dirname,'prototype-v13.0','sample131-data.js');
const raw=JSON.parse(fs.readFileSync(SRC,'utf8')),d=raw.data;

const slugify=s=>String(s||'').toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,24)||'label';
const used=new Set(['awan','embun']);
const uniq=base=>{let id=base,n=2;while(used.has(id))id=base+'-'+n++;used.add(id);return id;};
const day=v=>{if(!v)return null;const s=String(v).slice(0,10);if(/^\d{4}-\d{2}-\d{2}$/.test(s))return s;const us=String(v).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);if(us)return us[3]+'-'+us[1].padStart(2,'0')+'-'+us[2].padStart(2,'0');const t=Date.parse(v);return Number.isFinite(t)?new Date(t).toISOString().slice(0,10):null;};
const int=v=>Math.round(Number(v)||0);
const title=s=>String(s||'').trim();

/* Label → member id slug */
const labelId=new Map(d.labels.map(l=>[l.id,uniq(slugify(l.label_name))]));
const owner=new Map();for(const u of d.users)if(u.role==='label'){for(const l of d.labels)if(l.user_id===u.id||u.active_label_id===l.id||u.primary_label_id===l.id)owner.set(l.id,u);}
const bankOf=new Map();for(const b of d.bank_accounts){if(!bankOf.has(b.label_id)||b.verified_status==='verified')bankOf.set(b.label_id,b);}
const kycOf=new Map();for(const k of d.kyc_documents)if(k.is_current!==false)kycOf.set(k.label_id,k);
const contractOf=new Map();for(const c of d.contracts)if(c.status==='active')contractOf.set(c.label_id,c);
const PLAN={pay_per_release:'Flex',annual_subscription:'Pro'};

const labels=d.labels.map(l=>{const u=owner.get(l.id)||{},b=bankOf.get(l.id),k=kycOf.get(l.id),c=contractOf.get(l.id);return {
  id:labelId.get(l.id),source:l.id,name:title(l.label_name),pic:title(l.pic_name||u.name||u.responsible_name||''),email:(l.email||u.email||'').toLowerCase(),
  city:title(l.city||''),country:title(l.country||'Indonesia'),address:title(l.address||''),whatsapp:l.whatsapp||u.responsible_whatsapp||'',
  account:l.account_status||'active',kyc:l.kyc_status||null,kycReason:l.kyc_rejection_reason||k?.rejection_reason||null,kycSubmitted:day(l.kyc_submitted_at||k?.uploaded_at),kycReviewed:day(l.kyc_reviewed_at||k?.reviewed_at),
  plan:l.subscription_tier==='multi_label'?'Business':PLAN[l.payment_type]||'Flex',subscription:l.subscription_status||'inactive',tier:l.subscription_tier||null,subscriptionEnd:day(l.subscription_expires_at),
  contract:l.contract_status==='active',contractAt:day(c?.accepted_at),contractBy:title(c?.accepted_by_name||''),
  bank:b?{bank:title(b.bank_name),number:String(b.account_number||''),holder:title(b.account_holder_name),status:b.verified_status||'pending',verifiedAt:day(b.verified_at)}:null,
  balance:{available:int(l.balance_available_idr),pending:int(l.balance_pending_idr),requested:int(l.balance_withdraw_requested_idr)},
  royaltyPercent:Number(l.royalty_percentage_default)||null,joined:day(l.created_at)||'2024-01-01',lastWithdrawnPeriod:l.last_withdrawn_period||null,
  legacyImport:!!l.legacy_import,multi:!!u.multi_label_started_at,logo:l.logo_url||null,blacklisted:!!l.blacklisted
};});

const tracksOf=new Map();for(const t of d.tracks){if(!tracksOf.has(t.release_id))tracksOf.set(t.release_id,[]);tracksOf.get(t.release_id).push(t);}
const artistNames=r=>Array.isArray(r.primary_artists)&&r.primary_artists.length?r.primary_artists.map(a=>title(a.name||a.artist_name||a)).filter(Boolean):[title(r.artist_name)].filter(Boolean);
const releaseId=new Map();
const releases=d.releases.filter(r=>labelId.has(r.label_id)).map((r,i)=>{const id='P-'+String(i+1).padStart(3,'0');releaseId.set(r.id,id);const ts=(tracksOf.get(r.id)||[]).sort((a,b)=>(a.track_number||0)-(b.track_number||0));return {
  id,source:r.id,label:labelId.get(r.label_id),title:title(r.release_title),artists:artistNames(r),featured:Array.isArray(r.featured_artists)?r.featured_artists.map(a=>title(a.name||a)).filter(Boolean):[],
  type:r.release_type||'single',date:day(r.release_date),year:r.year||null,genre:title(r.genre||''),subgenre:title(r.subgenre||''),language:title(r.language||''),explicit:!!r.explicit,
  copyright:title(r.copyright_line||''),pline:title(r.p_line||''),upc:r.upc||null,status:r.status,cover:r.cover_url||null,
  created:day(r.created_at),submitted:day(r.submitted_at),reviewStarted:day(r.review_started_at),delivered:day(r.delivered_to_believe_at),note:title(r.admin_note||''),
  history:(Array.isArray(r.status_history)?r.status_history:[]).map(h=>({status:h.status||h.to||'',at:day(h.at||h.changed_at||h.timestamp),by:title(h.by_name||h.actor_name||h.by||'')})).filter(h=>h.status),
  addons:Array.isArray(r.selected_addons)?r.selected_addons.map(a=>title(a.name||a)).filter(Boolean):[],
  tracks:ts.length?ts.map(t=>({title:title(t.track_title),isrc:t.isrc||'',number:t.track_number||1,composer:title(t.composer||''),lyricist:title(t.lyricist||''),producer:title(t.producer||''),explicit:!!t.explicit,language:title(t.language||''),vocal:t.vocal_type||'',audio:!!t.audio_url})):[{title:title(r.release_title),isrc:'',number:1,composer:'',lyricist:'',producer:'',explicit:!!r.explicit,language:title(r.language||''),vocal:'',audio:false}]
};});

/* Royalti */
const importId=new Map(d.royalty_imports.map((im,i)=>[im.id,'IMP-P'+String(i+1).padStart(2,'0')]));
const imports=d.royalty_imports.map(im=>({id:importId.get(im.id),source:im.id,period:im.period,status:im.status,rate:int(im.exchange_rate_eur_idr),fee:Number(im.fee_percent)||0,file:im.filename||('believe_'+im.period+'.csv'),
  lines:int(im.total_lines),matched:int(im.matched_lines),unmatched:int(im.unmatched_lines),totalEur:Number(im.total_revenue_eur)||0,totalIdr:int(im.total_label_idr),published:day(im.published_at),danaReceived:day(im.dana_received_at),uploaded:day(im.created_at),source_:im.source||'believe'}));
const summary=d.royalty_summary.filter(x=>labelId.has(x.label_id)&&importId.has(x.import_id)).map(x=>({label:labelId.get(x.label_id),import:importId.get(x.import_id),period:x.period,lines:int(x.lines),idr:int(x.label_idr),eur:Math.round((Number(x.revenue_eur)||0)*100)/100,qty:int(x.quantity)}));
const perKey=new Map();
const byTrack=d.royalty_by_track.filter(x=>labelId.has(x.label_id)).sort((a,b)=>int(b.label_idr)-int(a.label_idr)).filter(x=>{const k=x.label_id+'|'+x.period;const n=perKey.get(k)||0;if(n>=25)return false;perKey.set(k,n+1);return true;}).map(x=>({label:labelId.get(x.label_id),period:x.period,isrc:x.isrc||'',title:title(x.title),artist:title(x.artist),idr:int(x.label_idr),qty:int(x.quantity)}));
const byPlatform=d.royalty_by_platform.filter(x=>labelId.has(x.label_id)).map(x=>({label:labelId.get(x.label_id),period:x.period,platform:title(x.platform||'Lainnya'),idr:int(x.label_idr),qty:int(x.quantity)})).filter(x=>x.idr>0||x.qty>0);

const withdrawals=d.withdraw_requests.filter(w=>labelId.has(w.label_id)).sort((a,b)=>String(a.request_date||a.created_at).localeCompare(String(b.request_date||b.created_at))).map((w,i)=>({id:'WD-P'+String(i+1).padStart(3,'0'),label:labelId.get(w.label_id),amount:int(w.amount_idr),royalty:int(w.royalty_amount_idr??w.amount_idr),adjustment:int(w.adjustment_amount_idr),status:w.status,
  requested:day(w.request_date||w.created_at),approved:day(w.approved_date),paid:day(w.paid_date),periodFrom:w.period_from||null,periodTo:w.period_to||null,lines:int(w.lines_count),
  bank:w.bank_snapshot?{bank:title(w.bank_snapshot.bank_name),number:String(w.bank_snapshot.account_number||''),holder:title(w.bank_snapshot.account_holder_name)}:null,reference:w.payment_reference||null,note:title(w.admin_note||''),proof:!!w.payment_proof_url}));

const commentsOf=new Map();for(const c of d.ticket_comments){if(!commentsOf.has(c.ticket_id))commentsOf.set(c.ticket_id,[]);commentsOf.get(c.ticket_id).push(c);}
const tickets=d.support_tickets.filter(t=>labelId.has(t.label_id)).sort((a,b)=>String(a.created_at).localeCompare(String(b.created_at))).map(t=>({no:t.ticket_no,label:labelId.get(t.label_id),release:releaseId.get(t.release_id)||null,releaseTitle:title(t.release_title||''),category:t.category,categoryLabel:title(t.category_label||t.category),subject:title(t.subject),description:title(t.description||''),reason:title(t.reason||''),status:t.status,
  created:day(t.created_at),resolved:day(t.resolved_at),cancelled:day(t.cancelled_at),believe:day(t.submitted_to_believe_at),takedownDone:day(t.takedown_completed_at),newMetadata:t.new_metadata||null,
  comments:(commentsOf.get(t.id)||[]).sort((a,b)=>String(a.created_at).localeCompare(String(b.created_at))).map(c=>({who:title(c.user_name||'Sistem'),role:c.role||'system',system:!!c.is_system,body:title(c.body||''),at:day(c.created_at)}))}));

const convs=d.chat_conversations.filter(c=>labelId.has(c.label_id)).map(c=>({id:c.id,label:labelId.get(c.label_id),kind:c.kind,status:c.status,created:day(c.created_at),last:day(c.last_message_at),messages:d.chat_messages.filter(m=>m.conversation_id===c.id).sort((a,b)=>String(a.created_at).localeCompare(String(b.created_at))).map(m=>({who:title(m.sender_name||''),role:m.sender_role||'label',body:title(m.body||''),attachment:!!m.attachment,at:day(m.created_at)}))}));

const services=d.service_orders.filter(o=>labelId.has(o.label_id)).map(o=>({label:labelId.get(o.label_id),name:title(o.name),amount:int(o.amount),status:o.status,created:day(o.created_at)}));
const products=d.payment_products.map(p=>({name:title(p.name),amount:int(p.amount),active:!!p.active,description:title(p.description||'')}));

const out={version:1,exportedAt:raw.meta.exportedAt,source:{db:raw.meta.db,population:raw.meta.population,selection:raw.meta.selection.map(s=>({id:labelId.get(s.id),name:s.name,reasons:s.reasons}))},labels,releases,royalty:{imports,summary,byTrack,byPlatform},withdrawals,tickets,chats:convs,services,products};
const js='/* Cuplikan produksi untuk skenario prototype V13.0 — dibangkitkan oleh build-sample.cjs dari sample/production-sample.json ('+raw.meta.exportedAt.slice(0,10)+').\n   Jangan sunting manual; jalankan `npm run build:sample`. Nomor rekening sudah disamarkan di sumber. */\nwindow.SAMPLE131='+JSON.stringify(out)+';\n';
fs.writeFileSync(OUT,js);
console.log('sample131-data.js:',Math.round(js.length/1024)+' KB |',labels.length,'label,',releases.length,'rilisan,',imports.length,'import royalti,',summary.length,'ringkasan,',byTrack.length,'baris lagu,',byPlatform.length,'baris platform,',withdrawals.length,'penarikan,',tickets.length,'tiket,',convs.length,'chat');
