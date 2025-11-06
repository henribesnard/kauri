# Script de test rapide pour Document Sourcing (Windows PowerShell)
# Usage: .\test_sourcing_curl.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST DOCUMENT SOURCING - KAURI" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Obtenir le token
Write-Host ""
Write-Host "[1] Authentification..." -ForegroundColor Yellow

$loginBody = @{
    email = "henribesnard@example.com"
    password = "Harena123456"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:3201/api/v1/auth/login" `
        -Method Post `
        -ContentType "application/json" `
        -Body $loginBody

    $TOKEN = $response.access_token
    Write-Host "[OK] Token obtenu" -ForegroundColor Green
} catch {
    Write-Host "[ERREUR] Authentification echouee: $_" -ForegroundColor Red
    exit 1
}

# 2. Test NON-STREAM - Document Sourcing
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[2] TEST NON-STREAM: Document Sourcing" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[QUERY] Dans quels documents parle-t-on des amortissements ?" -ForegroundColor Yellow

$headers = @{
    "Authorization" = "Bearer $TOKEN"
    "Content-Type" = "application/json"
}

$queryBody1 = @{
    query = "Dans quels documents parle-t-on des amortissements ?"
} | ConvertTo-Json

try {
    $result1 = Invoke-RestMethod -Uri "http://localhost:3202/api/v1/chat/query" `
        -Method Post `
        -Headers $headers `
        -Body $queryBody1

    Write-Host "[OK] Reponse recue" -ForegroundColor Green
    Write-Host "[INFO] Intent: $($result1.metadata.intent_type)" -ForegroundColor Cyan
    Write-Host "[INFO] Sourcing mode: $($result1.metadata.sourcing_mode)" -ForegroundColor Cyan
    Write-Host "[INFO] Nombre de sources: $($result1.sources.Count)" -ForegroundColor Cyan

    if ($result1.metadata.sourcing_mode) {
        Write-Host "[INFO] Categories: $($result1.metadata.categories_found -join ', ')" -ForegroundColor Cyan
        Write-Host "[INFO] Keywords: $($result1.metadata.keywords_used -join ', ')" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "[REPONSE]" -ForegroundColor Yellow
    # Supprimer les emojis pour Windows
    $answer = $result1.answer -replace '[^\x00-\x7F]', ''
    Write-Host $answer

} catch {
    Write-Host "[ERREUR] $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# 3. Test NON-STREAM - RAG Query
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[3] TEST NON-STREAM: RAG Query (controle)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[QUERY] C'est quoi un amortissement ?" -ForegroundColor Yellow

$queryBody2 = @{
    query = "C'est quoi un amortissement ?"
} | ConvertTo-Json

try {
    $result2 = Invoke-RestMethod -Uri "http://localhost:3202/api/v1/chat/query" `
        -Method Post `
        -Headers $headers `
        -Body $queryBody2

    Write-Host "[OK] Reponse recue" -ForegroundColor Green
    Write-Host "[INFO] Intent: $($result2.metadata.intent_type)" -ForegroundColor Cyan
    Write-Host "[INFO] Nombre de sources: $($result2.sources.Count)" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "[REPONSE (extrait)]" -ForegroundColor Yellow
    $answer2 = $result2.answer -replace '[^\x00-\x7F]', ''
    Write-Host $answer2.Substring(0, [Math]::Min(200, $answer2.Length))

} catch {
    Write-Host "[ERREUR] $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# 4. Test STREAM - Document Sourcing
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[4] TEST STREAM: Document Sourcing" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[QUERY] Quels documents traitent des provisions ?" -ForegroundColor Yellow

$queryBody3 = @{
    query = "Quels documents traitent des provisions ?"
} | ConvertTo-Json

Write-Host "[INFO] Streaming en cours..." -ForegroundColor Yellow
Write-Host ""

# Note: PowerShell streaming est plus complexe, on utilise curl si disponible
if (Get-Command curl -ErrorAction SilentlyContinue) {
    curl -s --request POST `
      --url http://localhost:3202/api/v1/chat/stream `
      --header "authorization: Bearer $TOKEN" `
      --header 'content-type: application/json' `
      --data $queryBody3
} else {
    Write-Host "[INFO] curl non disponible, utilisez Git Bash ou installez curl" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TESTS TERMINES" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
