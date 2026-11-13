/* 3D Simulator page controller. Every value comes from GET /api/simulator/soleus; this file only
   renders it (and turns it into geometry through sim/scene.js). The model and its controls are live
   on load: there is no "Show results" step. */
import { createStage, webglAvailable } from './sim/scene.js';

const {get,el,callout,tag,rows}=window.AA;
/* Must match API_VERSION in api.py (the Explorer carries the same string). */
const API_VERSION='2026-11-12.3d-simulator';
const RESTART_COMMAND='.\\.venv\\Scripts\\python.exe app.py';
const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const showFps=new URLSearchParams(location.search).has('fps');

const $=id=>document.getElementById(id);
const slider=$('sim-day'), dayValue=$('sim-day-value'), playButton=$('sim-play'), recoveryButton=$('sim-recovery');
const shapeSelect=$('sim-shape'), cohortSelect=$('sim-cohort');
const state={day:0,cohort:'all',shape:null,phase:'mission'};
const options={compare:false,overlay:false,types:true,gastro:true,labels:true,em:false};
let view=null, stage=null, latest=0, timer=null, playing=null, lastPick=null;

/* ---------------------------------------------------------------- server */

async function checkVersion(){
  let health=null, status=null;
  try{ health=await get('/api/health'); }catch(error){ status=error.status; }
  if(health && health.api_version===API_VERSION){ $('version-notice').replaceChildren(); return; }
  if(!health && status!==404) return;
  $('version-notice').replaceChildren(callout('warn','Server is outdated or from a different version of the app (page '+API_VERSION+', server '+(health?health.api_version:'unknown')+'). Restart it with '+RESTART_COMMAND+' and reload the page.'));
}

async function load(){
  const requestId=++latest;
  let next;
  try{ next=await get('/api/simulator/soleus',{day:state.day,cohort:state.cohort,shape:state.shape,phase:state.phase}); }
  catch(error){
    if(requestId!==latest) return;
    const hint=error.status===404?' The running server looks out of date — restart it with '+RESTART_COMMAND+'.':'';
    $('sim-status').replaceChildren(callout('error','The simulator values could not be loaded ('+(error.status||'no response')+'): '+error.message+hint));
    return;
  }
  if(requestId!==latest) return;   /* a newer request is on its way */
  view=next;
  if(!state.shape) state.shape=view.time_course.shape;
  render();
}
function schedule(delay=120){ clearTimeout(timer); timer=setTimeout(load,delay); }

/* ---------------------------------------------------------------- rendering */

function fmt(value,unit){
  if(value===null||value===undefined) return 'not reported';
  const a=Math.abs(value), digits=a>=100?0:a>=10?1:a>=1?2:3;
  return value.toFixed(digits)+(unit?' '+unit:'');
}
function pct(value){ return value===null||value===undefined?'—':(value>0?'+':'')+value.toFixed(1)+' %'; }
function disp(record,type){ return record.dispersion&&record.dispersion.length?` ± ${record.dispersion.join('–')} (${type})`:' (dispersion not reported)'; }

function render(){
  fillControls();
  const notices=view.notices.map((text,i)=>callout(i>1?'approx':'info',text));
  $('sim-status').replaceChildren(...notices);
  slider.max=String(view.day.end); slider.value=String(view.day.value);
  dayValue.textContent=view.day.phase==='recovery'?'R+19':String(Math.round(view.day.value));
  slider.disabled=view.day.phase==='recovery';
  $('sim-day-help').textContent=view.day.range_note;
  const shape=view.time_course.shapes.find(s=>s.id===view.time_course.shape);
  $('sim-model-label').replaceChildren(document.createTextNode(shape.label+' '),tag('approximation'));
  $('sim-model-notice').replaceChildren(view.day.status==='interpolated'?callout('approx',shape.notice):
    callout('info',view.day.status==='preflight'?'Day 0 shows the preflight values as reported.':view.day.phase==='recovery'?'Recovery view: R+19 muscle volumes as reported; deeper levels show landing-day values.':'End of mission: the reported postflight values (fibres R+0, muscle volume R+4).'));
  if(stage) stage.setView(view,options);
  renderValues(); renderModel(); renderIllustrative(); renderValueTypes();
  if(lastPick) showInfo(lastPick.info,lastPick.level,false);
}

