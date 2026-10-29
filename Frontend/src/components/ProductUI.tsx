'use client';
import {T} from '@/components/LocalizedText';
import {StatusMotion} from '@/components/StatusMotion';

import {useCallback,useEffect,useRef,useState} from 'react';import {request} from '@/lib/product';
export function useData(path:string,interval=0){
 const [state,setState]=useState<{path:string;data:any;error:string;loading:boolean}>({path,data:null,error:'',loading:true});
 const generation=useRef(0);
 const reload=useCallback(async()=>{
  const run=++generation.current;
  setState(previous=>({path,data:previous.path===path?previous.data:null,error:'',loading:true}));
  try{const next=await request(path);if(run===generation.current)setState({path,data:next,error:'',loading:false})}
  catch(e){if(run===generation.current)setState(previous=>({...previous,path,error:(e as Error).message,loading:false}))}
 },[path]);
 useEffect(()=>{void reload();const id=interval?setInterval(reload,interval):undefined;return()=>{generation.current++;if(id)clearInterval(id)}},[reload,interval]);
 const setData=useCallback((value:any)=>setState(previous=>({...previous,path,data:typeof value==='function'?value(previous.path===path?previous.data:null):value})),[path]);
 const setError=useCallback((error:string)=>setState(previous=>({...previous,path,data:previous.path===path?previous.data:null,error})),[path]);
 // A new tab must never render the previous endpoint's rows with a different schema.
 const current=state.path===path?state:{path,data:null,error:'',loading:true};
 return {...current,setError,reload,setData};
}
export function Heading({title,action}:{eyebrow?:string;title:string;subtitle?:string;action?:React.ReactNode}){return <div className="page-heading"><h1><T>{title}</T></h1>{action}</div>}
export function ErrorBox({text}:{text:string}){return text?<p className="error-box" role="alert"><T>{text}</T></p>:null}
export function Empty({title,text}:{title:string;text:string}){return <div className="product-empty"><StatusMotion/><h3><T>{title}</T></h3>{text&&<p><T>{text}</T></p>}</div>}
