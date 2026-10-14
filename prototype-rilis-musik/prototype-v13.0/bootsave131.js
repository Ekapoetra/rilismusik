/* v117 melepas rem simpan (booting116=false) di tengah boot, sehingga setiap
   render lapisan berikutnya ikut menyimpan seluruh data (±50% waktu render).
   Rem dipasang lagi di sini; skrip penutup index.html melepasnya dan
   menyimpan SEKALI setelah aplikasi tampil. */
booting116=true;
