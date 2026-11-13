/* Geometry and material helpers for the 3D Simulator. No scientific constants live here:
   every size that matters comes from the API; shapes and counts here are illustrative. */
import * as THREE from 'three';

/* Deterministic pseudo-random numbers, so illustrative layouts are the same on every load. */
export function rng(seed){
  let s=seed>>>0;
  return ()=>{ s=(s+0x6D2B79F5)>>>0; let t=s; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296; };
}

/* A closed body lofted along y from elliptical sections.
   section(t) -> {cx, cz, rx, rz} for t in [0,1] from y0 to y1; `scale` multiplies rx and rz
   (the transverse-only scaling used for atrophy). Vertex colours carry a cheap baked
   ambient-occlusion term: darker towards the deep (bone-facing) side and the attachments. */
export function loftY(y0,y1,section,{rings=72,radial=48,scale=1,ao=true,deepZ=-1}={}){
  const positions=[], colors=[], indices=[];
  const ring=(i)=>{
    const t=i/rings, y=y0+(y1-y0)*t, s=section(t);
    for(let j=0;j<radial;j++){
      const a=j/radial*Math.PI*2, x=s.cx+Math.cos(a)*s.rx*scale, z=s.cz+Math.sin(a)*s.rz*scale;
      positions.push(x,y,z);
      let shade=1;
      if(ao){
        const deep=Math.max(0,Math.sin(a)*deepZ);        /* faces towards the bones */
        const end=Math.min(1,Math.min(t,1-t)*8);          /* attachments */
        shade=0.62+0.38*(1-0.55*deep)*(0.7+0.3*end);
      }
      colors.push(shade,shade,shade);
    }
  };
  for(let i=0;i<=rings;i++) ring(i);
  for(let i=0;i<rings;i++) for(let j=0;j<radial;j++){
    const a=i*radial+j, b=i*radial+(j+1)%radial, c=(i+1)*radial+j, d=(i+1)*radial+(j+1)%radial;
    indices.push(a,c,b,b,c,d);
  }
  /* caps */
  const capStart=positions.length/3; const s0=section(0); positions.push(s0.cx,y0,s0.cz); colors.push(.6,.6,.6);
  const capEnd=positions.length/3; const s1=section(1); positions.push(s1.cx,y1,s1.cz); colors.push(.6,.6,.6);
  for(let j=0;j<radial;j++){ indices.push(capStart,j,(j+1)%radial); const o=rings*radial; indices.push(capEnd,o+(j+1)%radial,o+j); }
  const g=new THREE.BufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
  g.setAttribute('color',new THREE.Float32BufferAttribute(colors,3));
  g.setIndex(indices); g.computeVertexNormals();
  return g;
}

/* Volume of a loftY body, by summing elliptical slices (cm³ when lengths are in cm). */
export function loftVolume(y0,y1,section,scale=1,steps=400){
  let v=0; const dy=(y1-y0)/steps;
  for(let i=0;i<steps;i++){ const s=section((i+0.5)/steps); v+=Math.PI*s.rx*s.rz*scale*scale*Math.abs(dy); }
  return v;
}

/* Concatenate geometries (all must share attribute names). */
export function mergeGeometries(list){
  const names=Object.keys(list[0].attributes);
  const out=new THREE.BufferGeometry(); const index=[]; let offset=0;
  const data={}; names.forEach(n=>data[n]=[]);
  list.forEach(g=>{
    const geo=g;
    names.forEach(n=>data[n].push(...geo.attributes[n].array));
    if(geo.index){ for(const i of geo.index.array) index.push(i+offset); }
    else { for(let i=0;i<geo.attributes.position.count;i++) index.push(i+offset); }
    offset+=geo.attributes.position.count;
  });
  names.forEach(n=>out.setAttribute(n,new THREE.Float32BufferAttribute(data[n],list[0].attributes[n].itemSize)));
  out.setIndex(index);
  return out;
}

/* Diverging colour for a percent change: losses red/orange, gains blue, zero near white. */
export function changeColor(pct,limit=25){
  const stops=[[-1,[0.843,0.188,0.122]],[-0.5,[0.988,0.553,0.349]],[0,[0.969,0.969,0.969]],[0.5,[0.569,0.749,0.859]],[1,[0.271,0.459,0.706]]];
  const x=Math.max(-1,Math.min(1,(pct||0)/limit));
  for(let i=0;i<stops.length-1;i++){
    const [a,ca]=stops[i],[b,cb]=stops[i+1];
    if(x>=a && x<=b){ const t=(x-a)/(b-a); return new THREE.Color(ca[0]+(cb[0]-ca[0])*t,ca[1]+(cb[1]-ca[1])*t,ca[2]+(cb[2]-ca[2])*t); }
  }
  return new THREE.Color(1,1,1);
}

/* Sarcomere banding along the object-space x axis. Band positions are passed in from the
   API values (sarcomere length, thick-filament length); nothing is hard-coded here. */
