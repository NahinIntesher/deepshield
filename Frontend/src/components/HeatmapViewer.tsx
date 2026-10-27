'use client';
import {useEffect,useRef,useState} from 'react';
import {Expand,Minus,Plus,X} from 'lucide-react';
import {useLocale} from '@/lib/Locale';

export default function HeatmapViewer({image,overlay}:{image:string;overlay:string}){
 const {t}=useLocale(),canvas=useRef<HTMLCanvasElement>(null),dialog=useRef<HTMLDialogElement>(null),trigger=useRef<HTMLButtonElement>(null),wasExpanded=useRef(false);
 const [mode,setMode]=useState<'overlay'|'map'>('overlay'),[enhanced,setEnhanced]=useState(false),[opacity,setOpacity]=useState(85),[zoom,setZoom]=useState(1),[expanded,setExpanded]=useState(false),[error,setError]=useState(false);
 useEffect(()=>{
  let active=true;setError(false);
  const layer=new Image();
  layer.onload=()=>{
   if(!active||!canvas.current)return;
   const target=canvas.current;target.width=layer.naturalWidth;target.height=layer.naturalHeight;
   const context=target.getContext('2d');if(!context){setError(true);return}
   context.drawImage(layer,0,0);const pixels=context.getImageData(0,0,target.width,target.height);
   const recordedAlpha=[];for(let i=3;i<pixels.data.length;i+=4)recordedAlpha.push(pixels.data[i]);
   recordedAlpha.sort((a,b)=>a-b);
   const scale=enhanced?Math.max(1,recordedAlpha[Math.floor((recordedAlpha.length-1)*.98)]):220;
   for(let i=0;i<pixels.data.length;i+=4){
    const raw=pixels.data[i+3]/scale;
    if(!raw){pixels.data[i+3]=0;continue}
    const value=Math.min(1,enhanced?Math.sqrt(raw):raw);
    // A monotonic display mapping makes the existing gradient values easier to inspect.
    const low=[32,112,180],mid=[255,199,46],high=[235,49,29],from=value<.5?low:mid,to=value<.5?mid:high,fraction=value<.5?value*2:(value-.5)*2;
    for(let c=0;c<3;c++)pixels.data[i+c]=Math.round(from[c]+(to[c]-from[c])*fraction);
    pixels.data[i+3]=mode==='map'?255:Math.round(value*255);
   }
   context.putImageData(pixels,0,0);
  };
  layer.onerror=()=>active&&setError(true);layer.src=overlay;
  return()=>{active=false};
 },[overlay,enhanced,mode,expanded]);
 useEffect(()=>{setZoom(1)},[image]);
 useEffect(()=>{if(!expanded){if(wasExpanded.current)trigger.current?.focus();return}wasExpanded.current=true;const modal=dialog.current;modal?.showModal();return()=>{modal?.close()}},[expanded]);
 const viewer=<>
  <div className="heatmap-toolbar"><div className="auth-tabs" role="tablist" aria-label={t('Heatmap view','Heatmap ভিউ')}><button role="tab" aria-selected={mode==='overlay'} className={mode==='overlay'?'selected':''} onClick={()=>setMode('overlay')}>{t('Face + heatmap','মুখের ওপর heatmap')}</button><button role="tab" aria-selected={mode==='map'} className={mode==='map'?'selected':''} onClick={()=>setMode('map')}>{t('Heatmap only','শুধু heatmap')}</button></div><label className="heatmap-enhance"><input type="checkbox" checked={enhanced} onChange={e=>setEnhanced(e.target.checked)}/>{t('Boost display contrast','দেখার সুবিধায় রং গাঢ় করুন')}</label></div>
  <div className="heatmap-compare"><figure><div className="heatmap-viewport" tabIndex={0} aria-label={t('Original face, scroll when zoomed','মূল মুখ; zoom করলে scroll করুন')}><div className="heatmap-image-plane" style={{width:`${zoom*100}%`}}><img src={image} alt={t('Original face crop','মূল face crop')} draggable={false}/></div></div><figcaption><strong>{t('Original face','মূল মুখ')}</strong><span>{t('Unchanged model input','মডেলে দেওয়া একই ছবি')}</span></figcaption></figure><figure><div className="heatmap-viewport" tabIndex={0} aria-label={t('Heatmap, scroll when zoomed','Heatmap; zoom করলে scroll করুন')}><div className="heatmap-image-plane" style={{width:`${zoom*100}%`}}>{mode==='overlay'&&<img src={image} alt="" draggable={false}/>}<canvas ref={canvas} role="img" aria-label={t('Relative input sensitivity heatmap','মডেলের sensitivity heatmap')} style={{position:mode==='overlay'?'absolute':'relative',opacity:mode==='overlay'?opacity/100:1}}/></div></div><figcaption><strong>{mode==='map'?t('Sensitivity map','Sensitivity map'):t('Face with heatmap','Heatmap-সহ মুখ')}</strong><span>{t('Warmer colours = stronger sensitivity','হলুদ ও লাল অংশে sensitivity বেশি')}</span></figcaption></figure></div>
  {error&&<p className="error-box" role="alert">{t('Could not load this heatmap. Select another frame.','Heatmap লোড হয়নি। অন্য ফ্রেম বেছে নিন।')}</p>}
  <div className="heatmap-display-controls"><div><div className="heatmap-colour-key" aria-hidden="true">{['#2070b4','#6ba4bd','#ffc72e','#f58228','#eb311d'].map(colour=><i key={colour} style={{background:colour}}/>)}</div><div className="heatmap-scale-labels"><span>{t('Lower sensitivity','Sensitivity কম')}</span><span>{t('Higher sensitivity','Sensitivity বেশি')}</span></div></div><label>{t('Overlay strength','রঙের দৃশ্যমানতা')} · {opacity}%<input type="range" min={10} max={100} value={opacity} disabled={mode==='map'} onChange={e=>setOpacity(Number(e.target.value))}/></label></div>
  <div className="heatmap-zoom-controls"><button className="icon-button" disabled={zoom<=1} onClick={()=>setZoom(v=>Math.max(1,v-.5))} aria-label={t('Zoom out','Zoom কমান')}><Minus size={18}/></button><span>{Math.round(zoom*100)}%</span><button className="icon-button" disabled={zoom>=3} onClick={()=>setZoom(v=>Math.min(3,v+.5))} aria-label={t('Zoom in','Zoom বাড়ান')}><Plus size={18}/></button><button className="text-link" onClick={()=>setZoom(1)}>{t('Reset zoom','Zoom রিসেট')}</button>{!expanded&&<button ref={trigger} className="secondary-button heatmap-expand" onClick={()=>setExpanded(true)}><Expand size={17}/>{t('Enlarge','বড় করে দেখুন')}</button>}</div>
  <p className="muted text-sm heatmap-reading-note">{t('Colours compare sensitivity within this frame. Enhanced visibility changes only the display, not the prediction. Highlighted areas are not proof of an edit.','এই ফ্রেমের কোন অংশে মডেল বেশি sensitive তা রঙে দেখানো হয়েছে। স্পষ্টতার সেটিং শুধু দেখানোর ধরন বদলায়, ফলাফল বদলায় না। রঙিন অংশ মানেই সেখানে edit করা হয়েছে—এমন নয়।')}</p>
 </>;
 return expanded?<dialog ref={dialog} className="heatmap-dialog" onCancel={()=>setExpanded(false)} onClose={()=>setExpanded(false)}><div className="heatmap-dialog-heading"><h2>{t('Inspect the heatmap','Heatmap বিস্তারিত দেখুন')}</h2><button className="icon-button" autoFocus onClick={()=>setExpanded(false)} aria-label={t('Close heatmap','Heatmap বন্ধ করুন')}><X size={21}/></button></div>{viewer}</dialog>:<div className="heatmap-viewer">{viewer}</div>;
}
