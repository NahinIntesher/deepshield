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

The release keystore and `android/key.properties` are private local files and must remain outside Git. APK generation is explicitly on hold until the owner approves it after review. Do not run APK packaging, install an APK, copy an APK to the project root or send a completion email during this hold.

## Verification limits

The current automated checks cover responsive screen rendering, authentication validation, protected owner controls, API retry behavior, SHAP contract integrity, research answer order and research review navigation. Earlier Android integration checks covered account navigation, saved results and an actual scan. The latest UI changes still need a new Android run once APK testing resumes.

Real MediaProjection capture, app-switch behavior and Fake-only alerts across physical Android devices remain pending. Debug capture harnesses are excluded from release and default to disabled. Email verification delivery remains paused by the owner. Free hosting can sleep or cold-start. No claim of universal device support or validated usability for older adults/children is made by layout tests alone.
