# build.ps1
# PowerShell script to compile the Voice Typist App into a single standalone .exe

$ErrorActionPreference = "Stop"

Write-Host "Installing PyInstaller in the virtual environment..." -ForegroundColor Cyan
& .venv\Scripts\pip.exe install pyinstaller

if (-not $?) {
    Write-Error "Failed to install PyInstaller."
}

Write-Host "Cleaning up old build cache and spec files..." -ForegroundColor Cyan
Remove-Item -Path "build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "VoiceTypist.spec" -Force -ErrorAction SilentlyContinue

Write-Host "`nCompiling application using PyInstaller..." -ForegroundColor Cyan
# --clean: Cleans PyInstaller cache before building
# --onefile: Bundles everything into a single .exe
# --noconsole: Suppresses the black terminal console window on startup (runs in background)
# --name: Specifies output executable name
& .venv\Scripts\pyinstaller.exe --clean --onefile --noconsole --paths . --name "VoiceTypist" app.py

if ($?) {
    Write-Host "`nBuild completed successfully!" -ForegroundColor Green
    Write-Host "The standalone executable is located at: dist\VoiceTypist.exe" -ForegroundColor Green
    Write-Host "You can now distribute dist\VoiceTypist.exe to others. Double-click it to run silently in the background!" -ForegroundColor Green
} else {
    Write-Error "PyInstaller build failed."
}
