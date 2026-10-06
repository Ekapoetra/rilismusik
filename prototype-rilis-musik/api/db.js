/* Koneksi MongoDB bersama untuk service API prototype.
   Memakai MONGO_URL + DB_NAME yang sama dengan aplikasi produksi;
   pada preview, DB_NAME menunjuk ke salinan database, bukan produksi. */
const {MongoClient}=require('mongodb');

let client=null,connecting=null;

function configured(){return Boolean(process.env.MONGO_URL);}

async function db(){
  if(!configured())throw Object.assign(Error('MONGO_URL belum diatur pada environment ini.'),{code:'no_db'});
  if(!connecting){
    client=new MongoClient(process.env.MONGO_URL,{maxPoolSize:3,serverSelectionTimeoutMS:8000});
    connecting=client.connect().catch(err=>{connecting=null;client=null;throw err});
  }
  await connecting;
  return client.db(process.env.DB_NAME||'rilismusik');
}

module.exports={db,configured};
