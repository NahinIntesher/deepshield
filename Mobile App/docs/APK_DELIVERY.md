# Latest Android artifact — 29 October 2026

`Mobile App/DeepShield-1.0.2.apk` is the latest review build, version 1.0.2 (3). Prior 1.0.0 and 1.0.1 files are retained.

- Size: 60,811,369 bytes. SHA-256: `c9483673dbabbfad4ed190b15b7e9c65295bcd269d73f354b27a205610a03b0f`.
- The original remains at `build/app/outputs/flutter-apk/app-release.apk`; copy and original match exactly.
- Release v2 signature verified with the existing owner certificate, SHA-256 `9e5ca5445fcaa8a00172a4ffe4c9bffab8c315e8f2fc2e666d9eb7c6496c860b`.
- API 24 minimum, API 36 target; ARM64, ARMv7 and x86_64. Production API only; no debug flag, integration-test plugin, capture harness, env/database/checkpoint/keystore files.
- Approved brand and local motion assets are present; bilingual copy and guide exactly match source. The narrow-header/130% Bengali text fix is included.
- Analyzer passed; 34 Flutter tests passed. Web production build passed for 33 routes; dependency audit reported zero vulnerabilities.
- Installed this copied APK on Android 15 and performed a clean launch: `Status: ok`, cold launch 1.694 seconds. This is an emulator measurement, not a promise for every phone. Actual screen and crash log were checked.
- Responsive browser audit scope is documented in `../../Frontend/docs/RESPONSIVE_REVIEW.md`. The tested pages/states are ready for owner review; this does not establish universal physical-device compatibility.

Hosted YouTube public-link retrieval remains blocked for the selected Short (`platform_restriction`). Pairing works, and no fabricated prediction was shown. Physical-device social capture/Google checks and owner-paused email delivery remain pending.

The notes below refer to earlier artifacts and earlier test counts.

---

# Android delivery — 29 October 2026

Latest copied file: `Mobile App/DeepShield-1.0.1.apk` (version 1.0.1, build 2).

- 60,811,113 bytes; SHA-256 `e4476049473a2a5b92b5f295c541cd98415faf387733cfb25a8e3927ae386a15`.
- Original build remains at `build/app/outputs/flutter-apk/app-release.apk`. The root copy has the same hash; 1.0.0 is retained.
- Release signature v2 verified; existing RSA 3072-bit owner certificate SHA-256 `9e5ca5445fcaa8a00172a4ffe4c9bffab8c315e8f2fc2e666d9eb7c6496c860b`.
- Android API 24 minimum, 36 target; ARM64, ARMv7 and x86_64. No debug flag, integration-test plugin, capture harness, private database, checkpoint, env file or signing key in the APK.
- Production API present; local emulator API absent. Approved folded logo, Orbit loading, Focus scanning and original Not Found artwork are bundled locally.
- Analyzer passed; 20 Flutter tests passed, including 20 screens in English/Bengali, light/dark and 320/768 px layouts. Web production build: 33 routes passed.
- Installed successfully on Android 15 emulator. Initial launch timed out during slow emulator boot; after boot settled, repeat cold launch returned `Status: ok`, 3.610 seconds. Actual sign-in screenshot was inspected.

## Remaining review

The full responsive web audit is still in progress after the owner reported a broken signup screenshot. Do not treat this APK as final visual approval. Any further mobile fixes require a new build.

Hosted YouTube URL retrieval was tested on 29 October against the deployed backend. The selected Short failed with `platform_restriction`; no model result was fabricated. The same public video downloaded locally. Pairing is fixed; cloud retrieval remains limited. Authorized direct upload remains available.

Physical-phone social scrolling and Google login remain unverified. Earlier emulator tests verified Real did not notify and Fake did, with the original model, and verified the Google PKCE handoff. The compact overlay compiles in this release but its new size has not been retested across physical devices.

Email verification delivery remains paused by the owner. No completion email has been sent because the wider responsive review is still open.

---

# Android delivery — 27 October 2026

- File copied to `Mobile App/DeepShield-1.0.0.apk`; the original remains at `build/app/outputs/flutter-apk/app-release.apk`.
- Version 1.0.0 (1), package `bd.com.nahin.deepshield_mobile`.
- 60,799,307 bytes; universal ARM64, ARMv7 and x86_64 APK; minimum Android 7/API 24, target API 36.
- Release entry point: `lib/main.dart`; API: `https://api.deepshield.nahin.com.bd`.
- SHA-256: `227245fdc6dab1481690119c9d2d449316b8b802359f176f44bea629d40372b6`.
- Production signing certificate SHA-256: `9e5ca5445fcaa8a00172a4ffe4c9bffab8c315e8f2fc2e666d9eb7c6496c860b`.

## Verified

- Flutter analyzer: no issues. Workflow/explanation/motion suite: 19 passed.
- Original bundled Lottie assets decode, contain no remote images, follow both theme colors and respect reduced motion. Light/dark previews were rendered and visually inspected.
- Release build passed. APK signature v2 verified with the private release key; no debug signing fallback.
- Packaged assets include scan, empty and success motion. ARM64 Dart code contains the hosted API and excludes the local emulator API.
- APK excludes the debug capture harness/test class and private `.env`, model checkpoint, database and keystore files. Native Live Guard service is present.
- Root copy matches the original build's hash. The signing key remains private and must be preserved for future app updates.
- Installed the signed root-copy APK on a clean Android 15/API 35 emulator. Package install succeeded; the normal launcher opened `MainActivity` with `Status: ok`, a cold-start time of 4.717 seconds and no AndroidRuntime crash. The production sign-in screen was captured and visually inspected. This is a release launch check, not a rerun of every signed-in workflow.

## Scope

Earlier Android 15 emulator tests exercised the capture/model/Fake-warning pipeline and production Google PKCE handoff (provider login in the existing desktop browser session). Details and remaining physical-device checks are in `REVIEW_STATUS.md`. Packaging does not establish accuracy across arbitrary AI videos or full compatibility across every phone.

The Chrome companion's approved origin was deployed and pairing succeeded in the installed Chrome extension. The chosen YouTube Short reached the overlay but public-link retrieval failed, so it correctly displayed **Not analyzed**. This is a separate unresolved retrieval limitation; it is not a model verdict or a mobile APK build failure.

Email verification delivery is still paused. No final completion email has been sent.
