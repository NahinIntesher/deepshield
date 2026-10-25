# Verification and limits

Completed checks:

- TypeScript checking and Next.js production build.
- 12 backend tests: existing auth, solo/multiplayer, qualification and migrations; new pairing/revocation, membership/support privacy, quota ledger and assessment behavior.
- Eight real videos: indexing, byte-range playback, clean metrics, game submission and explicit missing-checkpoint handling.
- Deterministic alignment, JPEG normalization, padding and no-face rejection checks.
- Chromium: 21 desktop/mobile route visits; no detected page errors or horizontal overflow. Signup, support submission, membership request, pairing code, Bengali font loading, mobile menu and cookie session restore checked.
- Original game, room, model architecture, preprocessing, model manager and all eight supplied video files preserved byte-for-byte.
- Browser extension JavaScript syntax validation.

Limits:

- Trained weights and InsightFace ONNX files were not supplied. Actual trained prediction, accuracy, GPU memory and throughput remain to be checked locally.
- Live extension browsing and retrieval on YouTube/Facebook/Instagram have not been end-to-end accepted on the user's computer. Platform restrictions can require direct upload.
- Premium supports manual administrator verification and clearly labelled academic demonstrations; no live gateway or automatic billing is included.
- Before/after assessment scores are exploratory, not causal proof of learning.
- The GPU backend is a single-process deployment; follow README before public service.
