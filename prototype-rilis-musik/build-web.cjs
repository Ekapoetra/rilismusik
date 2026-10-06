/* Menyalin berkas runtime V13.0 ke web-dist/ untuk service statis Vercel.
   Artefak pengembangan (qa, build, standalone 6 MB) tidak ikut. */
const fs=require('node:fs'),path=require('node:path');
const SRC=path.join(__dirname,'prototype-v13.0'),OUT=path.join(__dirname,'web-dist');
const SKIP=new Set(['build.cjs','Rilis-Musik-V13.0.html']);
const SKIP_DIR=new Set(['qa','__tests__','node_modules']);

fs.rmSync(OUT,{recursive:true,force:true});
fs.mkdirSync(OUT,{recursive:true});
let copied=0,skipped=0;
for(const entry of fs.readdirSync(SRC,{withFileTypes:true})){
  if(entry.isDirectory()){skipped+=SKIP_DIR.has(entry.name)?1:0;continue;}
  if(SKIP.has(entry.name)||entry.name.endsWith('.md')){skipped++;continue;}
  fs.copyFileSync(path.join(SRC,entry.name),path.join(OUT,entry.name));
  copied++;
}
console.log(`web-dist: ${copied} berkas disalin, ${skipped} dilewati`);
