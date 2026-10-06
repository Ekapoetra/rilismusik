const http=require('node:http'),fs=require('node:fs'),path=require('node:path');
const dir=path.join(__dirname,'prototype-v13.0');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.woff2':'font/woff2','.ttf':'font/ttf','.otf':'font/otf'};
/* Jika dependensi terpasang, /api dilayani aplikasi Express (database);
   tanpa dependensi server tetap statis murni seperti semula. */
let apiApp=null;
try{apiApp=require('./api/index.js');}catch{}
const server=(req,res)=>{
 if(apiApp&&req.url.startsWith('/api'))return apiApp(req,res);
 let file;try{const p=new URL(req.url,'http://localhost').pathname;file=path.resolve(dir,'.'+decodeURIComponent(p==='/'?'/index.html':p));}catch{res.writeHead(400);res.end();return;}if(!file.startsWith(dir+path.sep)||!mime[path.extname(file)]||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end('Not found');return;}res.writeHead(200,{'Content-Type':mime[path.extname(file)],'Cache-Control':'no-store'});fs.createReadStream(file).pipe(res);};
http.createServer(server).listen(Number(process.env.PORT||4343),'0.0.0.0',()=>console.log('Rilis Musik V13.0: http://localhost:'+Number(process.env.PORT||4343)+(apiApp?' (+/api)':'')));
