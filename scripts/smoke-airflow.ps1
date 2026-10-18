param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    function Invoke-AirflowCompose {
        & docker compose -f docker-compose.yml -f docker-compose.airflow.yml @args
        if ($LASTEXITCODE -ne 0) { throw "Airflow Compose failed: $args" }
    }
    if (-not $SkipBuild) {
        Invoke-AirflowCompose build backend
        Invoke-AirflowCompose build orchestration
    }
    Invoke-AirflowCompose up -d --wait backend frontend orchestration
    Invoke-AirflowCompose exec -T -w /app orchestration /opt/customerpulse-runtime/bin/python3.13 -s -m deployment.airflow.smoke_check
} finally {
    Pop-Location
}
