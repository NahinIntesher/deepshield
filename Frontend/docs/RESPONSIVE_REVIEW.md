# Responsive review — 29 October 2026

## Changes

- Authentication containers explicitly fill their available width; desktop columns use minmax(0, ...), and forms can shrink safely.
- On narrow phones, scan-source tabs place the icon above readable 14px labels with touch targets of at least 64px.
- The mobile brand scales down inside constrained headers. The actual 320px Bengali/130% text overflow is covered by a regression check.
- Records no longer render rows from a previous endpoint while changing category. The old Scan-to-Research transition crashed in Bengali; repeated Scan/Research/Support/Subscription switching was verified after the shared hook fix.
- Missing optional translation input cannot crash the interface; known scan status copy is localized without rewriting users' notes.
- Language changes update the document language before rerendering locale-sensitive dates.
- Additional empty activity/training/subscription views use the shared local Not Found animation. Errors retain their error/retry flow.

## Browser checks

Local production build and a separate isolated review preview were used. The production database was not reset. Fixtures include long names, long support messages, a long payment reference, saved scans and the learning library. Review account credentials and screenshots remain private.

Widths checked: 320, 390, 768, 1024 and 1440 CSS pixels; short 320x568 and landscape 768x540 windows were also inspected. English/light and Bengali/dark layouts were checked. This is representative coverage, not every possible width/theme/browser combination.

- Public/authentication: landing, login, signup mode, admin login, verification status, mobile handoff status, guide and 404.
- Member/researcher: overview, media analysis, history, companion, learning, game lobby, assessment entry, research challenge, insights, subscription, support and account.
- Admin: overview, users, content, records, activity, research, training, operations, audit and subscription management.
- Expanded states: onboarding labels, account editor, English/Bengali lesson editor, video upload metadata form, record editor with a long ID, all record categories, public-link input tab, and a short-phone sidebar with logout pinned inside the viewport.

Measured main layouts had no document-width overflow in the saved cases. Scrolling within legitimate tables/media viewers is separate from whole-page overflow. Saved screenshots use actual viewports: the browser's full-page export distorted the signup layout and is not reliable evidence.

## Limits

This review did not execute destructive deletes, approve real payments, start model training, or prove every media/player/keyboard combination on physical hardware. The hosted YouTube test still failed with platform_restriction; it is not a model result. Email delivery remains paused by the owner. Physical-phone live social scrolling and Google sign-in still require device checks.
