$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

# Reuse the active project's Python environment; otherwise use the installed Python launcher.
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { py -3 -m venv .venv } else { python -m venv .venv }
}
$Python = Join-Path $Root '.venv\Scripts\python.exe'
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
$envText = Get-Content '.env' -Raw
$jwtLine = [regex]::Match($envText, '(?m)^JWT_SECRET=(.*)$')
$existingSecret = if ($jwtLine.Success) { $jwtLine.Groups[1].Value.Trim() } else { '' }
if ($existingSecret.Length -lt 32 -or $existingSecret -match 'replace|your_') {
    $randomBytes = New-Object byte[] 48
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($randomBytes)
    $rng.Dispose()
    $secret = [Convert]::ToBase64String($randomBytes)
    if ($jwtLine.Success) { $envText = [regex]::Replace($envText, '(?m)^JWT_SECRET=.*$', "JWT_SECRET=$secret") }
    else { $envText += "`nJWT_SECRET=$secret`n" }
    [IO.File]::WriteAllText((Join-Path $Root '.env'), $envText, (New-Object System.Text.UTF8Encoding -ArgumentList $false))
    Write-Host 'Generated a local JWT secret in .env.' -ForegroundColor Green
}

$health = $null
try { $health = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2 } catch {}
if (-not $health) {
    $api = Start-Process -FilePath $Python -ArgumentList '-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000' -PassThru -WindowStyle Normal
    $ready = $false
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try { Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 2 | Out-Null; $ready = $true; break } catch {}
    }
    if (-not $ready) { throw 'FastAPI did not become ready. Check the API terminal output.' }
}
Write-Host 'TripLedger API: http://127.0.0.1:8000/docs' -ForegroundColor Cyan
Write-Host 'Starting the Streamlit application...' -ForegroundColor Green
& $Python -m streamlit run app.py
