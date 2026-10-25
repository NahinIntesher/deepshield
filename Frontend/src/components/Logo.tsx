export function Logo({compact=false}:{compact?:boolean}) {
 return <span className="brand-lockup"><svg width="38" height="42" viewBox="0 0 40 44" fill="none" aria-hidden="true"><path d="M20 2 36 8v13c0 10-9 17-16 21C13 38 4 31 4 21V8L20 2Z" fill="currentColor" opacity=".16"/><path d="M20 3 35 9v12c0 9-8 16-15 20C13 37 5 30 5 21V9L20 3Z" stroke="currentColor" strokeWidth="2"/><path d="m16 14 12 8-12 8V14Z" fill="currentColor"/><path d="m24 28 3 3 7-8" stroke="#8ce7b3" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>{!compact&&<span>DeepShield</span>}</span>;
}
