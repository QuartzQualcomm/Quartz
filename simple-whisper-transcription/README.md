# Live Transcription with AI Hub Whisper

Streaming transcription application built with [Whisper Base En](https://aihub.qualcomm.com/compute/models/whisper_base_en?domain=Audio) from [Qualcomm AI Hub](https://aihub.qualcomm.com/).

### Table of Contents
[1. Purpose](#purpose)<br>
[2. Implementation](#implementation)<br>
[3. Setup](#setup)<br>
[4. Usage](#usage)<br>
[5. Contributing](#contributing)<br>
[6. Code of Conduct](#code-of-conduct)<br>

### Purpose
This is an extensible base app for custom language transcription workflows using Whisper. Base performance is acceptable and can be improved.

### Implementation
This app was built for the Snapdragon X Elite but designed to be platform agnostic. Performance may vary on other hardware.

- Machine: Thinkpad 14s
- Chip: Snapdragon X Elite
- OS: Windows 11
- Memory: 32 GB
- Python Version: 3.11.9 (ARM64)

### Setup
1. Download & Extract [FFMPeg for Windows](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip).
    1. Extract the zip to `C:\Program Files`
    2. Rename `ffmpeg-master-latest-win64-gpl` to `ffmpeg`
    3. Add `C:\Program Files\ffmpeg\bin` to your $PATH
        1. Click the Windows button and search "Edit environment variables"
        2. Click "Edit environment variables for your account"
        3. In User variables, choose `Path` and click edit
        4. Click new to make an entry with `C:\Program Files\ffmpeg\bin`
        5. Click OK to save
        6. In a new PowerShell, run ffmpeg to verify installation
1. Open a PowerShell instance and clone the repo
    ```
    git clone https://github.com/thatrandomfrenchdude/simple-whisper-transcription.git
    ```
2. Create and activate your virtual environment with reqs
    ```
    # 1. navigate to the cloned directory
    cd simple-whisper-transcription

    # 2. create the python virtual environment
    python -m venv whisper-venv

    # 3. activate the virtual environment
    ./whisper-venv/Scripts/Activate.ps1     # windows

    # 4. install the requirements
    pip install -r requirements.txt
    ```
3. Download the model from AI Hub
    1. Create a directory called `models` at the project root
    2. From the project root, run `python -m qai_hub_models.models.whisper_base_en.export --target-runtime onnx`
    3. Copy the model files from `build` to `models` 
3. Create your `config.yaml` file with the following variables
    ```
    # audio settings
    "sample_rate": 16000          # Audio sample rate in Hz
    "chunk_duration": 4           # Duration of each audio chunk in seconds
    "channels": 1                 # Number of audio channels (1 for mono)

    # processing settings
    "max_workers": 4              # Number of parallel transcription workers
    "silence_threshold": 0.001    # Threshold for silence detection
    "queue_timeout": 1.0          # Timeout for audio queue operations

    # model paths
    "encoder_path": "models/WhisperEncoder.onnx"
    "decoder_path": "models/WhisperDecoder.onnx"
    ```
4. You can run `python src/openai_server.py` to launch the Whisper server.