# Installation Guide

This guide provides instructions on how to set up the project environment using Conda and Node.js, and run the necessary services.

## Prerequisites

1.  **Conda**: Ensure you have Conda (Miniconda or Anaconda) installed. If not, you can download Miniconda from [https://docs.conda.io/en/latest/miniconda.html](https://docs.conda.io/en/latest/miniconda.html).
2.  **Node.js and npm**: Ensure you have Node.js and npm installed. If not, you can download Node.js (which includes npm) from [https://nodejs.org/](https://nodejs.org/).
3.  **`environment.yml`**: Make sure you have the `environment.yml` file in the root directory of this project. This file contains all the Python dependencies required.
4.  **Project Dependencies**: Ensure you have run `npm install` in the root directory of the project to install Node.js dependencies.

## Setup Instructions

1.  **Install Node.js Dependencies**:
    Open your terminal and navigate to the root directory of this project. Then, run:

    ```bash
    npm install
    ```

2.  **Create Conda Environment**:
    Open your terminal or Anaconda Prompt and navigate to the root directory of this project. Then, run the following command to create the Conda environment from the `environment.yml` file.

    ```bash
    conda env create -f environment.yml
    ```

3.  **Activate Conda Environment**:
    Once the environment is created, activate it using:

    ```bash
    conda activate quartz-venv
    ```
    *(Replace `quartz-venv` if your environment has a different name specified in `environment.yml`)*

4.  **Run Services**:
    After activating the Conda environment (for the Python services) and installing Node.js dependencies, you need to run four services in parallel. You can do this by opening four separate terminals. Activate the `quartz-venv` Conda environment in the terminals designated for Python services.

    *   **Terminal 1 (Uvicorn Server - Python)**:
        Activate Conda environment: `conda activate quartz-venv`
        Navigate to the `scripts` directory and run the Uvicorn server:

        ```bash
        cd scripts
        uvicorn main:router --reload
        ```

    *   **Terminal 2 (OpenAI Server - Python)**:
        Activate Conda environment: `conda activate quartz-venv`
        Navigate to the `simple-whisper-transcription` directory and run the Python server:

        ```bash
        cd simple-whisper-transcription
        python openai_server.py
        ```

    *   **Terminal 3 (npm run dev - Node.js)**:
        Navigate to the root project directory and run:

        ```bash
        npm run dev
        ```

    *   **Terminal 4 (npm run start - Node.js)**:
        Navigate to the root project directory and run:

        ```bash
        npm run start
        ```

You should now have all four services running.
