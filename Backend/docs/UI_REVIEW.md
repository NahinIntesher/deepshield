# UI review — 26 October 2026

This release adds a public landing page while preserving the signed-in dashboard and all member/admin routes. Solid green accents, charcoal dark surfaces, local Quicksand/Baloo Da 2 fonts and shared controls apply across the application.

## Changes

- Responsive public navigation and member/admin drawers, Escape handling and focus restoration.
- Login/signup, administrator login and centered onboarding/email screens; visible loading and validation feedback.
- Session restoration distinguishes authentication expiry from connection failure and offers retry.
- Responsive Google button and retry for provider configuration failures.
- Readable dark/light status colors, chart legends, research labels, inputs, tables and empty states.
- Shorter English/Bengali interface copy; translated research clues, account heading and result frame labels.
- Admin editors scroll into view and focus an input. Owner account protection and deletion confirmations remain.

## Validation

Local UI review used an isolated SQLite database and separate backend, without editing production accounts. Observations covered all member routes, ten administrator routes, public login/signup, email error and 404 screens, at CSS widths 320, 390, 768 and 1440 as appropriate. Both English/Bengali and light/dark were exercised; intermediate defects were fixed during review. Tables, lesson lists and activity charts intentionally scroll within their containers.

Browser interactions included signup to dashboard, invalid email, incorrect password, password visibility, keyboard login tabs, Bengali lesson quiz success, navigation Escape/focus restoration, admin create/delete confirmation cancellation, editor focus, qualified research verdict and confidence controls, support submission and connection retry. A real supplied video completed inference and displayed its prediction and heatmap in both themes.

Type checking and the production Next.js build passed (31 routes). The selected backend regression suite passed 39 tests. Stored UI observations and screenshots are local review artifacts, excluded from the public repository.

## Limits

Responsive browser emulation is not a physical-device certification. Not every possible populated dataset or destructive action was exercised through the browser. Email verification delivery remains disabled at the user's request. Free backend cold starts and shared inference quota remain service limits. Still-image accuracy is unvalidated. These checks do not constitute an unconditional production-readiness certification.