export function bandMaterial(base,{period,aHalf,zHalf=0.05,mHalf=0.03}){
  const m=new THREE.MeshStandardMaterial({color:base,roughness:0.55,metalness:0});
  m.onBeforeCompile=(shader)=>{
    shader.uniforms.uPeriod={value:period}; shader.uniforms.uAHalf={value:aHalf};
    shader.uniforms.uZHalf={value:zHalf}; shader.uniforms.uMHalf={value:mHalf};
    m.userData.shader=shader;
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying float vBandX;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvBandX=position.x;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>',`#include <common>
varying float vBandX; uniform float uPeriod; uniform float uAHalf; uniform float uZHalf; uniform float uMHalf;`)
      .replace('#include <color_fragment>',`#include <color_fragment>
{ float p=mod(vBandX,uPeriod); float c=uPeriod*0.5; float d=abs(p-c);
  float band=1.0;
  if(d<uAHalf) band=0.62;            /* A band: dense, darker */
  if(d<uMHalf) band=0.45;            /* M line */
  float dz=min(p,uPeriod-p);
  if(dz<uZHalf) band=0.35;           /* Z disc */
  diffuseColor.rgb*=band; }`);
  };
  return m;
}

/* Faint stripes across mitochondria to suggest cristae (illustrative). */
export function cristaeMaterial(color){
  const m=new THREE.MeshPhysicalMaterial({color,roughness:0.45,clearcoat:0.4,clearcoatRoughness:0.4});
  m.onBeforeCompile=(shader)=>{
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nvarying vec3 vObj;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvObj=position;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nvarying vec3 vObj;')
      .replace('#include <color_fragment>','#include <color_fragment>\n{ float s=0.5+0.5*sin(vObj.x*38.0); diffuseColor.rgb*=0.78+0.22*s; }');
  };
  return m;
}

/* Sutherland–Hodgman clip of a polygon by a convex polygon (both arrays of [x,y], CCW). */
export function clipPolygon(subject,clip){
  let output=subject;
  for(let i=0;i<clip.length;i++){
    const a=clip[i], b=clip[(i+1)%clip.length], input=output; output=[];
    const inside=p=>(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])>=0;
    const cross=(p,q)=>{ const x1=p[0],y1=p[1],x2=q[0],y2=q[1],x3=a[0],y3=a[1],x4=b[0],y4=b[1];
      const den=(x1-x2)*(y3-y4)-(y1-y2)*(x3-x4); const t=((x1-x3)*(y3-y4)-(y1-y3)*(x3-x4))/den; return [x1+t*(x2-x1),y1+t*(y2-y1)]; };
    for(let j=0;j<input.length;j++){
      const p=input[j], q=input[(j+1)%input.length];
      if(inside(q)){ if(!inside(p)) output.push(cross(p,q)); output.push(q); }
      else if(inside(p)) output.push(cross(p,q));
    }
    if(!output.length) break;
  }
  return output;
}

/* Voronoi cells of `points` inside a convex `boundary`, by half-plane clipping (n is small). */
export function voronoiCells(points,boundary){
  return points.map((p,i)=>{
    let cell=boundary.slice();
    points.forEach((q,j)=>{
      if(i===j || !cell.length) return;
      const mx=(p[0]+q[0])/2, my=(p[1]+q[1])/2, dx=q[0]-p[0], dy=q[1]-p[1];
      if(dx*dx+dy*dy>4*maxR2(cell,p)) return;              /* too far to matter */
      const big=1e4, nx=-dy, ny=dx;                          /* bisector direction */
      const half=[[mx+nx*big,my+ny*big],[mx-nx*big,my-ny*big],[mx-nx*big-dx*big,my-ny*big-dy*big],[mx+nx*big-dx*big,my+ny*big-dy*big]];
      cell=clipPolygon(cell,orient(half));
    });
    return cell;
  });
}
function maxR2(cell,p){ let m=0; cell.forEach(c=>{ const d=(c[0]-p[0])**2+(c[1]-p[1])**2; if(d>m) m=d; }); return m; }
export function orient(poly){ let a=0; for(let i=0;i<poly.length;i++){ const p=poly[i],q=poly[(i+1)%poly.length]; a+=p[0]*q[1]-q[0]*p[1]; } return a<0?poly.slice().reverse():poly; }
export function polygonArea(poly){ let a=0; for(let i=0;i<poly.length;i++){ const p=poly[i],q=poly[(i+1)%poly.length]; a+=p[0]*q[1]-q[0]*p[1]; } return Math.abs(a)/2; }
export function centroid(poly){ let x=0,y=0; poly.forEach(p=>{x+=p[0];y+=p[1];}); return [x/poly.length,y/poly.length]; }
export function insidePolygon(pt,poly){
  let c=false; for(let i=0,j=poly.length-1;i<poly.length;j=i++){ const a=poly[i],b=poly[j];
    if(((a[1]>pt[1])!==(b[1]>pt[1])) && (pt[0]<(b[0]-a[0])*(pt[1]-a[1])/(b[1]-a[1])+a[0])) c=!c; }
  return c;
}

/* Value lookups in the API payload. */
export function param(view,id){ return view && view.parameters.find(p=>p.id===id); }
export function derived(view,id){ return view && view.derived.find(p=>p.id===id); }
export function stat(view,id){ return view && view.static.find(p=>p.id===id); }
export function illus(view,id){ return view && view.illustrative.find(p=>p.id===id); }
