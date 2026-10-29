'use client';
import {useLocale} from '@/lib/Locale';
import guide from '@/lib/user-guide.json';
import {Heading} from '@/components/ProductUI';
export default function Guide(){const {lang,t}=useLocale();const language=lang==='bn'?'bn':'en';return <div className="page-container"><Heading title={t('User guide')}/><div className="card">{guide.map(section=><details key={section.title.en} className="faq"><summary>{section.title[language]}</summary><ol className="space-y-3 mt-4 pl-5 list-decimal">{section.steps.map(step=><li key={step.en}>{step[language]}</li>)}</ol></details>)}</div></div>}
