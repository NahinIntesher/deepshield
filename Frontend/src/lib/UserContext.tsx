"use client";
import {createContext,useContext,useEffect,useRef,useState} from 'react';
import {User} from './types';
import {API_BASE,apiFetch,loginUser,registerUser,loginAdmin} from './api';
interface State{user:User|null;loading:boolean;sessionError:string;login:(u:string,p:string)=>Promise<void>;adminLogin:(u:string,p:string)=>Promise<void>;signup:(u:string,n:string,p:string,e:string,l:string)=>Promise<boolean>;logout:()=>Promise<void>;refreshUser:()=>Promise<void>}
const Context=createContext<State|undefined>(undefined);
export function UserProvider({children}:{children:React.ReactNode}){
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true),[sessionError,setSessionError]=useState('');
 const generation=useRef(0);
 async function refreshUser(){const run=++generation.current;try{const response=await apiFetch(API_BASE+'/api/auth/me',{signal:AbortSignal.timeout(75_000)});if(run!==generation.current)return;if(response.status===401){setUser(null);setSessionError('');return}if(!response.ok)throw Error('Could not connect to DeepShield. Please try again.');const next=await response.json();if(run===generation.current){setUser(next);setSessionError('')}}catch(error){if(run===generation.current)setSessionError('Could not connect to DeepShield. Please try again.');throw error}finally{if(run===generation.current)setLoading(false)}}
 useEffect(()=>{localStorage.removeItem('deepfake_platform_auth_user');void refreshUser().catch(()=>{});return()=>{generation.current++}},[]);
 useEffect(()=>{if(!user)return;const restore=()=>{if(document.visibilityState==='visible')void refreshUser().catch(()=>{})};window.addEventListener('focus',restore);return()=>window.removeEventListener('focus',restore)},[user?.id]);
 async function authenticate(u:string,p:string,admin=false){const run=++generation.current;try{const next=await(admin?loginAdmin(u,p):loginUser(u,p));if(run===generation.current){setUser(next);setSessionError('')}}finally{if(run===generation.current)setLoading(false)}}
 async function signup(u:string,n:string,p:string,e:string,l:string){const result=await registerUser(u,n,p,e,l);if(!result.verification_required)await authenticate(u,p);return result.verification_required}
 async function logout(){++generation.current;const response=await apiFetch(API_BASE+'/api/auth/logout',{method:'POST'});if(!response.ok)throw Error('Sign out failed. Try again.');setUser(null);setSessionError('');setLoading(false)}
 return <Context.Provider value={{user,loading,sessionError,login:(u,p)=>authenticate(u,p),adminLogin:(u,p)=>authenticate(u,p,true),signup,logout,refreshUser}}>{children}</Context.Provider>
}
export function useUser(){const value=useContext(Context);if(!value)throw Error('UserProvider required');return value}
