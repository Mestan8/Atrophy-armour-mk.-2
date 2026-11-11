/* Helpers shared by the pages: server requests, safe element building, charts and remembered selections.
   Text from the server only ever reaches the page through textContent, so stored records cannot inject markup. */
(function(){
"use strict";

async function request(url,options){
  let response;
  try{ response=await fetch(url,options); }
  catch(_){ throw new Error('The Atrophy Armour server is not responding. Check that it is still running.'); }
  let body=null;
  try{ body=await response.json(); }catch(_){ /* handled below */ }
  if(!response.ok || body===null){
    const error=new Error((body && body.error) || 'The server could not complete this request.');
    error.status=response.status;   /* lets a page explain, for example, a 404 from an outdated server */
    throw error;
  }
  return body;
}
function get(path,params){
  const query=new URLSearchParams();
  Object.entries(params||{}).forEach(([key,value])=>{ if(value!==null && value!==undefined) query.set(key,value); });
  const text=query.toString();
  return request(path+(text?'?'+text:''));
}

function el(tag,props,...children){
  const node=document.createElement(tag);
  Object.entries(props||{}).forEach(([key,value])=>{
    if(value===null || value===undefined || value===false) return;
    if(key==='class') node.className=value; else if(key==='text') node.textContent=value; else node.setAttribute(key,value);
  });
  node.append(...children.filter(child=>child!==null && child!==undefined));
  return node;
}
function callout(kind,text){ return el('p',{class:'callout '+kind,text}); }
function tag(kind){ return kind ? el('span',{class:'tag '+kind,text:kind}) : null; }
/* Label-and-value rows. A row without a label is a plain sentence. */
function rows(items){
  return el('dl',{class:'rows'},...items.map(row=>row.label===null
    ? el('div',{class:'plain'},el('dd',{text:row.text}))
    : el('div',{},el('dt',{text:row.label}),el('dd',{text:row.text}))));
}
/* Options may be disabled; their label then already carries the reason. */
function fillSelect(select,options,value){
  select.replaceChildren(...options.map(option=>{
    const node=el('option',{value:String(option.value),text:option.label});
    if(option.disabled){ node.disabled=true; if(option.reason) node.title=option.reason; }
    return node;
  }));
  select.value=String(value);
}

/* Provenance dialog, opened from a chart point or a "Source" button. */
function openDetails(details){
  const dialog=document.getElementById('observation');
  if(!dialog || !details) return;
  document.getElementById('observation-title').textContent=details.heading;
  document.getElementById('observation-body').replaceChildren(...details.sections.flatMap(section=>[
    el('h4',{text:section.title}),rows(section.rows)
  ]));
  dialog.showModal();
  dialog.scrollTop=0;
}
(function wireDialog(){
  const close=document.getElementById('observation-close');
  if(close) close.addEventListener('click',()=>document.getElementById('observation').close());
})();

/* Draws a Plotly figure built by the server. Only fonts and backgrounds are adjusted here, never data. */
function drawChart(node,figure,details){
  Plotly.purge(node);
  if(!figure){ node.hidden=true; return; }
  node.hidden=false;
  const layout=Object.assign({},figure.layout,{
    title:undefined,
    paper_bgcolor:'#ffffff',plot_bgcolor:'#ffffff',
    font:{family:getComputedStyle(document.body).fontFamily,size:13,color:'#1c1c1c'},
    margin:{t:16,r:16,b:16,l:16},
    hoverlabel:{bgcolor:'#ffffff',bordercolor:'#8a8a8a',font:{color:'#1c1c1c',size:12},align:'left'},
    xaxis:Object.assign({},figure.layout.xaxis,{automargin:true,gridcolor:'#e6e6e6'}),
    yaxis:Object.assign({},figure.layout.yaxis,{automargin:true,gridcolor:'#e6e6e6'})
  });
  Plotly.newPlot(node,figure.data,layout,{responsive:true,displaylogo:false}).then(()=>{
    node.on('plotly_click',event=>{
      const point=event.points && event.points[0];
      const id=point && (Array.isArray(point.customdata)?point.customdata[0]:point.customdata);
      if(id && details && details[id]) openDetails(details[id]);
    });
  });
}

/* Selections last for the browser tab. Storage can be blocked, which only loses the memory. */
const store={
  get(key){ try{ return JSON.parse(sessionStorage.getItem(key)); }catch(_){ return null; } },
  set(key,value){ try{ sessionStorage.setItem(key,JSON.stringify(value)); }catch(_){ /* not remembered */ } },
  remove(key){ try{ sessionStorage.removeItem(key); }catch(_){ /* nothing to forget */ } }
};

window.AA={get,el,callout,tag,rows,fillSelect,openDetails,drawChart,store};
})();
