#!/usr/bin/env python3
"""Download ML models for Nora Voice Agent.

This script downloads model files during Docker build.
Only VAD can be pre-downloaded - turn detector requires job context
and will download automatically at runtime.

Usage:
    python scripts/download_models.py
"""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-downloader")

# Ensure cache is in the right place
os.environ.setdefault("HF_HOME", "/app/.cache/huggingface")
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


def main():
    """Download all required models."""
    print("\n" + "=" * 50)
    print("  NORA - Model Downloader")
    print("=" * 50 + "\n")

    print(f"Cache directory: {os.environ.get('HF_HOME', 'default')}")

    download_silero_vad()

    print("\nNOTE: Turn detector will download at runtime (requires job context)")

    print("\n" + "=" * 50)
    print("  Model download complete!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
