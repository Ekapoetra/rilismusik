/* Ambil cuplikan dari preview Vercel (MONGO_URL bersifat Sensitive → tidak
   bisa ditarik ke lokal, jadi ekspor dijalankan di Vercel):
     1. Buat/ambil Protection Bypass for Automation lewat API Vercel (token CLI).
     2. Masuk ke preview-api dengan PROTO_PASSWORD (env lokal, wajib) lewat
        POST /api/auth/login (header bypass Vercel ikut dikirim), lalu panggil
        <deployment>/api/sample-export dengan cookie sesi rm_proto_session.
        Cookie Vercel saja TIDAK lagi cukup untuk lolos guard.
   Hasil ekspor sudah dipseudonimkan di server. Tidak ada rahasia yang dicetak. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const args=Object.fromEntries(process.argv.slice(2).map((a,i,arr)=>a.startsWith('--')?[a.slice(2),arr[i+1]]:null).filter(Boolean));
const out=path.resolve(__dirname,args.out||'../prototype-rilis-musik/sample/production-sample.json');
const authFile=path.join(process.env.APPDATA||path.join(os.homedir(),'.config'),'com.vercel.cli','Data','auth.json');
const token=process.env.VERCEL_TOKEN||JSON.parse(fs.readFileSync(authFile,'utf8')).token;
const link=JSON.parse(fs.readFileSync(path.resolve(__dirname,'..','.vercel','project.json'),'utf8'));
if(!process.env.PROTO_PASSWORD){console.error('GAGAL: set PROTO_PASSWORD di environment (kata sandi preview) sebelum menjalankan skrip ini.');process.exit(1);}
const H={Authorization:'Bearer '+token,'Content-Type':'application/json'};
const api=async(p,opt={})=>{const r=await fetch('https://api.vercel.com'+p+(p.includes('?')?'&':'?')+'teamId='+link.orgId,{...opt,headers:{...H,...(opt.headers||{})}});const j=await r.json().catch(()=>({}));if(!r.ok)throw Error(p+' → '+r.status+' '+JSON.stringify(j).slice(0,200));return j;};

(async()=>{
  const project=await api('/v9/projects/'+link.projectId);
  let secret=Object.keys(project.protectionBypass||{})[0];
  if(!secret){const r=await api('/v1/projects/'+link.projectId+'/protection-bypass',{method:'PATCH',body:JSON.stringify({generate:{}})});secret=Object.keys(r.protectionBypass||{})[0];}
  if(!secret)throw Error('Tidak bisa membuat protection bypass');
  console.log('bypass: siap');

  const deps=await api('/v6/deployments?projectId='+link.projectId+'&target=preview&state=READY&limit=10');
  const dep=(deps.deployments||[]).find(d=>d.meta?.githubCommitRef==='prototype-node-api')||deps.deployments?.[0];
  if(!dep)throw Error('Deployment preview READY tidak ditemukan');
  console.log('deployment:',dep.url,'('+(dep.meta?.githubCommitSha||'').slice(0,7)+')');

  const base=`https://${dep.url}`;
  const url=`${base}/api/sample-export?labels=${args.labels||15}&releases=${args.releases||6}&imports=${args.imports||4}${args.light?'&light=1':''}`;
  const bypass={'x-vercel-protection-bypass':secret};
  const cookiesOf=r=>(r.headers.getSetCookie?r.headers.getSetCookie():[r.headers.get('set-cookie')].filter(Boolean)).map(c=>c.split(';')[0]);
  const login=await fetch(base+'/api/auth/login',{method:'POST',headers:{...bypass,'Content-Type':'application/json'},body:JSON.stringify({password:process.env.PROTO_PASSWORD}),redirect:'manual'});
  if(login.status!==200)throw Error('Login preview-api gagal: HTTP '+login.status);
  const session=cookiesOf(login).find(c=>c.startsWith('rm_proto_session='));
  if(!session)throw Error('Login preview-api tidak mengembalikan cookie sesi');
  console.log('sesi preview-api: siap');
  const r=await fetch(url,{headers:{...bypass,cookie:session}});
  if(r.status!==200)throw Error('HTTP '+r.status+': '+(await r.text()).slice(0,300));
  const sample=await r.json();
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(sample,null,1));
  console.log('tersimpan:',out,Math.round(fs.statSync(out).size/1024)+' KB');
  console.log('db:',sample.meta.db,'| label terpilih:',sample.meta.selection.map(s=>`${s.name}${s.verified?'':' (belum KYC)'}`).join(' | '));
  console.log('jumlah per koleksi:',JSON.stringify(sample.meta.counts));
})().catch(e=>{console.error('GAGAL:',e.message);process.exit(1)});