function fillControls(){
  if(!shapeSelect.options.length){
    view.time_course.shapes.forEach(s=>shapeSelect.append(el('option',{value:s.id,text:s.label})));
    view.cohorts.forEach(c=>cohortSelect.append(el('option',{value:c.id,text:`${c.label} (n = ${c.n_crew} crew)`})));
  }
  shapeSelect.value=view.time_course.shape; cohortSelect.value=view.cohort.id;
  $('sim-cohort-help').textContent=view.cohort.note||'';
}

function valueRow(p){
  if(!p.available) return el('tr',{},el('td',{text:p.name}),el('td',{colspan:'6',text:p.message}));
  return el('tr',{},
    el('td',{text:p.name+' ('+p.unit+')'}),
    el('td',{class:'num',text:fmt(p.value)}),
    el('td',{class:'num',text:fmt(p.pre.value)+disp(p.pre,p.dispersion_type)}),
    el('td',{class:'num',text:fmt(p.end.value)+disp(p.end,p.dispersion_type)}),
    el('td',{class:'num',text:pct(p.percent_change)}),
    el('td',{},tag(p.value_type)),
    el('td',{text:`${p.timepoint}. ${p.end.source}, ${p.end.location}`}));
}

function renderValues(){
  const head=el('tr',{},...['Value','Current','Preflight','End / timepoint value','% change','Type','Timepoint and source'].map(t=>el('th',{text:t})));
  const table=el('table',{class:'sim-table'},el('thead',{},head),el('tbody',{},...view.parameters.map(valueRow)));
  const ft=view.fibre_types;
  const types=el('table',{class:'sim-table'},el('thead',{},el('tr',{},...['Fibre type (MHC)','Current %','Preflight %','End %','Type'].map(t=>el('th',{text:t})))),
    el('tbody',{},...ft.categories.map(c=>el('tr',{},el('td',{text:c.label}),el('td',{class:'num',text:fmt(c.value)}),
      el('td',{class:'num',text:fmt(c.pre.value)+disp(c.pre,'SE')}),el('td',{class:'num',text:fmt(c.end.value)+disp(c.end,'SE')}),el('td',{},tag(c.value_type))))));
  const derived=el('ul',{},...view.derived.map(d=>el('li',{},document.createTextNode(`${d.name}: ${fmt(d.value,d.unit)} `),tag(d.value_type),el('span',{class:'help',text:' '+d.formula}))));
  const statics=el('ul',{},...view.static.map(s=>el('li',{},document.createTextNode(`${s.name}: ${s.value===null?'(description)':fmt(s.value,s.unit)}${s.dispersion&&s.dispersion.length?' ± '+s.dispersion.join('–')+' ('+s.dispersion_type+')':''}${s.n?', n = '+s.n+' '+s.n_counts:''} — ${s.source}, ${s.location} `),tag(s.value_type))));
  $('sim-values').replaceChildren(
    el('p',{class:'help',text:`Day ${view.day.phase==='recovery'?'R+19 (recovery)':Math.round(view.day.value)} · ${view.cohort.label} (n = ${view.cohort.n_crew} crew) · fibre n counts fibres, not people.`}),
    el('div',{class:'sim-table-wrap'},table),
    el('h4',{text:`Fibre-type distribution (${ft.n_counts}; ${ft.timepoint})`}), el('div',{class:'sim-table-wrap'},types),
    el('p',{class:'help',text:ft.note}),
    el('h4',{text:'Derived drawing quantities'}),derived,
    el('h4',{text:'Fixed anatomy and ultrastructure (not changed by the slider)'}),statics);
}

