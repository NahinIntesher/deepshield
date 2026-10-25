'use client';
import Link from 'next/link';
import {AlertCircle} from 'lucide-react';
import {useLocale} from '@/lib/Locale';

export default function ErrorPage({reset}: {error: Error; reset: () => void}) {
  const {t} = useLocale();
  return <section className="card product-empty" role="alert"><AlertCircle size={36}/><h1>{t('This page could not load.','পেজটি লোড হয়নি।')}</h1><p>{t('Your saved work is still available. Try opening the page again.','সংরক্ষিত তথ্য আছে। পেজটি আবার খোলার চেষ্টা করুন।')}</p><div className="flex gap-3 flex-wrap justify-center mt-5"><button className="primary-button" onClick={reset}>{t('Try again','আবার চেষ্টা করুন')}</button><Link href="/" className="secondary-button">{t('Go to overview','ওভারভিউতে যান')}</Link></div></section>;
}
