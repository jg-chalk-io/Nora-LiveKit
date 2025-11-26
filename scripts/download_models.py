#!/usr/bin/env python3
"""Download ML models for Nora Voice Agent.

This script downloads all model files during Docker build:
- Silero VAD model (for voice activity detection)
- Turn Detector model (for end-of-turn prediction)

The turn detector MODEL FILES can be pre-downloaded, but EnglishModel()
instantiation requires job context - that happens at runtime.

Usage:
    python scripts/download_models.py
"""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-downloader")

# Ensure cache is in the right place for both build and runtime
os.environ.setdefault("HF_HOME", "/app/.cache/huggingface")
os.environ.setdefault("HF_HUB_CACHE", "/app/.cache/huggingface/hub")
os.environ.setdefault("TORCH_HOME", "/app/.cache/torch")
os.environ.setdefault("XDG_CACHE_HOME", "/app/.cache")


def download_silero_vad():
    """Download Silero VAD model."""
    logger.info("Downloading Silero VAD model...")
    try:
        import livekit.plugins.silero as silero
        silero.VAD.load()
        logger.info("✓ Silero VAD model downloaded")
    except Exception as e:
        logger.error(f"Silero VAD download failed: {e}")
        raise


def download_turn_detector():
    """Download Turn Detector model files from HuggingFace.

    Downloads:
    - Tokenizer files (via transformers)
    - ONNX model file (model_q8.onnx)
    - Language config (languages.json)

    These files are cached so EnglishModel() can load them at runtime
    without network access.
    """
    logger.info("Downloading Turn Detector model...")

    HG_MODEL = "livekit/turn-detector"
    REVISION = "v1.2.2-en"

    try:
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer

        # Download tokenizer (multiple files)
        logger.info(f"  Downloading tokenizer from {HG_MODEL}@{REVISION}...")
        AutoTokenizer.from_pretrained(HG_MODEL, revision=REVISION)
        logger.info("  ✓ Tokenizer downloaded")

        # Download ONNX model
        logger.info("  Downloading ONNX model...")
        hf_hub_download(
            repo_id=HG_MODEL,
            filename="model_q8.onnx",
            subfolder="onnx",
            revision=REVISION,
        )
        logger.info("  ✓ ONNX model downloaded")

        # Download language config
        logger.info("  Downloading language config...")
        hf_hub_download(
            repo_id=HG_MODEL,
            filename="languages.json",
            revision=REVISION,
        )
        logger.info("  ✓ Language config downloaded")

        logger.info("✓ Turn Detector model downloaded successfully")

    except Exception as e:
        logger.error(f"Turn Detector download failed: {e}")
        logger.warning("Turn detector will be disabled at runtime")
        # Don't raise - allow build to continue without turn detector
        # The agent will fall back to VAD-only turn detection


def main():
    """Download all required models."""
    print("\n" + "=" * 50)
    print("  NORA - Model Downloader")
    print("=" * 50 + "\n")

    print(f"HF_HOME: {os.environ.get('HF_HOME', 'default')}")
    print(f"HF_HUB_CACHE: {os.environ.get('HF_HUB_CACHE', 'default')}")
    print()

    # Download VAD (required)
    download_silero_vad()

    # Download Turn Detector (optional but recommended)
    download_turn_detector()

    print("\n" + "=" * 50)
    print("  All models downloaded!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
