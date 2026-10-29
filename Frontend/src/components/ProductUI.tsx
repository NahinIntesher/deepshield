'use client';
import {T} from '@/components/LocalizedText';
import {StatusMotion} from '@/components/StatusMotion';

import {useCallback,useEffect,useRef,useState} from 'react';import {request} from '@/lib/product';
export function useData(path:string,interval=0){const [data,setData]=useState<any>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);const generation=useRef(0);const reload=useCallback(async()=>{const run=++generation.current;setLoading(true);try{const next=await request(path);if(run===generation.current){setData(next);setError('')}}catch(e){if(run===generation.current)setError((e as Error).message)}finally{if(run===generation.current)setLoading(false)}},[path]);useEffect(()=>{setData(null);void reload();const id=interval?setInterval(reload,interval):undefined;return()=>{generation.current++;if(id)clearInterval(id)}},[reload,interval]);return {data,error,setError,reload,setData,loading}}
export function Heading({title,action}:{eyebrow?:string;title:string;subtitle?:string;action?:React.ReactNode}){return <div className="page-heading"><h1><T>{title}</T></h1>{action}</div>}
export function ErrorBox({text}:{text:string}){return text?<p className="error-box" role="alert"><T>{text}</T></p>:null}
export function Empty({title,text}:{title:string;text:string}){return <div className="product-empty"><StatusMotion/><h3><T>{title}</T></h3>{text&&<p><T>{text}</T></p>}</div>}
