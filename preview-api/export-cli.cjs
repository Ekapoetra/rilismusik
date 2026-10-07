/* Ekspor cuplikan dari terminal:
     node export-cli.cjs [--env .env.preview] [--out ../prototype-rilis-musik/sample/production-sample.json] [--labels 15] [--releases 6] [--imports 4]
   Hanya MONGO_URL dan DB_NAME yang dibaca dari berkas env; nilai tidak pernah dicetak. */
const fs=require('node:fs'),path=require('node:path');
const args=Object.fromEntries(process.argv.slice(2).map((a,i,arr)=>a.startsWith('--')?[a.slice(2),arr[i+1]]:null).filter(Boolean));
const envFile=path.resolve(__dirname,args.env||'.env.preview');
if(fs.existsSync(envFile)){
  for(const line of fs.readFileSync(envFile,'utf8').split(/\r?\n/)){
    const m=line.match(/^\s*(MONGO_URL|DB_NAME)\s*=\s*(.*)\s*$/);
    if(m&&!process.env[m[1]])process.env[m[1]]=m[2].replace(/^"(.*)"$/,'$1');
  }
}
const out=path.resolve(__dirname,args.out||'../prototype-rilis-musik/sample/production-sample.json');
(async()=>{
  const {db}=require('./db');
  const {exportSample}=require('./sample');
  const d=await db();
  console.log('db:',d.databaseName);
  const sample=await exportSample(d,{labels:Number(args.labels)||15,releasesPerLabel:Number(args.releases)||6,imports:Number(args.imports)||4});
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(sample,null,1));
  console.log('tersimpan:',out,Math.round(fs.statSync(out).size/1024)+' KB');
  console.log('label terpilih:',sample.meta.selection.map(s=>`${s.name}${s.verified?'':' (belum KYC)'}`).join(' | '));
  console.log('jumlah per koleksi:',JSON.stringify(sample.meta.counts));
  process.exit(0);
})().catch(e=>{console.error('GAGAL:',e.code||'',e.message);process.exit(1)});
