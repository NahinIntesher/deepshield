'use client';
import {useEffect,useRef,useState} from 'react';
import Script from 'next/script';
import {useLocale} from '@/lib/Locale';
import {useUser} from '@/lib/UserContext';
import {request} from '@/lib/product';
import {ErrorBox} from './ProductUI';

type GoogleWindow=Window & {google?:{accounts:{id:{initialize:(options:Record<string,unknown>)=>void;renderButton:(element:HTMLElement,options:Record<string,unknown>)=>void}}}};

export default function GoogleSignIn(){
 const {t,lang}=useLocale(),{refreshUser}=useUser();
 const mount=useRef<HTMLDivElement>(null);
 const [config,setConfig]=useState<{enabled:boolean;client_id:string}|null>(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[attempt,setAttempt]=useState(0);
 useEffect(()=>{let active=true;request('/auth/providers').then(r=>{if(active)setConfig(r.google)}).catch(()=>{if(active)setError(t('Google sign-in is temporarily unavailable. Use your username and password.','Google লগইন এখন পাওয়া যাচ্ছে না। ইউজারনেম ও পাসওয়ার্ড দিয়ে ঢুকুন।'))});return()=>{active=false}},[]);
 useEffect(()=>{if(!ready||!config?.enabled||!mount.current)return;let active=true;setError('');request('/auth/google/challenge',{}).then(({nonce})=>{if(!active||!mount.current)return;const api=(window as GoogleWindow).google?.accounts.id;if(!api)return;api.initialize({client_id:config.client_id,nonce,auto_select:false,callback:async({credential}:{credential:string})=>{if(!active)return;setBusy(true);setError('');try{await request('/auth/google',{credential});await refreshUser()}catch(e){setError((e as Error).message)}finally{setBusy(false)}}});mount.current.replaceChildren();api.renderButton(mount.current,{type:'standard',theme:'outline',size:'large',text:'continue_with',shape:'rectangular',locale:lang==='bn'?'bn':'en',width:Math.min(360,mount.current.clientWidth||280)})}).catch(e=>{if(active)setError((e as Error).message)});return()=>{active=false}},[ready,config,lang,attempt]);
 return <div className="google-signin"><div className="auth-divider"><span>{t('or','অথবা')}</span></div>{config?.enabled?<><Script src="https://accounts.google.com/gsi/client" strategy="afterInteractive" onLoad={()=>setReady(true)} onReady={()=>setReady(true)} onError={()=>setError(t('Could not load Google sign-in. Use your username and password.','Google লগইন লোড হয়নি। ইউজারনেম ও পাসওয়ার্ড ব্যবহার করুন।'))}/><div ref={mount} aria-busy={busy}/>{(!ready||busy)&&<p className="muted text-sm" role="status">{busy?t('Signing in…','লগইন হচ্ছে…'):t('Loading Google sign-in…','Google লগইন লোড হচ্ছে…')}</p>}</>:<button className="secondary-button w-full" type="button" disabled>{config?t('Google sign-in · coming soon','Google লগইন · শিগগিরই'):t('Loading Google sign-in…','Google লগইন লোড হচ্ছে…')}</button>}<ErrorBox text={error}/>{error&&config?.enabled&&<button className="text-link mt-2" type="button" onClick={()=>setAttempt(v=>v+1)}>{t('Try again','আবার চেষ্টা করুন')}</button>}</div>
}
