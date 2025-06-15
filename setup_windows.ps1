@echo off
REM Windows Installation Script for Quartz Project

REM Check if Conda is installed
conda --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Conda is not installed or not in PATH.
    echo Please install Miniconda or Anaconda from https://docs.conda.io/en/latest/miniconda.html and ensure it is added to your PATH.
    exit /b 1
)

REM Check if Node.js and npm are installed
node --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Node.js is not installed or not in PATH.
    echo Please install Node.js from https://nodejs.org/ and ensure it is added to your PATH.
    exit /b 1
)
npm --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo npm is not installed or not in PATH.
    echo Please ensure npm is installed (it comes with Node.js) and is in your PATH.
    exit /b 1
)

REM Check for environment.yml
IF NOT EXIST .\environment.yml (
    echo environment.yml not found in the current directory.
    echo Please ensure the environment.yml file is present in the project root.
    exit /b 1
)

REM Check for package.json (indicative of Node.js project setup)
IF NOT EXIST .\package.json (
    echo package.json not found in the current directory.
    echo Please ensure your Node.js project is set up correctly with a package.json file.
    exit /b 1
)

REM Install Node.js dependencies
echo Installing Node.js dependencies...
npm install
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to install Node.js dependencies.
    exit /b 1
)

REM Create Conda environment
echo Creating Conda environment from environment.yml...
conda env create -f environment.yml
IF %ERRORLEVEL% NEQ 0 (
    echo Failed to create Conda environment.
    exit /b 1
)

REM Determine the environment name
SET ENV_NAME=quartz-venv

echo Activating Conda environment: %ENV_NAME%

REM Start Uvicorn server in a new window
echo Starting Uvicorn server...
start "Uvicorn Server" cmd /k "conda activate %ENV_NAME% && cd scripts && uvicorn main:router --reload"

REM Start OpenAI server in a new window
echo Starting OpenAI server...
start "OpenAI Server" cmd /k "conda activate %ENV_NAME% && cd simple-whisper-transcription && python openai_server.py"

REM Start npm run dev in a new window
echo Starting npm run dev...
start "npm dev" cmd /k "npm run dev"

REM Start npm run start in a new window
echo Starting npm run start...
start "npm start" cmd /k "npm run start"

echo Setup complete. All four services should be starting in new terminal windows.

exit /b 0
