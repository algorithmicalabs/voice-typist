# setup.ps1
# PowerShell script to set up Python and dependencies for the Voice Typing App.

$ErrorActionPreference = "Stop"

# Helper to find a real Python executable
function Find-Python {
    # Check if python is in PATH and is not the Windows Store app execution alias (size 0 or in WindowsApps)
    $paths = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    foreach ($p in $paths) {
        if ($p -and ($p -notlike "*WindowsApps*")) {
            # Test running it
            try {
                $ver = & $p --version 2>&1
                if ($ver -like "Python *") {
                    return $p
                }
            } catch {}
        }
    }

    # Check common install locations
    $localAppPath = "$env:USERPROFILE\AppData\Local\Programs\Python"
    if (Test-Path $localAppPath) {
        $exes = Get-ChildItem -Path $localAppPath -Filter "python.exe" -Recurse -Depth 2 -ErrorAction SilentlyContinue
        foreach ($exe in $exes) {
            return $exe.FullName
        }
    }

    $programFilesPath = "C:\Program Files\Python*"
    $exes = Get-ChildItem -Path $programFilesPath -Filter "python.exe" -Recurse -Depth 2 -ErrorAction SilentlyContinue
    foreach ($exe in $exes) {
        return $exe.FullName
    }

    return $null
}

Write-Host "Checking for existing Python installation..." -ForegroundColor Cyan
$pythonPath = Find-Python

if (-not $pythonPath) {
    Write-Host "Python not found. Installing Python 3.12 via winget..." -ForegroundColor Yellow
    # Run winget to install Python
    try {
        winget install --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        Write-Host "Python installation command finished. Waiting a few seconds..." -ForegroundColor Cyan
        Start-Sleep -Seconds 5
    } catch {
        Write-Error "Failed to install Python via winget. Please install Python 3.12 manually from python.org and add it to your PATH, then re-run setup.ps1."
    }

    # Look for it again
    $pythonPath = Find-Python
    if (-not $pythonPath) {
        Write-Error "Python was installed but could not be located. Please restart your shell or add Python to your PATH manually, then re-run setup.ps1."
    }
}

Write-Host "Using Python executable: $pythonPath" -ForegroundColor Green

# Create Virtual Environment
if (Test-Path ".venv") {
    Write-Host "Virtual environment (.venv) already exists. Re-using it." -ForegroundColor Cyan
} else {
    Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
    & $pythonPath -m venv .venv
    if (-not $?) {
        Write-Error "Failed to create virtual environment."
    }
}

# Upgrade pip and install packages
Write-Host "Upgrading pip..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Cyan
& .venv\Scripts\pip.exe install -r requirements.txt

if ($?) {
    Write-Host "`nSetup completed successfully! All dependencies installed." -ForegroundColor Green
    Write-Host "To run the application, execute: .venv\Scripts\python.exe app.py" -ForegroundColor Green
} else {
    Write-Error "Failed to install some dependencies."
}
