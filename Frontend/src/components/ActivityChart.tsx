"use client";
import {useEffect,useRef,useState} from 'react';
import {ResponsiveTable} from '@/components/ResponsiveTable';

import {useLocale} from '@/lib/Locale';

import {T} from '@/components/LocalizedText';

export function ActivityChart({rows}:{rows:any[]}){
 const {t}=useLocale(),plot=useRef<HTMLDivElement>(null),[width,setWidth]=useState(700);
 useEffect(()=>{const node=plot.current;if(!node)return;const observer=new ResizeObserver(([entry])=>setWidth(Math.max(180,Math.floor(entry.contentRect.width))));observer.observe(node);return()=>observer.disconnect()},[]);
 const max=Math.max(1,...rows.map(r=>r.rounds+r.detections+r.research)),step=width/Math.max(rows.length,1),ticks=Math.max(1,Math.ceil(rows.length/Math.max(2,Math.floor(width/75))));
 return <div><div className="chart-legend"><span><T text="● Game rounds" /></span><span><T text="● AI detections" /></span><span><T text="● Research answers" /></span></div>
 <div ref={plot} className="activity-chart activity-chart-fit"><svg width="100%" height="205" viewBox={`0 0 ${width} 205`} role="img" aria-label={t('Daily recorded activity, UTC. Exact values are in the table below.')}>
 {rows.map((r,index)=>{let bottom=170;const tick=index===0||index===rows.length-1||(index%ticks===0&&index<rows.length-2);return <g key={r.date}><title>{`${r.date}: ${r.rounds} ${t('Rounds')}, ${r.detections} ${t('Detections')}, ${r.research} ${t('Research answers')}`}</title>{['rounds','detections','research'].map((key,i)=>{const height=r[key]/max*150;bottom-=height;return <rect key={key} x={index*step+Math.min(3,step/5)} y={bottom} width={Math.max(1,step-Math.min(6,step/2.5))} height={height} rx="2" fill={['#14875e','#73ba92','#ccaa65'][i]}/>})}{tick&&<text x={index===0?0:index===rows.length-1?width:(index+.5)*step} y="194" textAnchor={index===0?'start':index===rows.length-1?'end':'middle'} fill="var(--muted)" fontSize="12">{r.date.slice(5)}</text>}</g>})}
 <line x1="0" x2={width} y1="171" y2="171" stroke="var(--line)"/>
 </svg></div><details className="mt-4"><summary className="muted text-sm cursor-pointer"><T text="View exact daily counts" /></summary><ResponsiveTable className="table-wrap" tabIndex={0} role="region" aria-label={t('Data table','ডেটা টেবিল')}><table className="admin-table"><thead><tr><th><T text="Date · UTC" /></th><th><T text="Rounds" /></th><th><T text="Detections" /></th><th><T text="Research" /></th></tr></thead><tbody>{rows.map(r=><tr key={r.date}><td>{r.date}</td><td>{r.rounds}</td><td>{r.detections}</td><td>{r.research}</td></tr>)}</tbody></table></ResponsiveTable></details></div>
}
export function Bars({rows}:{rows:{label:string,value:number}[]}){const max=Math.max(1,...rows.map(r=>r.value));return <div className="metric-bars">{rows.map(r=><div key={r.label}><div className="flex justify-between text-sm"><span><T>{r.label}</T></span><strong>{r.value}</strong></div><div className="bar-track"><div style={{width:`${r.value/max*100}%`}}/></div></div>)}</div>}
