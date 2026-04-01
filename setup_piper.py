"""Download and install Piper TTS engine + voice model."""

import os
import shutil
import urllib.request
import zipfile

PIPER_DIR = "piper"
VOICES_DIR = os.path.join(PIPER_DIR, "voices")
PIPER_EXE = os.path.join(PIPER_DIR, "piper.exe")

PIPER_URL = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
VOICE_NAME = "en_US-lessac-medium"


def download_piper():
    """Download and extract the Piper binary."""
    if os.path.exists(PIPER_EXE):
        print("Piper already installed.")
        return

    os.makedirs(PIPER_DIR, exist_ok=True)
    zip_path = os.path.join(PIPER_DIR, "piper.zip")
    temp_dir = os.path.join(PIPER_DIR, "_temp")

    print("Downloading Piper TTS engine...")
    urllib.request.urlretrieve(PIPER_URL, zip_path)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp_dir)

    # Handle nested directory — the zip may extract to a subdirectory
    contents = os.listdir(temp_dir)
    src = temp_dir
    if len(contents) == 1 and os.path.isdir(os.path.join(temp_dir, contents[0])):
        src = os.path.join(temp_dir, contents[0])

    for item in os.listdir(src):
        src_path = os.path.join(src, item)
        dst_path = os.path.join(PIPER_DIR, item)
        if os.path.exists(dst_path):
            if os.path.isdir(dst_path):
                shutil.rmtree(dst_path)
            else:
                os.remove(dst_path)
        shutil.move(src_path, dst_path)

    shutil.rmtree(temp_dir)
    os.remove(zip_path)
    print("Piper installed.")


def download_voice():
    """Download the voice model files."""
    os.makedirs(VOICES_DIR, exist_ok=True)
    model_path = os.path.join(VOICES_DIR, f"{VOICE_NAME}.onnx")

    if os.path.exists(model_path):
        print("Voice model already downloaded.")
        return

    print(f"Downloading voice model ({VOICE_NAME})...")
    urllib.request.urlretrieve(
        f"{VOICE_BASE}/{VOICE_NAME}.onnx", model_path
    )
    urllib.request.urlretrieve(
        f"{VOICE_BASE}/{VOICE_NAME}.onnx.json", f"{model_path}.json"
    )
    print("Voice model downloaded.")


if __name__ == "__main__":
    download_piper()
    download_voice()
