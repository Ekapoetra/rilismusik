/* Gerbang akses preview: satu kata sandi bersama (PROTO_PASSWORD) menghasilkan
   sesi cookie bertanda HMAC. FAIL-CLOSED: tanpa PROTO_PASSWORD semua endpoint
   data menolak (503 not_configured) supaya isi database tidak terekspos.
   Cookie Deployment Protection Vercel TIDAK lagi dianggap bukti akses (bisa
   dipalsukan oleh siapa pun yang menulis header Cookie sendiri). */
const crypto=require('crypto');

const COOKIE='rm_proto_session';
const MAX_AGE=7*24*3600*1000;
const HKDF_SALT='rilismusik-preview-api';
const HKDF_INFO='rm_proto_session/hmac/v1';

const enabled=()=>Boolean(process.env.PROTO_PASSWORD);

/* Kunci HMAC: PROTO_SESSION_SECRET bila ada; jika tidak, diturunkan via HKDF
   dari kata sandi dengan konteks tetap (bukan kata sandi mentah). Mengganti
   kata sandi otomatis membatalkan semua sesi. */
let keyCache={src:null,key:null};
function hmacKey(){
  const src=process.env.PROTO_SESSION_SECRET?'s:'+process.env.PROTO_SESSION_SECRET:'p:'+(process.env.PROTO_PASSWORD||'');
  if(keyCache.src!==src){
    const ikm=process.env.PROTO_SESSION_SECRET||process.env.PROTO_PASSWORD||'';
    keyCache={src,key:Buffer.from(crypto.hkdfSync('sha256',ikm,HKDF_SALT,HKDF_INFO,32))};
  }
  return keyCache.key;
}
const sign=v=>crypto.createHmac('sha256',hmacKey()).update(v).digest('hex');
const eq=(a,b)=>{const x=Buffer.from(String(a)),y=Buffer.from(String(b));return x.length===y.length&&crypto.timingSafeEqual(x,y);};
/* Bandingkan digest (panjang tetap) agar panjang kata sandi tidak bocor lewat waktu. */
const digestEq=(a,b)=>crypto.timingSafeEqual(crypto.createHash('sha256').update(String(a)).digest(),crypto.createHash('sha256').update(String(b)).digest());

const ATTRS=`HttpOnly; Secure; SameSite=Lax; Path=/`;
function issue(res){
  const t=Date.now().toString(36);
  res.setHeader('Set-Cookie',`${COOKIE}=${t}.${sign(t)}; ${ATTRS}; Max-Age=${Math.floor(MAX_AGE/1000)}`);
}
function clear(res){res.setHeader('Set-Cookie',`${COOKIE}=; ${ATTRS}; Max-Age=0`);}

function check(req){
  if(!enabled())return false;
  const m=(req.headers.cookie||'').match(new RegExp(`(?:^|;\\s*)${COOKIE}=([a-z0-9]{1,16})\\.([a-f0-9]{64})(?:;|$)`));
  if(!m)return false;
  const[,t,sig]=m;
  if(!eq(sign(t),sig))return false;
  const age=Date.now()-parseInt(t,36);
  return Number.isFinite(age)&&age>=0&&age<MAX_AGE;
}

const authed=req=>check(req);

/* Middleware: 503 bila preview belum dikonfigurasi (fail-closed), 401 bila
   belum masuk dengan PROTO_PASSWORD. */
function guard(req,res,next){
  if(!enabled())return res.status(503).json({ok:false,error:'not_configured'});
  if(!check(req))return res.status(401).json({ok:false,error:'auth_required'});
  next();
}

function passwordOk(candidate){
  if(!enabled()||typeof candidate!=='string'||!candidate||candidate.length>256)return false;
  return digestEq(candidate,process.env.PROTO_PASSWORD);
}

/* Pembatas percobaan login sederhana di memori (per instance fungsi):
   maks. 10 percobaan gagal per IP per 15 menit. */
const WINDOW_MS=15*60*1000,MAX_FAILS=10;
const fails=new Map();
function clientIp(req){
  const xr=req.headers['x-real-ip'];
  const xf=String(req.headers['x-forwarded-for']||'').split(',')[0].trim();
  return String(xr||xf||req.socket?.remoteAddress||'unknown').slice(0,64);
}
function prune(now){if(fails.size<5000)return;for(const [k,v] of fails)if(now-v.start>WINDOW_MS)fails.delete(k);}
function rateLimited(req){
  const now=Date.now();const e=fails.get(clientIp(req));
  if(!e||now-e.start>WINDOW_MS)return 0;
  return e.n>=MAX_FAILS?Math.ceil((e.start+WINDOW_MS-now)/1000):0;
}
function noteFailure(req){
  const now=Date.now();prune(now);const ip=clientIp(req);const e=fails.get(ip);
  if(!e||now-e.start>WINDOW_MS)fails.set(ip,{start:now,n:1});else e.n++;
}
function noteSuccess(req){fails.delete(clientIp(req));}

module.exports={guard,check,issue,clear,enabled,passwordOk,authed,rateLimited,noteFailure,noteSuccess,_resetRateLimit:()=>fails.clear()};
