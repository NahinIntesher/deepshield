'use client';
import {useEffect,useRef,useState} from 'react';
import type {AnimationItem} from 'lottie-web';
import {useAppearance} from '@/lib/Appearance';

/** Local, authored animations only; an animation is never a model result. */
export function StatusMotion({kind='empty',size=104}:{kind?:'empty'|'loading'|'scan';size?:number}){
 const host=useRef<HTMLDivElement>(null),{theme}=useAppearance();
 const [ready,setReady]=useState(false);
 useEffect(()=>{
  const controller=new AbortController();let animation:AnimationItem|undefined;let disposed=false;
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  function applyMotion(){if(!animation)return;if(motion.matches)animation.goToAndStop(animation.totalFrames-1,true);else animation.goToAndPlay(0,true)}
  setReady(false);
  Promise.all([import('lottie-web'),fetch(`/motion/${kind}.json`,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error('Animation unavailable');return r.json()})]).then(([player,data])=>{
   if(disposed||!host.current)return;
   const color=theme==='dark'?[.69,.83,.71,1]:[.09,.31,.22,1];
   function recolor(value:any){if(!value||typeof value!=='object')return;if((value.ty==='st'||value.ty==='fl')&&value.c?.a===0)value.c.k=color;Object.values(value).forEach(v=>{if(typeof v==='object')recolor(v)})}
   recolor(data);
   animation=player.default.loadAnimation({container:host.current,renderer:'svg',loop:kind!=='empty',autoplay:false,animationData:data,rendererSettings:{preserveAspectRatio:'xMidYMid meet'}});
   animation.addEventListener('DOMLoaded',()=>{if(!disposed){setReady(true);applyMotion()}});
  }).catch(()=>{/* Text and retry actions remain available without artwork. */});
  motion.addEventListener('change',applyMotion);
  return()=>{disposed=true;controller.abort();motion.removeEventListener('change',applyMotion);animation?.destroy()};
 },[kind,theme]);
 return <div aria-hidden="true" className="status-motion" style={{width:size,height:size,margin:'0 auto 12px',position:'relative'}}><div ref={host} style={{width:'100%',height:'100%'}}/>{!ready&&<svg viewBox="0 0 64 64" style={{position:'absolute',inset:0,color:'var(--accent)',opacity:.4}}><circle cx="27" cy="27" r="15" fill="none" stroke="currentColor" strokeWidth="2"/><path d="m38 38 13 13" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/></svg>}</div>;
}
