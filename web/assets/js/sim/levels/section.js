/* L1 · Whole-muscle cross-section through the soleus belly (units: mm).
   How the packing is calculated:
   - The outline is the L0 soleus slice at the belly; its area follows the MRI volume ratio
     (Trappe Table 5) via the API's transverse scale factor (length held constant).
   - Fascicles are a representative mosaic (count illustrative). Each fascicle shrinks about its
     centre by √(fibre area ratio ÷ outline area ratio), where the fibre area ratio is the
     fibre-type-weighted (diameter ÷ preflight diameter)² from Fitts Tables 2 and 5. Fibre number
     is held constant (no fibre-loss data). Because fibres shrink more than the whole muscle,
     the space between fascicles (perimysium) widens; the page shows this mismatch, it does not
     resolve it.
   - Anterior bipennate / posterior unipennate compartments and the 80 % posterior share follow
     Bolsterlee et al. (2018). */
import * as THREE from 'three';
import { soleusSection, SOLEUS_Y } from './leg.js';
import { rng, loftVolume, voronoiCells, orient, polygonArea, centroid, insidePolygon, mergeGeometries,
         param, derived, stat, illus, changeColor } from '../util.js';

const BELLY_T=0.42;

export function createSection(ctx){
  const scene=new THREE.Scene();
  const root=new THREE.Group(); scene.add(root);
  const pickables=[], labels=[];
  const perimysiumMat=new THREE.MeshPhysicalMaterial({color:0xf3dcd2,roughness:0.6,sheen:0.5,sheenColor:new THREE.Color(0xffffff)});
  const epiMat=new THREE.MeshPhysicalMaterial({color:0xe9c3b8,roughness:0.28,clearcoat:0.7,clearcoatRoughness:0.25,sheen:0.6,sheenColor:new THREE.Color(0xffeeee)});
  const fasMat=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:0.5,clearcoat:0.25});
  const lineMat=new THREE.LineBasicMaterial({color:0xffffff,transparent:true,opacity:0.85});
  const ghostMat=new THREE.LineBasicMaterial({color:0xffffff,transparent:true,opacity:0.45});
  const arteryMat=new THREE.MeshStandardMaterial({color:0xb3121f,roughness:0.35});
  const veinMat=new THREE.MeshStandardMaterial({color:0x34459a,roughness:0.4});
  const nerveMat=new THREE.MeshStandardMaterial({color:0xf2d36b,roughness:0.5});
  let dynamic=[], basePoly=null, points=null, built=false, inset=null;

  function outlinePolygon(view){
    /* L0 belly slice in mm, with the same absolute preflight scale as the 3D leg */
    const vol=param(view,'soleus_volume'); const shank=stat(view,'shank_length'); const k=(shank?shank.value:39.3)/39.3;
    const base=Math.sqrt(vol.pre.value/(loftVolume(SOLEUS_Y[0],SOLEUS_Y[1],soleusSection)*k*k*k));
    const s=soleusSection(BELLY_T), rx=s.rx*base*k*10, rz=s.rz*base*k*10;
    const poly=[]; const n=96;
    for(let i=0;i<n;i++){ const a=i/n*Math.PI*2, sin=Math.sin(a);
      poly.push([rx*Math.cos(a), rz*sin*(sin>=0?1:0.62)]); }   /* flatter anterior (deep) face */
    const f=Math.sqrt(Math.PI*rx*rz/polygonArea(poly));        /* same area as the L0 slice */
    return orient(poly.map(p=>[p[0]*f,p[1]*f]));
  }

  function build(view){
    basePoly=outlinePolygon(view);
    const area=polygonArea(basePoly), count=(illus(view,'l1_fascicle_count')||{value:160}).value;
    const spacing=Math.sqrt(area/count), rand=rng(11);
    points=[]; const xs=basePoly.map(p=>p[0]), ys=basePoly.map(p=>p[1]);
    for(let x=Math.min(...xs);x<Math.max(...xs);x+=spacing) for(let y=Math.min(...ys);y<Math.max(...ys);y+=spacing*0.87){
      const p=[x+(rand()-0.5)*spacing*0.8+((Math.round(y/spacing)%2)?spacing/2:0), y+(rand()-0.5)*spacing*0.6];
      if(insidePolygon(p,basePoly)) points.push(p);
    }
    built=true;
    inset=buildInset(view, basePoly);
    root.add(inset);
  }

  function buildInset(view, poly){
    /* longitudinal (sagittal) schematic beside the section: fascicle angles from Bolsterlee 2018 */
    const g=new THREE.Group();
    const xs=poly.map(p=>p[0]); const w=Math.max(...xs);
    g.position.set(w+26,0,0);
    const fl=stat(view,'fascicle_length'), post=stat(view,'pennation_medial_posterior'), ant=stat(view,'pennation_medial_anterior');
    const H=78, Wp=22, Wa=12;
    const verts=[];
    const box=(x0,x1)=>{ verts.push(x0,-H/2,0,x1,-H/2,0, x1,-H/2,0,x1,H/2,0, x1,H/2,0,x0,H/2,0, x0,H/2,0,x0,-H/2,0); };
    box(-Wa,0); box(0,Wp);
    verts.push(-Wa/2,-H/2,0,-Wa/2,H/2,0);                       /* median septum of the anterior part */
    const L=fl?fl.value:36.8;
    const add=(x0,y0,angleDeg,dir,maxW)=>{ const a=angleDeg*Math.PI/180; let dx=Math.sin(a)*L*dir, dy=-Math.cos(a)*L;
      const lim=Math.abs(maxW/dx); if(lim<1){ dx*=lim; dy*=lim; } verts.push(x0,y0,0,x0+dx,y0+dy,0); };
    for(let y=-H/2+L;y<=H/2;y+=9){ if(post) add(Wp,y,post.value,-1,Wp); }        /* posterior: unipennate */
    for(let y=-H/2+L*0.7;y<=H/2;y+=9){ if(ant){ add(-Wa/2,y,ant.value,1,Wa/2); add(-Wa/2,y,ant.value,-1,Wa/2); } }
    const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));
    const lines=new THREE.LineSegments(geo,lineMat); g.add(lines);
    const bg=new THREE.Mesh(new THREE.PlaneGeometry(Wa+Wp+8,H+8),new THREE.MeshBasicMaterial({color:0x6e1f22,transparent:true,opacity:0.45}));
    bg.position.set((Wp-Wa)/2,0,-0.5); g.add(bg);
    bg.userData.pick={structure:'pennation',label:'Pennation (longitudinal section, schematic)',statics:['compartment_structure','fascicle_length','pennation_medial_anterior','pennation_lateral_anterior','pennation_medial_posterior','pennation_lateral_posterior']};
    pickables.push(bg);
    labels.push({id:'penn',text:'Longitudinal section',sub:'schematic, fascicle angles',at:new THREE.Vector3(w+26+Wp,H/2,0),dx:20,dy:-24,info:bg.userData.pick});
    return g;
  }

  function fibreAreaRatio(view){
    /* fibre-type-weighted cross-sectional area ratio from the reported diameters */
    const d1=param(view,'type_i_diameter'), d2=param(view,'type_ii_diameter');
    const shares=view.fibre_types.render_shares.values;
    const r=(p)=>p && p.available ? (p.value/p.pre.value)**2 : null;
    const r1=r(d1), r2=r(d2); if(r1===null) return null;
    const s1=(shares.type_i||0)+(shares.hybrid||0), s2=shares.type_ii||0;
    return r2===null ? r1 : (r1*s1+r2*s2)/(s1+s2);
  }

  function update(view,opts){
    if(!view) return;
    if(!built) build(view);
    dynamic.forEach(o=>{ root.remove(o); o.geometry && o.geometry.dispose(); const i=pickables.indexOf(o); if(i>=0) pickables.splice(i,1); }); dynamic=[];
    const ts=derived(view,'soleus_transverse_scale'), ar=derived(view,'soleus_area_ratio');
    const s=ts?ts.value:1, poly=basePoly.map(p=>[p[0]*s,p[1]*s]);
    const fib=fibreAreaRatio(view), outlineRatio=ar?ar.value:1;
    const shrink=0.9*Math.min(1.07,Math.sqrt((fib===null?outlineRatio:fib)/outlineRatio));
    const add=(o,pick)=>{ root.add(o); dynamic.push(o); if(pick){ o.userData.pick=pick; pickables.push(o); } return o; };
    /* slab with epimysium */
    const shape=new THREE.Shape(poly.map(p=>new THREE.Vector2(p[0],p[1])));
    const slab=new THREE.ExtrudeGeometry(shape,{depth:30,bevelEnabled:true,bevelThickness:0.6,bevelSize:0.6,bevelSegments:2,curveSegments:4});
    slab.translate(0,0,-30.6);
    add(new THREE.Mesh(slab,epiMat),{structure:'epimysium',params:['soleus_volume']});
    const disc=new THREE.Mesh(new THREE.ShapeGeometry(shape),perimysiumMat); disc.position.z=0.05;
    add(disc,{structure:'perimysium',params:['soleus_volume','type_i_diameter','type_ii_diameter']});
    /* fascicles */
    const cells=voronoiCells(points.map(p=>[p[0]*s,p[1]*s]),poly);
    const rand=rng(5), geos=[];
    const vol=param(view,'soleus_volume');
    cells.forEach(cell=>{
      if(cell.length<3) return;
      const c=centroid(cell), sh=new THREE.Shape(cell.map(p=>new THREE.Vector2(c[0]+(p[0]-c[0])*shrink,c[1]+(p[1]-c[1])*shrink)));
      const g=new THREE.ExtrudeGeometry(sh,{depth:1.2,bevelEnabled:false,curveSegments:1});
      g.deleteAttribute('uv');
      const col=opts.overlay?changeColor(vol?vol.percent_change:0):new THREE.Color().setHSL(0.99+rand()*0.015,0.68+rand()*0.12,0.24+rand()*0.07);
      const cols=new Float32Array(g.attributes.position.count*3);
      for(let i=0;i<g.attributes.position.count;i++){ const shade=0.88+0.12*rand(); cols[i*3]=col.r*shade; cols[i*3+1]=col.g*shade; cols[i*3+2]=col.b*shade; }
      g.setAttribute('color',new THREE.BufferAttribute(cols,3));
      geos.push(g);
    });
    const fascicles=new THREE.Mesh(mergeGeometries(geos),fasMat); fascicles.position.z=0.06;
    add(fascicles,{structure:'perimysium',label:'Fascicles in perimysium',params:['type_i_diameter','type_ii_diameter','soleus_volume'],illustrative:['l1_fascicle_count']});
    geos.forEach(g=>g.dispose());
    /* compartment boundary (anterior bipennate part, ~20 % of the area) and median septum */
    const share=stat(view,'posterior_compartment_share'); const antShare=share?1-share.value/100:0.2;
    const xs=poly.map(p=>p[0]), ys=poly.map(p=>p[1]), rx=Math.max(...xs), ryMin=Math.min(...ys);
    const ax=rx*0.56, ay=antShare*polygonArea(poly)/(Math.PI*ax), cy=ryMin+ay*0.95;
    const ring=[]; for(let i=0;i<=72;i++){ const a=i/72*Math.PI*2; ring.push(new THREE.Vector3(ax*Math.cos(a),cy+ay*Math.sin(a),1.35)); }
    add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(ring),lineMat));
    add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,cy-ay,1.36),new THREE.Vector3(0,cy+ay,1.36)]),lineMat));
    /* vessels and nerve in the connective tissue (illustrative positions and sizes) */
    [[ax*0.95,cy+ay*0.35,1.3,arteryMat,'Artery'],[ax*0.82,cy+ay*0.72,1.7,veinMat,'Vein'],[-ax*0.9,cy+ay*0.5,1.0,nerveMat,'Nerve']].forEach(([x,y,r,m,name])=>{
      const t=new THREE.Mesh(new THREE.CylinderGeometry(r,r,34,18),m); t.rotation.x=Math.PI/2; t.position.set(x,y,-14);
      add(t,{structure:'vessel',label:name+' (in the connective tissue)',illustrative:['soleus_shape']});
    });
    /* preflight ghost */
    if(opts.compare){
      const pre=basePoly.map(p=>new THREE.Vector3(p[0],p[1],1.5)); pre.push(pre[0].clone());
      add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pre),ghostMat));
      const verts=[]; voronoiCells(points,basePoly).forEach(cell=>{ if(cell.length<3) return; const c=centroid(cell);
        cell.forEach((p,i)=>{ const q=cell[(i+1)%cell.length]; verts.push(c[0]+(p[0]-c[0])*0.9,c[1]+(p[1]-c[1])*0.9,1.5,c[0]+(q[0]-c[0])*0.9,c[1]+(q[1]-c[1])*0.9,1.5); }); });
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));
      add(new THREE.LineSegments(g,ghostMat));
    }
    labels.length=0;
    const top=Math.max(...ys);
    labels.push(
      {id:'epi',text:'Epimysium',at:new THREE.Vector3(-rx*0.98,0,0.5),dx:-70,dy:-40,info:{structure:'epimysium',params:['soleus_volume']}},
      {id:'fas',text:'Fascicle',sub:'in perimysium',at:new THREE.Vector3(rx*0.3,top*0.55,1.3),dx:80,dy:-50,info:{structure:'perimysium',label:'Fascicles in perimysium',params:['type_i_diameter','type_ii_diameter','soleus_volume'],illustrative:['l1_fascicle_count']}},
      {id:'post',text:'Posterior compartment',sub:'unipennate',at:new THREE.Vector3(-rx*0.45,top*0.4,1.3),dx:-60,dy:-80,info:{structure:'compartments',label:'Posterior compartments (unipennate)',statics:['posterior_compartment_share','compartment_structure','pennation_medial_posterior','pennation_lateral_posterior']}},
      {id:'ant',text:'Anterior compartment',sub:'bipennate',at:new THREE.Vector3(0,cy,1.4),dx:-70,dy:60,info:{structure:'compartments',label:'Anterior compartments (bipennate, around a median septum)',statics:['posterior_compartment_share','compartment_structure','pennation_medial_anterior','pennation_lateral_anterior']}},
      {id:'art',text:'Blood vessels',at:new THREE.Vector3(ax*0.95,cy+ay*0.35,3.5),dx:70,dy:40,info:{structure:'vessel',label:'Blood vessels (in the connective tissue)',illustrative:['soleus_shape']}},
      {id:'nerve',text:'Nerve',at:new THREE.Vector3(-ax*0.9,cy+ay*0.5,3.5),dx:-50,dy:50,info:{structure:'vessel',label:'Nerve (in the connective tissue)',illustrative:['soleus_shape']}}
    );
    if(inset) labels.push({id:'penn',text:'Longitudinal section',sub:'schematic, fascicle angles',at:new THREE.Vector3(inset.position.x+22,39,0),dx:20,dy:-24,info:inset.children[1].userData.pick});
    ctx.relabel && ctx.relabel('L1');
  }

  function caption(view){
    const ar=derived(view,'soleus_area_ratio'), fib=fibreAreaRatio(view);
    if(!ar) return '';
    return `Cut through the belly. Outline area ${(ar.value*100).toFixed(0)} % of preflight (from MRI volume, ${param(view,'soleus_volume').timepoint}); `
      +(fib===null?'fibre data not reported for this group.':`fibre cross-sectional area ${(fib*100).toFixed(0)} % of preflight (biopsies, R+0). Fibres shrink more than the whole muscle, so the perimysium between fascicles widens; the two data sources are shown as reported, not reconciled.`);
  }

  return {id:'L1',title:'Muscle',unitsToMetres:0.001,scene,pickables,labels,update,caption,
    target:new THREE.Vector3(26,0,0),camDir:new THREE.Vector3(0.08,0.32,1).normalize(),
    minDist:55,maxDist:330,defaultDist:225};
}
