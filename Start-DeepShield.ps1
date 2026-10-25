param([switch]$Build)
$ErrorActionPreference='Stop'
$projectRoot=$PSScriptRoot
$pythonPath=Join-Path $projectRoot '.venv/Scripts/python.exe'
$backendPath=Join-Path $projectRoot 'Backend'
$frontendPath=Join-Path $projectRoot 'Frontend'
$logPath=Join-Path $projectRoot 'Database/logs'
if(-not (Test-Path -LiteralPath $pythonPath)){throw 'Python environment missing. Install Backend/requirements.txt in .venv first.'}
$nodePath=(Get-Command node -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $logPath -Force | Out-Null
if($Build){
 Push-Location -LiteralPath $frontendPath
 try {& npm.cmd run build;if($LASTEXITCODE -ne 0){throw 'Frontend build failed.'}} finally {Pop-Location}
}
if(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue){Write-Host 'Port 8000 is already in use; no additional backend started.'}
else {Start-Process -FilePath $pythonPath -ArgumentList '-u','run.py' -WorkingDirectory $backendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'api.stdout.log') -RedirectStandardError (Join-Path $logPath 'api.stderr.log')}
if(Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue){Write-Host 'Port 3000 is already in use; no additional web server started.'}
else {Start-Process -FilePath $nodePath -ArgumentList 'node_modules/next/dist/bin/next','start','-H','127.0.0.1','-p','3000' -WorkingDirectory $frontendPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logPath 'web.stdout.log') -RedirectStandardError (Join-Path $logPath 'web.stderr.log')}
Write-Host 'DeepShield: http://localhost:3000'
Write-Host 'Admin: http://localhost:3000/admin/login'
Write-Host "Logs: $logPath"
