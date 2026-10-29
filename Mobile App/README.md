# DeepShield Android app

Flutter client for the existing DeepShield API, database and trained model. Android is the deployment target; the browser build is a UI review preview. It does not replace the deployed Next.js website.

## Connections

- API: `https://api.deepshield.nahin.com.bd`
- Website and Google login handoff: `https://deepshield.nahin.com.bd`
- Public API contract snapshot: `api/openapi.json`
- Change the API address with a Dart define named `API_BASE`. Never embed database credentials, storage credentials or Hugging Face tokens in the app. Inference runs through the authenticated backend.

## Included screens

| Area | Features |
| --- | --- |
| Account | Username login, signup, Google browser handoff, required username/name onboarding, profile, logout |
| Analysis | Image/video upload, 50 MB video limit, supported public links, presets, queued scan status, private history and deletion |
| Results | Real/Fake model answer, verified SHAP region comparisons, enlarged previews, branch/frame values, optional gradient heatmap, model details |
| Learning | Bilingual lessons, lesson quizzes, completion tracking and optional learning assessment |
| Practice | Solo rounds, rooms, leaderboard, research eligibility and independent research evaluation |
| Subscription | Free/Premium usage, manual bKash transaction review and personal CSV export |
| Support | Tickets, notifications, browser companion pairing and preferences |
| Administration | Protected owner account, users, content, records, activity, research sample review, candidate training, service operations and audit history |
| Live Guard | Explicit overlay, usage access and per-session screen sharing permissions; chosen-app scope; pause/stop; Fake-only warnings |

Language and appearance use the same English/Bengali, Quicksand/Baloo Da 2 and solid green/charcoal design direction as the website. Navigation adapts to Android touch interaction.

## Live Guard behavior

YouTube, Facebook and Instagram can be selected separately; TikTok and an explicitly chosen other app are optional. Social-account passwords are not requested. Usage access checks which selected app is in front. Screen capture requires Android's normal MediaProjection consent for each session. Leaving selected apps or locking the device pauses sampling. Pause and Stop remain available.

The current pipeline samples 16 frames over about eight seconds and then waits for backend inference. It is not instantaneous and cannot guarantee detection of every video during fast scrolling. Real results do not generate verdict notifications. A current Fake result may show a possible-deepfake warning; it is not forensic proof. Android still displays its required screen-sharing foreground-service indicator. Quotas and server availability apply.

## Development checks

Use the project Flutter SDK or a compatible installation, then run `flutter pub get`, `flutter analyze` and `flutter test`. A browser preview can be compiled with `flutter build web --no-web-resources-cdn --dart-define=API_BASE=http://localhost:8001` when using the isolated review API. The preview supports username login; native Google handoff and Android permissions require Android testing.

The release keystore and `android/key.properties` are private local files and must remain outside Git. The owner authorized release APK packaging on 27 October 2026. The release entry point is `lib/main.dart`, with the hosted HTTPS API; integration-test entry points must never be distributed.

## Motion

Original bundled Lottie vector artwork appears during session restoration, remote-page loading, scan processing, ordinary empty lists and challenge completion. Loading and scanning loop; empty and success states play once. Empty/success artwork plays once, respects Android reduced-motion preferences, follows light/dark theme colors and contains no embedded language-specific text. It makes no model-accuracy or authenticity claim. The website logo remains the app's brand mark. Assets can be regenerated with `python tool/create_status_art.py`.

## Verification limits

The current automated checks cover responsive screen rendering, authentication validation, protected owner controls, API retry behavior, SHAP contract integrity, research answer order, research review navigation and bundled motion/reduced-motion behavior. Android 15 emulator checks exercised actual MediaProjection capture through the original model: a Real fixture produced no verdict notification; a Fake fixture produced a warning; leaving the selected app cleared the warning and stopping released capture. These are functional examples, not an accuracy benchmark. Earlier lossy capture trials produced false positives and are recorded in private test evidence.

An actual Google account completed the production browser login and the Android PKCE session exchange. The test used the desktop browser's existing Google session for the provider step and delivered its one-time return URI through Android's normal VIEW intent; it did not test typing Google credentials in Android Chrome. The user matched `/auth/me` and the PKCE state/verifier were cleared. No session or Google tokens are published.

Real MediaProjection capture, app-switch behavior and Fake-only alerts across physical Android devices remain pending. Debug capture harnesses are excluded from release and default to disabled. Email verification delivery remains paused by the owner. Free hosting can sleep or cold-start. No claim of universal device support or validated usability for older adults/children is made by layout tests alone.
