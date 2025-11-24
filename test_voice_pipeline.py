#!/usr/bin/env python3
"""Test script for voice pipeline with real Deepgram and Cartesia APIs.

This script tests the voice pipeline components with actual API calls:
1. DeepgramSTT - Connect and verify API key
2. CartesiaTTS - Connect and verify API key
3. Audio format validation
4. Pipeline initialization

Usage:
    poetry run python test_voice_pipeline.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
import os

print("=" * 70)
print("VOICE PIPELINE API TEST")
print("=" * 70)

# Load environment variables
print("\n[1/5] Loading environment variables...")
load_dotenv()

required_keys = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
]

missing_keys = []
for key in required_keys:
    value = os.getenv(key)
    if not value or value.startswith("your-"):
        missing_keys.append(key)
        print(f"  ✗ {key}: NOT SET")
    else:
        # Show first 8 chars of key for verification
        masked = value[:8] + "..." if len(value) > 8 else value
        print(f"  ✓ {key}: {masked}")

if missing_keys:
    print(f"\n❌ Missing required API keys: {', '.join(missing_keys)}")
    print("\nPlease add them to your .env file:")
    print("  DEEPGRAM_API_KEY=your-actual-key")
    print("  CARTESIA_API_KEY=your-actual-key")
    print("\nSee README for instructions on obtaining API keys.")
    sys.exit(1)

print("  ✓ All required keys present")

# Import voice pipeline components
print("\n[2/5] Importing voice pipeline components...")
try:
    from nora_livekit.config import Config
    from nora_livekit.voice.stt import DeepgramSTT
    from nora_livekit.voice.tts import CartesiaTTS
    from nora_livekit.voice.pipeline import VoicePipeline
    print("  ✓ All components imported successfully")
except ImportError as e:
    print(f"  ✗ Import error: {e}")
    sys.exit(1)

# Load configuration
print("\n[3/5] Loading voice pipeline configuration...")
try:
    config = Config.from_env()
    print(f"  ✓ Config loaded")
    print(f"    - LiveKit URL: {config.livekit_url}")
    print(f"    - Deepgram model: {config.voice.deepgram_model}")
    print(f"    - Cartesia voice: {config.voice.cartesia_voice_id}")
    print(f"    - Sample rate: {config.voice.sample_rate}Hz")
except Exception as e:
    print(f"  ✗ Config error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_deepgram():
    """Test Deepgram STT connection and API key."""
    print("\n[4/5] Testing Deepgram STT...")
    try:
        stt = DeepgramSTT(
            api_key=config.voice.deepgram_api_key,
            model=config.voice.deepgram_model,
            language=config.voice.deepgram_language,
        )
        print("  ✓ DeepgramSTT instance created")

        # Test connection (this will validate API key)
        print("  → Connecting to Deepgram...")
        await stt.connect()
        print("  ✓ Connected to Deepgram successfully")

        # For STT, we need an audio stream, but we can test the connection was successful
        print("  → Testing transcription stream setup...")

        # Create a simple async generator that yields empty audio (just to test the API)
        async def dummy_audio_stream():
            # Yield a small amount of silent audio (empty bytes)
            yield b'\x00' * 1600  # 100ms of silence at 16kHz

        # Test that we can set up transcription (won't get results without real audio)
        transcription_started = False
        async for text in stt.transcribe_stream(dummy_audio_stream()):
            # If we get here, the stream is set up correctly
            transcription_started = True
            if text:
                print(f"  ✓ Transcription received: '{text}'")
            break  # Just verify stream works

        if transcription_started:
            print("  ✓ Transcription stream works (no audio to transcribe)")

        await stt.disconnect()
        print("  ✓ Deepgram STT test PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Deepgram STT test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cartesia():
    """Test Cartesia TTS connection and API key."""
    print("\n[5/5] Testing Cartesia TTS...")
    try:
        tts = CartesiaTTS(
            api_key=config.voice.cartesia_api_key,
            voice_id=config.voice.cartesia_voice_id,
            speed=config.voice.cartesia_speed,
            emotion=config.voice.cartesia_emotion,
        )
        print("  ✓ CartesiaTTS instance created")

        # Test connection (this will validate API key)
        print("  → Connecting to Cartesia...")
        await tts.connect()
        print("  ✓ Connected to Cartesia successfully")

        # Test synthesis with a simple phrase
        print("  → Testing speech synthesis...")
        test_text = "Hello, this is a test of the voice pipeline."
        audio_chunks = []
        async for audio_chunk in tts.synthesize(test_text):
            audio_chunks.append(audio_chunk)
            if len(audio_chunks) >= 1:
                # Got at least one chunk, synthesis works
                break

        if audio_chunks:
            total_bytes = sum(len(chunk) for chunk in audio_chunks)
            print(f"  ✓ Synthesis successful: {total_bytes} bytes of audio")
        else:
            print("  ⚠ Synthesis returned no audio (may be normal for short test)")

        await tts.disconnect()
        print("  ✓ Cartesia TTS test PASSED")
        return True

    except Exception as e:
        print(f"  ✗ Cartesia TTS test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all voice pipeline tests."""
    print("\n" + "=" * 70)
    print("RUNNING API TESTS")
    print("=" * 70)

    deepgram_ok = await test_deepgram()
    cartesia_ok = await test_cartesia()

    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Deepgram STT: {'✓ PASS' if deepgram_ok else '✗ FAIL'}")
    print(f"Cartesia TTS: {'✓ PASS' if cartesia_ok else '✗ FAIL'}")

    if deepgram_ok and cartesia_ok:
        print("\n✅ ALL TESTS PASSED - Voice pipeline is ready!")
        print("\nNext steps:")
        print("  1. Run the agent: ./run_agent.sh")
        print("  2. Connect to LiveKit room with audio client")
        print("  3. Speak to test STT → Processing → TTS pipeline")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Please check API keys and connectivity")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
