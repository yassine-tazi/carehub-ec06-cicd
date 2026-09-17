$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$ComposeDir = Join-Path $Root '02_conteneurisation'
$EnvFile = Join-Path $ComposeDir '.env.dev'

Write-Host '=== CAREHUB EC06 - DEMO LOCALE WINDOWS ==='
& docker version | Out-Host
& docker compose version | Out-Host

if (-not (Test-Path $EnvFile)) {
    $pwd = 'LocalDemo-' + [Guid]::NewGuid().ToString('N')
    @"
APP_ENV=development
APP_PORT=8080
APP_IMAGE=carehub-app:local
APP_REPLICAS=1
POSTGRES_DB=carehub
POSTGRES_USER=carehub
POSTGRES_PASSWORD=$pwd
VCS_REF=local-demo
BUILD_DATE=$([DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))
"@ | Set-Content -Encoding UTF8 $EnvFile
    Write-Host 'Created local .env.dev (not to be committed).'
}

Push-Location $ComposeDir
try {
    Write-Host "`n[1] Build + start"
    & docker compose --env-file .env.dev up -d --build

    Write-Host "`n[2] Wait for /ready"
    $ready = $false
    for ($i=1; $i -le 30; $i++) {
        try {
            $r = Invoke-RestMethod -Uri 'http://localhost:8080/ready' -TimeoutSec 3
            if ($r.status -eq 'ready') { $ready = $true; break }
        } catch { Start-Sleep -Seconds 2 }
    }
    if (-not $ready) { throw 'CareHub did not become ready in time.' }

    Write-Host "`n[3] Containers - CAPTURE 01"
    & docker compose --env-file .env.dev ps | Out-Host

    Write-Host "`n[4] Health - CAPTURE 02"
    Invoke-RestMethod -Uri 'http://localhost:8080/health' | ConvertTo-Json | Out-Host
    Invoke-RestMethod -Uri 'http://localhost:8080/ready' | ConvertTo-Json | Out-Host

    Write-Host "`n[5] Create one appointment - CAPTURE 03"
    $body = @{
        patient_reference = 'PATIENT-DEMO-001'
        requested_at = '2026-09-18T10:00:00Z'
        specialty = 'Cardiologie'
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/api/appointments' -ContentType 'application/json' -Body $body | ConvertTo-Json | Out-Host

    Write-Host "`n[6] Resource limits / usage - CAPTURE 04"
    & docker stats --no-stream | Out-Host

    Write-Host "`n[7] Scale app from 1 to 3 replicas"
    & docker compose --env-file .env.dev up -d --scale app=3 app
    & docker compose --env-file .env.dev restart proxy
    Start-Sleep -Seconds 4
    Write-Host "`n[8] Scaled containers - CAPTURE 05"
    & docker compose --env-file .env.dev ps | Out-Host

    Write-Host "`n[9] Load-balancing evidence - CAPTURE 06"
    1..12 | ForEach-Object {
        try { (Invoke-RestMethod -Uri 'http://localhost:8080/instance' -TimeoutSec 3) | ConvertTo-Json -Compress | Write-Host }
        catch { Write-Host $_.Exception.Message }
    }

    Write-Host "`n[10] Metrics endpoint - CAPTURE 07"
    $metrics = (Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8080/metrics').Content
    ($metrics -split "`n" | Where-Object { $_ -match '^carehub_http_requests_total|^carehub_appointment' } | Select-Object -First 20) | Out-Host

    Write-Host "`n=== DEMO LOCALE TERMINEE ==="
    Write-Host 'Keep the stack running for screenshots. Stop later with:'
    Write-Host 'docker compose --env-file .env.dev down'
} finally {
    Pop-Location
}
