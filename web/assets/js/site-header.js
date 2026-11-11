/* Shared header: title, page links and a one-line description of the current page. */
(function(){
"use strict";
const PAGES=[
  {id:'explorer',href:'index.html',label:'Scenario Explorer',blurb:'Explore published postflight muscle results by outcome, region, regimen, crew subgroup, recovery day and mission duration.'},
  {id:'library',href:'library.html',label:'Study Library',blurb:'The eight library studies, and separately the external supporting evidence.'},
  {id:'measurements',href:'measurements.html',label:'Measurements',blurb:'Every study through the same seven measurement categories, each value traced to its source.'}
];
const current=document.body.dataset.page;
const page=PAGES.find(p=>p.id===current);
const wrap=document.createElement('div'); wrap.className='wrap';
const title=document.createElement('h1'); title.textContent='Atrophy Armour';
const nav=document.createElement('nav'); nav.setAttribute('aria-label','Pages');
const list=document.createElement('ul');
PAGES.forEach(p=>{
  const item=document.createElement('li'), link=document.createElement('a');
  link.href=p.href; link.textContent=p.label;
  if(p.id===current) link.setAttribute('aria-current','page');
  item.append(link); list.append(item);
});
nav.append(list);
const blurb=document.createElement('p'); blurb.textContent=page.blurb;
const note=document.createElement('p');
note.textContent='Educational tool. It organizes published group results; it is not a clinical, operational or mission-planning predictor.';
wrap.append(title,nav,blurb,note);
document.getElementById('site-header').append(wrap);
})();
