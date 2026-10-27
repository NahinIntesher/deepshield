'use client';
import {useEffect,useState} from 'react';
import {Smartphone,Loader2} from 'lucide-react';
import {useUser} from '@/lib/UserContext';
import {useLocale} from '@/lib/Locale';
import {request} from '@/lib/product';
import GoogleSignIn from '@/components/GoogleSignIn';
import CompleteProfile from '../complete-profile/page';

export default function MobileConnect(){
 const {user,loading,logout}=useUser(),{t}=useLocale();
 const [params,setParams]=useState<{challenge:string;state:string}|null>(null),[ready,setReady]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[returnUrl,setReturnUrl]=useState('');
 useEffect(()=>{const p=new URLSearchParams(window.location.search),challenge=p.get('challenge')||'',state=p.get('state')||'';if(/^[A-Za-z0-9_-]{43}$/.test(challenge)&&/^[A-Za-z0-9_-]{43}$/.test(state))setParams({challenge,state});setReady(true)},[]);
 async function connect(){if(!params)return;setBusy(true);setError('');setReturnUrl('');try{const result=await request('/auth/mobile/handoff',{challenge:params.challenge});const url='deepshield://auth?'+new URLSearchParams({code:result.code,state:params.state}).toString();setReturnUrl(url);window.location.href=url}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 if(user?.needs_profile&&params)return <CompleteProfile/>;
 return <main className="auth-page auth-single"><section className="card auth-form space-y-5"><Smartphone size={32}/><h1>{t('Sign in to the app','অ্যাপে লগইন করুন')}</h1>{!ready||loading?<p role="status">{t('Loading…','লোড হচ্ছে…')}</p>:!params?<p>{t('Open Google sign-in from the DeepShield Android app.','DeepShield Android অ্যাপ থেকে Google লগইন চালু করুন।')}</p>:user?<><p>{t('Continue as','এই অ্যাকাউন্টে এগিয়ে যান')} <strong>{user.display_name}</strong> (@{user.username})</p><button className="primary-button w-full" disabled={busy} onClick={connect}>{busy?<Loader2 className="animate-spin" size={18}/>:null}{t('Continue to DeepShield app','DeepShield অ্যাপে ফিরুন')}</button>{returnUrl&&<div className="space-y-3"><p role="status">{t('If the app did not open, use this link within one minute.','অ্যাপ না খুললে এক মিনিটের মধ্যে নিচের লিংকটি চাপুন।')}</p><a className="secondary-button w-full" href={returnUrl}>{t('Open DeepShield app','DeepShield অ্যাপ খুলুন')}</a></div>}<button className="text-link" disabled={busy} onClick={()=>{setReturnUrl('');logout().catch(e=>setError(e.message))}}>{t('Use another account','অন্য অ্যাকাউন্ট ব্যবহার করুন')}</button></>:<GoogleSignIn/>}{error&&<p className="error-box" role="alert">{t(error)}</p>}</section></main>
}
