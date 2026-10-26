'use client';
import Link from 'next/link';
import {Users,Activity,ShieldCheck,ClipboardCheck,ArrowUpRight,Info} from 'lucide-react';
import {useLocale} from '@/lib/Locale';

export function AdminSummary({data,days}:{data:any;days:number}){
 const {t}=useLocale(),s=data.summary;
 const cards=[
  {Icon:Users,value:s.members,title:t('Community members','মোট সদস্য'),description:t('Registered members, excluding the owner administrator.','একমাত্র Admin ছাড়া নিবন্ধিত সদস্যের সংখ্যা।'),href:'/admin/users'},
  {Icon:Activity,value:s.active,title:t(`Active in ${days} days`,`গত ${days} দিনে সক্রিয়`),description:t('People with a recorded game, scan, research answer or lesson activity in this period.','এই সময়ে খেলা, স্ক্যান, গবেষণা বা পাঠে অংশ নেওয়া মানুষের সংখ্যা।'),href:'/admin/activity'},
  {Icon:ShieldCheck,value:s.qualified,title:t('Research qualified','গবেষণার যোগ্য'),description:t('Members meeting both the recorded score and accuracy requirements.','সংরক্ষিত পয়েন্ট ও সঠিক উত্তরের হার—দুটি শর্ত পূরণ করা সদস্য।'),href:'/admin/research'},
  {Icon:ClipboardCheck,value:s.pending_reviews,title:t('Awaiting review','যাচাইয়ের অপেক্ষায়'),description:t('Research samples that still need an independent label and source check.','গবেষণার যে নমুনাগুলোর সোর্স ও label আলাদাভাবে যাচাই করতে হবে।'),href:'/admin/research'}
 ];
 const totals=(data.daily||[]).reduce((sum:any,r:any)=>({rounds:sum.rounds+r.rounds,detections:sum.detections+r.detections,research:sum.research+r.research}),{rounds:0,detections:0,research:0});
 return <><div className="admin-metric-grid">{cards.map(({Icon,value,title,description,href})=><Link href={href} className="admin-metric" key={href+title}><div className="section-heading"><span className="admin-metric-icon"><Icon size={21}/></span><ArrowUpRight size={17}/></div><strong className="admin-metric-value">{value.toLocaleString()}</strong><h2>{title}</h2><p>{description}</p></Link>)}</div><section className="admin-insight-strip"><Info size={22}/><p>{t('Member totals include all accounts. Activity counts use the selected period.','ইউজারের সংখ্যা সব অ্যাকাউন্টের হিসাব। অ্যাক্টিভিটি রিপোর্ট বেছে নেওয়া সময়ের হিসাব দেখায়।')}</p></section><div className="admin-period-totals">{[[totals.rounds,t('Game rounds','খেলার রাউন্ড'),t('One recorded answer per round','প্রতি রাউন্ডে একটি সংরক্ষিত উত্তর')],[totals.detections,t('AI analyses','AI বিশ্লেষণ'),t('Saved model predictions','সংরক্ষিত মডেলের ফলাফল')],[totals.research,t('Research answers','গবেষণার উত্তর'),t('Independent human–AI comparisons','মানুষ ও AI-এর স্বাধীন তুলনা')]].map(([n,label,detail])=><div key={String(label)}><strong>{Number(n).toLocaleString()}</strong><span>{label}</span><small>{detail}</small></div>)}</div></>;
}

export function RoleChart({rows}:{rows:{label:string;value:number}[]}){
 const {t}=useLocale(),total=rows.reduce((n,r)=>n+r.value,0),colors=['#185c3d','#729877','#b6ccb2','#d9e4d4'];let offset=0;
 return <div className="role-chart"><div className="role-ring"><svg viewBox="0 0 120 120" role="img" aria-label={t('Account roles. Exact counts are listed beside the chart.','ইউজারের রোল। পাশে সঠিক সংখ্যা আছে।')}><circle cx="60" cy="60" r="45" fill="none" stroke="var(--soft)" strokeWidth="13"/>{rows.map((r,i)=>{const length=total?r.value/total*100:0;const start=offset;offset+=length;return <circle key={r.label} cx="60" cy="60" r="45" pathLength="100" fill="none" stroke={colors[i%colors.length]} strokeWidth="13" strokeDasharray={`${length} ${100-length}`} strokeDashoffset={-start} transform="rotate(-90 60 60)"/>})}</svg><div><strong>{total}</strong><span>{t('accounts','অ্যাকাউন্ট')}</span></div></div><dl className="role-chart-legend">{rows.map((r,i)=><div key={r.label}><dt><i style={{background:colors[i%colors.length]}}/>{t(r.label)}</dt><dd>{r.value}<small>{total?Math.round(r.value/total*100):0}%</small></dd></div>)}</dl></div>;
}
