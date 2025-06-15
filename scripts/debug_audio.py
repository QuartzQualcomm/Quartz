#!/usr/bin/env python3
"""
Debug script to test DeepFilter model loading in isolation.
Run this on the problematic laptop to identify the exact issue.
"""

import os
import time
import traceback

def test_imports():
    """Test if all required imports work."""
    print("Testing imports...")
    try:
        import torch
        print(f"✓ PyTorch {torch.__version__}")
    except ImportError as e:
        print(f"✗ PyTorch: {e}")
        return False
    
    try:
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
    except ImportError as e:
        print(f"✗ NumPy: {e}")
        return False
    
    try:
        import soundfile as sf
        print(f"✓ SoundFile")
    except ImportError as e:
        print(f"✗ SoundFile: {e}")
        return False
    
    try:
        from df import enhance, init_df
        print("✓ DeepFilter imports")
    except ImportError as e:
        print(f"✗ DeepFilter: {e}")
        return False
    
    return True

def test_deepfilter_init():
    """Test DeepFilter model initialization."""
    print("\nTesting DeepFilter model loading...")
    try:
        start_time = time.time()
        from df import init_df
        model, df_state, _ = init_df()
        load_time = time.time() - start_time
        print(f"✓ DeepFilter model loaded in {load_time:.2f}s")
        return True
    except Exception as e:
        print(f"✗ DeepFilter model loading failed: {e}")
        traceback.print_exc()
        return False

def test_ffmpeg():
    """Test if ffmpeg is available."""
    print("\nTesting ffmpeg availability...")
    try:
        import subprocess
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"✓ {version_line}")
            return True
        else:
            print(f"✗ ffmpeg returned error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg not found in PATH")
        return False
    except Exception as e:
        print(f"✗ ffmpeg test failed: {e}")
        return False

def main():
    print("=== Audio API Debug Script ===\n")
    
    all_good = True
    all_good &= test_imports()
    all_good &= test_deepfilter_init()
    all_good &= test_ffmpeg()
    
    print(f"\n=== Summary ===")
    if all_good:
        print("✓ All tests passed! The issue might be elsewhere.")
    else:
        print("✗ Some tests failed. Fix the above issues first.")
    
    print("\nIf all tests pass but the API still hangs:")
    print("1. Check server logs for detailed error messages")
    print("2. Increase FastAPI timeout settings")
    print("3. Try smaller audio files first")
    print("4. Monitor CPU/RAM usage during processing")

if __name__ == "__main__":
    main()