function renderModel(){
  const blocks=view.time_course.shapes.map(s=>el('div',{class:'result'},
    el('h4',{},document.createTextNode(s.label+' '),tag(s.value_type),s.id===view.time_course.shape?el('span',{class:'tag',text:'in use'}):null),
    rows([{label:'What the in-between days assume',text:s.assumed},{label:'Why',text:s.why},{label:'Method',text:s.method},{label:'What would replace it',text:s.needed_to_replace},
      {label:'Sources',text:s.sources.map(x=>x.label+(x.evidence_type?' ('+x.evidence_type+')':'')).join('; ')}]),
    ...s.supporting_quotes.map(q=>el('p',{class:'sim-quote',text:`“${q.quote}” — ${q.source}, ${q.location}`}))));
  const checks=el('ul',{},...view.time_course.check_points.map(c=>el('li',{text:`Day ${c.day}: another crew (17-day Shuttle flight) measured ${c.percent_change} % for ${c.parameter.replace(/_/g,' ')}; the curve in use gives ${c.model_percent_change===null?'—':c.model_percent_change.toFixed(1)+' %'} for this cohort. ${c.note} (${c.source}, ${c.location})`})));
  const context=el('ul',{},...view.time_course.context.map(c=>el('li',{text:`${c.source} (${c.evidence_type}): “${c.quote}” ${c.use}`})));
  $('sim-model').replaceChildren(
    el('p',{text:'In plain language: nobody measured these crew members during the flight. Day 0 shows their preflight averages and day 177 shows what was measured after landing. Every day in between is drawn by assuming the change follows a chosen shape. Two shapes are offered because the evidence disagrees: spaceflight cohorts suggest fast early loss that levels off, while a bed-rest study found a steady straight-line loss. The truth for this crew is unknown.'}),
    ...blocks, el('h4',{text:'Comparison with a 17-day flight (not used to build the curve)'}),checks,
    el('h4',{text:'Context only'}),context,
    el('p',{class:'help',text:view.day.range_note+' '+view.day.mission_quote.source+', '+view.day.mission_quote.location+': “'+view.day.mission_quote.quote+'”'}));
}

const LEVEL_SUMMARY={
  L0:['Soleus and gastrocnemius volumes (Trappe Table 5) scale the 3D shapes; shank length (Bolsterlee 2018) sets the leg size.','Bone, tendon, skin and muscle shapes.'],
  L1:['Outline area from the MRI volume ratio; fascicle shrinkage from the fibre diameters (Fitts); 80 % posterior share and pennation angles (Bolsterlee 2018).','Number and arrangement of fascicles; vessel and nerve positions.'],
  L2:['Fibre diameters per type (Fitts Tables 2, 5); type I / II / hybrid shares (Trappe Table 8); capillaries per fibre (Hendrickse 2022 baseline, unchanged).','Number of fibres drawn, their positions, capillary positions; hybrids sized as type I (approximation).'],
  L3:['Fibre diameter; myofibril diameter; band pattern from sarcomere and thick-filament length; triads at the A–I junctions.','Numbers and positions of myofibrils (count scaled with CSA: approximation), nuclei, mitochondria and triads.'],
  L4:['Sarcomere length, thick-filament length, longest thin filaments; thin-filament reach and thin:thick ratio before flight and on landing day; lattice spacing from the thick-filament density.','Filament thickness, head spacing, which filaments are long, positions of extra thin filaments.']
};
function renderIllustrative(){
  const table=el('table',{class:'sim-table'},el('thead',{},el('tr',{},el('th',{text:'Level'}),el('th',{text:'Data-driven'}),el('th',{text:'Illustrative'}))),
    el('tbody',{},...view.levels.map(l=>el('tr',{},el('td',{text:`${l.id} ${l.label}`}),el('td',{text:LEVEL_SUMMARY[l.id][0]}),el('td',{text:LEVEL_SUMMARY[l.id][1]})))));
  const list=el('ul',{},...view.illustrative.map(i=>el('li',{},document.createTextNode(`${i.name}${i.value!==undefined?' ('+i.value+' '+(i.unit||'')+')':''}: ${i.reason} `),tag('illustrative'))));
  const findings=el('ul',{},...view.qualitative_findings.map(f=>el('li',{text:`“${f.quote}” — ${f.source}, ${f.location}. ${f.applies_to}`})));
  $('sim-illustrative').replaceChildren(el('div',{class:'sim-table-wrap'},table),el('h4',{text:'Illustrative elements'}),list,el('h4',{text:'Qualitative electron-microscopy findings'}),findings);
}
function renderValueTypes(){
  $('sim-value-types').replaceChildren(rows(Object.entries(view.value_types).map(([k,v])=>({label:k,text:v}))));
}

