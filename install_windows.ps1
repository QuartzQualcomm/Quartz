# Windows Setup Script for Quartz AI Video Editor
# This PowerShell script automates environment setup on Windows 10/11.
# Run this in an elevated PowerShell (Run as Administrator) for full functionality.

param(
    [string]$RepoUrl = 'https://github.com/QuartzQualcomm/Quartz.git',
    [string]$CloneDir = "$PWD\Quartz",
    [string]$FFmpegUrl = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip',
    [string]$FFmpegZip = "$env:TEMP\ffmpeg.zip",
    [string]$FFmpegInstallDir = 'C:\Program Files\ffmpeg'
)

Write-Host '=== 1. Install prerequisites (Git, Node.js, Python, 7zip) ==='
# Check and guide installation if missing
function Check-Command { param($cmd,$name) if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Warning "$name not found. Please install it before continuing." } }
Check-Command git "Git"
Check-Command node "Node.js"
Check-Command npm "npm"
Check-Command python "Python"
Check-Command 7z "7-Zip"  # For extracting archives

Write-Host '=== 2. Download and install FFmpeg ==='
if (-Not (Test-Path "$FFmpegInstallDir\bin\ffmpeg.exe")) {
    Write-Host 'Downloading FFmpeg...'
    Invoke-WebRequest -Uri $FFmpegUrl -OutFile $FFmpegZip
    Write-Host 'Extracting FFmpeg...'
    New-Item -ItemType Directory -Path $FFmpegInstallDir -Force | Out-Null
    7z x $FFmpegZip -o"$FFmpegInstallDir" -y | Out-Null
    # Some builds name the folder differently, move contents up
    $sub = Get-ChildItem $FFmpegInstallDir | Where-Object { $_.PSIsContainer } | Select-Object -First 1
    if ($sub) { Move-Item -Path "$FFmpegInstallDir\$($sub.Name)\*" -Destination $FFmpegInstallDir -Force }    
    Remove-Item $FFmpegZip
    # Update user PATH
    [Environment]::SetEnvironmentVariable('Path', $Env:Path + ";$FFmpegInstallDir\bin", 'User')
    Write-Host 'FFmpeg installed and PATH updated.'
} else { Write-Host 'FFmpeg already installed.' }

Write-Host '=== 3. Clone Quartz repository ==='
if (-Not (Test-Path $CloneDir)) { git clone $RepoUrl $CloneDir } else { Write-Host 'Repository already exists.' }

Push-Location $CloneDir

Write-Host '=== 4. Setup Electron Desktop App ==='
if (Test-Path "package.json") {
    npm install
    # Uncomment to start in dev mode:
    # npm run dev
    # To build for production:
    # npm run build
} else { Write-Warning 'package.json not found in root. Check your clone.' }

Write-Host '=== 5. Setup Python Backend ==='
Set-Location .\scripts

# Prefer conda, fallback to venv
if (Get-Command conda -ErrorAction SilentlyContinue) {
    Write-Host 'Creating Conda environment...'
    conda create -y -n quartz python=3.11
    conda activate quartz
} else {
    Write-Host 'Creating Python venv...'
    python -m venv quartz-venv
    .\quartz-venv\Scripts\Activate.ps1
}

Write-Host 'Installing uv (env manager) and dependencies...'
pip install uv
uv pip sync

Write-Host '=== 6. Install Bark TTS Model ==='
pip install git+https://github.com/suno-ai/bark.git

Write-Host '=== 7. Run FastAPI Server ==='
if (Test-Path run_server) { chmod +x run_server; .\run_server } else { Write-Host 'run_server script not found, starting via uvicorn'; uv run uvicorn main:app --reload }

Write-Host '=== Setup Complete! ==='
Write-Host 'To launch the Electron app, run `npm start` in the root directory.'
