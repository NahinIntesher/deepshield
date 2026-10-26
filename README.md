# DeepShield

A face-based deepfake analysis and media-literacy application.

Frontend: https://deepshield.nahin.com.bd (Vercel).
Backend: https://api.deepshield.nahin.com.bd (Render Free, Singapore).
Database: Neon PostgreSQL; private media uses a private Neon storage bucket.
Inference: the original trained checkpoint runs in the private Hugging Face ZeroGPU Space `nahin-intesher/deepshield-inference`.
Vercel root directory: `Frontend`.

See `Backend/docs/HOSTED_SERVICES.md` for verification and free hosting limits.

## Project layout

- `Backend/` — FastAPI, authentication, admin APIs, migrations, tests and documentation.
- `Frontend/` — Next.js UI, local fonts, browser extension and its legacy source.
- `Model/` — trained checkpoint and the original sample videos.
- `Database/` — SQLite database, private uploads, library additions, replay memory, backups and logs.

`.venv` is a local Python environment, not a deployment package. Keep `.env`, databases, model weights and private media out of public static hosting.

## Run locally on Windows

From the project root:

```powershell
.\Start-DeepShield.ps1 -Build
```

Or start the services separately:

```powershell
cd F:\fydp\Backend
..\.venv\Scripts\python.exe run.py
```

```powershell
cd F:\fydp\Frontend
npm run build
npm start
```

Web: http://localhost:3000 · Admin: http://localhost:3000/admin/login · API: http://localhost:8000/docs.

The existing owner username is `admin`. Its password is not stored in this documentation. To rotate it locally, run `Backend/reset_admin.py` with the project Python environment and enter `admin`.

## Accounts and management

Roles are **Admin**, **Researcher** and **Participant**. There is one owner Admin. Former Moderator accounts are migrated to Participant with their history preserved and old access tokens revoked.

The Admin can create, read, edit and delete non-admin accounts. Account deletion requires the exact username, blocks active scans/games, removes dependent private records and uploaded media, and records the action. The owner account cannot be edited or deleted through account-management APIs. Audit history and payment-reference fingerprints are retained.

Admin Content manages bilingual lessons and the game/research video library. Archive/restore preserves existing references. Updating a lesson quiz resets that lesson's completion while retaining attempt counts. Admin Records manages scan names, support records, pending subscription metadata and research review notes. Original model predictions and original research answers cannot be rewritten. Records are created by their actual scan, game, support and research workflows.

## Analysis

The existing Swin + DCT + temporal-transformer checkpoint and 16-frame video preprocessing are retained. Uploads support JPG/JPEG, PNG and static WebP up to 20 MiB; videos support MP4, MOV, AVI, MKV and WebM up to 50 MB / 10 minutes. A face is required.

**Still-image analysis is experimental.** One aligned face is repeated across 16 model positions. No motion analysis is claimed; the image heatmap sums signed gradients across the tied inputs before taking magnitude. Image accuracy is not validated. A local frame extracted from a Real-labelled video produced a Fake prediction, demonstrating that video performance must not be assumed for images.

Images and videos share the existing daily allowance. Public-link and extension retrieval remain video-only. Deleting completed results does not refund used quota; failed/cancelled queued scans are refunded.

## Membership

bKash recipient: **01815808291**. Default Premium: **BDT 299 / 30 days**. The member pays independently, submits the transaction ID and waits for Admin verification. Approval requires the Admin to confirm the actual recipient, amount and transaction. This is manual payment verification; no gateway, PIN/OTP collection or automatic charge is implemented. Academic demonstration access remains explicitly separate from paid activation.

## Configuration and hosting

See `Backend/.env.example` and `Frontend/.env.local.example`. Set `GOOGLE_CLIENT_ID` only on the backend; the browser receives the public client ID from `/api/auth/providers`. No Google client secret is needed for this flow.

Paths can be moved using `DATA_ROOT`, `MODEL_ROOT`, `CHECKPOINT_PATH`, `VIDEOS_DIR` and `DATABASE_URL`. Hosted prediction runs in the private Hugging Face Space configured by `MODEL_SPACE_ID`; without remote configuration the Backend can load a local checkpoint. The `Model` folder contains weights and deployment source. Set the frontend's `NEXT_PUBLIC_API_URL` before building. The hosted deployment uses exact HTTPS origins, secure cookies and server-side secrets.

More detail:

- `Backend/docs/GOOGLE_SIGN_IN.md`
- `Backend/docs/CONTINUAL_LEARNING_SETUP.md`
- `Backend/docs/CRUD_OPERATIONS.md`

## Verify

```powershell
cd F:\fydp\Backend
..\.venv\Scripts\python.exe -m pytest -q tests/test_platform.py tests/test_migrations.py tests/test_backup.py tests/test_image_preprocessing.py
..\.venv\Scripts\python.exe tests/test_preprocessing.py
```

```powershell
cd F:\fydp\Frontend
npm run lint
npm run build
```

Backups: `python backup.py backup`. Verify: `python backup.py verify --source PATH`. Restore to a **new** database file: `python backup.py restore --source BACKUP --destination NEW_DATABASE`. Stop the API before switching database/media snapshots. Keep the corresponding `Database` media directories with a database backup; a database alone does not contain uploaded files.
