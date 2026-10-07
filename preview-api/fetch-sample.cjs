/* Ambil cuplikan dari preview Vercel (MONGO_URL bersifat Sensitive → tidak
   bisa ditarik ke lokal, jadi ekspor dijalankan di Vercel):
     1. Buat/ambil Protection Bypass for Automation lewat API Vercel (token CLI).
     2. Panggil <deployment>/api/sample-export dengan header bypass; cookie
        _vercel_jwt yang dikembalikan edge dipakai ulang agar lolos guard.
   Tidak ada rahasia yang dicetak ke konsol. */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const args=Object.fromEntries(process.argv.slice(2).map((a,i,arr)=>a.startsWith('--')?[a.slice(2),arr[i+1]]:null).filter(Boolean));
const out=path.resolve(__dirname,args.out||'../prototype-rilis-musik/sample/production-sample.json');
const authFile=path.join(process.env.APPDATA||path.join(os.homedir(),'.config'),'com.vercel.cli','Data','auth.json');
const token=process.env.VERCEL_TOKEN||JSON.parse(fs.readFileSync(authFile,'utf8')).token;
const link=JSON.parse(fs.readFileSync(path.resolve(__dirname,'..','.vercel','project.json'),'utf8'));
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

  const url=`https://${dep.url}/api/sample-export?labels=${args.labels||15}&releases=${args.releases||6}&imports=${args.imports||4}`;
  const bypass={'x-vercel-protection-bypass':secret,'x-vercel-set-bypass-cookie':'true'};
  let r=await fetch(url,{headers:bypass,redirect:'manual'});
  const setCookie=r.headers.getSetCookie?r.headers.getSetCookie():[r.headers.get('set-cookie')].filter(Boolean);
  const jwt=setCookie.map(c=>c.split(';')[0]).find(c=>c.startsWith('_vercel_jwt='));
  if(r.status!==200){
    if(!jwt)throw Error('HTTP '+r.status+' tanpa cookie bypass: '+(await r.text()).slice(0,200));
    r=await fetch(url,{headers:{...bypass,cookie:jwt}});
  }
  if(r.status!==200)throw Error('HTTP '+r.status+': '+(await r.text()).slice(0,300));
  const sample=await r.json();
  fs.mkdirSync(path.dirname(out),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(sample,null,1));
  console.log('tersimpan:',out,Math.round(fs.statSync(out).size/1024)+' KB');
  console.log('db:',sample.meta.db,'| label terpilih:',sample.meta.selection.map(s=>`${s.name}${s.verified?'':' (belum KYC)'}`).join(' | '));
  console.log('jumlah per koleksi:',JSON.stringify(sample.meta.counts));
})().catch(e=>{console.error('GAGAL:',e.message);process.exit(1)});
