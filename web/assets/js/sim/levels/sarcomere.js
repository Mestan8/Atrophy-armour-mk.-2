/* L4 · One sarcomere (units: nm), longitudinal view, plus a cross-section of the filament lattice
   near the M line, where Fitts et al. counted filaments.
   Data-driven: sarcomere length used by Fitts (2.5 µm), thick-filament length (Szikora 2022), the
   longest thin filaments (~1.27 µm, Fitts; unit corrected, approximation), the share of thin
   filaments long enough to reach the near-M region (calculated from the reported densities), the
   thin:thick ratio in the lattice (reported) and the lattice spacing (calculated from the reported
   thick-filament density). Illustrative: filament thickness, myosin-head spacing, which filaments
   are long, and positions of thin filaments beyond the trigonal sites.
   Not interpolated: these values exist only before flight and on landing day. */
import * as THREE from 'three';
import { rng, param, derived, stat, changeColor } from '../util.js';

const ROWS=7, LAYERS=3, LATTICE_SCALE=4;

export function createSarcomere(ctx){
  const scene=new THREE.Scene();
  const root=new THREE.Group(); scene.add(root);
  const pickables=[], labels=[];
  const thickMat=new THREE.MeshStandardMaterial({color:0xc9353f,roughness:0.45});
  const headMat=new THREE.MeshStandardMaterial({color:0xe0606a,roughness:0.5});
  const thinMat=new THREE.MeshStandardMaterial({color:0x3b8fd9,roughness:0.4});
  const extMat=new THREE.MeshStandardMaterial({color:0xff7a2a,roughness:0.4,emissive:0x401000});
  const zMat=new THREE.MeshStandardMaterial({color:0xf0f0f0,roughness:0.4,transparent:true,opacity:0.85});
  const mMat=new THREE.MeshStandardMaterial({color:0xffffff,roughness:0.4,transparent:true,opacity:0.35});
  const titinMat=new THREE.LineBasicMaterial({color:0xf3d36b,transparent:true,opacity:0.8});
  const zoneMat=new THREE.MeshBasicMaterial({color:0x46e0d0,transparent:true,opacity:0.12,depthWrite:false});
  const bandMatI=new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:0.05,depthWrite:false});
  const bandMatA=new THREE.MeshBasicMaterial({color:0x000000,transparent:true,opacity:0.12,depthWrite:false});
  const ghostMat=new THREE.LineDashedMaterial({color:0xffffff,dashSize:20,gapSize:14,transparent:true,opacity:0.7});
  let parts=[];
  const clear=()=>{ parts.forEach(o=>{ root.remove(o); o.geometry&&o.geometry.dispose(); const i=pickables.indexOf(o); if(i>=0) pickables.splice(i,1); }); parts=[]; };
  const add=(o,pick,parent=root)=>{ parent.add(o); parts.push(o); if(pick){ o.userData.pick=pick; pickables.push(o); } return o; };

  function thinLengths(sites,reach,maxLen,half){
    /* each site gets a fixed random key; keys below `reach` are long enough to reach the near-M zone */
    return sites.map((_,i)=>{ const r=rng(1000+i), key=r(), jitter=r();
      if(reach===null) return {key,len:half*0.5+jitter*half*0.42,long:false};
      return key<reach ? {key,len:half-100+jitter*(maxLen-(half-100)),long:true} : {key,len:300+jitter*(half-100-300-40),long:false}; });
  }

  function update(view,opts){
    if(!view) return;
    clear();
    const SL=stat(view,'sarcomere_length').value*1000, TL=stat(view,'thick_filament_length').value*1000;
    const maxThin=stat(view,'thin_filament_max_length').value*1000, a=derived(view,'thick_lattice_spacing').value;
    const half=SL/2, M=half, aI=M-TL/2, aI2=M+TL/2;
    const thin=param(view,'thin_filament_density'), ratio=param(view,'thin_thick_ratio');
    const reachD=derived(view,'thin_reach_fraction');
    const available=thin && thin.available && reachD;
    const atEnd=view.day.status==='end_of_mission'||view.day.status==='recovery';
    const reachPre=available? reachD.pre_value : null;
    const reachNow=available? reachD.value : null;
    const H=(ROWS-1)*a;
    /* bands, near-M sampling zones, Z discs and M line */
    const plane=(x0,x1,mat,z=-a*1.6)=>{ const p=new THREE.Mesh(new THREE.PlaneGeometry(x1-x0,H+a*1.6),mat); p.position.set((x0+x1)/2,H/2,z); return p; };
    add(plane(0,aI,bandMatI),{structure:'i_band',statics:['sarcomere_length','thick_filament_length']});
    add(plane(aI2,SL,bandMatI),{structure:'i_band',statics:['sarcomere_length','thick_filament_length']});
    add(plane(aI,aI2,bandMatA),{structure:'a_band',statics:['thick_filament_length']});
    [[M-300,M-100],[M+100,M+300]].forEach(([x0,x1])=>add(plane(x0,x1,zoneMat,a*1.7),{structure:'near_m',label:'Near-M region (where thin filaments were counted)',params:['thin_filament_density','thin_thick_ratio']}));
    [0,SL].forEach(x=>{ const z=new THREE.Mesh(new THREE.BoxGeometry(22,H+a*1.4,a*(LAYERS+0.4)),zMat); z.position.set(x,H/2,0); add(z,{structure:'z_disc',params:['thin_filament_density'],statics:['z_band_thin_density_max']}); });
    const mLine=new THREE.Mesh(new THREE.BoxGeometry(12,H+a*1.2,a*(LAYERS+0.2)),mMat); mLine.position.set(M,H/2,0); add(mLine,{structure:'m_line'});
    /* thick filaments with myosin heads (head spacing and bare zone width illustrative) */
    const thickGeo=new THREE.CylinderGeometry(7,7,TL,10,1); thickGeo.rotateZ(Math.PI/2);
    const sites=[], thickPos=[];
    for(let r=0;r<ROWS;r++) for(let l=0;l<LAYERS;l++){ const y=r*a, z=(l-(LAYERS-1)/2)*a*0.866; thickPos.push([y,z]); }
    const thick=new THREE.InstancedMesh(thickGeo,thickMat,thickPos.length); const m=new THREE.Matrix4();
    thickPos.forEach(([y,z],i)=>{ m.makeTranslation(M,y,z); thick.setMatrixAt(i,m); });
    add(thick,{structure:'thick_filament',params:['thick_filament_density'],statics:['thick_filament_length']});
    const headsPer=Math.floor((TL/2-80)/43), heads=new THREE.InstancedMesh(new THREE.SphereGeometry(4.2,8,6),headMat,thickPos.length*headsPer*2);
    let h=0; thickPos.forEach(([y,z])=>{ for(let k=0;k<headsPer;k++) for(const sgn of [-1,1]){ const x=M+sgn*(80+k*43), ang=k*2.1;
      m.makeTranslation(x,y+Math.sin(ang)*9,z+Math.cos(ang)*9); heads.setMatrixAt(h++,m); } });
    add(heads,{structure:'thick_filament',params:['thick_filament_density'],statics:['thick_filament_length']});
    /* thin filaments at the sites between thick filaments, from both Z discs */
    for(let r=0;r<ROWS-1;r++) for(let l=0;l<LAYERS;l++){ const z=(l-(LAYERS-1)/2)*a*0.866; sites.push([(r+0.5)*a,z]); }
    const shown=atEnd?reachNow:reachPre;
    const lens=thinLengths(sites.concat(sites),shown,maxThin,half);
    const preLens=thinLengths(sites.concat(sites),reachPre,maxThin,half);
    const thinGeo=new THREE.CylinderGeometry(3.4,3.4,1,6,1); thinGeo.rotateZ(Math.PI/2); thinGeo.translate(0.5,0,0);
    const thinMesh=new THREE.InstancedMesh(thinGeo,thinMat,lens.length), extMesh=new THREE.InstancedMesh(thinGeo,extMat,lens.length);
    const q=new THREE.Quaternion(), flip=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,0,1),Math.PI);
    let ne=0;
    lens.forEach((t,i)=>{ const [y,z]=sites[i%sites.length], left=i<sites.length, x0=left?0:SL, rot=left?q:flip;
      const base=atEnd && available && preLens[i].len<t.len ? preLens[i].len : t.len;
      m.compose(new THREE.Vector3(x0,y,z),rot,new THREE.Vector3(base,1,1)); thinMesh.setMatrixAt(i,m);
      if(base<t.len){ m.compose(new THREE.Vector3(left?x0+base:x0-base,y,z),rot,new THREE.Vector3(t.len-base,1,1)); extMesh.setMatrixAt(ne++,m); } });
    extMesh.count=ne;
    const thinPick={structure:'thin_filament',params:['thin_filament_density','thin_thick_ratio'],derived:['thin_reach_fraction'],statics:['thin_filament_max_length','z_band_thin_density_max'],illustrative:['l4_thin_length_mix']};
    if(!available){ thinMat.color.set(0x8a99a8); } else if(opts.overlay){ thinMat.color.copy(changeColor(thin.percent_change)); } else thinMat.color.set(0x3b8fd9);
    add(thinMesh,thinPick); if(ne) add(extMesh,{...thinPick,label:'Added thin-filament length after flight (Fitts Fig. 16 concept)'});
    /* titin, schematic: Z disc to the thick-filament tip, then along it to the M line */
    const tv=[]; thickPos.forEach(([y,z])=>{ const o=10; tv.push(0,y+o,z,aI,y+o,z, aI,y+o,z,M,y+o,z, SL,y+o,z,aI2,y+o,z, aI2,y+o,z,M,y+o,z); });
    const tg=new THREE.BufferGeometry(); tg.setAttribute('position',new THREE.Float32BufferAttribute(tv,3)); add(new THREE.LineSegments(tg,titinMat),{structure:'titin'});
    /* compare: preflight thin-filament ends as dashed ghosts */
    if(opts.compare && atEnd && available){
      const gv=[]; preLens.forEach((t,i)=>{ const [y,z]=sites[i%sites.length], left=i<sites.length; const x=left?t.len:SL-t.len; gv.push(x,y-6,z,x,y+6,z); });
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(gv,3)); const ls=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0xffffff})); add(ls);
    }
    /* lattice cross-section near the M line (drawn ×4 beside the sarcomere) */
    const lat=new THREE.Group(); lat.position.set(SL+700,H/2,0); lat.scale.setScalar(LATTICE_SCALE); add(lat);
    const hex=[]; for(let i=-3;i<=3;i++) for(let j=-3;j<=3;j++){ if(Math.abs(i+j)<=3) hex.push([(i+j/2)*a,j*a*Math.sqrt(3)/2]); }   /* 37 sites */
    const ratioValue=ratio&&ratio.available?(atEnd?ratio.end.value:ratio.pre.value):null;
    const tri=[], mids=[];
    hex.forEach((p,i)=>hex.forEach((q2,j)=>{ if(j<=i) return; const d=Math.hypot(p[0]-q2[0],p[1]-q2[1]); if(Math.abs(d-a)<1e-6*a+0.5){
      mids.push([(p[0]+q2[0])/2,(p[1]+q2[1])/2]);
      hex.forEach((s,k)=>{ if(k<=j) return; if(Math.abs(Math.hypot(p[0]-s[0],p[1]-s[1])-a)<0.5 && Math.abs(Math.hypot(q2[0]-s[0],q2[1]-s[1])-a)<0.5) tri.push([(p[0]+q2[0]+s[0])/3,(p[1]+q2[1]+s[1])/3]); }); } }));
    const nThin=Math.round((ratioValue===null?2:ratioValue)*hex.length);
    const ordered=tri.map((p,i)=>({p,k:rng(500+i)()})).sort((u,v)=>u.k-v.k).map(o=>o.p)
      .concat(mids.map((p,i)=>({p,k:rng(900+i)()})).sort((u,v)=>u.k-v.k).map(o=>o.p));
    const disc=(r)=>new THREE.CircleGeometry(r,14);
    const latThick=new THREE.InstancedMesh(disc(7),thickMat,hex.length); hex.forEach(([x,y],i)=>{ m.makeTranslation(x,y,0); latThick.setMatrixAt(i,m); });
    const latThin=new THREE.InstancedMesh(disc(3.4),thinMat,nThin); ordered.slice(0,nThin).forEach(([x,y],i)=>{ m.makeTranslation(x,y,0.5); latThin.setMatrixAt(i,m); });
    latThin.count=Math.min(nThin,ordered.length);
    const latBg=new THREE.Mesh(new THREE.CircleGeometry(3.6*a,48),new THREE.MeshBasicMaterial({color:0x0b2f30,transparent:true,opacity:0.7})); latBg.position.z=-0.5;
    const latPick={structure:'lattice',label:'Filament lattice near the M line (cross-section)',params:['thin_thick_ratio','thin_filament_density','thick_filament_density'],derived:['thick_lattice_spacing'],statics:['thick_filament_spacing'],illustrative:['l4_lattice_size']};
    add(latBg,latPick,lat); add(latThick,latPick,lat); add(latThin,latPick,lat);
    /* labels */
    labels.length=0;
    const top=H+a*0.8;
    labels.push(
      {id:'z',text:'Z-disc',at:new THREE.Vector3(0,top,0),dx:-40,dy:-50,info:{structure:'z_disc',params:['thin_filament_density'],statics:['z_band_thin_density_max']}},
      {id:'i',text:'I-band',at:new THREE.Vector3(aI*0.5,-a*0.6,0),dx:-90,dy:45,info:{structure:'i_band',statics:['sarcomere_length','thick_filament_length']}},
      {id:'a',text:'A-band',at:new THREE.Vector3(aI+TL*0.2,-a*0.6,0),dx:30,dy:60,info:{structure:'a_band',statics:['thick_filament_length']}},
      {id:'m',text:'M-line / H-zone',at:new THREE.Vector3(M,top,0),dx:30,dy:-60,info:{structure:'m_line'}},
      {id:'nearm',text:'Near-M region',sub:'counted here',at:new THREE.Vector3(M+200,top*0.6,a*1.7),dx:90,dy:-40,info:{structure:'near_m',label:'Near-M region (100–300 nm from the M line)',params:['thin_filament_density','thin_thick_ratio']}},
      {id:'thick',text:'Thick filament',sub:'myosin',at:new THREE.Vector3(M-TL*0.3,thickPos[ROWS*LAYERS-2][0],thickPos[ROWS*LAYERS-2][1]),dx:-60,dy:-70,info:{structure:'thick_filament',params:['thick_filament_density'],statics:['thick_filament_length']}},
      {id:'thin',text:'Thin filament',sub:'actin',at:new THREE.Vector3(aI*0.6,sites[sites.length-1][0],sites[sites.length-1][1]),dx:-30,dy:95,info:thinPick},
      {id:'titin',text:'Titin',sub:'schematic',at:new THREE.Vector3(aI2+(SL-aI2)*0.5,thickPos[0][0]+10,thickPos[0][1]),dx:60,dy:60,info:{structure:'titin'}},
      {id:'lat',text:'Lattice near M',sub:`cross-section, ×${LATTICE_SCALE}`,at:new THREE.Vector3(SL+700,H/2+3.6*a*LATTICE_SCALE,0),dx:-150,dy:-40,info:latPick}
    );
    if(ne) labels.push({id:'ext',text:'Added length',sub:'after flight',at:new THREE.Vector3(half-60,sites[1][0],sites[1][1]),dx:60,dy:80,info:{...thinPick,label:'Added thin-filament length after flight (Fitts Fig. 16 concept)'}});
    ctx.relabel && ctx.relabel('L4');
  }

  function banner(view){
    const thin=param(view,'thin_filament_density');
    if(!thin || !thin.available) return 'Electron-microscopy values are reported for all crew only. The filaments are drawn in grey with illustrative lengths; switch to “All crew” to see the data.';
    if(view.day.status==='interpolated') return 'Between launch and landing this level is not modelled: filaments were counted only before flight and on landing day, and after a 17-day flight the change went the other way. The preflight lattice is shown.';
    if(view.day.phase==='recovery') return 'Not measured at R+19: the landing-day (R+0) lattice is shown.';
    return null;
  }

  function caption(view){
    const thin=param(view,'thin_filament_density'), ratio=param(view,'thin_thick_ratio'), reach=derived(view,'thin_reach_fraction');
    if(!thin||!thin.available) return 'Sarcomere at 2.5 µm (the length at which Fitts et al. measured). No subgroup data for this level.';
    return `Sarcomere at 2.5 µm. Near the M line: ${thin.value.toFixed(0)} thin filaments µm⁻² (${thin.value_type}; ${thin.timepoint}), thin:thick ${ratio.value.toFixed(1)}; ${(reach.value*100).toFixed(0)} % of thin filaments are long enough to reach the near-M region (${reach.value_type}). Orange: added length after flight.`;
  }

  return {id:'L4',title:'Sarcomere',unitsToMetres:1e-9,scene,pickables,labels,update,caption,banner,
    target:new THREE.Vector3(1850,100,0),camDir:new THREE.Vector3(0.12,0.18,1).normalize(),
    minDist:220,maxDist:6200,defaultDist:4600};
}
