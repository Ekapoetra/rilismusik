/* preview-api — service kecil di preview Vercel, TERPISAH dari prototype.
   Tugasnya hanya: cek koneksi database dan mengekspor cuplikan data produksi
   (dipseudonimkan, lihat pseudonym.js) menjadi JSON statis (bahan dummy
   tambahan prototype V13.0).
   Tidak menyentuh prototype saat runtime; tidak menulis ke database. */
const express=require('express');
const {db,configured}=require('./db');
const auth=require('./auth');
const {exportSample}=require('./sample');

const app=express();
app.disable('x-powered-by');
app.use((req,res,next)=>{
  res.setHeader('Cache-Control','no-store');
  res.setHeader('X-Content-Type-Options','nosniff');
  next();
});
app.use(express.json({limit:'10kb'}));

/* Detail error hanya ke log server; klien menerima kode generik. */
const fail=(res,err,where)=>{
  console.error(`[preview-api] ${where}:`,err?.code||'',err?.message||err);
  if(err?.code==='no_db')return res.status(503).json({ok:false,error:'not_configured'});
  res.status(500).json({ok:false,error:'internal_error'});
};

app.get('/api/health',(req,res)=>res.json({ok:true,service:'rilismusik-preview-api'}));

app.get('/api/auth/status',(req,res)=>res.json({ok:true,configured:auth.enabled(),required:auth.enabled()&&!auth.authed(req),session:auth.authed(req)}));
app.post('/api/auth/login',(req,res)=>{
  if(!auth.enabled())return res.status(503).json({ok:false,error:'not_configured'});
  const wait=auth.rateLimited(req);
  if(wait){res.setHeader('Retry-After',String(wait));return res.status(429).json({ok:false,error:'too_many_attempts'});}
  if(!auth.passwordOk(req.body?.password)){auth.noteFailure(req);return res.status(401).json({ok:false,error:'bad_password'});}
  auth.noteSuccess(req);auth.issue(res);res.json({ok:true});
});
app.post('/api/auth/logout',(req,res)=>{auth.clear(res);res.json({ok:true});});

app.get('/api/db-check',auth.guard,async(req,res)=>{
  if(!configured())return res.status(503).json({ok:false,error:'not_configured'});
  try{
    const d=await db();
    await d.command({ping:1,maxTimeMS:5000});
    res.json({ok:true,ping:true});
  }catch(err){fail(res,err,'db-check');}
});

/* GET /api/sample-export?labels=15&releases=6&imports=4&lines=400&light=1
   Mengunduh berkas production-sample.json (sudah dipseudonimkan). */
const intParam=(req,k,d,max)=>{const raw=req.query[k];const v=typeof raw==='string'&&/^\d{1,5}$/.test(raw)?parseInt(raw,10):d;return Math.min(max,Math.max(1,v));};
app.get('/api/sample-export',auth.guard,async(req,res)=>{
  try{
    const sample=await exportSample(await db(),{labels:intParam(req,'labels',15,40),releasesPerLabel:intParam(req,'releases',6,30),imports:intParam(req,'imports',4,12),linesPerImport:intParam(req,'lines',400,2000),light:req.query.light==='1'});
    res.setHeader('Content-Disposition','attachment; filename="production-sample.json"');
    res.type('application/json').send(JSON.stringify(sample,null,1));
  }catch(err){fail(res,err,'sample-export');}
});

app.use((req,res)=>res.status(404).json({ok:false,error:'not_found'}));
/* Error dari middleware (mis. JSON rusak / body terlalu besar) → generik. */
app.use((err,req,res,next)=>{
  if(res.headersSent)return next(err);
  const status=Number(err?.status||err?.statusCode);
  if(status>=400&&status<500)return res.status(status).json({ok:false,error:'bad_request'});
  fail(res,err,'unhandled');
});

module.exports=app;
if(require.main===module){
  const port=Number(process.env.PORT)||4344;
  app.listen(port,()=>console.log(`preview-api di http://localhost:${port}`));
}
