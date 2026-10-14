/* Uji offline gerbang akses preview-api (tanpa database):
   fail-closed, cookie Vercel palsu ditolak, rate limit login, atribut cookie,
   Cache-Control no-store, error generik. */
const crypto=require('node:crypto');
delete process.env.PROTO_PASSWORD;delete process.env.PROTO_SESSION_SECRET;delete process.env.MONGO_URL;
const app=require('./index');
const auth=require('./auth');

let fails=0;const check=(name,ok,extra='')=>{console.log((ok?'PASS':'FAIL')+' '+name+(extra?' — '+extra:''));if(!ok)fails++;};
(async()=>{
  const srv=app.listen(0,'127.0.0.1');await new Promise(r=>srv.once('listening',r));
  const base='http://127.0.0.1:'+srv.address().port;
  const req=(p,opt={})=>fetch(base+p,{redirect:'manual',...opt});
  const forged={cookie:'_vercel_jwt=palsu; _vercel_share=x'};

  let r=await req('/api/db-check',{headers:forged});
  check('tanpa PROTO_PASSWORD → 503 not_configured (fail-closed)',r.status===503&&(await r.json()).error==='not_configured');
  check('Cache-Control: no-store',r.headers.get('cache-control')==='no-store');
  r=await req('/api/sample-export',{headers:forged});
  check('sample-export juga 503 tanpa konfigurasi',r.status===503);
  r=await req('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"password":"x"}'});
  check('login 503 tanpa konfigurasi',r.status===503);

  process.env.PROTO_PASSWORD='kata-sandi-uji';
  r=await req('/api/db-check',{headers:forged});
  check('cookie _vercel_* palsu ditolak (401)',r.status===401);
  r=await req('/api/auth/status',{headers:forged});
  const st=await r.json();
  check('status: belum ada sesi',st.session===false&&st.required===true&&!('vercel'in st));

  const login=(pw,ip='10.0.0.1')=>req('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json','x-real-ip':ip},body:JSON.stringify({password:pw})});
  r=await login('salah');
  check('kata sandi salah → 401',r.status===401);
  for(let i=0;i<9;i++)await login('salah');
  r=await login('kata-sandi-uji');
  check('rate limit: percobaan ke-11 dari IP sama → 429 (meski benar)',r.status===429&&Number(r.headers.get('retry-after'))>0);
  r=await login('kata-sandi-uji','10.0.0.2');
  check('IP lain tetap bisa masuk',r.status===200);
  const sc=r.headers.get('set-cookie')||'';
  check('cookie HttpOnly; Secure; SameSite=Lax',/HttpOnly/.test(sc)&&/Secure/.test(sc)&&/SameSite=Lax/.test(sc));
  const cookie=sc.split(';')[0];
  const [t,sig]=cookie.split('=')[1].split('.');
  check('kunci HMAC bukan kata sandi mentah',sig!==crypto.createHmac('sha256','kata-sandi-uji').update(t).digest('hex'));
  r=await req('/api/db-check',{headers:{cookie}});
  const body=await r.json();
  check('sesi sah lolos guard; tanpa MONGO_URL → 503 generik',r.status===503&&body.error==='not_configured'&&!('message'in body)&&!('collections'in body));
  r=await req('/api/auth/status',{headers:{cookie}});
  check('status: sesi aktif',(await r.json()).session===true);
  process.env.PROTO_PASSWORD='kata-sandi-baru';
  r=await req('/api/db-check',{headers:{cookie}});
  check('ganti kata sandi membatalkan sesi lama',r.status===401);
  process.env.PROTO_PASSWORD='kata-sandi-uji';
  r=await req('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json','x-real-ip':'10.0.0.3'},body:'{rusak'});
  const bad=await r.json();
  check('JSON rusak → 400 generik tanpa detail',r.status===400&&bad.error==='bad_request'&&Object.keys(bad).length===2);
  r=await req('/api/tidak-ada');
  check('404 + no-store',r.status===404&&r.headers.get('cache-control')==='no-store');
  auth._resetRateLimit();
  srv.close();
  process.exit(fails?1:0);
})().catch(e=>{console.error(e);process.exit(1)});
