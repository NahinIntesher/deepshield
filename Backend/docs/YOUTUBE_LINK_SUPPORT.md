# Public video retrieval

Both the website's public-link scans and Browser Companion use `services.links.retrieve` and its restricted `social_worker.py` subprocess.

The deployment must install `yt-dlp[default]`, which includes the matching `yt-dlp-ejs` challenge solver, and provide a supported JavaScript runtime. The worker discovers Deno or Node from PATH and explicitly enables it. Render's native Python environment includes Node at runtime. No cookies, account credentials, proxy rotation or remote solver components are enabled. Existing non-public-IP, 50 MB, duration, single-video and subprocess-time limits remain enforced.

yt-dlp raises `MaxDownloadsReached` after its single permitted download completes. Only that specific signal is accepted, and only when exactly one completed media file within the size limit exists. Other retrieval failures still fail the job.

On 28 October 2026, the owner's public YouTube Short (`9pEx7ZaD_6I`) downloaded successfully in the local restricted worker with Node 22.11.0 and the bundled EJS components; approximately 729 KiB. This verifies local retrieval, not a universal promise that YouTube will serve every public video from a cloud IP. Hosted deployment and model-result checks must be recorded separately.

Private, age-restricted, login-only and DRM-protected content is not bypassed. A refused video remains unclassified; the UI must not show a fabricated Real/Fake result. Runtime failures and platform refusals are logged by category without recording social cookies or credentials.

References: [yt-dlp EJS setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS), [Render native runtime tools](https://render.com/docs/native-runtimes).
