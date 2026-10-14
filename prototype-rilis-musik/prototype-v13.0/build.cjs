const fs=require('node:fs'),path=require('node:path');
let html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
html=html.replace(/<link rel="stylesheet" href="([^"]+)">/g,(_,file)=>{let css=fs.readFileSync(path.join(__dirname,file),'utf8');css=css.replace(/url\(['"]?([^)'"\s]+)['"]?\)/g,(match,url)=>{const p=path.join(__dirname,url);if(!url.startsWith('data:')&&fs.existsSync(p)){const mime=url.endsWith('woff2')?'font/woff2':url.endsWith('woff')?'font/woff':'application/octet-stream';return 'url(data:'+mime+';base64,'+fs.readFileSync(p).toString('base64')+')'}return match});return '<style>'+css+'</style>'});
const lazy131=JSON.parse(fs.readFileSync(path.join(__dirname,'lazy131.js'),'utf8').match(/lazyFiles131=(\{[^}]*\})/)[1]);
html=html.replace('<script src="lazy131.js"></script>',()=>'<script src="lazy131.js"></script>'+Object.values(lazy131).map(f=>'<script src="'+f+'"></script>').join(''));
html=html.replace(/<script src="([^"]+)"><\/script>/g,(_,file)=>'<script>'+fs.readFileSync(path.join(__dirname,file),'utf8').replace(/<\/script/gi,'<\\/script')+'</script>');
fs.writeFileSync(path.join(__dirname,'Rilis-Musik-V13.0.html'),html);
console.log('V13.0 standalone built, '+html.length+' characters');

