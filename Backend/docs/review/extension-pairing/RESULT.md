# Chrome companion test — 27 October 2026

Render's `EXTENSION_ORIGINS` now contains only the owner's approved unpacked extension origin, `chrome-extension://fhjcnooodecbppcebmaoplnpkbhmodhb`. Existing web CORS origins and secrets were preserved. Deployment: `dep-dbg8op6c6qcc73emtu10`.

The hosted pairing preflight returned 200 and the exact allow-origin value. An invalid-code POST reached normal validation rather than the origin denial. In the installed Chrome extension, a fresh one-time code successfully paired; the popup displayed **Connected to your model server** and **FREE · 0 / 10 daily scans**. The scoped token is revocable in the account's Browser Companion page.

Refreshing the owner's open YouTube Short loaded the companion overlay. Public-link retrieval failed and the overlay displayed **Not analyzed** with the direct-upload fallback. No Real/Fake prediction was fabricated. Pairing is fixed; this YouTube retrieval limitation remains separate. Social cookies/passwords were not exported or transmitted, and no platform protection was bypassed.

Screenshots are local review evidence and are not needed in the public source repository.
