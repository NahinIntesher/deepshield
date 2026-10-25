---
tags:
- deepfake-detection
- video-classification
- pytorch
---

# DeepShield checkpoint

Private storage for DeepShield's trained video deepfake detection checkpoint.

| Artifact | Value |
|---|---|
| File | `best_model.pth` |
| Size | 618,147,845 bytes (589.51 MiB) |
| SHA-256 | `be33edbb69a80072439b8ea361ee9b00f635a2604ea2a4b9c1bfabe731067b7e` |
| Architecture | Swin-Small RGB, DCT frequency branch and temporal transformer |
| Input | 16 aligned, normalized face frames |
| Checkpoint epoch | 7 |

This repository stores the original checkpoint. It does not run a prediction API. Use DeepShield's matching model definition and preprocessing pipeline to load it; this is not an AutoModel-compatible Transformers repository.

The detector was trained on videos. Still-image analysis in DeepShield is experimental and has not been validated for image accuracy.

Application databases, account credentials, uploaded user media and training videos are not included.
