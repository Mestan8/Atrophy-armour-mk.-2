/* L0 · Leg (units: cm). Posterior view of a left lower leg: tibia, fibula, calcaneus, Achilles
   tendon, ghosted gastrocnemius, translucent skin and the soleus highlighted in cyan.
   Shapes are illustrative; the soleus and gastrocnemius VOLUMES come from the API (Trappe Table 5),
   and the leg length from the shank length in the parameter file (Bolsterlee 2018 Table 1). */
import * as THREE from 'three';
import { loftY, loftVolume, param, derived, stat, changeColor } from '../util.js';

/* x: lateral (−) to medial (+) for a left leg seen from behind; y: up; z: posterior (+). */
const sm=(a,b,x)=>{ const t=Math.min(1,Math.max(0,(x-a)/(b-a))); return t*t*(3-2*t); };
const bump=(t,c,w)=>Math.exp(-(((t-c)/w)**2));
export const SOLEUS_Y=[6,34];
export function soleusSection(t){
  /* broad and flat, widest in the lower half (it extends below the gastrocnemius), narrowing to
     the Achilles tendon below and spreading across the tibia and fibula at its origin above */
  const b=bump(t,0.45,0.33);
  const rx=0.9+2.8*b+0.5*sm(0.75,1,t);
  const rz=0.5+1.3*b;
  const cx=0.4-1.0*sm(0.6,1,t);
  const cz=0.7+rz+1.6*(1-sm(0,0.3,t));      /* deep surface on the bones, posterior towards the tendon */
  return {cx,cz,rx,rz};
}
function gastroSection(side){
  /* medial (+) and lateral (−) heads: from the femoral condyles down to the aponeurosis, posterior to the soleus */
  return t=>{
    const b=bump(t,side>0?0.38:0.42,0.3);
    const rz=0.4+1.55*b;
    return {cx:side*(1.45+0.3*b+0.75*sm(0.75,1,t)), cz:3.3+rz-2.2*sm(0.8,1,t), rx:0.4+2.0*b, rz};
  };
}
const GASTRO=[[21,43,1],[24,43,-1]];

