/* Scenario Explorer in two steps.
   Step 1 (Scenario): control changes fetch only the control state from /api/scenario/controls,
   so unsupported options grey out live but nothing is calculated.
   Step 2 (Results): "Show results" / "Update results" and the duration slider fetch /api/scenario.
   All selection rules and calculations stay on the server; this file only renders. */
(function(){
"use strict";
const {get,el,callout,tag,rows,fillSelect,openDetails,drawChart}=window.AA;
const STORE_KEY='atrophy.scenario.v3';
/* Must match API_VERSION in api.py. A different value means the running server is older or newer than this page. */
const API_VERSION='2026-11-12.3d-simulator';
const RESTART_COMMAND='.\\.venv\\Scripts\\python.exe app.py';
const RESTART_HINT='The running server looks out of date — restart it with '+RESTART_COMMAND;

const form=document.getElementById('controls');
const controlsStatus=document.getElementById('controls-status');
const showButton=document.getElementById('show-results');
const section=document.getElementById('results-section');
const heading=document.getElementById('results-title');
const resultsStatus=document.getElementById('results-status');
const resultsBody=document.getElementById('results-body');
const slider=document.getElementById('duration');
const versionNotice=document.getElementById('version-notice');

/* The saved scenario survives a reload (localStorage). Whether results were shown is never saved. */
const saved={
  get(){ try{ return JSON.parse(localStorage.getItem(STORE_KEY))||{}; }catch(_){ return {}; } },
  set(value){ try{ localStorage.setItem(STORE_KEY,JSON.stringify(value)); }catch(_){ /* not remembered */ } },
  clear(){ try{ localStorage.removeItem(STORE_KEY); }catch(_){ /* nothing to forget */ } }
};

let selection=saved.get();     // the scenario being edited (no duration)
let duration=null;            // slider value; null means "use the study's default"
let shown=false;              // results are visible
let stale=false;              // scenario changed since the results were calculated
let busy=false;
let latestControls=0, latestResults=0;
let details={};
let sliderTimer=null;

/* ---- Step 1: control state only ---- */

async function refreshControls(){
  const requestId=++latestControls;
  controlsStatus.textContent='Updating options…';
  let view;
  try{ view=await get('/api/scenario/controls',selection); }
  catch(error){
    if(requestId===latestControls) controlsStatus.replaceChildren(callout('error',describeError('The scenario options could not be loaded',error)));
    return;
  }
  if(requestId!==latestControls) return;
  /* A later success clears any earlier error box. */
  controlsStatus.replaceChildren();
  renderControls(view.controls);
  selection=Object.fromEntries(view.controls.map(control=>[control.id,control.value]));
  saved.set(selection);
}

/* Selects are updated in place so keyboard focus survives a change. */
function renderControls(controls){
  controls.forEach(control=>{
    let field=form.querySelector('.field[data-id="'+control.id+'"]');
    if(!field){
      const select=el('select',{id:'control-'+control.id,'aria-describedby':'help-'+control.id});
      select.addEventListener('change',()=>onScenarioChange(control.id,select.value));
      field=el('div',{class:'field','data-id':control.id},
        el('label',{for:'control-'+control.id,text:control.label}),select,
        el('p',{class:'help',id:'help-'+control.id,text:control.help}));
      form.append(field);
    }
    fillSelect(field.querySelector('select'),control.options,control.value);
  });
}

function onScenarioChange(id,value){
  selection[id]=value;
  /* A new scenario starts the slider at that study's reported mission length next time results are confirmed. */
  duration=null;
  if(shown) markStale();
  refreshControls();
}

function markStale(){
  if(stale) return;
  stale=true;
  /* The slider would recalculate with the changed scenario, so it waits for Update results. */
  slider.disabled=true;
  resultsBody.classList.add('is-stale');
  resultsStatus.replaceChildren(callout('warn','Scenario settings changed — press Update results to recalculate.'));
  setButton();
}

function setButton(){
  showButton.disabled=busy;
  showButton.textContent=busy?'Loading…':(shown?'Update results':'Show results');
}

/* Turns a failed request into a sentence that says what happened and what to do. */
function describeError(what,error){
  if(error.status===404) return what+' (HTTP 404). '+RESTART_HINT+'.';
  if(error.status) return what+' (HTTP '+error.status+'): '+error.message;
  return what+': '+error.message;
}

/* Warns once if the server and this page come from different versions of the app. */
async function checkServerVersion(){
  let health=null, status=null;
  try{ health=await get('/api/health'); }
  catch(error){ status=error.status||null; }
  if(health && health.api_version===API_VERSION){ versionNotice.replaceChildren(); return; }
  if(!health && status!==404) return;   /* server unreachable: the controls request reports that */
  versionNotice.replaceChildren(callout('warn','Server is outdated or from a different version of the app (page '+API_VERSION+', server '+(health?health.api_version:'unknown')+'). Restart it with '+RESTART_COMMAND+' and reload the page.'));
}

/* ---- Step 2: full results ---- */

async function loadResults({reveal}){
  const requestId=++latestResults;
  busy=true; setButton();
  if(reveal) slider.disabled=true;
  const params=Object.assign({},selection);
  if(duration!==null) params.duration=duration;
  let view;
  try{ view=await get('/api/scenario',params); }
  catch(error){
    if(requestId!==latestResults) return;
    busy=false;
    showError(describeError('Results could not be loaded',error));
    setButton();
    return;
  }
  if(requestId!==latestResults) return;
  busy=false;
  /* Unhide before drawing: Plotly measures its container, and a hidden one has no width. */
  section.hidden=false;
  resultsBody.hidden=false;
  render(view);
  stale=false;
  resultsBody.classList.remove('is-stale');
  resultsStatus.replaceChildren();
  const wasShown=shown;
  shown=true;
  setButton();
  if(reveal || !wasShown){
    heading.scrollIntoView({block:'start'});
    heading.focus({preventScroll:true});
  }
}

/* A failed request never leaves older results looking current. */
function showError(message){
  section.hidden=false;
  shown=true;
  stale=false;
  resultsBody.classList.remove('is-stale');
  resultsBody.hidden=true;
  ['duration','recovery','comparison'].forEach(name=>Plotly.purge(document.getElementById(name+'-chart')));
  resultsStatus.replaceChildren(callout('error',message));
  heading.scrollIntoView({block:'start'});
  heading.focus({preventScroll:true});
}

function render(view){
  details=view.details;
  /* A successful results request also clears an earlier error about loading the options. */
  controlsStatus.replaceChildren();
  /* The server may have adjusted the scenario; keep the form in step with what the results describe. */
  renderControls(view.controls);
  selection=Object.fromEntries(view.controls.map(control=>[control.id,control.value]));
  saved.set(selection);
  duration=view.slider.value;
  renderResults(view);
  renderSlider(view.slider);
  renderChart('duration',view.charts.duration);
  renderChart('recovery',view.charts.recovery);
  renderChart('comparison',view.charts.comparison);
  document.getElementById('models').replaceChildren(...(view.models.length
    ? view.models.map(card=>el('div',{class:'result'},el('h4',{text:card.title}),rows(card.rows)))
    : [el('p',{class:'empty',text:'No duration model applies to this selection.'})]));
  document.getElementById('context').replaceChildren(rows(view.context));
  document.getElementById('value-types').replaceChildren(rows(view.value_types));
}

function renderSlider(data){
  slider.min=data.min; slider.max=data.max; slider.step=data.step; slider.value=data.value;
  slider.disabled=!data.is_approximation;
  document.getElementById('duration-value').textContent=data.value;
  document.getElementById('slider-range').textContent='Slider range '+data.min+'–'+data.max+' days; default '+data.default+' days (the selected study\'s reported mission length).';
  const label=document.getElementById('model-label');
  label.replaceChildren(document.createTextNode(data.model_label));
  if(data.is_approximation) label.append(tag('approximation'));
  const notices=data.notices.map(text=>callout(data.is_approximation?'approx':'info',text));
  if(data.warning) notices.push(callout('warn',data.warning));
  data.statements.forEach(text=>notices.push(el('p',{class:'help',text:'Source statement: '+text})));
  document.getElementById('slider-notices').replaceChildren(...notices);
  document.getElementById('slider-supported').textContent=data.supported;
  document.getElementById('slider-sources').textContent=data.sources.length?'Sources: '+data.sources.join('; '):'';
}

function renderResults(view){
  const summary=[el('p',{text:view.summary})];
  if(view.headline) summary.push(el('p',{class:'caption',text:view.headline}));
  document.getElementById('summary').replaceChildren(...summary);
  document.getElementById('results').replaceChildren(...view.rows.map(row=>{
    const parts=[el('h4',{text:row.title}),el('p',{class:'help',text:row.subtitle})];
    if(row.metrics.length){
      parts.push(el('div',{class:'metrics'},...row.metrics.map(metric=>
        el('dl',{class:'metric'},el('dt',{},document.createTextNode(metric.label),tag(metric.tag)),el('dd',{text:metric.text})))));
    }
    row.warnings.forEach(text=>parts.push(callout('warn',text)));
    row.notes.forEach(text=>parts.push(el('p',{class:'help',text})));
    if(row.detail_id){
      const button=el('button',{class:'link',type:'button',text:'Source: '+row.source+' (show full provenance)'});
      button.addEventListener('click',()=>openDetails(details[row.detail_id]));
      parts.push(el('p',{},button));
    }
    return el('div',{class:'result'},...parts);
  }));
}

function renderChart(name,data){
  const node=document.getElementById(name+'-chart');
  const caption=document.getElementById(name+'-caption');
  if(data.message){ caption.textContent=data.message; drawChart(node,null); return; }
  caption.textContent=data.caption;
  drawChart(node,data.figure,details);
}

/* ---- Events ---- */

showButton.addEventListener('click',()=>loadResults({reveal:true}));

/* The slider belongs to reading the results: it updates them live, debounced. */
slider.addEventListener('input',()=>{
  document.getElementById('duration-value').textContent=slider.value;
  clearTimeout(sliderTimer);
  sliderTimer=setTimeout(()=>{ duration=Number(slider.value); loadResults({reveal:false}); },150);
});

document.getElementById('reset').addEventListener('click',()=>{
  selection={}; duration=null; shown=false; stale=false;
  latestResults++;            // drop any results request still in flight
  busy=false;
  saved.clear();
  section.hidden=true;
  resultsStatus.replaceChildren();
  resultsBody.classList.remove('is-stale');
  setButton();
  refreshControls();
});
form.addEventListener('submit',event=>event.preventDefault());

setButton();
refreshControls();
checkServerVersion();
})();
