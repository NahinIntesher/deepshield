# Verification of this integration

Passed in the implementation environment:

- Python syntax compilation and frontend TypeScript checking.
- 224 x 224 alignment geometry, training-equivalent JPEG round-trip and validation normalization, 16-frame packing, last-frame padding and no-face rejection (deterministic fixtures, not a real detector).
- Chunked forward calculation versus the supplied network's forward, and chain-rule replay gradients versus direct input gradients (seeded test-only weights; no prediction or accuracy claims).
- Safe checkpoint deserialization with NumPy metric scalars representative of the training checkpoint format.
- API smoke test: indexing all eight actual videos, byte-range playback, fresh dashboard metrics, game submission, explicit missing-checkpoint errors, and no research records on failed prediction.
- All eight source videos are byte-identical to the supplied videos ZIP.

Not verified here:

- The user's 589 MB best_model.pth was not uploaded, so strict trained weight compatibility and trained predictions are untested.
- The buffalo_l ONNX detector assets were unavailable, so actual face detection/alignment execution is untested here.
- GPU performance, memory usage on the GTX 1660 Super, model accuracy, and end-to-end playback on the user's browser are untested.

Local completion check (run inside backend with the configured environment):

```powershell
python check_model.py
python check_model.py --video ..\videos\real\00037.mp4
```

Use `--explain` to test full input-gradient sensitivity after ordinary prediction succeeds. No random or static prediction fallback exists in the application.
