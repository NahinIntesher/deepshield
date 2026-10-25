"""Verify the user's local trained checkpoint and optionally predict an actual video."""
import argparse
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--video', type=Path)
parser.add_argument('--explain', action='store_true', help='Also compute input-gradient sensitivity (slower)')
args = parser.parse_args()

try:
    from app.services.model_manager import model_manager
    with model_manager.lock:
        model_manager.ensure_loaded()
    print(json.dumps({'checkpoint_loaded': True, 'device':str(model_manager.device),
                      'checkpoint_epoch':model_manager.checkpoint_epoch,
                      'model_sha256':model_manager.checkpoint_sha256}, indent=2))
    if args.video:
        from app.services.inference import analyze_video
        result = analyze_video(args.video.resolve(), explain=args.explain)
        result.pop('spatial_heatmap_base64', None)
        # Keep encoded face crops/overlays out of diagnostic logs.
        result.pop('frame_explanations', None)
        result.pop('sampled_faces', None)
        for key, value in list(result.items()):
            if isinstance(value, list) and value and isinstance(value[0], dict):
                result[key] = [{k: v for k, v in item.items() if k not in ('image', 'overlay', 'heatmap', 'heatmap_base64', 'face_base64')} for item in value]
        print(json.dumps(result, indent=2))
except Exception as exc:
    print(f'CHECK FAILED: {getattr(exc, "detail", str(exc))}', file=sys.stderr)
    sys.exit(1)
