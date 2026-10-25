# Google Sign-In

The Web OAuth client **DeepShield Local Web** was created in the selected Google Cloud project. Authorized JavaScript origins are `http://localhost:3000` and `http://127.0.0.1:3000`; redirect URIs are empty because the app uses the Google Identity Services popup callback. Project consent-screen branding was renamed to **DeepShield** with the owner's approval. The project remains in Testing mode.

`Backend/.env` contains the public `GOOGLE_CLIENT_ID`. Restart the Backend after changing it. No client secret is used or stored. Google handles account authentication; the backend verifies the token signature, issuer, audience, expiry and per-attempt nonce before issuing an HttpOnly session cookie. Only Google's `sub` identifies the Google account; accounts are not silently linked by email and tokens cannot grant Admin/Researcher roles.

Open the member login page and use the Google button. An existing username/password account remains separate unless a future explicit account-linking flow is implemented. The Admin owner continues to use the admin login. Google setup does not change that owner's password or role.

For additional testers, configure permitted test users in Google Auth Platform → Audience. Before public hosting, add the exact HTTPS frontend origin to the OAuth client, set exact API CORS origins, use secure cookies and review Google's publishing requirements. Changes can take time to propagate. No public production OAuth publication has been performed.

If sign-in fails, check the browser origin, current client ID, Google testing-user access, network access and the backend logs. Never put a client secret or ID token in frontend source or commit `.env`.

Official references:
- https://developers.google.com/identity/gsi/web/guides/display-button
- https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
