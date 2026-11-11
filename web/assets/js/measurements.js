/* Measurements (read-only): harmonized category slots for every study, filters and comparison charts. */
(function(){
"use strict";
const {get,el,callout,tag,rows,fillSelect,openDetails,drawChart,store}=window.AA;
const STORE_KEY='atrophy.measurements.v2';

const filtersForm=document.getElementById('filters');
let filters=store.get(STORE_KEY)||{};
let details={};
let latestRequest=0;

async function load(){
  const requestId=++latestRequest;
  let view;
  try{ view=await get('/api/measurements',filters); }
  catch(error){ if(requestId===latestRequest) document.getElementById('status').replaceChildren(callout('error',error.message)); return; }
  if(requestId!==latestRequest) return;
  details=view.details;
  document.getElementById('status').replaceChildren();
  renderFilters(view.filters);
  renderCharts(view.charts);
  renderStudies(view);
  document.getElementById('value-types').replaceChildren(rows(view.value_types));
}

function renderFilters(list){
  list.forEach(filter=>{
    let field=filtersForm.querySelector('.field[data-id="'+filter.id+'"]');
    if(!field){
      const select=el('select',{id:'filter-'+filter.id});
      select.addEventListener('change',()=>{ filters[filter.id]=select.value; store.set(STORE_KEY,filters); load(); });
      field=el('div',{class:'field','data-id':filter.id},el('label',{for:'filter-'+filter.id,text:filter.label}),select);
      filtersForm.append(field);
    }
    fillSelect(field.querySelector('select'),filter.options,filter.value);
    filters[filter.id]=filter.value;
  });
  store.set(STORE_KEY,filters);
}

function renderCharts(charts){
  const box=document.getElementById('charts');
  box.replaceChildren(...charts.map(chart=>{
    const node=el('div',{class:'chart'});
    const block=el('details',{class:'panel chart-block','data-id':chart.id},
      el('summary',{text:chart.label}),el('p',{class:'caption',text:chart.message||chart.caption}),node);
    block.addEventListener('toggle',()=>{ if(block.open && !node.dataset.drawn){ node.dataset.drawn='1'; drawChart(node,chart.figure,details); } });
    return block;
  }));
  /* Open the first chart so the page always shows one comparison. */
  const first=box.querySelector('details');
  if(first) first.open=true;
}

function sourceButton(id){
  const button=el('button',{class:'link',type:'button',text:'Source'});
  button.addEventListener('click',()=>openDetails(details[id]));
  return button;
}

function renderStudies(view){
  document.getElementById('studies').replaceChildren(...view.studies.map(study=>{
    const blocks=study.categories.map(category=>{
      const head=el('h4',{text:category.label});
      const description=el('p',{class:'help',text:category.description});
      if(!category.rows.length) return el('div',{},head,description,el('p',{class:'empty',text:category.empty}));
      const table=el('table',{},
        el('thead',{},el('tr',{},...view.columns.map(name=>el('th',{scope:'col',text:name})),el('th',{scope:'col',text:'Details'}))),
        el('tbody',{},...category.rows.map(row=>el('tr',{},
          ...row.cells.map((cell,index)=>{
            const td=el('td',{class:index===4?'num':null,text:cell});
            if(index===5) td.replaceChildren(document.createTextNode(cell.split(':')[0]),tag(row.value_type),el('div',{class:'help',text:cell.includes(':')?cell.slice(cell.indexOf(':')+1).trim():''}));
            return td;
          }),
          el('td',{},sourceButton(row.detail_id))))));
      return el('div',{},head,description,el('div',{class:'table-scroll'},table));
    });
    return el('details',{class:'panel',open:view.studies.length===1?'':null},
      el('summary',{text:study.title}),el('p',{class:'caption',text:study.caption}),...blocks);
  }));
}

filtersForm.addEventListener('submit',event=>event.preventDefault());

load();
})();