/* ---------------------------------------------------------------- info panel */

function structureOf(id){ return view.structures.find(s=>s.id===id); }
function sourceRows(record,label){
  const out=[{label,text:`${fmt(record.value)}${disp(record,record.dispersion_type||'as printed')}; n = ${record.n===null||record.n===undefined?'not stated':record.n} (${record.n_counts}); ${record.timepoint||''}`},
             {label:'Source',text:`${record.source}, ${record.location}${record.quote?': “'+record.quote+'”':''}`}];
  if(record.formula) out.push({label:'Formula',text:record.formula});
  return out;
}
function paramBlock(id){
  const p=view.parameters.find(x=>x.id===id); if(!p) return null;
  if(!p.available) return el('div',{class:'result'},el('h4',{text:p.name}),callout('info',p.message));
  const list=[
    {label:'Current',text:`${fmt(p.value,p.unit)} · ${p.status.replace(/_/g,' ')} · ${p.timepoint}`},
    {label:'% change',text:`${pct(p.percent_change)} (calculated: ${p.percent_change_formula})`},
    ...sourceRows({...p.pre,dispersion_type:p.dispersion_type},'Preflight'),
    ...sourceRows({...p.end,dispersion_type:p.dispersion_type},view.day.phase==='recovery'&&p.end.timepoint.startsWith('R+19')?'R+19':'End of mission')];
  if(p.reported_change) list.push({label:'Reported change',text:`${p.reported_change.value} ${p.reported_change.unit}${p.reported_change.dispersion.length?' ± '+p.reported_change.dispersion[0]:''} — ${p.reported_change.source}, ${p.reported_change.location}${p.reported_change.note?'. '+p.reported_change.note:''}`});
  if(p.assumption) list.push({label:'Assumption',text:p.assumption});
  if(p.formula) list.push({label:'Interpolation',text:p.formula});
  if(p.recovery_note) list.push({label:'R+19',text:p.recovery_note});
  if(p.note) list.push({label:'Note',text:p.note});
  return el('div',{class:'result'},el('h4',{},document.createTextNode(p.name+' '),tag(p.value_type)),rows(list));
}
function staticBlock(id){
  const s=view.static.find(x=>x.id===id); if(!s) return null;
  const list=[{label:'Value',text:s.value===null?'Description (no number)':`${fmt(s.value,s.unit)}${s.dispersion&&s.dispersion.length?' ± '+s.dispersion.join('–')+' ('+s.dispersion_type+')':''}`},
    {label:'n',text:s.n?`${s.n} (${s.n_counts})`:s.n_counts},{label:'Source',text:`${s.source}, ${s.location}: “${s.quote}”`}];
  if(s.formula) list.push({label:'Formula',text:s.formula});
  if(s.assumed) list.push({label:'Assumption',text:s.assumed});
  if(s.note) list.push({label:'Note',text:s.note});
  list.push({label:'Slider',text:'Not changed by the mission slider (not measured in the crew).'});
  return el('div',{class:'result'},el('h4',{},document.createTextNode(s.name+' '),tag(s.value_type)),rows(list));
}

