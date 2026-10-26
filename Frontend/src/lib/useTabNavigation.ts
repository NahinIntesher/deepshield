'use client';
import {useEffect} from 'react';

/** Shared keyboard behavior for the app's horizontal tab lists. */
export function useTabNavigation(){
 useEffect(()=>{
  function navigate(event:KeyboardEvent){
   if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
   const current=(event.target as HTMLElement)?.closest<HTMLButtonElement>('[role="tab"]');
   const list=current?.closest('[role="tablist"]');
   if(!current||!list)return;
   const tabs=Array.from(list.querySelectorAll<HTMLButtonElement>('[role="tab"]:not(:disabled)')).filter(tab=>tab.getClientRects().length);
   const index=tabs.indexOf(current);
   if(index<0||!tabs.length)return;
   const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
   event.preventDefault();tabs[next].focus();tabs[next].click();
  }
  document.addEventListener('keydown',navigate);
  return()=>document.removeEventListener('keydown',navigate);
 },[]);
}
