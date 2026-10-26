"use client";
import Link from 'next/link';
import {useLocale} from '@/lib/Locale';
export default function NotFound(){const {t}=useLocale();return <section className="card product-empty"><span className="eyebrow">404</span><h1>{t('Page not found','পেজ পাওয়া যায়নি')}</h1><p>{t('Check the address or return to the home page.','ঠিকানাটি দেখুন অথবা হোম পেজে ফিরুন।')}</p><Link href="/" className="primary-button mt-5">{t('Back to home','হোমে ফিরুন')}</Link></section>}
