import Link from 'next/link';
export default function NotFound(){return <section className="card product-empty"><span className="eyebrow">404</span><h1>Page not found / পেজ পাওয়া যায়নি</h1><p>Check the address or return to your workspace.</p><Link href="/" className="primary-button mt-5">Go to overview / ওভারভিউ</Link></section>}
