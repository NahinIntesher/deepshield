# Local verification — 25 October 2026

The application runs locally at http://localhost:3000, with FastAPI at http://localhost:8000. This is a local verification record, not a production certification.

## Completed checks

- Latest production frontend build: successful, 29 generated pages.
- Functional, migration, backup and image preprocessing suite: 27 passed (four framework deprecation warnings).
- Standalone preprocessing contract: passed geometry, JPEG, normalization, padding and no-face rejection.
- Standalone model math fixture: chunked forward and chain-rule gradients agree. Fixture weights do not establish trained accuracy.
- Actual browser Admin login with the configured owner account: successful. User list has one Admin, one Researcher and four Participants; no Moderator role.
- Browser language toggle: English/Bengali content and navigation checked on Admin dashboard and Users; old English accuracy-band labels and obsolete Moderator translation corrected.
- Light/dark toggle checked. Desktop 1440, tablet 768 and mobile 390 layouts have no document horizontal overflow on the dashboard.
- Desktop Bengali light and mobile Bengali dark screenshots saved in review/.
- Google OAuth web client created for localhost:3000 and 127.0.0.1:3000; consent branding saved as DeepShield. Google button renders on member login. Real Google sign-in currently reports an origin rejection. Saved port-specific origins and backend client ID match; the additional bare localhost origin recommended by Google is awaiting action-time authorization. A completed real Google account callback is not yet verified; backend challenge/token contracts use mocked official verifier in tests.
- Database migrated to 0007 after snapshot backup. Tests use separate temporary data.

## Limits before release

- Google consent project remains in Testing; public hosting requires exact HTTPS origins and Google publishing review as applicable.
- Continual training needs curated replay, retention and new validation manifests plus reviewed contributions. No data has been invented to satisfy readiness.
- Still-image support is experimental. A frame extracted from a Real-labelled sample was predicted Fake with high confidence; video validation does not establish image accuracy. The UI explicitly identifies image analysis as experimental.
- bKash approval is manual independent verification, not a payment gateway.
- Production hosting, domain/TLS, deployment backups and a full release/security/accessibility audit remain outstanding. Not every application flow has been exercised manually in every viewport.
