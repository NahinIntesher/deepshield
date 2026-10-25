'use client';
import {createContext,useContext,useEffect,useState} from 'react';
type Language='en'|'bn';
type Locale={language:Language;setLanguage:(next:Language)=>void;pick:(english:string,bangla:string)=>string};
const Context=createContext<Locale>({language:'en',setLanguage:()=>{},pick:(en)=>en});
export function LocaleProvider({children}:{children:React.ReactNode}){
 const [language,setLanguage]=useState<Language>('en');
 useEffect(()=>{setLanguage(localStorage.getItem('ds-language')==='bn'?'bn':'en')},[]);
 function change(next:Language){setLanguage(next);localStorage.setItem('ds-language',next);document.documentElement.lang=next;}
 const pick=(en:string,bn:string)=>language==='bn'?bn:en;
 return <Context.Provider value={{language,setLanguage:change,pick}}>{children}</Context.Provider>;
}
export const useLocale=()=>useContext(Context);
export const banglaNav:Record<string,string>={
 'Overview':'ওভারভিউ','Learn & Scams':'শিখুন ও সচেতন থাকুন','Real vs Fake':'আসল নাকি নকল',
 'AI Detector':'এআই ডিটেক্টর','Browser Extension':'ব্রাউজার এক্সটেনশন',
 'Membership':'সাবস্ক্রিপশন','Research Challenge':'রিসার্চ চ্যালেঞ্জ',
 'Research Insights':'রিসার্চ বিশ্লেষণ','My Profile':'আমার প্রোফাইল',
 'Admin Overview':'অ্যাডমিন ওভারভিউ','User Management':'ইউজার ম্যানেজমেন্ট',
 'Subscriptions':'সাবস্ক্রিপশন','Activity Analytics':'অ্যাক্টিভিটি বিশ্লেষণ',
 'Research Reviews':'রিসার্চ রিভিউ','Continual Learning':'কন্টিনিউয়াল লার্নিং','Audit Trail':'অডিট লগ'
};
