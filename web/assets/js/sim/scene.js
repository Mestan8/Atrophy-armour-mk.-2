/* Stage for the 3D Simulator: one WebGL renderer, five nested scenes (one per zoom level, each in
   its own units so float precision holds from 40 cm down to nanometres), a single camera with
   OrbitControls, and a semantic zoom that hands over to the next level when you zoom past a
   level's closest distance (or back when you zoom past its farthest). */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { makeLabel } from './labels.js';
import { createLeg } from './levels/leg.js';
import { createSection } from './levels/section.js';
import { createFascicle } from './levels/fascicle.js';
import { createFibre } from './levels/fibre.js';
import { createSarcomere } from './levels/sarcomere.js';

export function webglAvailable(){
  try{ const c=document.createElement('canvas'); return !!(window.WebGL2RenderingContext && c.getContext('webgl2')); }
  catch(_){ return false; }
}

export function createStage(container,{onPick,onLevel,reducedMotion=false,showFps=false}){
  const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=0.95;
  renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.setClearColor(0x000000,0);
  container.prepend(renderer.domElement);
  const labelRenderer=new CSS2DRenderer(); labelRenderer.domElement.className='sim-css2d'; container.append(labelRenderer.domElement);
  const fade=document.createElement('div'); fade.className='sim-fade'; container.append(fade);

  const pmrem=new THREE.PMREMGenerator(renderer);
  const env=pmrem.fromScene(new RoomEnvironment(),0.04).texture;
  const camera=new THREE.PerspectiveCamera(38,1,0.1,1000);
  const controls=new OrbitControls(camera,renderer.domElement);
  controls.enableDamping=!reducedMotion; controls.dampingFactor=0.12; controls.zoomSpeed=0.9;
  controls.listenToKeyEvents(container);

  const ctx={state:{},relabel:(id)=>relabel(levels.find(l=>l.id===id))};
  const levels=[createLeg(ctx),createSection(ctx),createFascicle(ctx),createFibre(ctx),createSarcomere(ctx)];
  levels.forEach(level=>{
    level.scene.environment=env; level.scene.environmentIntensity=0.45;
    const hemi=new THREE.HemisphereLight(0xe8fbff,0x2a1a18,0.55); level.scene.add(hemi);
    const key=new THREE.DirectionalLight(0xffffff,1.6); key.position.set(0.6,1,0.9); level.scene.add(key);
    const rim=new THREE.DirectionalLight(0x9fe8ff,0.7); rim.position.set(-1,0.4,-0.8); level.scene.add(rim);
    level.labelObjects=[]; level.stale=true;
  });

  let current=0, view=null, options={labels:true}, dirty=true, transitioning=false, pushIn=0, pushOut=0;

  function relabel(level){
    if(!level) return;
    level.labelObjects.forEach(o=>{ level.scene.remove(o); o.element.remove(); });
    level.labelObjects=level.labels.map(def=>{
      const obj=makeLabel({text:def.text,sub:def.sub,dx:def.dx,dy:def.dy,onPick:()=>onPick(def.info,level)});
      obj.position.copy(def.at); obj.visible=options.labels && level===levels[current];
      level.scene.add(obj); return obj;
    });
    dirty=true;
  }

  function placeCamera(level,distance){
    camera.near=level.minDist/60; camera.far=level.maxDist*30; camera.updateProjectionMatrix();
    controls.target.copy(level.target);
    camera.position.copy(level.target).addScaledVector(level.camDir,distance);
    controls.minDistance=level.minDist; controls.maxDistance=level.maxDist;
    controls.update(); dirty=true;
  }

  function refresh(level){
    if(view && level.stale){ level.update(view,options); level.stale=false; relabel(level); }
  }

  function enter(index,distance){
    index=Math.max(0,Math.min(levels.length-1,index));
    const previous=levels[current];
    previous.labelObjects.forEach(o=>o.visible=false);
    labelRenderer.render(previous.scene,camera);           /* hides the old level's labels */
    current=index;
    const level=levels[current];
    refresh(level);
    level.labelObjects.forEach(o=>o.visible=options.labels);
    placeCamera(level,distance===undefined?level.defaultDist:distance);
    pushIn=pushOut=0;
    onLevel(level,current);
  }

  function goTo(index,distance){
    if(transitioning || index===current && distance===undefined){ if(index===current) placeCamera(levels[current],levels[current].defaultDist); return; }
    if(reducedMotion){ enter(index,distance); return; }
    transitioning=true; fade.classList.add('on');
    setTimeout(()=>{ enter(index,distance); fade.classList.remove('on'); setTimeout(()=>{ transitioning=false; },230); },230);
  }

  function distance(){ return camera.position.distanceTo(controls.target); }

  /* Crossing a level boundary: zooming past the closest distance moves in, past the farthest moves out. */
  function edgeZoom(direction){
    const level=levels[current], d=distance();
    if(direction>0 && d<=level.minDist*1.04 && current<levels.length-1){ if(++pushIn>=3) goTo(current+1,levels[current+1].maxDist*0.9); return true; }
    if(direction<0 && d>=level.maxDist*0.96 && current>0){ if(++pushOut>=3) goTo(current-1,levels[current-1].minDist*1.15); return true; }
    pushIn=pushOut=0; return false;
  }
  renderer.domElement.addEventListener('wheel',event=>{ edgeZoom(event.deltaY<0?1:-1); },{passive:true});
  /* pinch: compare successive two-finger spans */
  const touches=new Map(); let lastSpan=null;
  renderer.domElement.addEventListener('pointermove',event=>{
    if(!touches.has(event.pointerId)) return; touches.set(event.pointerId,[event.clientX,event.clientY]);
    if(touches.size===2){ const [a,b]=[...touches.values()], span=Math.hypot(a[0]-b[0],a[1]-b[1]);
      if(lastSpan!==null && Math.abs(span-lastSpan)>6){ edgeZoom(span>lastSpan?1:-1); lastSpan=span; } else if(lastSpan===null) lastSpan=span; }
  });
  const endTouch=event=>{ touches.delete(event.pointerId); if(touches.size<2) lastSpan=null; };
  renderer.domElement.addEventListener('pointerup',endTouch); renderer.domElement.addEventListener('pointercancel',endTouch);

  function zoomBy(factor){
    const level=levels[current], d=distance(), next=d*factor;
    if(next<level.minDist*0.999){ if(current<levels.length-1) goTo(current+1,levels[current+1].maxDist*0.9); else placeCamera(level,level.minDist); return; }
    if(next>level.maxDist*1.001){ if(current>0) goTo(current-1,levels[current-1].minDist*1.15); else placeCamera(level,level.maxDist); return; }
    camera.position.sub(controls.target).multiplyScalar(factor).add(controls.target); controls.update(); dirty=true;
  }

  /* Picking: a click (not a drag) on a structure. */
  const raycaster=new THREE.Raycaster(); let down=null;
  renderer.domElement.addEventListener('pointerdown',event=>{ down=[event.clientX,event.clientY];
    if(event.pointerType==='touch') touches.set(event.pointerId,[event.clientX,event.clientY]); });
  renderer.domElement.addEventListener('pointerup',event=>{
    if(!down || Math.hypot(event.clientX-down[0],event.clientY-down[1])>5) return;
    const rect=renderer.domElement.getBoundingClientRect();
    const p=new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
    raycaster.setFromCamera(p,camera);
    const level=levels[current];
    const hits=raycaster.intersectObjects(level.pickables,false);
    for(const hit of hits){
      const info=level.pickInstance && hit.instanceId!==undefined ? level.pickInstance(hit.object,hit.instanceId) : hit.object.userData.pick;
      if(info){ onPick(info,level); return; }
    }
  });
  controls.addEventListener('change',()=>{ dirty=true; });

  /* Scale bar from the camera distance: metres per pixel at the orbit target. */
  const barLine=document.getElementById('scalebar-line'), barText=document.getElementById('scalebar-text');
  function updateScaleBar(){
    const level=levels[current], h=renderer.domElement.clientHeight||1;
    const worldPerPx=2*distance()*Math.tan(THREE.MathUtils.degToRad(camera.fov/2))/h;
    const metresPerPx=worldPerPx*level.unitsToMetres, target=metresPerPx*110;
    const pow=Math.pow(10,Math.floor(Math.log10(target))), nice=[5,2,1].map(n=>n*pow).find(v=>v<=target)||pow;
    barLine.style.width=Math.round(nice/metresPerPx)+'px';
    barText.textContent=formatLength(nice);
  }

  function resize(){
    const w=container.clientWidth, h=container.clientHeight;
    renderer.setSize(w,h,false); renderer.domElement.style.width=w+'px'; renderer.domElement.style.height=h+'px';
    labelRenderer.setSize(w,h); camera.aspect=w/Math.max(1,h); camera.updateProjectionMatrix(); dirty=true;
  }
  new ResizeObserver(resize).observe(container); resize();

  /* Render on demand; ?fps=1 renders every frame and shows the measured frame rate. */
  const fpsNode=document.getElementById('sim-fps'); let frames=0, last=performance.now();
  if(showFps) fpsNode.hidden=false;
  function loop(now){
    requestAnimationFrame(loop);
    const moving=controls.update();
    if(dirty || moving || showFps){
      const level=levels[current];
      renderer.render(level.scene,camera); labelRenderer.render(level.scene,camera); updateScaleBar(); dirty=false;
    }
    if(showFps){ frames++; if(now-last>=1000){ fpsNode.textContent=`${(frames*1000/(now-last)).toFixed(0)} fps · ${levels[current].id}`; frames=0; last=now; } }
  }
  requestAnimationFrame(loop);

  return {
    levels,
    get current(){ return current; },
    setView(next,opts){
      view=next; options={...options,...opts};
      levels.forEach(level=>level.stale=true);
      refresh(levels[current]); onLevel(levels[current],current); dirty=true;
    },
    setOptions(opts){
      options={...options,...opts};
      levels.forEach(level=>level.stale=true); refresh(levels[current]);
      levels[current].labelObjects.forEach(o=>o.visible=options.labels); onLevel(levels[current],current); dirty=true;
    },
    start(){ enter(0); },
    goTo:(i)=>goTo(i),
    zoomIn:()=>zoomBy(0.7), zoomOut:()=>zoomBy(1/0.7),
    reset:()=>goTo(0,levels[0].defaultDist),
    distance,
    zoomLevel(){ const l=levels[current]; return current+Math.log(l.maxDist/distance())/Math.log(l.maxDist/l.minDist); },
    renderer
  };
}

export function formatLength(m){
  if(m>=0.01) return `${+(m*100).toPrecision(3)} cm`;
  if(m>=0.001) return `${+(m*1000).toPrecision(3)} mm`;
  if(m>=1e-6) return `${+(m*1e6).toPrecision(3)} µm`;
  return `${+(m*1e9).toPrecision(3)} nm`;
}