export function createLeg(ctx){
  const scene=new THREE.Scene();
  const group=new THREE.Group(); scene.add(group);
  const pickables=[];
  const labels=[];

  const bone=new THREE.MeshPhysicalMaterial({color:0xece3d0,roughness:0.55,clearcoat:0.25,clearcoatRoughness:0.6,vertexColors:true});
  const tendonMat=new THREE.MeshPhysicalMaterial({color:0xf6f3ec,roughness:0.3,clearcoat:0.6,sheen:0.6,sheenColor:new THREE.Color(0xffffff)});
  const soleusMat=new THREE.MeshPhysicalMaterial({color:0x14c4d4,roughness:0.32,clearcoat:0.55,clearcoatRoughness:0.25,emissive:0x00363c,emissiveIntensity:0.35,vertexColors:true});
  const gastroMat=new THREE.MeshPhysicalMaterial({color:0xc4534a,roughness:0.4,transparent:true,opacity:0.34,depthWrite:false,vertexColors:true,side:THREE.DoubleSide});
  const skinMat=new THREE.MeshPhysicalMaterial({color:0xf3cdb4,roughness:0.5,transparent:true,opacity:0.1,depthWrite:false,side:THREE.DoubleSide,clearcoat:0.3});
  const ghostMat=new THREE.MeshBasicMaterial({color:0xffffff,wireframe:true,transparent:true,opacity:0.22,depthWrite:false});

  let length=39.3, k=1, built=false;
  let soleus=null, soleusGhost=null, gastro=[], skin=null;
  const tag=(mesh,info)=>{ mesh.userData.pick=info; pickables.push(mesh); return mesh; };

  function buildStatic(view){
    const shank=stat(view,'shank_length'); length=shank?shank.value:length;
    k=length/39.3;                                       /* proportions drawn for a 39.3 cm shank */
    group.scale.setScalar(k);
    /* tibia: plateau on top, medial malleolus below */
    const tibia=loftY(-0.6,39.3,t=>({cx:1.2+0.4*sm(0.85,1,t),cz:-0.6,rx:1.1+1.7*sm(0.85,1,t)+0.6*(1-sm(0,0.08,t)),rz:0.95+0.9*sm(0.85,1,t)+0.3*(1-sm(0,0.08,t))}),{deepZ:1});
    group.add(tag(new THREE.Mesh(tibia,bone),{structure:'tibia_fibula',label:'Tibia'}));
    const fibula=loftY(-1.4,37.2,t=>({cx:-2.9,cz:-1.1,rx:0.48+0.5*sm(0.9,1,t)+0.4*(1-sm(0,0.06,t)),rz:0.48+0.4*sm(0.9,1,t)+0.3*(1-sm(0,0.06,t))}),{deepZ:1});
    group.add(tag(new THREE.Mesh(fibula,bone),{structure:'tibia_fibula',label:'Fibula'}));
    const femur=loftY(40.3,47,t=>({cx:0.6,cz:-0.3,rx:3.3-1.3*sm(0,1,t),rz:2.3-0.6*sm(0,1,t)}),{deepZ:1});
    group.add(new THREE.Mesh(femur,bone));
    const calc=new THREE.Mesh(new THREE.SphereGeometry(1,40,28),bone.clone()); calc.material.vertexColors=false;
    calc.scale.set(1.6,1.45,3.4); calc.position.set(0.5,-2.6,0.9); calc.rotation.x=-0.25;
    group.add(tag(calc,{structure:'achilles_tendon',label:'Calcaneus'}));
    const talus=new THREE.Mesh(new THREE.SphereGeometry(1,32,20),calc.material); talus.scale.set(1.7,1.0,2.1); talus.position.set(0.6,-0.9,-0.8); group.add(talus);
    /* tendinous arch between the fibular head and the tibia (soleal line) */
    const arch=new THREE.QuadraticBezierCurve3(new THREE.Vector3(-2.7,34.6,-0.2),new THREE.Vector3(-0.6,31.2,1.7),new THREE.Vector3(1.6,34.0,0.4));
    group.add(tag(new THREE.Mesh(new THREE.TubeGeometry(arch,40,0.16,10),tendonMat),{structure:'tibia_fibula',label:'Tendinous arch of the soleus'}));
    /* Achilles (calcaneal) tendon */
    const achilles=new THREE.CatmullRomCurve3([new THREE.Vector3(0.35,12,3.3),new THREE.Vector3(0.4,6,3.25),new THREE.Vector3(0.45,1.5,3.4),new THREE.Vector3(0.5,-1.6,3.6)]);
    const tubeGeo=new THREE.TubeGeometry(achilles,60,1,16);
    const pos=tubeGeo.attributes.position, center=new THREE.Vector3();
    for(let i=0;i<pos.count;i++){ /* flatten and taper: wide above, narrow above the heel */
      const u=Math.floor(i/17)/60; achilles.getPointAt(Math.min(1,u),center);
      const w=1.35-0.75*u+0.25*Math.max(0,u-0.85)*6, d=0.42+0.08*u;
      pos.setX(i,center.x+(pos.getX(i)-center.x)*w); pos.setZ(i,center.z+(pos.getZ(i)-center.z)*d);
    }
    tubeGeo.computeVertexNormals();
    group.add(tag(new THREE.Mesh(tubeGeo,tendonMat),{structure:'achilles_tendon',label:'Achilles (calcaneal) tendon'}));
    /* skin */
    skin=new THREE.Mesh(loftY(-4.2,45,t=>{ const calf=bump(t,0.6,0.22);
      return {cx:0.2,cz:1.0+1.9*calf+0.6*sm(0.85,1,t),rx:3.3+2.5*calf+1.4*sm(0.82,1,t),rz:3.3+2.3*calf+0.6*sm(0.85,1,t)}; },{ao:false}),skinMat);
    skin.renderOrder=3; group.add(skin);   /* not pickable: it would cover every structure */

    const anchor=(x,y,z)=>new THREE.Vector3(x,y,z).multiplyScalar(k);
    labels.push(
      {id:'soleus',text:'Soleus',sub:'',at:anchor(3.4,13,3.0),dx:80,dy:-10,info:{structure:'soleus'}},
      {id:'gastro',text:'Gastrocnemius',sub:'ghosted',at:anchor(-2.3,28,6.0),dx:-90,dy:30,info:{structure:'gastrocnemius'}},
      {id:'tibia',text:'Tibia',sub:'',at:anchor(2.0,24,-0.1),dx:80,dy:30,info:{structure:'tibia_fibula',label:'Tibia'}},
      {id:'fibula',text:'Fibula',sub:'',at:anchor(-3.3,22,-0.8),dx:-70,dy:20,info:{structure:'tibia_fibula',label:'Fibula'}},
      {id:'arch',text:'Tendinous arch',sub:'origin',at:anchor(-0.6,31.4,1.7),dx:-90,dy:-40,info:{structure:'tibia_fibula',label:'Tendinous arch of the soleus'}},
      {id:'achilles',text:'Achilles tendon',sub:'',at:anchor(0.45,4,3.7),dx:-90,dy:-10,info:{structure:'achilles_tendon'}},
      {id:'calcaneus',text:'Calcaneus',sub:'insertion',at:anchor(0.6,-2.6,4.2),dx:80,dy:-20,info:{structure:'achilles_tendon',label:'Calcaneus'}}
    );
    built=true;
  }

  function update(view,opts){
    if(!view) return;
    if(!built) buildStatic(view);
    const vol=param(view,'soleus_volume');
    if(soleus){ group.remove(soleus); soleus.geometry.dispose(); pickables.splice(pickables.indexOf(soleus),1); }
    if(soleusGhost){ group.remove(soleusGhost); soleusGhost.geometry.dispose(); soleusGhost=null; }
    gastro.forEach(m=>{ group.remove(m); m.geometry.dispose(); pickables.splice(pickables.indexOf(m),1); }); gastro=[];
    if(vol && vol.available){
      /* absolute size: preflight shape scaled to the reported preflight volume (cm³), then the
         API's transverse scale factor (√ of the volume ratio) applied to the cross-section */
      const base=Math.sqrt(vol.pre.value/(loftVolume(SOLEUS_Y[0],SOLEUS_Y[1],soleusSection)*k*k*k));
      const ts=derived(view,'soleus_transverse_scale');
      const geo=loftY(SOLEUS_Y[0],SOLEUS_Y[1],soleusSection,{scale:base*(ts?ts.value:1)});
      soleus=new THREE.Mesh(geo,soleusMat);
      if(opts.overlay){ soleusMat.color.copy(changeColor(vol.percent_change)); soleusMat.emissiveIntensity=0.1; }
      else { soleusMat.color.set(0x14c4d4); soleusMat.emissiveIntensity=0.35; }
      soleus.renderOrder=1; group.add(tag(soleus,{structure:'soleus'}));
      if(opts.compare){
        soleusGhost=new THREE.Mesh(loftY(SOLEUS_Y[0],SOLEUS_Y[1],soleusSection,{scale:base*1.002,rings:36,radial:28}),ghostMat);
        group.add(soleusGhost);
      }
      ctx.state.soleusBase=base;
    }
    const gv=param(view,'gastrocnemius_volume');
    if(gv && gv.available && opts.gastro){
      const raw=GASTRO.reduce((sum,[y0,y1,side])=>sum+loftVolume(y0,y1,gastroSection(side)),0);
      const base=Math.sqrt(gv.pre.value/(raw*k*k*k)), ts=derived(view,'gastrocnemius_transverse_scale');
      GASTRO.forEach(([y0,y1,side])=>{
        const m=new THREE.Mesh(loftY(y0,y1,gastroSection(side),{scale:base*(ts?ts.value:1),rings:48,radial:36}),gastroMat);
        m.renderOrder=2; group.add(tag(m,{structure:'gastrocnemius'})); gastro.push(m);
      });
      gastroMat.color.set(opts.overlay?changeColor(gv.percent_change):0xc4534a);
    }
    skin.visible=true;
  }

  function caption(view,opts){
    const vol=param(view,'soleus_volume');
    if(!vol || !vol.available) return '';
    return `Lower leg, posterior view. The soleus (cyan) lies deep to the gastrocnemius and inserts through the Achilles tendon on the calcaneus. Volume ${fmt(vol.value)} cm³ (${vol.value_type}; ${vol.timepoint}).`;
  }

  return {id:'L0',title:'Leg',unitsToMetres:0.01,scene,pickables,labels,update,caption,
    target:new THREE.Vector3(0.3,19.5,1.5),camDir:new THREE.Vector3(0.22,0.06,1).normalize(),
    minDist:22,maxDist:120,defaultDist:86,
    zoomTarget:new THREE.Vector3(0.6,17,4)};
}
function fmt(v){ return Math.abs(v)>=100?v.toFixed(0):v.toFixed(1); }