function showInfo(info,level,focus=true){
  if(!view||!info) return;
  lastPick={info,level};
  const structure=structureOf(info.structure);
  const title=info.label||(structure&&structure.name)||({soleus:'Soleus',gastrocnemius:'Gastrocnemius',fibre:'Muscle fibre',vessel:'Vessel',compartments:'Compartments',pennation:'Pennation',near_m:'Near-M region',lattice:'Filament lattice'}[info.structure])||info.structure;
  const body=[];
  const fn=(structure&&structure.function)||(info.structure==='soleus'?(view.parameters.find(p=>p.id==='soleus_volume')||{}).function:null)||(info.structure==='gastrocnemius'?(view.parameters.find(p=>p.id==='gastrocnemius_volume')||{}).function:null);
  if(fn) body.push(el('p',{class:'sim-quote',text:`“${fn.text}” — ${fn.source}, ${fn.location}`}));
  if(structure&&structure.note) body.push(el('p',{class:'help',text:structure.note}));
  const params=info.params||({soleus:['soleus_volume'],gastrocnemius:['gastrocnemius_volume']}[info.structure])||[];
  params.forEach(id=>{ const b=paramBlock(id); if(b) body.push(b); });
  if(info.distribution){
    const ft=view.fibre_types, cls=info.renderClass;
    body.push(el('div',{class:'result'},el('h4',{text:'Share of this fibre class'}),
      rows([{label:'Current',text:`${(100*(ft.render_shares.values[cls]||0)).toFixed(1)} % of fibres (${ft.render_shares.value_type}: ${ft.render_shares.formula})`},
            {label:'Class',text:ft.render_shares.classes[cls]},
            {label:'From',text:ft.categories.filter(c=>c.render_class===cls).map(c=>`${c.label}: ${fmt(c.value)} % (pre ${fmt(c.pre.value)}, end ${fmt(c.end.value)}; ${c.value_type})`).join(' · ')},
            {label:'Source',text:`${ft.categories[0].end.source}, ${ft.categories[0].end.location}; n = ${ft.n} (${ft.n_counts})`}])));
  }
  (info.derived||[]).forEach(id=>{ const d=view.derived.find(x=>x.id===id); if(d) body.push(el('div',{class:'result'},el('h4',{},document.createTextNode(d.name+' '),tag(d.value_type)),
    rows([{label:'Value',text:fmt(d.value,d.unit)},{label:'Formula',text:d.formula},...(d.assumed?[{label:'Assumption',text:d.assumed}]:[]),...(d.note?[{label:'Note',text:d.note}]:[])]))); });
  (info.statics||[]).forEach(id=>{ const b=staticBlock(id); if(b) body.push(b); });
  (info.findings||[]).forEach(id=>{ const f=view.qualitative_findings.find(x=>x.id===id); if(f) body.push(el('div',{class:'result'},el('h4',{},document.createTextNode('Electron microscopy (qualitative) '),tag(f.value_type)),el('p',{class:'sim-quote',text:`“${f.quote}” — ${f.source}, ${f.location}`}),el('p',{class:'help',text:f.applies_to}))); });
  (info.illustrative||[]).forEach(id=>{ const i=view.illustrative.find(x=>x.id===id); if(i) body.push(el('p',{},tag('illustrative'),document.createTextNode(` ${i.name}: ${i.reason}`))); });
  if(!params.length && !(info.statics||[]).length && !info.distribution && !(info.derived||[]).length)
    body.push(el('p',{},tag('illustrative'),document.createTextNode(' Shape and position are illustrative. Neither study measured this structure, so it does not change with the slider.')));
  $('sim-info-title').textContent=`${title} · ${level.title}`;
  $('sim-info-body').replaceChildren(...body);
  if(focus && window.matchMedia('(max-width:980px)').matches) $('sim-info').scrollIntoView({behavior:reducedMotion?'auto':'smooth',block:'nearest'});
}

/* ---------------------------------------------------------------- stage */

function onLevel(level,index){
  const crumbs=$('sim-breadcrumb');
  if(!crumbs.children.length){
    ['Leg','Muscle','Fascicle','Fibre','Sarcomere'].forEach((name,i)=>{
      const b=el('button',{type:'button',text:name,title:`Jump to ${name} (key ${i})`}); b.addEventListener('click',()=>stage.goTo(i));
      crumbs.append(el('li',{},b)); });
  }
  [...crumbs.querySelectorAll('button')].forEach((b,i)=>{ if(i===index) b.setAttribute('aria-current','true'); else b.removeAttribute('aria-current'); });
  if(!view) return;
  $('sim-caption').textContent=level.caption(view,options);
  const banner=level.banner?level.banner(view,options):null;
  $('sim-banner').hidden=!banner; $('sim-banner').textContent=banner||'';
  const legend=$('sim-legend');
  if(options.overlay){
    legend.hidden=false;
    legend.replaceChildren(el('div',{text:'% change from preflight'}),el('div',{class:'bar'}),el('div',{class:'ends'},el('span',{text:'−25 % or less'}),el('span',{text:'0'}),el('span',{text:'+25 % or more'})));
  } else if(index===2 && options.types){
    legend.hidden=false;
    legend.replaceChildren(...[['#8e1424','Type I'],['#f08f86','Type II'],['#9b59b6','Slow–fast hybrid']].map(([c,t])=>el('div',{},Object.assign(el('span',{class:'swatch'}),{style:`background:${c}`}),document.createTextNode(t))));
  } else legend.hidden=true;
}

