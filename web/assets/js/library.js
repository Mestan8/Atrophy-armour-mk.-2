/* Study Library: one summary per library study, then the separate external-evidence register. */
(function(){
"use strict";
const {get,el,callout,rows,fillSelect,store}=window.AA;
const STORE_KEY='atrophy.library';

const select=document.getElementById('study-select');
const box=document.getElementById('study');
let latestRequest=0;

async function load(studyId){
  const requestId=++latestRequest;
  let view;
  try{ view=await get('/api/library',{study:studyId}); }
  catch(error){ if(requestId===latestRequest) box.replaceChildren(callout('error',error.message)); return; }
  if(requestId!==latestRequest) return;
  document.getElementById('study-label').textContent=view.label;
  document.getElementById('library-note').textContent=view.library_note;
  fillSelect(select,view.options,view.value);
  store.set(STORE_KEY,view.value);
  document.getElementById('external').replaceChildren(...view.external.map(source=>
    el('details',{class:'panel'},el('summary',{text:source.title}),rows(source.rows))));
  if(view.error){ box.replaceChildren(callout('error',view.error)); return; }
  const study=view.study;
  box.replaceChildren(el('div',{class:'panel'},
    el('h3',{text:study.title}),...study.captions.map(text=>el('p',{class:'caption',text})),
    ...study.sections.flatMap(section=>[el('h4',{text:section.heading}),el('p',{text:section.text})])));
}

select.addEventListener('change',()=>load(select.value));
load(store.get(STORE_KEY));
})();
