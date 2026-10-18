param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    function Invoke-StreamCompose {
        & docker compose -f docker-compose.yml -f docker-compose.kafka.yml @args
        if ($LASTEXITCODE -ne 0) { throw "Kafka Compose command failed: $args" }
    }
    if (-not $SkipBuild) { Invoke-StreamCompose build backend frontend }
    Invoke-StreamCompose up -d backend frontend stream-inference stream-analytics
    # The application must already have a trained, activated model.
    Invoke-StreamCompose exec -T stream-inference python -m streaming.smoke_check prepare
    Invoke-StreamCompose restart stream-inference stream-analytics
    # Explicit redelivery tests the DB-commit/offset-commit crash boundary too.
    Invoke-StreamCompose stop stream-analytics
    Invoke-StreamCompose exec -T stream-inference python -m streaming.smoke_check rewind
    Invoke-StreamCompose start stream-analytics
    Invoke-StreamCompose exec -T stream-inference python -m streaming.smoke_check verify
    Write-Host 'PASS: API/stream probabilities match; invalid event reached DLQ; restart, offset replay and producer replay kept one history/analytics entry per event.'
} finally {
    Pop-Location
}
