# Veritas AI: Swin-Small + DCT + Temporal Transformer

This version integrates the supplied `training/model.py` and the 16-frame InsightFace preprocessing pipeline. It keeps the browser-playback fix, solo/multiplayer games, detector, research challenge and actual-result dashboard.

## 1. Put the new checkpoint here

`model/best_model.pth`

Use the new 589 MB checkpoint from `DeepFake_Research/checkpoints/best_model.pth`. It is not included in this ZIP. The old `best_vit_lstm.pth` is incompatible and is not used. Do not retrain just to run this app.

Your checkpoint dictionary contains `model`, with training metadata such as `epoch` and `stage`. The loader validates every model key/shape strictly, uses all saved Swin weights, and does not download pretrained classification weights. Optimizer and scheduler state are discarded after loading. A checkpoint fingerprint is recorded with research submissions.

## 2. Python setup (Windows, Python 3.10 or 3.11)

Create a separate environment at the extracted project root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

For CUDA, install the PyTorch build compatible with your NVIDIA setup. The app uses CUDA when `torch.cuda.is_available()` is true, otherwise CPU. Face detection uses CPU by default, leaving GPU memory for Swin. This does not change the face model or alignment method.

If `insightface` installation fails while building its Windows extension, use the working InsightFace installation from your training environment or install Microsoft C++ Build Tools and retry. Use the same `timm` version as your training environment if strict checkpoint loading reports incompatible Swin keys; the ZIP did not contain a dependency lockfile.

## 3. Reuse the face detector

The training scripts used InsightFace `FaceAnalysis(name="buffalo_l")`, detection module, size 640 x 640. Its model files are separate from `best_model.pth`.

By default this app looks in:

`C:\Users\YOUR_NAME\.insightface\models\buffalo_l\`

If the app is running under the same Windows user as training, that directory may already exist. Reuse it. A different root can be set before starting the backend:

```powershell
$env:INSIGHTFACE_ROOT="D:\my_insightface"
```

This root must contain `models\buffalo_l\*.onnx`. If no copy exists, run the explicit one-time setup (internet needed):

```powershell
cd backend
python setup_face_model.py
```

Inference does not silently switch to Haar/full-frame crops or synthesize faces when the detector is unavailable. If no sampled frame has an alignable face, analysis returns an error.

## 4. Check the checkpoint, then start

From `backend` with the virtual environment active:

```powershell
python check_model.py
python check_model.py --video ..\videos\real\00037.mp4
python run.py
```

The first command verifies strict checkpoint compatibility. The second runs actual preprocessing and prediction locally. Optionally add `--explain` to test sensitivity maps.

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:3000 and create an account. The default API is http://localhost:8000.

## Videos and games

Add videos to `videos/real/` and `videos/fake/`. The eight supplied example videos are included. Folder names provide the owner's labels used for game scoring; model predictions are computed independently and can be wrong. URLs/titles do not reveal folder labels before answers.

The backend caches H.264/yuv420p MP4 playback copies in `backend/data/browser_media`. It uses FFmpeg from PATH or the executable supplied by imageio-ffmpeg. Originals remain the model inputs. First playback may take a few seconds for conversion. The solo timer starts when playback starts. New videos appear when starting a new game or refreshing the item list.

Games request predictions without expensive gradient explanations. Detector and research endpoints additionally request explanations. Model predictions are cached in memory for repeated requests, keyed by source path/stat, checkpoint path/stat and explanation mode. Replacing the checkpoint or modifying a video invalidates its cached results. Restart the backend after changing face-detector files or preprocessing code.

Missing checkpoint, failed strict loading, missing face model and invalid/no-face media return explicit errors. No invented predictions or confidences are used. A failed research prediction creates no evaluation record. If only the gradient explanation fails, the real prediction is preserved with a visible explanation error.

## Exact preprocessing and architecture

Inference follows the validation preprocessing, with no random training augmentation:

1. OpenCV video frame count; 16 indices from `np.linspace(0,total-1,16,dtype=int)`.
2. JPEG encode/decode matching the frame-extraction JPG files.
3. `buffalo_l` detection, highest detection-score face, bounding-box margin 0.25.
4. Same five target landmarks: (70,90), (154,90), (112,130), (80,170), (144,170).
5. `estimateAffinePartial2D`, warp to 224 x 224, then JPEG encode/decode matching saved aligned JPGs.
6. RGB conversion and ImageNet normalization, matching `normalize_celebdf.py`.
7. Retain successful aligned frames in order. If fewer than 16 remain, repeat the final one as in the supplied DataLoader. The response records detected/repeated counts and source frame indices.

Architecture: `swin_small_patch4_window7_224` (768-D) -> projection (256-D), DCT frequency branch (256-D), 2-layer temporal transformer (4 heads), gated fusion of RGB/frequency/temporal paths, 2-class head. Labels are `0=Real`, `1=Fake`. Classification uses softmax and the higher-probability class. Probabilities are not calibrated certainty.

Frame encoders run one frame at a time in eval mode to reduce peak memory. The temporal/fusion/head equations are unchanged. Inference does not use the training Swin feature cache. No training-stage parameter freezing changes inference outputs in eval mode.

## Explanations

The real model's input gradients produce the heatmap and 16-frame sensitivity curve. Gradients include all three branches. The code differentiates the shared head and replays each frame encoder using the chain rule, so it does not retain sixteen Swin backward graphs simultaneously. These are sensitivity maps, not attention rollout, LRP, verified artifact localization or proof of the cause of an error. Returned fusion-gate averages are learned weights, not causal importance scores.

The heatmap displays the aligned face at the sequence position with greatest mean absolute input gradient. The temporal curve normalizes these means across all positions. Repeated frames are explicitly reported and must not be interpreted as extra observed motion.

## Research records

The new default database is `backend/swin_research.db`, separate from the older `real_data.db`. This prevents earlier ViT-LSTM research results from mixing with the new model's results. You will create a fresh account in this version. Old database files are not deleted. Each new research record includes model SHA-256, model name, checkpoint epoch and preprocessing/explanation metadata. CSV/JSON export includes model identification. Metrics reflect actual submissions only.

The inherited user-ID based login/role/demo-unlock flow remains a local academic prototype, not a production authentication system.

## Checks

```powershell
cd backend
python tests/smoke_test.py
python tests/test_preprocessing.py
```

The smoke test uses a temporary database. Without a checkpoint it checks video streaming, clean data and missing-model handling. With a checkpoint it requires the face detector and tests an actual video's trained prediction. It is not an accuracy benchmark.

```powershell
cd frontend
npx tsc --noEmit
```

The deliverable has no trained checkpoint or ONNX detector files. Architecture/preprocessing code and error paths can be verified here; actual checkpoint compatibility, detector execution and trained accuracy must be verified with your local model files using `check_model.py`.
