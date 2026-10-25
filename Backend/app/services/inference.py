import copy
from collections import OrderedDict
from fastapi import HTTPException
from .runtime import model_manager

_cache = OrderedDict()

def analyze_video(path, explain=True):
    try:
        from . import remote_inference
        if remote_inference.enabled():
            return remote_inference.analyze(path, explain=explain)
        # One shared lock bounds concurrent GPU memory and protects in-process cache.
        with model_manager.lock:
            model_manager.ensure_loaded()
            stat = path.stat()
            key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns, model_manager.signature, explain)
            if key in _cache:
                _cache.move_to_end(key)
                return copy.deepcopy(_cache[key])
            from .video_processor import video_processor
            result = model_manager.predict(video_processor.prepare(path), explain=explain)
            if not result.get('xai_error'):
                _cache[key] = result
                while len(_cache) > 16:
                    _cache.popitem(last=False)
            return copy.deepcopy(result)
    except HTTPException:
        raise
    except (RuntimeError, ImportError) as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, f'Media analysis failed: {exc}') from exc

def game_prediction(item):
    from ..data.sample_dataset import item_path
    try:
        result = analyze_video(item_path(item), explain=False)
        return {'ai_prediction': result['verdict'], 'ai_confidence': result['confidence_percentage'] / 100, 'ai_error': None}
    except (HTTPException, FileNotFoundError) as exc:
        return {'ai_prediction': None, 'ai_confidence': None, 'ai_error': str(exc.detail if isinstance(exc, HTTPException) else exc)}
