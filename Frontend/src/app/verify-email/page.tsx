'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {Mail,CheckCircle2,Loader2} from 'lucide-react';
import {useLocale} from '@/lib/Locale';
import {request} from '@/lib/product';

export default function VerifyEmail(){
 const {t}=useLocale();const [token,setToken]=useState(''),[busy,setBusy]=useState(false),[done,setDone]=useState(false),[error,setError]=useState('');
 useEffect(()=>{setToken(new URLSearchParams(location.hash.slice(1)).get('token')||'');history.replaceState(null,'','/verify-email')},[]);
 async function verify(){setBusy(true);setError('');try{await request('/auth/verify-email',{token});setToken('');setDone(true)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <main className="auth-page"><section className="card auth-form space-y-5">{done?<CheckCircle2 size={36}/>:<Mail size={36}/>}<h1>{done?t('Email verified','Email যাচাই হয়েছে'):t('Verify your email','আপনার email যাচাই করুন')}</h1><p>{done?t('Your account is ready. Sign in with your username and password.','আপনার account তৈরি হয়েছে। ইউজারনেম ও পাসওয়ার্ড দিয়ে লগইন করুন।'):t('Confirm this email address to finish creating your DeepShield account.','DeepShield account তৈরি শেষ করতে email ঠিকানাটি নিশ্চিত করুন।')}</p>{error&&<p className="error-box" role="alert">{error}</p>}{!done&&(token?<button className="primary-button" disabled={busy} onClick={verify}>{busy?<Loader2 className="animate-spin" size={18}/>:t('Verify email','Email যাচাই করুন')}</button>:<p role="status">{t('Open the link from your verification email.','আপনার verification email থেকে লিংকটি খুলুন।')}</p>)}<Link className="text-link" href="/login">{t('Go to sign in','লগইনে যান')}</Link></section></main>
}
