"""Test-only numerical equivalence using untrained fixture weights, never app predictions."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from app.services.swin_model import DeepfakeModel
from app.services.model_manager import classify_features

torch.set_num_threads(2)
torch.manual_seed(123)
model = DeepfakeModel(pretrained=False)
model.set_stage(2)
model.eval()
for parameter in model.parameters():
    parameter.requires_grad_(False)
x = torch.randn(1,2,3,224,224) * .5
with torch.no_grad():
    direct = model(x)
    raw = torch.cat([model.rgb(frame[None]) for frame in x[0]])[None]
    freq = torch.cat([model.freq(frame[None]) for frame in x[0]])[None]
    chunked, _ = classify_features(model, raw, freq)
torch.testing.assert_close(direct, chunked, rtol=2e-4, atol=2e-6)

full_x = x.clone().requires_grad_(True)
full_grad = torch.autograd.grad(model(full_x)[0,0], full_x)[0]
r = raw.detach().requires_grad_(True)
f = freq.detach().requires_grad_(True)
logits, _ = classify_features(model,r,f)
dr, df = torch.autograd.grad(logits[0,0],(r,f))
parts=[]
for i in range(2):
    frame=x[:,i].clone().requires_grad_(True)
    objective=(model.rgb(frame)*dr[:,i]).sum()+(model.freq(frame)*df[:,i]).sum()
    parts.append(torch.autograd.grad(objective,frame)[0])
replayed=torch.stack(parts,dim=1)
torch.testing.assert_close(full_grad,replayed,rtol=3e-3,atol=2e-7)
assert full_grad.abs().sum()>0
print('Chunked forward and chain-rule input gradients match supplied forward: PASS')
print('Fixture-only test. This does not verify trained weights or accuracy.')
