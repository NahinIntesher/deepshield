'use client';
import {createContext,useContext,useEffect,useState} from 'react';
import {translateBn} from './messages.bn';
import {authoredCopy} from './interfaceCopy';
const C=createContext({lang:'en',setLang:(_v:string)=>{},t:(en:string,_bn?:string)=>en});
export function LocaleProvider({children}:{children:React.ReactNode}){const [lang,setLanguage]=useState('en');useEffect(()=>setLanguage(localStorage.getItem('deepshield-language')==='bn'?'bn':'en'),[]);useEffect(()=>{document.documentElement.lang=lang},[lang]);function setLang(v:string){if(v!=='en'&&v!=='bn')return;setLanguage(v);localStorage.setItem('deepshield-language',v)}return <C.Provider value={{lang,setLang,t:(en,bn)=>authoredCopy(en,bn,lang,translateBn)}}>{children}</C.Provider>}
export const useLocale=()=>useContext(C);
