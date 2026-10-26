# Responsive layout, copy and playback follow-up — 27 October 2026

## Fixed

- Shared responsive tables retain desktop columns and display labelled record cards below 1000 CSS pixels. Applied to Users, Content, Records, activity tables, scan history, profile and dashboard tables. Long names and account forms wrap without hiding actions.
- Authored Bengali UI copy uses contextual wording for file selection, source, delete, activity, roles and model results. Existing course data is formatted for display without resetting quiz progress or replacing administrator content in the database.
- Heatmap viewer compares the original face and recorded sensitivity layer. It adds overlay/map modes, raw/enhanced visibility, opacity, zoom and a keyboard-accessible enlarged dialog. Enhanced visibility uses a monotonic square-root colour mapping scaled to the frame's 98th-percentile alpha; zero values stay zero. No model score, gradient source, model weight or temporal score is changed.
- Private video playback uses pre-encoded H.264 fast-start copies, up to 720p, with byte-range streaming. The backend authenticates each media request and streams the requested storage range instead of downloading and transcoding a complete original first. Storage remains private. Original videos remain unchanged for inference.
- New library uploads prepare a playback copy in the background. Existing eight library videos were prepared before rollout.

## Checks

44 isolated backend tests passed, including range parsing, suffix/invalid ranges, byte-limited streaming, body cleanup, private cache headers, HEAD and conditional responses. Frontend production build and type validation passed. Browser review recorded 86 layout observations across member, admin and public routes at phone/tablet/desktop widths, with long-name/edit-form and enlarged-heatmap checks. This is browser viewport testing, not physical-device certification.

Before rollout, three live original playback paths took 50.244, 105.789 and 33.292 seconds to deliver their first 8192-byte chunk after login. Post-deployment timing is recorded in local review artifacts. Render cold starts and external network latency remain independent limits.