function initStage(){
  const container=$('sim-stage');
  if(!webglAvailable()){
    const box=$('sim-webgl-fallback'); box.hidden=false;
    box.textContent='WebGL 2 is not available in this browser, so the 3D model cannot be drawn. Every value is still listed in the text panel below.';
    return;
  }
  stage=createStage(container,{onPick:(info,level)=>showInfo(info,level),onLevel,reducedMotion,showFps});
  stage.start();
  if(showFps) window.__simStage=stage;   /* debug handle, only with ?fps=1 */
  $('zoom-in').addEventListener('click',()=>stage.zoomIn());
  $('zoom-out').addEventListener('click',()=>stage.zoomOut());
  $('zoom-reset').addEventListener('click',()=>stage.reset());
  container.addEventListener('keydown',event=>{
    if(event.target!==container) return;
    if(event.key==='+'||event.key==='='){ stage.zoomIn(); event.preventDefault(); }
    else if(event.key==='-'||event.key==='_'){ stage.zoomOut(); event.preventDefault(); }
    else if(/^[0-4]$/.test(event.key)){ stage.goTo(Number(event.key)); event.preventDefault(); }
    else if(event.key==='r'||event.key==='R'){ stage.reset(); event.preventDefault(); }
  });
}

/* ---------------------------------------------------------------- controls */

function setDay(day,{immediate=false}={}){
  state.day=Math.round(day); state.phase='mission'; recoveryButton.setAttribute('aria-pressed','false');
  dayValue.textContent=String(state.day); slider.value=String(state.day);
  schedule(immediate?0:120);
}
slider.addEventListener('input',()=>{ stopPlay(); setDay(Number(slider.value)); });
$('sim-end').addEventListener('click',()=>{ stopPlay(); setDay(Number(slider.max),{immediate:true}); });
recoveryButton.addEventListener('click',()=>{
  stopPlay();
  const on=state.phase!=='recovery'; state.phase=on?'recovery':'mission';
  recoveryButton.setAttribute('aria-pressed',String(on)); schedule(0);
});
shapeSelect.addEventListener('change',()=>{ state.shape=shapeSelect.value; schedule(0); });
cohortSelect.addEventListener('change',()=>{ state.cohort=cohortSelect.value; schedule(0); });
[['opt-compare','compare'],['opt-overlay','overlay'],['opt-types','types'],['opt-gastro','gastro'],['opt-labels','labels'],['opt-em','em']].forEach(([id,key])=>{
  const box=$(id); options[key]=box.checked;
  box.addEventListener('change',()=>{ options[key]=box.checked; if(stage) stage.setOptions(options); });
});

/* Play: about 12 s per mission, only when the user presses it. */
function stopPlay(){ if(playing){ clearInterval(playing); playing=null; } playButton.textContent='Play mission'; playButton.setAttribute('aria-pressed','false'); }
playButton.addEventListener('click',()=>{
  if(playing){ stopPlay(); return; }
  const end=Number(slider.max);
  if(state.phase==='recovery'||state.day>=end) setDay(0,{immediate:true});
  playButton.textContent='Pause'; playButton.setAttribute('aria-pressed','true');
  playing=setInterval(()=>{
    const next=Math.min(end,state.day+3); setDay(next,{immediate:true});
    if(next>=end) stopPlay();
  },200);
});

initStage();
checkVersion();
load();
