/* Service API prototype V13.0 — Express.
   Endpoint /api/* untuk preview Vercel; state prototype disimpan pada
   koleksi proto_documents di database salinan (DB_NAME). */
const express=require('express');
const {db,configured}=require('./db');
const auth=require('./auth');
const {buildJourney,buildSharedPatch,domainSummary}=require('./seed');

const app=express();
const DOC_KEY='journey';
const COLLECTION=()=>process.env.PROTO_COLLECTION||'proto_documents';
const MAX_BYTES=5*1024*1024;

app.disable('x-powered-by');
app.use(express.json({limit:'6mb'}));

const dbError=(res,err)=>res.status(err.code==='no_db'?503:500).json({ok:false,error:err.code||'db_error',message:String(err.message||err)});

function okJourney(j){
  return j&&typeof j==='object'&&!Array.isArray(j)
    &&j.schema===1&&['label','admin','super'].includes(j.role)&&typeof j.member==='string'
    &&Array.isArray(j.members)&&j.members.length>0&&Array.isArray(j.releases)
    &&Array.isArray(j.events)&&Array.isArray(j.notifications);
}

app.get('/api/health',(req,res)=>res.json({ok:true,service:'rilismusik-proto-api'}));

app.get('/api/auth/status',(req,res)=>res.json({ok:true,required:!auth.authed(req)&&auth.enabled(),session:auth.authed(req),vercel:auth.viaVercel(req)}));

app.post('/api/auth/login',(req,res)=>{
  if(!auth.enabled())return res.status(503).json({ok:false,error:'preview_not_configured'});
  if(!auth.passwordOk(req.body?.password))return res.status(401).json({ok:false,error:'bad_password'});
  auth.issue(res);res.json({ok:true});
});

app.post('/api/auth/logout',(req,res)=>{auth.clear(res);res.json({ok:true});});

app.get('/api/db-check',auth.guard,async(req,res)=>{
  if(!configured())return res.status(503).json({ok:false,error:'no_db',message:'MONGO_URL belum diatur.'});
  try{
    const d=await db();
    await d.command({ping:1});
    res.json({ok:true,db:d.databaseName,collections:await domainSummary(d)});
  }catch(err){dbError(res,err);}
});

app.get('/api/domain/summary',auth.guard,async(req,res)=>{
  try{res.json({ok:true,collections:await domainSummary(await db())});}
  catch(err){dbError(res,err);}
});

app.get('/api/proto/state',auth.guard,async(req,res)=>{
  try{
    const d=await db();
    const doc=await d.collection(COLLECTION()).findOne({_id:DOC_KEY},{projection:{journey:1,updatedAt:1}});
    res.json({ok:true,journey:doc?.journey||null,updatedAt:doc?.updatedAt||null});
  }catch(err){dbError(res,err);}
});

app.put('/api/proto/state',auth.guard,async(req,res)=>{
  const journey=req.body?.journey;
  if(!okJourney(journey))return res.status(400).json({ok:false,error:'invalid_journey'});
  if(JSON.stringify(journey).length>MAX_BYTES)return res.status(413).json({ok:false,error:'too_large'});
  const rev=Number.isSafeInteger(journey.storageRevision116)?journey.storageRevision116:0;
  const isReal=j=>j&&j.dataSource==='production-copy';
  try{
    const d=await db();
    const col=d.collection(COLLECTION());
    const existing=await col.findOne({_id:DOC_KEY},{projection:{'journey.storageRevision116':1,'journey.dataSource':1}});
    const serverRev=existing?.journey?.storageRevision116;
    /* Dokumen dummy tak boleh menimpa dokumen asli; dokumen asli selalu boleh
       menimpa unggahan simulasi lama. Sisanya ikut aturan revisi biasa. */
    const stale=existing&&(
      (!isReal(journey)&&isReal(existing.journey))
      ||(Number.isSafeInteger(serverRev)&&rev<=serverRev&&!(isReal(journey)&&!isReal(existing.journey))));
    if(stale)
      return res.status(409).json({ok:false,error:'stale_revision',serverRevision:serverRev});
    await col.updateOne({_id:DOC_KEY},{$set:{journey,updatedAt:new Date().toISOString()}},{upsert:true});
    res.json({ok:true,revision:rev});
  }catch(err){dbError(res,err);}
});

app.get('/api/proto/bootstrap',auth.guard,async(req,res)=>{
  try{
    const d=await db();
    const[journey,sharedPatch]=await Promise.all([buildJourney(d),buildSharedPatch(d)]);
    res.json({ok:true,journey,sharedPatch});
  }catch(err){dbError(res,err);}
});

/* Utilitas admin: menyalin koleksi SOURCE_DB_NAME → DB_NAME.
   Dijaga COPY_SECRET (header x-copy-secret); hanya untuk menyiapkan salinan
   database preview, bukan bagian dari aplikasi. */
app.post('/api/admin/copy',auth.guard,async(req,res)=>{
  const secret=process.env.COPY_SECRET;
  if(!secret||req.headers['x-copy-secret']!==secret)return res.status(403).json({ok:false,error:'forbidden'});
  const source=process.env.SOURCE_DB_NAME;
  if(!source)return res.status(400).json({ok:false,error:'no_source',message:'SOURCE_DB_NAME belum diatur.'});
  try{
    const {db:getDb}=require('./db');
    const target=await getDb();
    const src=target.client.db(source);
    const names=(await src.listCollections().toArray()).map(c=>c.name).filter(n=>!n.startsWith('system.')&&!n.startsWith('proto_'));
    const only=Array.isArray(req.body?.collections)?new Set(req.body.collections):null;
    const report={};
    for(const name of names){
      if(only&&!only.has(name))continue;
      const tcol=target.collection(name);
      await tcol.deleteMany({});
      let n=0;
      const cursor=src.collection(name).find({}).batchSize(500);
      let batch=[];
      for await(const doc of cursor){
        batch.push(doc);
        if(batch.length>=500){await tcol.insertMany(batch,{ordered:false});n+=batch.length;batch=[];}
      }
      if(batch.length){await tcol.insertMany(batch,{ordered:false});n+=batch.length;}
      report[name]=n;
    }
    res.json({ok:true,from:source,to:target.databaseName,collections:report});
  }catch(err){dbError(res,err);}
});

app.use((req,res)=>res.status(404).json({ok:false,error:'not_found'}));

module.exports=app;
if(require.main===module){
  const port=Number(process.env.PORT)||4344;
  app.listen(port,()=>console.log(`API prototype di http://localhost:${port}`));
}
