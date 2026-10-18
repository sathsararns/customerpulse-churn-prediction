param([switch]$SkipBuild, [switch]$SkipTraining)
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    function Invoke-Compose {
        & docker compose @args
        if ($LASTEXITCODE -ne 0) { throw "Docker Compose failed: $args" }
    }
    function Wait-Ready {
        $apiPort = $composeConfig.services.backend.ports[0].published
        $script:ApiUrl = "http://127.0.0.1:$apiPort"
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            try {
                $health = Invoke-RestMethod "$script:ApiUrl/health" -TimeoutSec 5
                if ($health.ready) { return $health }
            } catch { }
            Start-Sleep -Seconds 2
        }
        throw 'API did not become ready; inspect docker compose logs backend mlflow postgres'
    }
    $composeConfig = (& docker compose config --format json) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read Docker Compose configuration' }
    if (-not $SkipBuild) { Invoke-Compose build }
    Invoke-Compose up -d postgres mlflow
    if (-not $SkipTraining) { Invoke-Compose run --rm train }
    Invoke-Compose up -d backend frontend
    $before = Wait-Ready
    $customer = Import-Csv backend/data/raw/churn.csv | Select-Object -First 1
    $payload = @{}
    foreach ($property in $customer.PSObject.Properties) {
        if ($property.Name -notin @('customerID', 'Churn')) { $payload[$property.Name] = $property.Value }
    }
    $payload.customer_id = $customer.customerID
    $payload.SeniorCitizen = [int]$payload.SeniorCitizen
    $payload.tenure = [int]$payload.tenure
    $payload.MonthlyCharges = [double]$payload.MonthlyCharges
    $payload.TotalCharges = if ([string]::IsNullOrWhiteSpace($payload.TotalCharges)) { $null } else { [double]$payload.TotalCharges }
    $prediction = Invoke-RestMethod "$script:ApiUrl/predict" -Method Post -ContentType 'application/json' -Body ($payload | ConvertTo-Json)
    if (-not $prediction.event_id -or $prediction.source -ne 'api') { throw 'Missing prediction trace' }
    # Recreate all four containers and keep the named volumes.
    Invoke-Compose down
    Invoke-Compose up -d
    $after = Wait-Ready
    $history = Invoke-RestMethod "$script:ApiUrl/recent-predictions?limit=100"
    $saved = $history.items | Where-Object event_id -EQ $prediction.event_id
    if (-not $saved -or $saved.customer_id -ne $customer.customerID) { throw 'Prediction history did not survive recreation' }
    if ($after.model_version -ne $prediction.model_version) { throw 'Selected model did not survive recreation' }
    if ($after.predictionCount -ne $before.predictionCount + 1) { throw 'History count changed unexpectedly' }
    $frontendPort = $composeConfig.services.frontend.ports[0].published
    $proxy = Invoke-RestMethod "http://127.0.0.1:$frontendPort/api/health"
    if (-not $proxy.ready) { throw 'Frontend API proxy is unavailable' }
    Write-Host "PASS: trained $($prediction.model_version); event $($prediction.event_id) survived container recreation."
} finally {
    Pop-Location
}
