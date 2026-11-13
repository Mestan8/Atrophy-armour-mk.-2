/* L2 · Fascicle (units: µm). A bundle of fibres in endomysium, with capillaries between them.
   Data-driven: each fibre's diameter (Fitts Table 2 type I, Table 5 type II) and the share of
   type I / type II / hybrid fibres (Trappe Table 8). Illustrative: the number of fibres drawn,
   their positions and the capillary positions. Hybrids (slow+fast myosin) are drawn with the
   type I diameter because Fitts excluded them (approximation, stated in the info panel). */
import * as THREE from 'three';
import { rng, param, stat, illus, changeColor } from '../util.js';

const LENGTH=700;
const TYPE_COLORS={type_i:0x8e1424,type_ii:0xf08f86,hybrid:0x9b59b6};
const PLAIN=0xa8232b;

export function createFascicle(ctx){
  const scene=new THREE.Scene();
  const root=new THREE.Group(); scene.add(root);
  const pickables=[], labels=[];
  const fibreMat=new THREE.MeshPhysicalMaterial({roughness:0.45,clearcoat:0.35,clearcoatRoughness:0.3,sheen:0.3,sheenColor:new THREE.Color(0xffd6d6)});
  const capMat=new THREE.MeshStandardMaterial({color:0xd0202e,roughness:0.3,emissive:0x3a0000});
  const endoMat=new THREE.MeshPhysicalMaterial({color:0xf6e6dd,roughness:0.7,transparent:true,opacity:0.9});
  const periMat=new THREE.MeshPhysicalMaterial({color:0xf3dcd2,roughness:0.35,transparent:true,opacity:0.18,depthWrite:false,side:THREE.DoubleSide,clearcoat:0.5});
  const ghostMat=new THREE.LineBasicMaterial({color:0xffffff,transparent:true,opacity:0.6});
  let layout=null, fibres=null, caps=null, endo=null, sheath=null, ghost=null, order=null;

  /* Circle packing of the preflight diameters (deterministic). */
  function buildLayout(view,count){
    const rand=rng(23), d1=param(view,'type_i_diameter').pre.value;
    const r=d1/2, pts=[]; const R=Math.sqrt(count)*r*1.08;
    for(let i=0;i<count;i++){ const a=rand()*Math.PI*2, q=Math.sqrt(rand())*R; pts.push([Math.cos(a)*q,Math.sin(a)*q]); }
    const gap=r*0.12;
    for(let it=0;it<260;it++){
      for(let i=0;i<count;i++){ /* pull to centre */ pts[i][0]*=0.997; pts[i][1]*=0.997; }
      for(let i=0;i<count;i++) for(let j=i+1;j<count;j++){
        const dx=pts[j][0]-pts[i][0], dy=pts[j][1]-pts[i][1], d=Math.hypot(dx,dy)||1e-6, min=2*r+gap;
        if(d<min){ const push=(min-d)/2, ux=dx/d, uy=dy/d; pts[i][0]-=ux*push; pts[i][1]-=uy*push; pts[j][0]+=ux*push; pts[j][1]+=uy*push; }
      }
    }
    /* capillary sites: interstices between three mutually neighbouring fibres */
    const sites=[]; const near=2*r+gap*3.2;
    for(let i=0;i<count;i++) for(let j=i+1;j<count;j++){
      if(Math.hypot(pts[i][0]-pts[j][0],pts[i][1]-pts[j][1])>near) continue;
      for(let k=j+1;k<count;k++){
        if(Math.hypot(pts[i][0]-pts[k][0],pts[i][1]-pts[k][1])>near || Math.hypot(pts[j][0]-pts[k][0],pts[j][1]-pts[k][1])>near) continue;
        sites.push([(pts[i][0]+pts[j][0]+pts[k][0])/3,(pts[i][1]+pts[j][1]+pts[k][1])/3]);
      }
    }
    order=Array.from({length:count},(_,i)=>i).sort((a,b)=>{ const ka=rng(a*97+7)(), kb=rng(b*97+7)(); return ka-kb; });
    const extent=Math.max(...pts.map(p=>Math.hypot(p[0],p[1])))+r;
    return {pts,sites,radius:extent};
  }

  function classCounts(shares,count){
    const keys=['type_i','hybrid','type_ii'], raw=keys.map(k=>(shares[k]||0)*count), base=raw.map(Math.floor);
    let left=count-base.reduce((a,b)=>a+b,0);
    raw.map((v,i)=>[v-base[i],i]).sort((a,b)=>b[0]-a[0]).forEach(([,i])=>{ if(left>0){ base[i]++; left--; } });
    return Object.fromEntries(keys.map((k,i)=>[k,base[i]]));
  }

  function update(view,opts){
    if(!view) return;
    const d1=param(view,'type_i_diameter'), d2=param(view,'type_ii_diameter');
    if(!d1 || !d1.available) return;
    const count=(illus(view,'l2_fibre_count')||{value:100}).value;
    if(!layout) layout=buildLayout(view,count);
    const shares=view.fibre_types.render_shares.values, counts=classCounts(shares,count);
    const types=new Array(count); let c=0;
    order.forEach(idx=>{ types[idx]= c<counts.type_i?'type_i':(c<counts.type_i+counts.hybrid?'hybrid':'type_ii'); c++; });
    const diam={type_i:d1.value,hybrid:d1.value,type_ii:(d2&&d2.available)?d2.value:d1.value};
    const pre={type_i:d1.pre.value,hybrid:d1.pre.value,type_ii:(d2&&d2.available)?d2.pre.value:d1.pre.value};
    const pct={type_i:d1.percent_change,hybrid:d1.percent_change,type_ii:(d2&&d2.available)?d2.percent_change:d1.percent_change};
    /* the bundle contracts with the mean diameter ratio (positions are illustrative) */
    const s=d1.value/d1.pre.value;
    if(!fibres){
      const geo=new THREE.CylinderGeometry(1,1,LENGTH,20,1); geo.rotateX(Math.PI/2); geo.translate(0,0,-LENGTH/2);
      fibres=new THREE.InstancedMesh(geo,fibreMat,count); fibres.userData.pick={structure:'fibre'}; root.add(fibres); pickables.push(fibres);
    }
    const m=new THREE.Matrix4(), col=new THREE.Color();
    for(let i=0;i<count;i++){
      const t=types[i], r=diam[t]/2;
      m.makeScale(r,r,1).setPosition(layout.pts[i][0]*s,layout.pts[i][1]*s,0);
      fibres.setMatrixAt(i,m);
      if(opts.overlay) col.copy(changeColor(pct[t])); else col.set(opts.types?TYPE_COLORS[t]:PLAIN);
      fibres.setColorAt(i,col);
    }
    fibres.instanceMatrix.needsUpdate=true; if(fibres.instanceColor) fibres.instanceColor.needsUpdate=true;
    fibres.userData.types=types;
    /* capillaries: about the reported capillaries-per-fibre (Hendrickse 2022 baseline); unchanged by the slider */
    const lc=stat(view,'capillaries_per_type_i_fibre'); const nCap=Math.min(layout.sites.length,Math.round((lc?lc.value:1.8)*count));
    if(!caps){
      const geo=new THREE.CylinderGeometry(2.6,2.6,LENGTH*1.02,10,1); geo.rotateX(Math.PI/2); geo.translate(0,0,-LENGTH/2+4);
      caps=new THREE.InstancedMesh(geo,capMat,layout.sites.length); caps.userData.pick={structure:'capillary',statics:['capillaries_per_type_i_fibre','capillary_density_type_i'],illustrative:['l2_capillary_placement']};
      root.add(caps); pickables.push(caps);
    }
    for(let i=0;i<layout.sites.length;i++){
      m.makeScale(i<nCap?1:0.0001,i<nCap?1:0.0001,1).setPosition(layout.sites[i][0]*s,layout.sites[i][1]*s,0); caps.setMatrixAt(i,m);
    }
    caps.instanceMatrix.needsUpdate=true;
    /* endomysium (matrix between fibres) and the perimysium sheath */
    const R=layout.radius*s;
    if(endo){ root.remove(endo); endo.geometry.dispose(); pickables.splice(pickables.indexOf(endo),1); }
    endo=new THREE.Mesh(new THREE.CylinderGeometry(R,R,LENGTH-6,64,1),endoMat); endo.rotation.x=Math.PI/2; endo.position.z=-LENGTH/2-4;
    endo.userData.pick={structure:'endomysium',params:['type_i_diameter','type_ii_diameter']}; root.add(endo); pickables.push(endo);
    if(sheath){ root.remove(sheath); sheath.geometry.dispose(); }
    sheath=new THREE.Mesh(new THREE.CylinderGeometry(R*1.06,R*1.06,LENGTH+20,64,1,true),periMat); sheath.rotation.x=Math.PI/2; sheath.position.z=-LENGTH/2+8; root.add(sheath);
    /* preflight ghost circles on the cut face */
    if(ghost){ root.remove(ghost); ghost.geometry.dispose(); ghost=null; }
    if(opts.compare){
      const v=[];
      for(let i=0;i<count;i++){ const r=pre[types[i]]/2, [x,y]=layout.pts[i];
        for(let k=0;k<24;k++){ const a=k/24*Math.PI*2, b=(k+1)/24*Math.PI*2; v.push(x+Math.cos(a)*r,y+Math.sin(a)*r,2,x+Math.cos(b)*r,y+Math.sin(b)*r,2); } }
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(v,3)); ghost=new THREE.LineSegments(g,ghostMat); root.add(ghost);
    }
    /* labels */
    labels.length=0;
    const pick=(t)=>{ const i=types.findIndex(x=>x===t); return i<0?null:i; };
    const lab=(t,text,dx,dy)=>{ const i=pick(t); if(i===null) return; labels.push({id:t,text,at:new THREE.Vector3(layout.pts[i][0]*s,layout.pts[i][1]*s,1),dx,dy,info:fibreInfo(t)}); };
    lab('type_i','Type I fibre',-90,-60);
    lab('type_ii','Type II fibre',90,-50); lab('hybrid','Hybrid fibre',90,60);
    if(nCap) labels.push({id:'cap',text:'Capillary',at:new THREE.Vector3(layout.sites[0][0]*s,layout.sites[0][1]*s,1),dx:-80,dy:70,info:caps.userData.pick});
    labels.push({id:'endo',text:'Endomysium',at:new THREE.Vector3(R*0.7,-R*0.72,0),dx:70,dy:40,info:endo.userData.pick});
    labels.push({id:'peri',text:'Perimysium',sub:'sheath',at:new THREE.Vector3(-R*1.05,R*0.2,-40),dx:-80,dy:-20,info:{structure:'perimysium'}});
    ctx.relabel && ctx.relabel('L2');
  }

  function fibreInfo(type){
    const params={type_i:['type_i_diameter','type_i_csa'],type_ii:['type_ii_diameter','type_ii_csa'],hybrid:['type_i_diameter']}[type];
    return {structure:'fibre_'+type,label:{type_i:'Slow type I fibre',type_ii:'Fast type II fibre',hybrid:'Hybrid fibre (slow + fast myosin)'}[type],
      params,distribution:true,illustrative:['l2_fibre_count'],renderClass:type};
  }

  function pickInstance(object,instanceId){
    if(object===fibres && fibres.userData.types) return fibreInfo(fibres.userData.types[instanceId]);
    return object.userData.pick;
  }

  function caption(view,opts){
    const d1=param(view,'type_i_diameter'); if(!d1||!d1.available) return '';
    const sh=view.fibre_types.render_shares.values;
    return `Fascicle, cut face. Type I fibre diameter ${d1.value.toFixed(1)} µm (${d1.value_type}, ${d1.timepoint}). Fibre-type mix: ${(100*(sh.type_i||0)).toFixed(0)} % type I, ${(100*(sh.type_ii||0)).toFixed(0)} % type II, ${(100*(sh.hybrid||0)).toFixed(0)} % slow–fast hybrids. ${opts.types?'Colours: dark red type I, pink type II, purple hybrid.':''}`;
  }

  return {id:'L2',title:'Fascicle',unitsToMetres:1e-6,scene,pickables,labels,update,caption,pickInstance,
    target:new THREE.Vector3(0,0,-60),camDir:new THREE.Vector3(0.45,0.35,1).normalize(),
    minDist:260,maxDist:3200,defaultDist:2300};
}
