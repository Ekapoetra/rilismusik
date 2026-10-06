/* Register before legacy click handlers; the implementation is loaded last. */
window.addEventListener('click',event=>{if(typeof interaction130==='function')interaction130(event);},true);
window.addEventListener('keydown',event=>{if(typeof key130==='function')key130(event);},true);
