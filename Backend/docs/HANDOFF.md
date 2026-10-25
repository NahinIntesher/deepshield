# DeepShield · UI/UX & Integration Handoff

## What was preserved
- Swin-Small + DCT + 2-layer temporal transformer + gated fusion architecture, checkpoint expectations and **16-frame InsightFace** preprocessing.
- Direct video upload, trained inference + gradient sensitivity explainability, saved detection details.
- All existing lessons, solo/multiplayer gamification, human–AI research flow, eligibility logic, research metrics, dashboard, profiles and administrative research modules.
- Existing local SQLite database and the eight provided labeled test videos. Database migration v0003 is additive and does not overwrite historical results.

## New work
- Reworked visual design system, responsive navigation, landing dashboard and detector analysis flow, refinements across existing cards/forms/tables, small Bengali/English navigation + main screen translation toggle.
- Public YouTube/Facebook/Instagram **link analysis** with an allowlist, public-only download extraction, 250 MiB/10 min bounds, temporary media lifecycle and explicit errors.
- Chrome/Edge MV3 **opt-in visible video** extension. Permission via clicking browser action, enabled per tab, captures visible on-screen frames and displays real model predictions. Token pairing is seven days, revocable and hashed in the DB.
- Member subscription statuses, Premium access requests, 5 daily free vs 50 daily premium link/extension scans, admin verification/activation (30-day default), audit entries, no fake payment confirmations.
- Detection-history deletion button; account token revocation and explicitly safer admin bootstrap (no hardcoded default password for new DB).
- DB migration `0003_integrations`, extra integration tests, local security headers, basic inference concurrency gate for new routes.

## Not provided or claimed
- **No model weights**: supply `model/best_model.pth` (~589–600 MiB) yourself. InsightFace files also separate. We cannot reproduce your 90% AUC / 86% accuracy or infer live here.
- **No payment integration**: needs genuine bKash/Nagad/Rocket merchant credentials, callback signing and compliance. Only a request workflow and admin-controlled activation are built. Do not tell a supervisor that payments are live.
- **No Android/iOS app** and no mobile system overlay. Extension targets desktop Chrome/Edge; actual website feed variants still require browser QA.
- **Partial bilingual support** only: navigation, landing and key detector labels; all remaining pages would need translation for complete localization.
- **Not certified production-ready**: full `npm ci && npm run build`, browser testing of all 3 sites, GPU inference, scale/load, egress SSRF controls, web security review, HTTPS deployment, paid merchant verification and realistic research benchmarks are required.

## Setup (Windows PowerShell)
1. Extract this archive. Confirm `backend`, `frontend`, `browser-extension`, `videos` and `model` folders.
2. Copy `best_model.pth` to `model/best_model.pth` and ensure InsightFace `buffalo_l` exists under `%USERPROFILE%\.insightface\models\buffalo_l`.
3. Backend from project root:
   ```powershell
   py -3.10 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend\requirements.txt
   cd backend
   python reset_admin.py
   python check_model.py
   python run.py
   ```
   If your working environment already has a compatible `timm`, PyTorch and InsightFace setup, reuse it. `reset_admin.py` runs the additive database migration automatically before updating credentials.
4. Separate terminal:
   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```
   Open <http://localhost:3000>, sign in and test local uploads first.
5. Open `/extension` in the signed-in web app, generate a token; use Chrome/Edge **Load unpacked** to add `browser-extension`. Start backend locally and follow extension README. Token should never be shared.
6. Use `/subscription` for Premium request and `/admin/subscriptions` for admin verification/activation. **Manual status only—no money is charged.**

## Checks performed for this handoff
- Python `compileall` passed for application and migrations.
- JavaScript `node --check` passed for extension code.
- 31 TS/TSX frontend files successfully parsed/transpiled by TypeScript 5.8.3 (syntax verification, **not** a Next.js build).
- Backend tests: `11 passed` with `ADMIN_INITIAL_PASSWORD=deepshield` on **temporary test databases** (including link validation, extension quotas/tokens, subscription review, existing auth/game tests, migrations).
- Model math test could not be collected because `timm` was missing in this environment; actual model checkpoint absent.
- npm registry access was unavailable (`EAI_AGAIN`), so `npm ci` and an actual frontend build could not be completed here. Install dependencies on a machine with network access and run `npm run build` plus `npm run lint` before deployment.

## Operational notes
- For existing `backend/swin_research.db`, check historical admin credentials: **rotate immediately** using `backend/reset_admin.py` (no default password is used for fresh installs).
- Internet access to YouTube/Facebook/Instagram extractors requires `yt-dlp` and possibly FFmpeg; authentication walls and platform protection aren't bypassed. Downloading links in a public SaaS requires network egress restrictions and rate limiting.
- The extension service is **local-only** (`http://localhost:8000`); remote production requires an HTTPS API host configured consistently in its manifest and background script.
- Current 5 vs 50 daily quotas cover **link/extension scans**, not legacy upload/game/research requests, to avoid changing existing project behavior.
