# UI review status — 27 October 2026

## Ready to review

The website's shared card, form, button and page hierarchy has been updated. The member dashboard now puts the scan action first. Flutter follows the same solid forest-green/light and charcoal/dark theme, fonts and bilingual content, with Android navigation. The post-Google profile form places every label on its own line.

Mobile research now shows verified model explanations only after the independent answer has been submitted. The research review entry opens the review queue rather than the insights dashboard. SHAP data must pass class, finite-value, additivity, region and preview consistency checks before the comparison is shown. Missing evidence falls back to a clear notice. The underlying checkpoint and classifier have not been retrained or changed.

## Checks completed

- Web production build: passed, 32 generated routes.
- Member layouts: 12 pages at 320/390/768/1024/1440 px in English light and Bengali dark; 120 checks, no page-level horizontal overflow.
- Admin layouts: 9 sidebar pages at the same five widths and two language/theme combinations; 90 checks, no page-level horizontal overflow.
- Public landing, login, signup and admin login: four widths; 16 additional English/light layout checks. Signup's email/name/username/password fields were inspected after hydration.
- Onboarding label geometry: 320/390/768/1440 px; all three labels above their inputs. The admin user editor was checked with a long display name at 390 px.
- Dark admin text contrast: a DOM audit of visible text found no values below the normal/large text thresholds on the tested pages. This is not a full accessibility certification.
- Flutter analyzer: no issues. Flutter tests: 17 passed, including 19 main screens across 320/768 px, English/Bengali and light/dark; owner protection; form validation; retry states; SHAP consistency; research answer order; admin review navigation.
- Flutter browser preview: compiled successfully. Real local API login, dashboard, saved-model explanation and Bengali lesson content were inspected in the browser.
- Backend targeted regressions: 6 passed for native login handoff, overlay alert behavior and research explanations, using an isolated database.
- Android Gradle configuration: `help --offline` passed; no APK task was run. Existing toolchain deprecation warnings remain.
- Public OpenAPI snapshot refreshed from the hosted API: 97 paths. Private credentials, signing keys, test accounts and media previews are excluded from the published mobile source.

## Still pending

APK packaging and installation are on hold at the owner's request. The latest UI changes therefore have not been rerun in a newly packaged Android app. Real MediaProjection permission/capture, selected-app switching and notifications require Android device testing when that phase resumes. The debug capture harness is disabled by default and excluded from release; no permission bypass was used.

Native Google login's final Android handoff still needs a device check. The browser preview uses username login and does not emulate native Google redirects or Android permissions. Room/video platform behavior and actual users' devices need continued integration testing; responsive rendering alone does not prove all workflows across every device.

Email verification delivery remains paused by the owner. Manual bKash review remains manual. Free-host cold starts and inference latency still apply. Usability with adults 55+ and children 11–18 has not been evaluated in a participant study.

No APK has been copied to the Mobile App root and no final completion email has been sent during the hold. Review feedback should be applied to both clients before the owner authorizes APK work.
