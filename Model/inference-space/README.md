---
title: DeepShield inference
emoji: 🛡️
colorFrom: gray
colorTo: gray
sdk: gradio
python_version: '3.10'
app_file: app.py
suggested_hardware: zero-a10g
---

# DeepShield inference

Private inference service for the original Swin-Small + DCT + temporal transformer checkpoint. The SHA-256 is checked before serving requests. The same face alignment, JPEG, normalization and 16-frame inference code as the Backend is bundled in `runtime.zip`.

The API `/predict` accepts an uploaded image/video and an explanation flag. Still-image results are experimental. No database or account credentials are stored here. Free ZeroGPU usage is subject to queueing and daily GPU-time quotas; it is not an unlimited production service.
