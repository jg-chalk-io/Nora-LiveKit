#!/usr/bin/env python3
"""Download ML models for Nora Voice Agent.

This script downloads model files during Docker build without requiring
environment variables. Run this before deploying to ensure models are
available at runtime.

Usage:
    python scripts/download_models.py
"""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-downloader")

# Ensure HuggingFace cache is in the right place
os.environ.setdefault("HF_HOME", "/app/.cache/huggingface")
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
    """Download turn detector model files from HuggingFace."""
    logger.info("Downloading turn detector model files...")
    try:
        # Download all required files from HuggingFace Hub
        from huggingface_hub import hf_hub_download

        repo_id = "livekit/turn-detector"
        files = [
            "model_q8.onnx",
            "languages.json",
            "en/model_q8.onnx",
            "en/tokenizer.json",
        ]

        for filename in files:
            try:
                path = hf_hub_download(repo_id=repo_id, filename=filename)
                logger.info(f"  ✓ Downloaded {filename} -> {path}")
            except Exception as e:
                logger.warning(f"  ⚠ Could not download {filename}: {e}")

        # Now try to initialize to verify
        from livekit.plugins.turn_detector.english import EnglishModel
        EnglishModel()
        logger.info("✓ Turn detector initialized successfully")
    except Exception as e:
        logger.error(f"Turn detector download failed: {e}")
        raise


def main():
    """Download all required models."""
    print("\n" + "=" * 50)
    print("  NORA - Model Downloader")
    print("=" * 50 + "\n")

    print(f"Cache directory: {os.environ.get('HF_HOME', 'default')}")

    download_silero_vad()
    download_turn_detector()

    print("\n" + "=" * 50)
    print("  Model download complete!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
