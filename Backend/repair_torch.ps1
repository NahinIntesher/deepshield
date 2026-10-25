$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
& $python -m pip install --upgrade --force-reinstall torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) { throw "PyTorch installation failed" }
& $python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
& $python -c "import torch; print(torch.__version__); assert hasattr(torch.serialization, 'safe_globals'); print('CUDA:',torch.cuda.is_available())"
