"use client";
import {useEffect,useRef,useState} from 'react';
import Link from 'next/link';
import {usePathname,useRouter} from 'next/navigation';
import {X,LogOut,ShieldCheck,ArrowUpRight,Loader2} from 'lucide-react';
import {Navbar} from './Navbar';
import {Logo} from './Logo';
import {useUser} from '@/lib/UserContext';
import {useLocale} from '@/lib/Locale';
import {memberLinks,adminLinks,bn} from '@/lib/navigation';
import {useTabNavigation} from '@/lib/useTabNavigation';

export function AuthGate({children}:{children:React.ReactNode}){
 useTabNavigation();
 const path=usePathname(),router=useRouter(),{user,loading,logout,sessionError,refreshUser}=useUser(),{lang,t}=useLocale();
 const drawer=useRef<HTMLElement>(null);
 const [open,setOpen]=useState(false),[error,setError]=useState(''),[retrying,setRetrying]=useState(false);
 const login=path==='/login'||path==='/admin/login',profilePage=path==='/complete-profile',adminPath=path.startsWith('/admin');
 const memberPath=memberLinks.some(([href])=>href===path)||path==='/moderation';
 const publicSpecial=path==='/verify-email'||(!adminPath&&!memberPath&&!login&&!profilePage);
 const publicPage=login||path==='/'||publicSpecial,admin=user?.role==='admin';
 const wrong=!!user&&!login&&!profilePage&&!publicSpecial&&(admin?memberPath:adminPath);
 useEffect(()=>{
  if(loading||(!user&&sessionError)||publicSpecial)return;
  if(user?.needs_profile){if(!profilePage)router.replace('/complete-profile');return}
  if(profilePage&&user){router.replace(admin?'/admin':'/');return}
  if(!user&&!publicPage)router.replace(adminPath?'/admin/login':'/login');
  if(user&&(login||wrong))router.replace(admin?'/admin':'/');
 },[loading,user,sessionError,publicSpecial,profilePage,publicPage,admin,adminPath,login,wrong,router]);
 useEffect(()=>{setOpen(false);setError('')},[path]);
 useEffect(()=>{
  if(!open)return;
  const previous=document.activeElement as HTMLElement|null,overflow=document.body.style.overflow;
  document.body.style.overflow='hidden';
  const focusable=()=>Array.from(drawer.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled]),select,input,[tabindex="0"]')||[]).filter(element=>element.getClientRects().length);
  focusable()[0]?.focus();
  function key(event:KeyboardEvent){
   if(event.key==='Escape')setOpen(false);
   if(event.key==='Tab'){const list=focusable(),first=list[0],last=list[list.length-1];if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}}
  }
  document.addEventListener('keydown',key);
  return()=>{document.removeEventListener('keydown',key);document.body.style.overflow=overflow;previous?.focus()};
 },[open]);
 async function signOut(){try{await logout();router.replace(admin?'/admin/login':'/')}catch(e){setError((e as Error).message)}}
 async function retry(){setRetrying(true);try{await refreshUser()}catch{}finally{setRetrying(false)}}
 const publicContent=(content:React.ReactNode)=><><a className="skip-link" href="#public-content">{t('Skip to content','মূল লেখায় যান')}</a><Navbar/><div id="public-content" tabIndex={-1}>{content}</div></>;
 if(sessionError&&!user&&!publicPage)return publicContent(<main className="auth-page auth-single"><section className="card auth-form space-y-5"><h1>{t('Connection unavailable','সংযোগ পাওয়া যাচ্ছে না')}</h1><p role="alert">{t('Could not connect to DeepShield. Please try again.','DeepShield-এর সঙ্গে সংযোগ হয়নি। আবার চেষ্টা করুন।')}</p><button className="primary-button" disabled={retrying} onClick={retry}>{retrying?<><Loader2 size={18} className="animate-spin"/>{t('Connecting…','সংযোগ হচ্ছে…')}</>:t('Try again','আবার চেষ্টা করুন')}</button></section></main>);
 if((loading&&!publicPage&&!user)||(user?.needs_profile&&!profilePage&&!publicSpecial)||(!publicPage&&!user)||(login&&!!user)||wrong)return <div className="loading-screen" role="status"><Logo/><p>{t('Opening your workspace…','ওয়ার্কস্পেস খুলছে…')}</p></div>;
 if((publicPage&&!user)||login||profilePage||publicSpecial)return publicContent(children);
 return <><a href="#main-content" className="skip-link">{t('Skip to content','মূল লেখায় যান')}</a>{open&&<button className={`sidebar-backdrop ${admin?'admin-backdrop':''}`} aria-label={t('Dismiss navigation','নেভিগেশন বন্ধ করুন')} onClick={()=>setOpen(false)}/>}
  <aside id="workspace-navigation" ref={drawer} role={open?'dialog':undefined} aria-modal={open?true:undefined} aria-label={t('Workspace navigation','ওয়ার্কস্পেস নেভিগেশন')} className={`sidebar ${admin?'admin-sidebar':''} ${open?'open':''}`}>
   <div className="sidebar-brand"><Link href={admin?'/admin':'/'}><Logo/></Link><button className="icon-button mobile-menu" aria-label={t('Close navigation','নেভিগেশন বন্ধ করুন')} onClick={()=>setOpen(false)}><X size={20}/></button></div>
   <p className="nav-label">{admin?t('Admin panel','অ্যাডমিন প্যানেল'):t('Your workspace','আপনার ওয়ার্কস্পেস')}</p>
   <nav aria-label={t('Main navigation','মূল নেভিগেশন')}>{(admin?adminLinks:memberLinks).map(([href,label,Icon],index)=><div key={href}>{!admin&&[4,9].includes(index)&&<p className="nav-label group-label">{index===4?t('Learn & explore','শিখুন ও জানুন'):t('Account','অ্যাকাউন্ট')}</p>}<Link href={href} className={`nav-item ${path===href?'active':''}`} aria-current={path===href?'page':undefined}><Icon size={18}/><span>{lang==='bn'?bn[href]||label:label}</span>{path===href&&<i className="nav-dot"/>}</Link></div>)}</nav>
   <div className="sidebar-bottom">{!admin&&<Link href="/subscription" className="sidebar-upgrade"><ShieldCheck size={21}/><span><strong>{t('Premium plans','Premium প্ল্যান')}</strong><small>{t('Explore Premium','Premium দেখুন')}</small></span><ArrowUpRight size={16}/></Link>}<button className="sidebar-logout" onClick={signOut}><LogOut size={17}/>{t('Sign out','সাইন আউট')}</button>{error&&<p className="error-box" role="alert">{t(error)}</p>}</div>
  </aside>
  <Navbar menuOpen={open} onMenu={()=>setOpen(!open)}/><div className={`app-content ${admin?'admin-content':''}`}><main id="main-content" tabIndex={-1}>{children}</main><footer><span>© {new Date().getFullYear()} DeepShield · Team Hexagon</span></footer></div>
 </>
}
