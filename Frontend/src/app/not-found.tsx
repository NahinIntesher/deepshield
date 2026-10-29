"use client";
import Link from 'next/link';
import {useLocale} from '@/lib/Locale';
import {StatusMotion} from '@/components/StatusMotion';
export default function NotFound(){const {t}=useLocale();return <section className="card product-empty"><StatusMotion size={128}/><h1>{t('Page not found','পেজটি পাওয়া যায়নি')}</h1><Link href="/" className="primary-button mt-5">{t('Back to home','হোমে ফিরুন')}</Link></section>}
