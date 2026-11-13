/* Leader-line labels: a small circle on the structure, a thin white line and the text.
   Built with DOM methods only (textContent), so no server text is parsed as markup. */
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const SVG='http://www.w3.org/2000/svg';

export function makeLabel({text,sub,dx=60,dy=-30,onPick}){
  const root=document.createElement('div'); root.className='sim-label'; root.tabIndex=0;
  root.setAttribute('role','button');
  root.setAttribute('aria-label',text+(sub?' ('+sub+')':'')+': show details');
  const dot=document.createElement('span'); dot.className='dot';
  const svg=document.createElementNS(SVG,'svg'); svg.setAttribute('width','1'); svg.setAttribute('height','1');
  const line=document.createElementNS(SVG,'line');
  line.setAttribute('x1','0'); line.setAttribute('y1','0'); line.setAttribute('x2',String(dx)); line.setAttribute('y2',String(dy));
  line.setAttribute('stroke','white'); line.setAttribute('stroke-width','1');
  svg.append(line);
  const box=document.createElement('span'); box.className='text'; box.textContent=text;
  if(sub){ const em=document.createElement('em'); em.textContent=' '+sub; box.append(em); }
  box.style.left=(dx>=0?dx+2:dx-2)+'px'; box.style.top=(dy-9)+'px';
  if(dx<0) box.style.transform='translateX(-100%)';
  root.append(svg,dot,box);
  const fire=(event)=>{ event.stopPropagation(); if(onPick) onPick(); };
  root.addEventListener('click',fire);
  root.addEventListener('keydown',event=>{ if(event.key==='Enter'||event.key===' '){ event.preventDefault(); fire(event); } });
  root.addEventListener('pointerdown',event=>event.stopPropagation());
  const object=new CSS2DObject(root);
  object.center.set(0,0);
  return object;
}
