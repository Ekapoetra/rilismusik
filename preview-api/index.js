/* preview-api — service kecil di preview Vercel, TERPISAH dari prototype.
   Tugasnya hanya: cek koneksi database dan mengekspor cuplikan data produksi
   menjadi JSON statis (bahan dummy tambahan prototype V13.0).
   Tidak menyentuh prototype saat runtime; tidak menulis ke database. */
const express=require('express');
const {db,configured}=require('./db');
const auth=require('./auth');
const {exportSample}=require('./sample');

const app=express();
app.disable('x-powered-by');
app.use(express.json({limit:'1mb'}));

const dbError=(res,err)=>res.status(err.code==='no_db'?503:500).json({ok:false,error:err.code||'db_error',message:String(err.message||err)});

app.get('/api/health',(req,res)=>res.json({ok:true,service:'rilismusik-preview-api'}));

app.get('/api/auth/status',(req,res)=>res.json({ok:true,required:!auth.authed(req)&&auth.enabled(),session:auth.authed(req),vercel:auth.viaVercel(req)}));
app.post('/api/auth/login',(req,res)=>{
  if(!auth.enabled())return res.status(503).json({ok:false,error:'preview_not_configured'});
  if(!auth.passwordOk(req.body?.password))return res.status(401).json({ok:false,error:'bad_password'});
  auth.issue(res);res.json({ok:true});
});

app.get('/api/db-check',auth.guard,async(req,res)=>{
  if(!configured())return res.status(503).json({ok:false,error:'no_db',message:'MONGO_URL belum diatur.'});
  try{
    const d=await db();
    await d.command({ping:1});
    const names=(await d.listCollections().toArray()).map(c=>c.name).sort();
    const counts={};
    for(const n of names)try{counts[n]=await d.collection(n).estimatedDocumentCount()}catch{}
    res.json({ok:true,db:d.databaseName,collections:counts});
  }catch(err){dbError(res,err);}
});

/* GET /api/sample-export?labels=15&releases=6&imports=4
   Mengunduh berkas production-sample.json. */
app.get('/api/sample-export',auth.guard,async(req,res)=>{
  const n=(k,d,max)=>Math.min(max,Math.max(1,parseInt(req.query[k],10)||d));
  try{
    const sample=await exportSample(await db(),{labels:n('labels',15,40),releasesPerLabel:n('releases',6,30),imports:n('imports',4,12)});
    res.setHeader('Content-Disposition','attachment; filename="production-sample.json"');
    res.type('application/json').send(JSON.stringify(sample,null,1));
  }catch(err){dbError(res,err);}
});

app.use((req,res)=>res.status(404).json({ok:false,error:'not_found'}));

module.exports=app;
if(require.main===module){
  const port=Number(process.env.PORT)||4344;
  app.listen(port,()=>console.log(`preview-api di http://localhost:${port}`));
}
