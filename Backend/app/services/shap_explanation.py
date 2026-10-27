"""Post-hoc SHAP for the frozen trained model. No fitting or weight updates.

All three games compare the same original input against a deterministic Gaussian-
blurred version of that input. These are input-reference attributions, not verified
manipulation labels or population-average causal explanations.
"""
import math
import base64
import io
import time
import numpy as np
import torch
from PIL import Image, ImageFilter

REGIONS = (
    ('eyes', ((42, 62, 98, 112), (126, 62, 182, 112))),
    ('nose', ((88, 112, 136, 148),)),
    ('mouth', ((56, 148, 168, 204),)),
    ('other', ()),
)


def region_masks():
    masks = []
    for _, rectangles in REGIONS[:3]:
        mask = np.zeros((224, 224), dtype=bool)
        for x1, y1, x2, y2 in rectangles:
            mask[y1:y2, x1:x2] = True
        masks.append(mask)
    masks.append(~np.logical_or.reduce(masks))
    return np.stack(masks)


def blur_reference(frames, device):
    """Keep the established alignment and normalization; blur RGB detail only."""
    mean = np.array([.485, .456, .406])
    std = np.array([.229, .224, .225])
    blurred = [frame.convert('RGB').filter(ImageFilter.GaussianBlur(radius=8)) for frame in frames]
    arrays = [((np.asarray(f) / 255. - mean) / std).astype(np.float32).transpose(2, 0, 1) for f in blurred]
    return torch.from_numpy(np.ascontiguousarray(np.stack(arrays))).to(device)


def encode(model, frames):
    # The same chunked frame encoders used by the production classifier.
    return (torch.cat([model.rgb(f[None]) for f in frames]).unsqueeze(0),
            torch.cat([model.freq(f[None]) for f in frames]).unsqueeze(0))


def probability(margin):
    return 1.0 / (1.0 + math.exp(-max(-700.0, min(700.0, float(margin)))))


def explain_game(score, names, *, exact=True):
    import shap
    count = len(names)
    background = np.zeros((1, count), dtype=np.float64)
    if exact:
        explainer = shap.ExactExplainer(score, background, feature_names=names)
        result = explainer(np.ones((1, count)), max_evals=2**count, batch_size=32)
    else:
        explainer = shap.PermutationExplainer(score, background, feature_names=names, seed=0)
        result = explainer(np.ones((1, count)), max_evals=2*(count+1)*8, batch_size=32, silent=True)
    base = float(np.asarray(result.base_values).reshape(-1)[0])
    values = np.asarray(result.values, dtype=np.float64).reshape(-1)
    output = float(np.asarray(score(np.ones((1, count)))).reshape(-1)[0])
    error = abs(base + float(values.sum()) - output)
    if not np.isfinite(values).all() or not all(math.isfinite(v) for v in (base, output, error)) or error > 5e-4:
        raise ValueError('SHAP additivity check failed')
    return {'algorithm': 'exact' if exact else 'permutation',
            'feature_names': names, 'values': values.tolist(), 'base_value': base,
            'output_value': output, 'additivity_error': error,
            'max_evals': 2**count if exact else 2*(count+1)*8,
            'seed': None if exact else 0}


