"""Strict Swin checkpoint inference. Untrained models are never used for predictions."""
import hashlib
import threading
import numpy as np
import torch
from ..config import CHECKPOINT_PATH, MODEL_NAME, NUM_FRAMES
from .swin_model import DeepfakeModel

class ModelUnavailable(RuntimeError):
    pass


def load_training_checkpoint(path):
    # sklearn metrics in the supplied training checkpoint may contain numpy scalars.
    # Explicitly allow those data types; do not enable arbitrary pickle execution.
    if tuple(int(n) for n in torch.__version__.split("+")[0].split(".")[:2]) < (2,6) or not hasattr(torch.serialization, "safe_globals"):
        raise RuntimeError("This Python environment has an incompatible PyTorch installation. Run backend/repair_torch.ps1 with the same virtual environment used to start the API, then restart it. PyTorch 2.6 or newer is required; unsafe pickle loading is disabled.")
    scalar = np.core.multiarray.scalar
    allowed = [np.dtype, (scalar, 'numpy.core.multiarray.scalar'),
               (scalar, 'numpy._core.multiarray.scalar')]
    allowed += [type(np.dtype(t)) for t in (np.float64, np.float32, np.int64, np.int32, np.bool_)]
    with torch.serialization.safe_globals(allowed):
        return torch.load(path, map_location='cpu', weights_only=True)


def classify_features(model, raw, frequency):
    """Same equations as training/model.py.forward, separated for chunked inference."""
    r = model.rgb_proj(raw)
    rgb = r.mean(1)
    freq = frequency.mean(1)
    temp = model.temporal(r + model.pos[:, :raw.shape[1]]).mean(1)
    fused, gates = model.fusion(rgb, freq, temp)
    return model.cls(fused), gates


