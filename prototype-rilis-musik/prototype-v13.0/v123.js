/* V12.3: shared visual header, independent sticky navigation and flowing sidebar. */
(function(){
 let frame=0;
 const observer=typeof ResizeObserver==='function'?new ResizeObserver(schedule):null;
 function sync(){
  frame=0;
  const header=document.querySelector('.header.header123'),hero=document.querySelector('.dashboard-hero122'),app=document.querySelector('#app');
  if(!header||!app)return;
  const expanded=!!hero&&document.body.classList.contains('dashboard123');
  header.classList.toggle('is-scrolled123',expanded&&window.scrollY>12);
  header.classList.toggle('is-compact123',!expanded);
  const height=header.getBoundingClientRect().height;
  document.documentElement.style.setProperty('--header-height123',height+'px');
  if(expanded){
   app.style.setProperty('--masthead-height123',(hero.offsetTop+hero.offsetHeight)+'px');
   const side=document.querySelector('.side5'),top=side?.getBoundingClientRect().top;
   app.dataset.scroll123=window.scrollY<1?'expanded':top!==undefined&&Math.abs(top-height-14)<2?'pinned':'moving';
  }else{app.style.removeProperty('--masthead-height123');delete app.dataset.scroll123}
 }
 function schedule(){if(!frame)frame=requestAnimationFrame(sync)}
 function stamp(){
  document.title='Rilis Musik · V12.3';document.documentElement.dataset.release='12.3';
  document.querySelectorAll('.version-pill,.floating107>strong').forEach(e=>e.textContent='V12.3');
  const footer=document.querySelector('.footer span');if(footer)footer.textContent='RILIS MUSIK · V12.3';
 }
 const priorStamp=stamp122;stamp122=function(){priorStamp();stamp()};
 const priorRender=render;render=function(){
  priorRender();
  const app=document.querySelector('#app'),header=document.querySelector('.header'),hero=document.querySelector('.dashboard-hero122');
  if(!app||!header)return;
  header.classList.add('header123');document.body.classList.toggle('dashboard123',!!hero);
  app.querySelector('.masthead-paint123')?.remove();
  if(hero){const paint=document.createElement('div');paint.className='masthead-paint123';paint.setAttribute('aria-hidden','true');app.prepend(paint)}
  observer?.disconnect();observer?.observe(header);if(hero)observer?.observe(hero);
  stamp();sync();schedule();
 };
 window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule,{passive:true});
 const scenes=[
  ['v123-super-header','v122-super','super','light',false,'Header menyatu · Super Admin','Unified header · Super Admin'],
  ['v123-super-scroll','v122-super','super','dark',true,'Scroll · bar menu tetap, sidebar mengikuti','Scroll · fixed navigation, flowing sidebar'],
  ['v123-admin-header','v122-admin','admin','light',false,'Header menyatu · Admin','Unified header · Admin'],
  ['v123-label-header','v122-label','label','dark',false,'Header menyatu · Label','Unified header · Label'],
  ['v123-staff-header','v122-staff','super','dark',false,'Header menyatu · ruang Staff','Unified header · Staff workspace']
 ];
 studioCatalog.unshift(...scenes.map(([id,,role,,,idTitle,enTitle])=>({id,role,version:'12.3',title:[idTitle,enTitle],description:['Sapaan dan Wawasan menyatu dalam header. Bar menu tetap terlihat ketika halaman digulir.','Greeting and Insights share the header. Navigation stays visible while scrolling.']})));
 const priorStudio=studioStart;studioStart=async function(id){
  const scene=scenes.find(s=>s[0]===id);if(!scene)return priorStudio(id);
  await priorStudio(scene[1]);closeModal();themeMode105(scene[3]);v5.collapsed=innerWidth<600;document.documentElement.classList.toggle('sidebar-small',v5.collapsed);studioSelected=id;
  // Visual scenes suppress unrelated sample reward prompts without marking an
  // award seen, granting credits, or changing the user's saved checkpoint.
  if(isLabel10()){const ids=(ten.bonuses||[]).filter(n=>n.member===ten.member).map(n=>n.id);ten.rewardPromptsShown=[...new Set([...(ten.rewardPromptsShown||[]),...ids])]}
  save10();render();
  await new Promise(resolve=>requestAnimationFrame(resolve));
  const hero=document.querySelector('.dashboard-hero122');window.scrollTo({top:scene[4]&&hero?hero.offsetTop+hero.offsetHeight+40:0,behavior:'instant'});sync();stamp();
 };
 render();
})();
