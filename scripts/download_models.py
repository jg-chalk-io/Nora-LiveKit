#!/usr/bin/env python3
"""Download ML models for Nora Voice Agent.

This script downloads model files during Docker build without requiring
environment variables. Run this before deploying to ensure models are
available at runtime.

Usage:
    python scripts/download_models.py
"""

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-downloader")


def download_silero_vad():
    """Download Silero VAD model."""
    logger.info("Downloading Silero VAD model...")
    try:
        import livekit.plugins.silero as silero
        silero.VAD.load()
        logger.info("✓ Silero VAD model downloaded")
    except Exception as e:
        logger.warning(f"Silero VAD download issue (may already exist): {e}")


def download_turn_detector():
    """Download turn detector model."""
    logger.info("Downloading turn detector model...")
    try:
        from livekit.plugins.turn_detector.english import EnglishModel
        EnglishModel()
        logger.info("✓ Turn detector model downloaded")
    except Exception as e:
        logger.warning(f"Turn detector download issue (may already exist): {e}")


def main():
    """Download all required models."""
    print("\n" + "=" * 50)
    print("  NORA - Model Downloader")
    print("=" * 50 + "\n")

    download_silero_vad()
    download_turn_detector()

    print("\n" + "=" * 50)
    print("  Model download complete!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