def explain_prediction(model, x, raw, frequency, prepared, cls, classify_features):
    start = time.perf_counter()
    if model.training:
        raise ValueError('Explanation requires the trained model in evaluation mode')
    other = 1-cls
    device = x.device
    with torch.no_grad():
        original_logits, _ = classify_features(model, raw, frequency)
        original_margin = float(original_logits[0, cls]-original_logits[0, other])
        reference = blur_reference(prepared.frames, device)
        reference_raw, reference_freq = encode(model, reference)
        reference_logits, _ = classify_features(model, reference_raw, reference_freq)
        reference_margin = float(reference_logits[0, cls]-reference_logits[0, other])

        def margin(logits):
            return (logits[:, cls]-logits[:, other]).detach().cpu().numpy().astype(np.float64)

        def branch_vectors(rgb_features, freq_features):
            r = model.rgb_proj(rgb_features)
            return (r.mean(1), freq_features.mean(1), model.temporal(r+model.pos[:, :r.shape[1]]).mean(1))

        original_branches = branch_vectors(raw, frequency)
        reference_branches = branch_vectors(reference_raw, reference_freq)

        def branch_score(masks):
            with torch.no_grad():
                selectors = torch.as_tensor(masks, device=device, dtype=torch.bool)
                mixed = [torch.where(selectors[:, i:i+1], original_branches[i], reference_branches[i]) for i in range(3)]
                fused, _ = model.fusion(*mixed)
                return margin(model.cls(fused))

        branches = explain_game(branch_score, ['rgb', 'frequency', 'temporal'])

        def frame_score(masks):
            with torch.no_grad():
                keep = torch.as_tensor(masks, device=device, dtype=torch.bool)[:, :, None]
                mixed_raw = torch.where(keep, raw, reference_raw)
                mixed_freq = torch.where(keep, frequency, reference_freq)
                logits, _ = classify_features(model, mixed_raw, mixed_freq)
                return margin(logits)

        if prepared.media_type == 'image':
            frames = None  # Repeated still inputs are not independent video moments.
        else:
            frames = explain_game(frame_score, [str(i) for i in range(x.shape[0])], exact=False)
            frames['source_indices'] = list(prepared.source_indices)
            frames['timestamps'] = [i/prepared.fps if prepared.fps else None for i in prepared.source_indices]
            frames['permutation_cycles'] = 8

        masks = torch.as_tensor(region_masks(), device=device)
        cache = {(1, 1, 1, 1): original_margin, (0, 0, 0, 0): reference_margin}

        def spatial_score(coalitions):
            answers = []
            with torch.no_grad():
                for coalition in coalitions:
                    key = tuple(int(v) for v in coalition)
                    if any(v not in (0, 1) for v in key):
                        raise ValueError('SHAP coalition must be binary')
                    if key not in cache:
                        keep = masks[torch.as_tensor(key, dtype=torch.bool, device=device)].any(0)
                        perturbed = torch.where(keep[None, None], x, reference)
                        # Still images share one input; video positions remain separate.
                        if prepared.media_type == 'image':
                            r, f = encode(model, perturbed[:1])
                            r, f = r.expand(1, x.shape[0], -1), f.expand(1, x.shape[0], -1)
                        else:
                            r, f = encode(model, perturbed)
                        logits, _ = classify_features(model, r, f)
                        cache[key] = float(logits[0, cls]-logits[0, other])
                    answers.append(cache[key])
            return np.asarray(answers, dtype=np.float64)

        spatial = explain_game(spatial_score, [r[0] for r in REGIONS])
        spatial['regions'] = []
        for i, (name, rectangles) in enumerate(REGIONS):
            coalition = [1]*4
            coalition[i] = 0
            masked_margin = float(spatial_score([coalition])[0])
            spatial['regions'].append({'id': name, 'rectangles': [list(r) for r in rectangles],
                'shap_value': spatial['values'][i],
                'masked_class_score_percent': probability(masked_margin)*100,
                'score_drop_percentage_points': (probability(original_margin)-probability(masked_margin))*100})
        preview_position = int(np.argmax(np.abs(frames['values']))) if frames else 0
        def png(image):
            output = io.BytesIO(); image.save(output, format='PNG')
            return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode()
        original_preview = prepared.frames[preview_position].convert('RGB')
        blurred_preview = original_preview.filter(ImageFilter.GaussianBlur(radius=8))
        spatial['preview'] = {'position': preview_position, 'source_frame': prepared.source_indices[preview_position],
                              'timestamp': prepared.source_indices[preview_position]/prepared.fps if prepared.fps else None,
                              'original': png(original_preview)}
        for i, region in enumerate(spatial['regions']):
            mask_image = Image.fromarray((region_masks()[i]*255).astype(np.uint8), 'L')
            altered = original_preview.copy(); altered.paste(blurred_preview, (0, 0), mask_image)
            region['preview'] = png(altered)
        spatial['coalitions_evaluated'] = len(cache)
        spatial['region_coordinates'] = 'Fixed non-overlapping regions in the 224x224 aligned face crop; other is the remaining crop.'

    for game in (branches, frames, spatial):
        if game and (abs(game['output_value']-original_margin) > 5e-4 or abs(game['base_value']-reference_margin) > 5e-4):
            raise ValueError('SHAP reference or original output did not match the trained classifier')
    return {'version': 1, 'method': 'SHAP', 'library_version': __import__('shap').__version__,
        'target_class': ['Real', 'Fake'][cls], 'target': 'predicted_class_logit_minus_other_class_logit',
        'units': 'logit margin', 'reference': {'type': 'per_input_gaussian_blur', 'radius': 8,
          'description': 'The same aligned faces, with fine detail blurred. Not a population background dataset.'},
        'branches': branches, 'frames': frames, 'spatial': spatial,
        'original_class_score_percent': probability(original_margin)*100,
        'reference_class_score_percent': probability(reference_margin)*100,
        'seconds': round(time.perf_counter()-start, 3),
        'limitation': 'Attribution relative to this blur reference. It does not establish eye, lip or other manipulation defects, calibrated certainty, or causation.'}
