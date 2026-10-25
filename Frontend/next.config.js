/** @type {import('next').NextConfig} */
module.exports = {
  outputFileTracingRoot: __dirname,
  async headers() {
    return [{source:'/:path*',headers:[
      {key:'X-Content-Type-Options',value:'nosniff'},
      {key:'X-Frame-Options',value:'DENY'},
      {key:'Cross-Origin-Opener-Policy',value:'same-origin-allow-popups'},
      {key:'Referrer-Policy',value:'strict-origin-when-cross-origin'}
    ]}];
  }
};
