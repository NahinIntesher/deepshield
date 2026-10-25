# DeepShield Video Insight · Chrome/Edge MV3

**Local academic prototype**: requires the DeepShield FastAPI backend running at `http://localhost:8000`, a configured `best_model.pth`, and a working face-alignment model. Nothing predicts without the actual checkpoint.

## Install
1. Start the backend and frontend, sign in to the web app.
2. Open `/extension` in the web app and generate a connection token.
3. Visit `chrome://extensions` or `edge://extensions`, enable Developer mode, click **Load unpacked**, and select this `browser-extension` folder.
4. Open the extension popup, paste the token, and connect; token expires in 7 days.
5. Navigate to a **playing, visible** YouTube, Facebook or Instagram video. Click the extension toolbar icon (this grants browser active-tab screenshot permission). Enable auto-scan or click Scan current video.
6. Keep the selected browser tab visible until frame capture and analysis complete. Review the on-video indicator and account history.

## What it does
- User-authorized `chrome.tabs.captureVisibleTab` screenshots are cropped in the content script to the visible video region, then recorded to a temporary WebM. Sixteen captures take approximately 15 seconds. The model reads sampled aligned faces via the original inference pipeline.
- Scans only after toolbar action grants permission. Per-tab on/off setting; output has predicted Real/Fake, model softmax score and failed-analysis states.
- Exact access token stored only in extension-local storage, not injected into any social website. Server stores SHA-256 of its token. Revoke via web app.
- The backend removes temporary media after inference. It stores the result in the member's history, not a persistent copy of the video.
- Limited to *currently visible* video: this may include page controls or partial crops. It **cannot** bypass DRM, authentication, private videos, tab-capture browser restrictions or social-media CORS protections. It is not a cross-browser mobile overlay and isn't independently validated on every feed variant.

## Production hardening required
This extension deliberately targets local development. For remote use, use HTTPS, configure explicit production host permission and backend CORS, distribute through a trusted channel, obtain informed consent, complete platform-specific UI checks, rate-limit per account at the edge, and test network failures plus real GPU load.
