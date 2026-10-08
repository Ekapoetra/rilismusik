const fs = require('fs');
let j = fs.readFileSync('prototype-v13.0/v122-packages.js', 'utf8');
const a = "${p.id!=='Basic'&&!q?`<small>${T('Periode ini belum dapat dibeli.','This period cannot be purchased yet.')}</small>`:''}";
if (!j.includes(a)) throw new Error('js not found');
j = j.replace(a, "${p.id!=='Basic'?`<small>${q?'':T('Periode ini belum dapat dibeli.','This period cannot be purchased yet.')}</small>`:''}");
fs.writeFileSync('prototype-v13.0/v122-packages.js', j);

let c = fs.readFileSync('prototype-v13.0/v122.css', 'utf8');
c = c.replace('.package-card122 footer>small{font-size:10px;text-align:center}', '.package-card122 footer>small{display:block;font-size:10px;text-align:center;min-height:14px}');
c = c.replace('.plans122{max-width:1160px!important;margin:0 auto}', '.plans122{max-width:1240px!important;margin:0 auto}');
fs.writeFileSync('prototype-v13.0/v122.css', c);
console.log('ok');
