# Hosted DeepShield services

Frontend: https://deepshield.nahin.com.bd
Backend: https://api.deepshield.nahin.com.bd
Render fallback: https://deepshield-api-4ujd.onrender.com
Render service display name: deepshield (renaming did not change its public URL).
Database: Neon DeepShield, Singapore, PostgreSQL, private credentials.
Private media: Neon deepshield-media bucket. Eight existing library videos persisted.
Inference: private nahin-intesher/deepshield-inference Hugging Face ZeroGPU Space.
Original model SHA-256: be33edbb69a80072439b8ea361ee9b00f635a2604ea2a4b9c1bfabe731067b7e

## Verified
Real supplied video was uploaded through the hosted Render API, stored privately,
analyzed by the hosted original checkpoint and returned Real (98.10317158699036%).
Visual explanation succeeded (xai_error=null). The verification scan was deleted.
Administrator login, anonymous admin rejection (401), and eight library items passed.
Hosted frontend connects to the custom HTTPS API; real browser admin and Google login passed.
A real prediction through the custom API returned the original checkpoint and heatmap.

43 isolated backend functional tests passed during hosting verification. Frontend release checks are recorded separately.
Video upload limit: 50,000,000 bytes (50 MB), including the model service.
Google accounts must choose username and display name before protected app access.
Optional onboarding password permits later username/password login.

## Deferred by user
Email verification delivery is disabled (EMAIL_VERIFICATION_REQUIRED=false by default).
Regular signup requires a syntactically valid email, without claiming ownership verification.
Brevo account is Under review / sending paused. No sender/domain changes were made.
The implemented verification workflow must remain disabled until domain authentication,
provider approval, server secrets and a real delivered-email test are completed.

## Free hosting limitations
Render may sleep while idle and take 50 seconds or more to resume.
Hugging Face ZeroGPU has a shared account quota; prediction availability is not unlimited.
Vercel hosts the frontend; a local isolated database is used for UI review.

The original backend deployment is live; later source releases are tracked in Git history.
Final live check: actual 50,000,001-byte upload rejected with 413; a permitted video returned original-model prediction plus a nonempty heatmap. Verification scan cleanup returned 200.
Evidence: docs/review/final-hosting-verification.json, hosted-admin-desktop.jpg, hosted-admin-mobile.jpg.
