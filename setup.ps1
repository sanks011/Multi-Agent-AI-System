# Multi-Agent AI System - Setup Script
Write-Host "Setting up Multi-Agent AI System..." -ForegroundColor Cyan

# Create required directories
Write-Host "Creating required directories..."
mkdir -Force samples
mkdir -Force output_logs

# Check Python installation
try {
    python --version
} catch {
    Write-Host "Python is not installed. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "Installing Python dependencies..."
python -m pip install -r requirements.txt

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "To start the system: python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
