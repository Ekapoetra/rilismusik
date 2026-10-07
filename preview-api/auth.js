/* Gerbang akses preview: satu kata sandi bersama (PROTO_PASSWORD) menghasilkan
   sesi cookie bertanda HMAC. Tanpa PROTO_PASSWORD endpoint data menolak (503)
   supaya isi database tidak terekspos pada URL preview. */
const crypto=require('crypto');

const COOKIE='rm_proto_session';
const MAX_AGE=7*24*3600*1000;

const enabled=()=>Boolean(process.env.PROTO_PASSWORD);
const secret=()=>process.env.PROTO_SESSION_SECRET||process.env.PROTO_PASSWORD;
const sign=v=>crypto.createHmac('sha256',secret()).update(v).digest('hex');
const eq=(a,b)=>{const x=Buffer.from(String(a)),y=Buffer.from(String(b));return x.length===y.length&&crypto.timingSafeEqual(x,y);};

function issue(res){
  const t=Date.now().toString(36);
  res.setHeader('Set-Cookie',`${COOKIE}=${t}.${sign(t)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${Math.floor(MAX_AGE/1000)}`);
}

function clear(res){res.setHeader('Set-Cookie',`${COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0`);}

function check(req){
  const m=(req.headers.cookie||'').match(new RegExp(`${COOKIE}=([a-z0-9]+)\\.([a-f0-9]{64})`));
  if(!m)return false;
  const[,t,sig]=m;
  if(!eq(sign(t),sig))return false;
  const age=Date.now()-parseInt(t,36);
  return Number.isFinite(age)&&age>=0&&age<MAX_AGE;
}

/* Siapa pun yang sudah melewati Deployment Protection Vercel membawa cookie
   sesi Vercel; itu dianggap akses yang sah — PROTO_PASSWORD jadi opsional. */
const VERCEL_COOKIE=/_vercel_(jwt|share|password)=/;
const viaVercel=req=>VERCEL_COOKIE.test(req.headers.cookie||'');

function authed(req){return viaVercel(req)||(enabled()&&check(req));}

/* Middleware: menolak dengan 401 bila belum lolos proteksi Vercel maupun
   sesi PROTO_PASSWORD — klien menampilkan layar masuk / petunjuk. */
function guard(req,res,next){
  if(!authed(req))return res.status(401).json({ok:false,error:'auth_required'});
  next();
}

function passwordOk(candidate){return enabled()&&eq(String(candidate),process.env.PROTO_PASSWORD);}

module.exports={guard,check,issue,clear,enabled,passwordOk,viaVercel,authed};
