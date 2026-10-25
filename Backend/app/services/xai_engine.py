import base64
import io
import numpy as np
from PIL import Image

def render_saliency(frame, values):
    scale = float(values.max())
    mask = values / scale if scale > 0 else np.zeros_like(values)
    base = np.asarray(frame.convert('RGB'), dtype=np.float32)
    color = np.zeros_like(base)
    color[:,:,0] = 255
    alpha = mask[:,:,None] * .65
    overlay = Image.fromarray(np.clip(base*(1-alpha)+color*alpha,0,255).astype(np.uint8))
    out = io.BytesIO()
    overlay.save(out, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(out.getvalue()).decode()

class XAIEngine:
    @staticmethod
    def explain_disagreement(quadrant, manipulation_type, clues):
        descriptions = {'Q1':'Both the human and model match the folder label.', 'Q2':'The human matches the folder label; the model does not.', 'Q3':'The model matches the folder label; the human does not.', 'Q4':'Neither the human nor the model matches the folder label.'}
        return descriptions[quadrant] + ' The heatmap and timeline show input-gradient sensitivity to the predicted class, not verified forensic artifacts. The reason for an error is not established by this comparison.'

xai_engine = XAIEngine()


def encode_face(frame):
    buffer=io.BytesIO()
    frame.convert('RGB').save(buffer,format='JPEG',quality=85)
    return 'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()

def sensitivity_layer(values):
    maximum=float(values.max())
    alpha=values/maximum if maximum>0 else np.zeros_like(values)
    rgba=np.zeros((*values.shape,4),dtype=np.uint8)
    rgba[:,:,0]=255;rgba[:,:,1]=128;rgba[:,:,2]=26
    rgba[:,:,3]=np.clip(alpha*220,0,220).astype(np.uint8)
    buffer=io.BytesIO();Image.fromarray(rgba,'RGBA').save(buffer,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
