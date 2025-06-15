# Installation Guide

This document provides instructions on how to set up and run Quartz, an AI First Video Editor. The project consists of an Electron-based desktop application - an editing engine with a custom MCP for high performant local hierarchical LLMs - and a Python FastAPI backend to orchestrate the video editing tasks. It is bundled with an NPU-accelerated Whisper enginer for transcription services.* 

## Prerequisites

Before you begin, ensure you have the following installed:

*   [Git](https://git-scm.com/downloads)
*   [Node.js](https://nodejs.org/) (which includes npm) - Please check the `engines` field in `package.json` for specific version requirements if any.
*   [Python](https://www.python.org/downloads/) (Version >=3.11, <3.13 as specified in `scripts/pyproject.toml`)
*   [uv](https://github.com/astral-sh/uv) (Python package installer and virtual environment manager)
*   [ffmpeg](https://ffmpeg.org/download.html) - Required for video processing tasks.

## I. Electron Desktop Application

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/QuartzQualcomm/Quartz.git
    cd Quartz
    ```

2.  **Install Node.js dependencies:**
    Navigate to the root directory of the project (`/Users/naraazanda/CodeFiles/personal_projects/Quartz`) and run:
    ```bash
    npm install
    ```

3.  **Run the editor with hot-reloading:**

    ```bash
    npm run dev 
    ```
    Alternatively, to just start the application:
    ```bash
    npm start
    ```

4.  **Build the application:**
    To build the application for production, you can use the following commands:
    ```bash
    npm run build
    ```


## II. Python FastAPI Backend

The backend server is located in the `./scripts` directory.

1.  **Navigate to the scripts directory:**
    ```bash
    cd scripts
    ```

2.  **Create and activate the virtual environment:**
    
    In our experience, conda has proven to be stable for the purposes:
    ```bash
    conda create -n quartz python=3.11
    conda activate quartz
    ```

3.  **Install Python dependencies using uv:**
    First, ensure `uv` is installed. If not, you can typically install it via pip:
    ```bash
    pip install uv
    ```
    Then, install the dependencies specified in `pyproject.toml`:
    ```bash
    uv pip sync 
    ```
    *Note: The `scripts/README.md` mentions `uv add <package>` for adding packages and `uv run <file>` for running. The primary way to install all dependencies from `pyproject.toml` is `uv pip sync pyproject.toml` or `uv pip install -e .` if it's a package.*

4.  **Run the FastAPI server:**
    The `scripts/README.md` mentions a `./run_server` script. Ensure this script is executable:
    ```bash
    chmod +x run_server
    ```
    Then run the server:
    ```bash
    ./run_server
    ```
    Alternatively, if `run_server` is a wrapper, you might run it directly with `uvicorn` (after activating the virtual environment and installing dependencies):
    ```bash
    uvicorn main:app --reload 
    # (Assuming your FastAPI app instance is named 'app' in 'main.py')
    ```

5. **Bark by Suno:**
    The project uses the Bark text-to-audio model by Suno. To set it up, follow these steps:
    - Install the Bark model by running:
      ```bash
      pip install git+https://github.com/suno-ai/bark.git
      ```

## III. Whisper Engine
This repo is a fork of the [Simple Whisper Transcription](https://github.com/thatrandomfrenchdude/simple-whisper-transcription)

1. Follow the instructions in the [Simple Whisper Transcription README](simple-whisper-transcription/README.md) to set up the following:
    - Install the ffmpeg package for your platform.
    - Clone the repository.
    - Avoid using venv, as the project is designed to run in a conda environment.
    - Install the requirements.

2. Donwnload the model from AI Hub.
3. Use the provided `config.yaml` file to set up the Whisper engine. The file should include paths to the encoder and decoder models, audio settings, and processing settings.

Please refer to the [Simple Whisper Transcription README](simple-whisper-transcription/README.md) for detailed instructions on how to run the transcription service.


## Additional Notes

*   Refer to the main `README.md` and `scripts/README.md` for more detailed information about the project structure, specific functionalities, and API endpoints.
*   Configuration files like `config.yaml` (in the root and scripts directory) might need adjustments based on your environment or specific needs.

This `INSTALL.md` provides a general guide. Specific version compatibilities or additional setup steps might be detailed in the respective `README.md` files or `package.json` / `pyproject.toml`.

Notes:

\* Thanks to Nick Debeurre for the Whisper Engine repository.
