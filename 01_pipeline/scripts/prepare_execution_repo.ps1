param([string]$Destination = "")
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($Destination)) { $Destination = Join-Path (Split-Path $Root -Parent) 'carehub_execution_repo' }
if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
Copy-Item -Recurse -Force (Join-Path $Root '01_pipeline') $Destination
Copy-Item -Recurse -Force (Join-Path $Root '02_conteneurisation') $Destination
Copy-Item -Force (Join-Path $Root 'README.md') $Destination
Copy-Item -Recurse -Force (Join-Path $Root '01_pipeline\.github') (Join-Path $Destination '.github')
Copy-Item -Force (Join-Path $Root '01_pipeline\.pre-commit-config.yaml') (Join-Path $Destination '.pre-commit-config.yaml')
Copy-Item -Force (Join-Path $Root '01_pipeline\.gitignore') (Join-Path $Destination '.gitignore')
Write-Host "Execution repository prepared at: $Destination"
Write-Host 'Next: git init ; git add . ; git commit -m "EC06 CareHub CI/CD" ; create/push to your repository.'
