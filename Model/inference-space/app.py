"""Private Gradio/ZeroGPU service using the unchanged DeepShield inference pipeline."""
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

print('DeepShield startup: loading ZeroGPU runtime', flush=True)
import spaces  # Import before torch so ZeroGPU can manage GPU initialization.
print('DeepShield startup: loading torch', flush=True)
import torch
import gradio as gr
print('DeepShield startup: loading inference source', flush=True)

ROOT = Path(__file__).resolve().parent
os.environ['DEEPSHIELD_ROOT'] = str(ROOT)
UPLOADS = Path(tempfile.gettempdir())/'deepshield-uploads'
UPLOADS.mkdir(parents=True, exist_ok=True)
os.environ['GRADIO_TEMP_DIR'] = str(UPLOADS)
with zipfile.ZipFile(ROOT/'runtime.zip') as bundle:
    if any(not p.startswith('engine/') or '..' in Path(p).parts for p in bundle.namelist()):
        raise RuntimeError('Invalid inference runtime bundle')
    bundle.extractall(ROOT/'runtime')
import sys
sys.path.insert(0, str(ROOT/'runtime'))
from engine.services.model_manager import model_manager
from engine.services.video_processor import video_processor
from engine.services.upload_validation import IMAGE_EXTENSIONS,validate_image,validate_video

face_dir = ROOT/'face-model/models/buffalo_l'
face_dir.mkdir(parents=True, exist_ok=True)
shutil.copyfile(ROOT/'det_10g.onnx', face_dir/'det_10g.onnx')
torch.set_num_threads(2)
model_manager.device = torch.device('cpu')
print('DeepShield startup: loading verified checkpoint', flush=True)
model_manager.ensure_loaded()
print('DeepShield startup: checkpoint loaded', flush=True)
EXPECTED = 'be33edbb69a80072439b8ea361ee9b00f635a2604ea2a4b9c1bfabe731067b7e'
if model_manager.checkpoint_sha256 != EXPECTED:
    raise RuntimeError('The model checkpoint does not match the verified original.')


@spaces.GPU(duration=120)
def gpu_predict(prepared, explain):
    start = time.perf_counter()
    model_manager.device = torch.device('cuda')
    model_manager.model.to(model_manager.device)
    try:
        result = model_manager.predict(prepared, explain=explain)
        result['inference_gpu_seconds'] = round(time.perf_counter()-start, 3)
        return result
    finally:
        model_manager.model.to('cpu')
        model_manager.device = torch.device('cpu')


def analyze(file_path, explain=True):
    if not file_path:
        raise gr.Error('Choose an image or video.')
    path = Path(file_path).resolve()
    if not path.is_file() or not path.is_relative_to(UPLOADS.resolve()):
        raise gr.Error('Choose a newly uploaded file.')
    try:
        (validate_image if path.suffix.lower() in IMAGE_EXTENSIONS else validate_video)(path)
        prepared = video_processor.prepare(path)
        return gpu_predict(prepared, bool(explain))
    except Exception as exc:
        # Return validation/runtime errors; no alternative model or guessed verdict.
        detail = getattr(exc, 'detail', None)
        raise gr.Error(str(detail or exc)[:500]) from None
    finally:
        path.unlink(missing_ok=True)


with gr.Blocks(title='DeepShield inference', delete_cache=(300,300)) as demo:
    gr.Markdown('# DeepShield inference\nPrivate video detector. Still-image analysis is experimental. Free GPU quota applies.')
    media = gr.File(label='Image or video', type='filepath', file_types=['.jpg','.jpeg','.png','.webp','.mp4','.mov','.avi','.mkv','.webm'])
    explain = gr.Checkbox(value=True, label='Include visual explanations')
    run = gr.Button('Analyze')
    output = gr.JSON(label='Result')
    run.click(analyze, inputs=[media,explain], outputs=output, api_name='predict', concurrency_limit=1)

demo.queue(max_size=8, default_concurrency_limit=1)
if __name__ == '__main__':
    demo.launch(server_name='0.0.0.0', server_port=7860, max_file_size='50mb',
                blocked_paths=[str(ROOT/'best_model.pth'),str(ROOT/'det_10g.onnx'),str(ROOT/'face-model')])
