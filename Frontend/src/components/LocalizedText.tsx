'use client';
import type {ReactNode} from 'react';
import {useLocale} from '@/lib/Locale';

/** Translate authored interface text without rewriting user-supplied content. */
export function T({text,children}:{text?:string;children?:ReactNode}) {
  const {t}=useLocale();
  const value=text??children;
  return <>{typeof value==='string'?t(value):value}</>;
}
