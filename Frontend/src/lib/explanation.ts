import type {DetectionResult} from './types';
import type {ShapEvidence,ShapRegion} from './explanationTypes';

export function validShap(result:DetectionResult):ShapEvidence|null{
 const s=result.shap_explanation;if(!s||s.method!=='SHAP'||s.target_class!==result.verdict)return null;
 for(const g of [s.branches,s.frames,s.spatial]){
  if(!g)continue;
  if(!Array.isArray(g.values)||g.values.length!==g.feature_names.length||!g.values.every(Number.isFinite)||![g.base_value,g.output_value].every(Number.isFinite))return null;
  if(Math.abs(g.base_value+g.values.reduce((a,b)=>a+b,0)-g.output_value)>0.001)return null;
 }
 if(!s.spatial.regions.length||!s.spatial.regions.every(r=>Number.isFinite(r.masked_class_score_percent)&&r.masked_class_score_percent>=0&&r.masked_class_score_percent<=100))return null;
 return s;
}
export function regionName(id:string,bn:boolean){return (bn?{eyes:'চোখের চারপাশ',nose:'নাকের আশপাশ',mouth:'ঠোঁটের আশপাশ',other:'মুখের ছবির বাকি অংশ'}:{eyes:'Around the eyes',nose:'Around the nose',mouth:'Mouth and lower face',other:'Rest of the face crop'})[id as ShapRegion['id']]||(bn?'মুখের অংশ':'Face area')}
export function resultMeaning(result:DetectionResult,bn:boolean){
 if(result.media_type==='image')return bn?`মডেলের মতে, ছবিটি ${result.verdict==='Fake'?'নকল হতে পারে':'আসল'}। তবে মডেলটিকে ভিডিও চিনতে শেখানো হয়েছে; স্থির ছবির এই ফল পরীক্ষামূলক। শুধু এই ফল দেখে সিদ্ধান্ত নেবেন না।`:`The model chose ${result.verdict} for this image. It was trained on videos, so this still-image result is experimental. Do not rely on this result alone.`;
 return result.verdict==='Fake'?(bn?'মডেলের মতে, এই ভিডিওর মুখের ছবি বদলানো হয়ে থাকতে পারে। শেয়ার করার আগে আসল ভিডিওটি খুঁজে দেখুন।':'The model thinks the face in this video may have been altered. Find the original video before sharing it.'):(bn?'মডেল এই ভিডিওটিকে আসল হিসেবে বেছে নিয়েছে। তবুও ভিডিওর মানুষটি কে, তাঁর কথার অর্থ বা খবরটি সত্য কি না—এই পরীক্ষা তা যাচাই করে না।':'The model chose Real for this video. This test does not verify the person, what they said, or whether the claim is true.');
}
export function blurObservation(result:DetectionResult,region:ShapRegion,bn:boolean){
 const format=(n:number)=>new Intl.NumberFormat(bn?'bn-BD':'en-US',{minimumFractionDigits:1,maximumFractionDigits:1}).format(n);const before=format(result.confidence_percentage),after=format(region.masked_class_score_percent);
 const name=regionName(region.id,bn),label=bn?(result.verdict==='Real'?'আসল':'নকল'):result.verdict;
 return bn?`${name} ঝাপসা করে আবার পরীক্ষা করলে মডেলের ${label} স্কোর ${before}% থেকে ${after}% হয়েছে। এভাবে এই অংশের প্রভাব পরীক্ষা করা হয়েছে। এই স্কোর নিশ্চিত প্রমাণ নয়।`:`When we blurred ${name.toLowerCase()}, the model’s ${label} score went from ${before}% to ${after}%. This tests how that area affects the answer. The score is not proof.`;
}
export function strongestRegion(s:ShapEvidence):ShapRegion{
 return [...s.spatial.regions].sort((a,b)=>Math.abs(b.shap_value)-Math.abs(a.shap_value))[0];
}
