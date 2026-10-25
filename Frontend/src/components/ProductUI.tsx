'use client';
import {T} from '@/components/LocalizedText';

import {useCallback,useEffect,useRef,useState} from 'react';import {request} from '@/lib/product';
export function useData(path:string,interval=0){const [data,setData]=useState<any>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);const generation=useRef(0);const reload=useCallback(async()=>{const run=++generation.current;setLoading(true);try{const next=await request(path);if(run===generation.current){setData(next);setError('')}}catch(e){if(run===generation.current)setError((e as Error).message)}finally{if(run===generation.current)setLoading(false)}},[path]);useEffect(()=>{setData(null);void reload();const id=interval?setInterval(reload,interval):undefined;return()=>{generation.current++;if(id)clearInterval(id)}},[reload,interval]);return {data,error,setError,reload,setData,loading}}
export function Heading({eyebrow,title,subtitle,action}:{eyebrow:string;title:string;subtitle:string;action?:React.ReactNode}){return <div className="page-heading"><div>{eyebrow&&<span className="eyebrow"><T>{eyebrow}</T></span>}<h1><T>{title}</T></h1>{subtitle&&<p><T>{subtitle}</T></p>}</div>{action}</div>}
export function ErrorBox({text}:{text:string}){return text?<p className="error-box" role="alert"><T>{text}</T></p>:null}
export function Empty({title,text}:{title:string;text:string}){return <div className="product-empty"><h3><T>{title}</T></h3><p><T>{text}</T></p></div>}