class ModelManager:
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.signature = None
        self.checkpoint_sha256 = None
        self.checkpoint_epoch = None
        self.lock = threading.RLock()
        self.is_custom_checkpoint_loaded = False
        self.last_error = None

    def ensure_loaded(self):
        if not CHECKPOINT_PATH.is_file():
            self.is_custom_checkpoint_loaded = False
            self.model = None
            self.last_error = 'Missing model/best_model.pth. Copy your new 589 MB checkpoint into that folder and retry.'
            raise ModelUnavailable(self.last_error)
        stat = CHECKPOINT_PATH.stat()
        signature = (str(CHECKPOINT_PATH.resolve()), stat.st_size, stat.st_mtime_ns)
        if self.model is not None and self.signature == signature:
            return
        self.model = None
        self.is_custom_checkpoint_loaded = False
        self.checkpoint_sha256 = None
        try:
            ckpt = load_training_checkpoint(CHECKPOINT_PATH)
            if not isinstance(ckpt, dict) or 'model' not in ckpt:
                raise ValueError('Expected checkpoint["model"] from the supplied train.py or train_recovery.py. The old ViT-LSTM checkpoint is incompatible.')
            model = DeepfakeModel(pretrained=False)
            model.load_state_dict(ckpt['model'], strict=True)
            epoch = ckpt.get('epoch')
            del ckpt  # Optimizer/scheduler state is not needed for inference.
            model.set_stage(2)
            model.eval().to(self.device)
            for param in model.parameters():
                param.requires_grad_(False)
            digest = hashlib.sha256()
            with CHECKPOINT_PATH.open('rb') as f:
                for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    digest.update(chunk)
            self.model, self.signature = model, signature
            self.checkpoint_sha256 = digest.hexdigest()
            self.checkpoint_epoch = int(epoch) if epoch is not None else None
            self.is_custom_checkpoint_loaded = True
            self.last_error = None
        except Exception as exc:
            self.last_error = f'Cannot load new trained model: {exc}'
            raise ModelUnavailable(self.last_error) from exc

    def predict(self, prepared, explain=True):
        from .xai_engine import render_saliency, encode_face, sensitivity_layer
        if prepared.tensors.shape != (NUM_FRAMES, 3, 224, 224):
            raise ValueError('Expected 16 normalized, aligned RGB frames')
        with self.lock:
            self.ensure_loaded()
            model = self.model
            x = torch.from_numpy(np.ascontiguousarray(prepared.tensors)).to(self.device)
            # One frame at a time keeps peak Swin memory small on the 6 GB GPU.
            with torch.no_grad():
                raw = torch.cat([model.rgb(frame[None]) for frame in x]).unsqueeze(0)
                freq = torch.cat([model.freq(frame[None]) for frame in x]).unsqueeze(0)
                logits, gates = classify_features(model, raw, freq)
                probs = logits.softmax(1)[0]
                if not torch.isfinite(probs).all():
                    raise ValueError('Model produced non-finite probabilities')
                cls = int(probs.argmax())
                fake_prob = float(probs[1])
                confidence = float(probs[cls]) * 100
            is_image = prepared.media_type == 'image'
            image_warning = ('Experimental image analysis: this detector was trained on videos, not validated on still images. '
                             'One aligned face is repeated 16 times; no motion evidence is available.')
            notes = [image_warning] if is_image else [f'{prepared.detected_frames}/16 sampled frames yielded aligned faces; {prepared.repeated_frames} final-frame repetitions.']
            heatmap, temporal = None, []
            frame_details = []
            focus_frame = None
            xai_error = None
            if explain:
                try:
                    # Chain rule: differentiate the shared head once, then replay each
                    # frame encoder. Includes RGB, frequency and temporal paths without
                    # retaining all 16 Swin activation graphs at once.
                    with torch.enable_grad():
                        r_leaf = raw.detach().requires_grad_(True)
                        f_leaf = freq.detach().requires_grad_(True)
                        head_logits, _ = classify_features(model, r_leaf, f_leaf)
                        dr, df = torch.autograd.grad(head_logits[0, cls], (r_leaf, f_leaf))
                        maps = []
                        image_gradient = None
                        for i in range(NUM_FRAMES):
                            frame = x[i:i+1].detach().requires_grad_(True)
                            spatial = model.rgb(frame)
                            frequency = model.freq(frame)
                            objective = (spatial * dr[0,i]).sum() + (frequency * df[0,i]).sum()
                            grad = torch.autograd.grad(objective, frame)[0]
                            if is_image:
                                # All 16 inputs originate from the same still. Sum the
                                # signed derivatives before taking magnitude (chain rule).
                                part = grad[0].detach().cpu()
                                image_gradient = part if image_gradient is None else image_gradient + part
                            else:
                                maps.append(grad[0].abs().mean(0).detach().cpu())
                            del frame, spatial, frequency, objective, grad
                    saliency = image_gradient.abs().mean(0)[None] if is_image else torch.stack(maps)
                    scores = saliency.mean((1,2))
                    if not torch.isfinite(scores).all():
                        raise ValueError('Non-finite sensitivity values')
                    temporal = [] if is_image else (scores / scores.sum()).tolist() if scores.sum() > 0 else [0.0] * NUM_FRAMES
                    best = int(scores.argmax())
                    focus_frame = best
                    heatmap = render_saliency(prepared.frames[best], saliency[best].numpy())
                    frame_details = [{'position':i,'source_frame':prepared.source_indices[i],'timestamp':prepared.source_indices[i]/prepared.fps if prepared.fps else None,'image':encode_face(prepared.frames[i]),'overlay':sensitivity_layer(saliency[i].numpy()),'sensitivity':1.0 if is_image else temporal[i],'repeated':False if is_image else i >= prepared.detected_frames} for i in range(1 if is_image else NUM_FRAMES)]
                    notes += ['Input-gradient map: combined sensitivity of the single repeated image.' if is_image else f'Input-gradient map: sequence position {best+1}, source frame index {prepared.source_indices[best]}.',
                              'Sensitivity uses all three model paths. It does not prove a forensic artifact.']
                except (RuntimeError, ValueError) as exc:
                    xai_error = f'Prediction succeeded, but sensitivity calculation failed: {exc}'
                    notes.append(xai_error)
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()
            shap_result, shap_error = None, None
            if explain:
                try:
                    from .shap_explanation import explain_prediction
                    shap_result = explain_prediction(model, x, raw, freq, prepared, cls, classify_features)
                except Exception as exc:
                    # Additional explanations must never replace a real prediction
                    # with a guessed verdict or silently fabricated attribution.
                    shap_error = f'SHAP explanation unavailable: {type(exc).__name__}: {str(exc)[:200]}'
                    if self.device.type == 'cuda':
                        torch.cuda.empty_cache()
            return {
                'media_type': prepared.media_type,
                'analysis_mode': 'repeated_still_experimental' if is_image else 'video_sequence',
                'experimental': is_image, 'analysis_warning': image_warning if is_image else None,
                'temporal_analysis_available': not is_image,
                'verdict': ['Real','Fake'][cls], 'fake_probability': fake_prob,
                'confidence_percentage': confidence, 'model_name': MODEL_NAME,
                'model_checkpoint_loaded': True, 'spatial_heatmap_base64': heatmap,
                'temporal_scores': temporal, 'detected_artifacts': notes,
                'verification_tips': ['Check the original source independently. Model probabilities are not calibrated certainty.'],
                'model_id': self.checkpoint_sha256, 'checkpoint_epoch': self.checkpoint_epoch,
                'fusion_gates': dict(zip(('rgb','frequency','temporal'), gates[0].cpu().tolist())),
                'frame_indices': prepared.source_indices, 'detected_frames': prepared.detected_frames,
                'repeated_frames': prepared.repeated_frames, 'xai_error': xai_error,
                'frame_details':frame_details,'focus_frame':focus_frame,
                'shap_explanation': shap_result, 'shap_error': shap_error,
                'explanation_method': ('input_gradient_and_shap' if frame_details else 'shap') if shap_result else ('input_gradient' if frame_details else None),
            }

model_manager = ModelManager()
