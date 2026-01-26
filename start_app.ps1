
# Start-LegalApp.ps1
# Script to start all services for the Legal Issue Classification App

# 1. Load Environment Variables from .env file
if (Test-Path ".env") {
    Write-Host "Loading environment variables from .env..." -ForegroundColor Green
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Loaded: $name" -ForegroundColor Gray
        }
    }
} else {
    Write-Error ".env file not found! Please create one using the template."
    exit 1
}

# 2. Start NLP Service (Python)
Write-Host "Starting NLP Service (Python)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd nlp-python; python main.py" -WindowStyle Normal

# 3. Start Backend Service (Java Spring Boot)
Write-Host "Starting Backend Service (Java)..." -ForegroundColor Cyan
# Wait a few seconds for Python to init? Not strictly necessary but good practice.
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend-java; mvn spring-boot:run" -WindowStyle Normal

# 4. Start Frontend Service (React)
Write-Host "Starting Frontend Service (React)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev" -WindowStyle Normal

Write-Host "All services started in separate windows." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend: http://localhost:$env:SERVER_PORT"
Write-Host "NLP: $env:NLP_SERVICE_URL"
