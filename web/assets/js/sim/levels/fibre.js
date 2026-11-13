/* L3 · Single slow type I fibre (units: µm), fibre axis along x.
   Data-driven: fibre diameter (Fitts Table 2), myofibril diameter (OpenStax), sarcomere length and
   thick-filament length for the band pattern (Fitts p.4; Szikora 2022), triads at the A–I junctions
   (Lainé 2018). Approximation: the number of myofibrils scales with fibre CSA (API value).
   Illustrative: counts and positions of myofibrils, nuclei, mitochondria and triads. The
   "EM findings" option shows the QUALITATIVE description for crew with high atrophy (Fitts Fig. 10). */
import * as THREE from 'three';
import { rng, bandMaterial, cristaeMaterial, param, derived, stat, illus, changeColor } from '../util.js';

const HALF=90, WIN_X=36, WIN_A=55*Math.PI/180;

export function createFibre(ctx){
  const scene=new THREE.Scene();
  const root=new THREE.Group(); scene.add(root);
  const pickables=[], labels=[];
  const membraneMat=new THREE.MeshPhysicalMaterial({color:0xf4e9ec,roughness:0.12,transmission:0,thickness:1.2,ior:1.35,
    clearcoat:1,clearcoatRoughness:0.08,transparent:true,opacity:0.3,side:THREE.DoubleSide,depthWrite:false,specularIntensity:1});
  const capMat=new THREE.MeshPhysicalMaterial({color:0xf2c7c9,roughness:0.5,transparent:true,opacity:0.35,depthWrite:false,side:THREE.DoubleSide});
  const nucleusMat=new THREE.MeshPhysicalMaterial({color:0x7b3fa0,roughness:0.35,clearcoat:0.6,clearcoatRoughness:0.2});
  const mitoMat=cristaeMaterial(0xf08a24);
  const tMat=new THREE.MeshStandardMaterial({color:0x2bb8b0,roughness:0.4,emissive:0x05302d});
  const srMat=new THREE.MeshStandardMaterial({color:0xbfe6f2,roughness:0.5,transparent:true,opacity:0.85});
  const ghostMat=new THREE.LineBasicMaterial({color:0xffffff,transparent:true,opacity:0.6});
  const glyMat=new THREE.PointsMaterial({color:0xe8e2c8,size:0.18,sizeAttenuation:true});
  let parts=[], bandMat=null, structure=null;

  function sarcolemma(R){
    const seg=128, ringsX=180, pos=[], idx=[];
    for(let i=0;i<=ringsX;i++){ const x=-HALF+2*HALF*i/ringsX; for(let j=0;j<=seg;j++){ const a=j/seg*Math.PI*2; pos.push(x,R*Math.sin(a),R*Math.cos(a)); } }
    for(let i=0;i<ringsX;i++) for(let j=0;j<seg;j++){
      const x=-HALF+2*HALF*(i+0.5)/ringsX, a=(j+0.5)/seg*Math.PI*2, ang=Math.atan2(Math.sin(a),Math.cos(a));
      if(Math.abs(x)<WIN_X && Math.abs(ang)<WIN_A) continue;          /* rectangular cutaway window */
      const p=i*(seg+1)+j, q=p+seg+1; idx.push(p,q,p+1,p+1,q,q+1);
    }
    const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3)); g.setIndex(idx); g.computeVertexNormals(); return g;
  }

  function clear(){ parts.forEach(o=>{ root.remove(o); o.geometry&&o.geometry.dispose(); const i=pickables.indexOf(o); if(i>=0) pickables.splice(i,1); }); parts=[]; }
  const add=(o,pick)=>{ root.add(o); parts.push(o); if(pick){ o.userData.pick=pick; pickables.push(o); } return o; };

  function update(view,opts){
    if(!view) return;
    const d=param(view,'type_i_diameter'); if(!d||!d.available) return;
    clear();
    const R=d.value/2, sl=stat(view,'sarcomere_length').value, thick=stat(view,'thick_filament_length').value;
    const myo=stat(view,'myofibril_diameter').value, count=derived(view,'myofibril_count_rendered');
    const atEnd=view.day.status==='end_of_mission'||view.day.status==='recovery';
    const em=opts.em && atEnd;                              /* qualitative EM picture only for the landing-day state */
    if(!bandMat) bandMat=bandMaterial(0xb3202c,{period:sl,aHalf:thick/2});
    bandMat.color.set(opts.overlay?changeColor(d.percent_change):0xb3202c);
    /* membrane, end caps */
    add(new THREE.Mesh(sarcolemma(R),membraneMat),{structure:'sarcolemma',params:['type_i_diameter','type_i_csa','type_i_peak_force','type_i_specific_tension','type_i_vo','type_i_peak_power','type_ii_peak_force','type_ii_vo','type_ii_peak_power']}).renderOrder=5;
    [-HALF,HALF].forEach(x=>{ const c=new THREE.Mesh(new THREE.CircleGeometry(R,96),capMat); c.rotation.y=Math.PI/2; c.position.x=x; add(c); });
    /* myofibrils under the window: hexagonal grid at the reported myofibril diameter */
    const r0=myo/2*(em?0.85:1), pitch=myo*(em?1.22:1.08), cand=[];
    for(let iy=-Math.ceil(R/pitch);iy<=Math.ceil(R/pitch);iy++) for(let iz=-Math.ceil(R/pitch);iz<=Math.ceil(R/pitch);iz++){
      const y=iy*pitch*0.866, z=iz*pitch+(iy%2?pitch/2:0), r=Math.hypot(y,z), a=Math.atan2(y,z);
      if(r>R-1.6) continue;
      cand.push({y,z,key:(R-r)+Math.abs(a)*R*0.18});
    }
    cand.sort((p,q)=>p.key-q.key);
    const n=Math.min(cand.length,count?count.value:600), sel=cand.slice(0,n);
    const cyl=new THREE.CylinderGeometry(r0,r0,2*HALF-0.4,10,1); cyl.rotateZ(Math.PI/2);
    const fibrils=new THREE.InstancedMesh(cyl,bandMat,n); const m=new THREE.Matrix4();
    sel.forEach((p,i)=>{ m.makeTranslation(0,p.y,p.z); fibrils.setMatrixAt(i,m); });
    add(fibrils,{structure:'myofibril',params:['type_i_diameter'],derived:['myofibril_count_rendered'],statics:['myofibril_diameter','sarcomere_length','thick_filament_length'],illustrative:['l3_myofibril_count_pre']});
    /* triads at the two A–I junctions of each sarcomere, around the outer layer of myofibrils */
    const outer=sel.filter(p=>Math.hypot(p.y,p.z)>R-3).slice(0,32);
    const planes=[]; for(let k=Math.floor(-(WIN_X-2)/sl);k*sl<WIN_X-2;k++){ planes.push(k*sl+sl/2-thick/2,k*sl+sl/2+thick/2); }
    const torusT=new THREE.TorusGeometry(r0+0.1,0.05,3,8); torusT.rotateY(Math.PI/2);
    const torusC=new THREE.TorusGeometry(r0+0.14,0.07,3,8); torusC.rotateY(Math.PI/2);
    const nT=outer.length*planes.length;
    const tt=new THREE.InstancedMesh(torusT,tMat,nT), cc=new THREE.InstancedMesh(torusC,srMat,nT*2);
    let it=0, ic=0;
    planes.forEach(x=>outer.forEach(p=>{ m.makeTranslation(x,p.y,p.z); tt.setMatrixAt(it++,m);
      m.makeTranslation(x-0.11,p.y,p.z); cc.setMatrixAt(ic++,m); m.makeTranslation(x+0.11,p.y,p.z); cc.setMatrixAt(ic++,m); }));
    const triadPick={structure:'t_tubule',statics:['triads_per_sarcomere','sarcomere_length','thick_filament_length'],illustrative:['l3_myofibril_count_pre']};
    add(tt,triadPick); add(cc,{...triadPick,structure:'sarcoplasmic_reticulum'});
    /* myonuclei under the sarcolemma (illustrative number and spacing) */
    const rn=rng(3), nNuc=(illus(view,'l3_myonuclei')||{value:10}).value;
    const sph=new THREE.SphereGeometry(1,24,16);
    const nuclei=new THREE.InstancedMesh(sph,nucleusMat,nNuc); let nucFront=null;
    for(let i=0;i<nNuc;i++){ const a=(i/nNuc)*Math.PI*2+rn()*0.4, x=-HALF+3+rn()*(2*HALF-6);
      const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),-a);
      const at=new THREE.Vector3(x,(R-1.3)*Math.sin(a),(R-1.3)*Math.cos(a)); if(!nucFront||at.z>nucFront.z) nucFront=at;
      m.compose(at,q,new THREE.Vector3(5.5,1.2,2.6)); nuclei.setMatrixAt(i,m); }
    add(nuclei,{structure:'myonucleus',illustrative:['l3_myonuclei']});
    /* mitochondria: filamentous around the I band (preflight description), or the EM picture in
       crew with high atrophy (globular, invading the A band) */
    const rm=rng(9), nMito=(illus(view,'l3_mitochondria')||{value:140}).value;
    const mito=new THREE.InstancedMesh(em?new THREE.SphereGeometry(1,14,10):new THREE.CapsuleGeometry(0.28,1.6,4,8),mitoMat,nMito);
    for(let i=0;i<nMito;i++){
      const p=sel[Math.floor(rm()*Math.min(sel.length,120))]; if(!p) break;
      const k=Math.round((rm()*2*(WIN_X-3)-(WIN_X-3))/sl);
      if(em){ const x=k*sl+sl/2+(rm()-0.5)*thick*0.8, s=0.3+rm()*0.25;
        m.compose(new THREE.Vector3(x,p.y+pitch*0.5,p.z+pitch*0.3),new THREE.Quaternion(),new THREE.Vector3(s,s,s)); }
      else { const x=k*sl+(rm()-0.5)*0.4, a=rm()*Math.PI*2;
        const q=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),a);
        m.compose(new THREE.Vector3(x,p.y+Math.sin(a)*r0*1.5,p.z+Math.cos(a)*r0*1.5),q,new THREE.Vector3(1,1,1)); }
      mito.setMatrixAt(i,m);
    }
    /* subsarcolemmal clusters near the nuclei */
    add(mito,{structure:'mitochondria',illustrative:['l3_mitochondria'],findings:em?['em_high_atrophy']:['em_low_atrophy']});
    const sub=new THREE.InstancedMesh(new THREE.SphereGeometry(1,16,10),mitoMat,24);
    for(let i=0;i<24;i++){ const a=(rm()-0.5)*WIN_A*2.6, x=-HALF+4+rm()*(2*HALF-8);
      m.compose(new THREE.Vector3(x,(R-0.9)*Math.sin(a),(R-0.9)*Math.cos(a)),new THREE.Quaternion(),new THREE.Vector3(0.9,0.45,0.6)); sub.setMatrixAt(i,m); }
    add(sub,{structure:'mitochondria',label:'Subsarcolemmal mitochondria',illustrative:['l3_mitochondria']});
    if(em){ /* glycogen particles in the widened space between myofibrils */
      const g=[]; for(let i=0;i<1600;i++){ const p=sel[Math.floor(rm()*Math.min(sel.length,300))]; g.push(-WIN_X+rm()*2*WIN_X,p.y+pitch*0.5,p.z+pitch*0.29); }
      const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(g,3)); add(new THREE.Points(geo,glyMat));
    }
    /* preflight ghost: the preflight membrane radius as rings */
    if(opts.compare){
      const Rp=d.pre.value/2, v=[];
      [-HALF,-WIN_X,WIN_X,HALF].forEach(x=>{ for(let k=0;k<64;k++){ const a=k/64*Math.PI*2,b=(k+1)/64*Math.PI*2; v.push(x,Rp*Math.sin(a),Rp*Math.cos(a),x,Rp*Math.sin(b),Rp*Math.cos(b)); } });
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(v,3)); add(new THREE.LineSegments(g,ghostMat));
    }
    /* labels */
    labels.length=0;
    const front=sel[0]||{y:0,z:R-3};
    labels.push(
      {id:'sl',text:'Sarcolemma',at:new THREE.Vector3(-HALF+4,R*0.7,R*0.71),dx:-80,dy:-50,info:parts[0].userData.pick},
      {id:'mf',text:'Myofibril',sub:'striated',at:new THREE.Vector3(-6,front.y,front.z+r0),dx:-90,dy:40,info:fibrils.userData.pick},
      {id:'nuc',text:'Myonucleus',at:nucFront.clone(),dx:80,dy:-40,info:{structure:'myonucleus',illustrative:['l3_myonuclei']}},
      {id:'mito',text:'Mitochondria',sub:em?'globular (EM, high atrophy)':'',at:new THREE.Vector3(sl*2,front.y+r0*1.5,front.z+0.4),dx:90,dy:30,info:mito.userData.pick},
      {id:'triad',text:'Triad',sub:'T-tubule + SR at A–I junction',at:new THREE.Vector3(planes[Math.floor(planes.length/2)],outer[0]?outer[0].y:0,(outer[0]?outer[0].z:R-3)+r0),dx:70,dy:-70,info:triadPick},
      {id:'win',text:'Cutaway window',sub:'illustrative',at:new THREE.Vector3(WIN_X,R*Math.sin(WIN_A),R*Math.cos(WIN_A)),dx:60,dy:-30,info:{structure:'sarcolemma',label:'Cutaway window (drawing device)',illustrative:['l3_myofibril_count_pre']}}
    );
    ctx.relabel && ctx.relabel('L3');
  }

  function caption(view,opts){
    const d=param(view,'type_i_diameter'), c=derived(view,'myofibril_count_rendered');
    if(!d||!d.available) return 'Fibre data are not reported for this group.';
    const atEnd=view.day.status==='end_of_mission'||view.day.status==='recovery';
    return `Slow type I fibre, ${d.value.toFixed(1)} µm across (${d.value_type}; ${d.timepoint}). ${c?c.value:''} myofibrils drawn under the window (${c?c.value_type:''}).`
      +(opts.em?(atEnd?' EM option on: qualitative picture for crew with high atrophy (smaller myofibrils, globular mitochondria in the A band, glycogen between myofibrils), not a group mean.':' EM option: the qualitative landing-day picture appears at the end of the mission.'):'');
  }

  return {id:'L3',title:'Fibre',unitsToMetres:1e-6,scene,pickables,labels,update,caption,
    target:new THREE.Vector3(0,8,24),camDir:new THREE.Vector3(0.3,0.38,1).normalize(),
    minDist:9,maxDist:420,defaultDist:240};
}
