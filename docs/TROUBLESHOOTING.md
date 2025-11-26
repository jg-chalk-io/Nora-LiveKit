# Troubleshooting Guide - Nora-LiveKit Voice Agent

Common issues, solutions, and diagnostic procedures for Nora-LiveKit voice agent.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Configuration Issues](#configuration-issues)
3. [API Connectivity](#api-connectivity)
4. [Audio Issues](#audio-issues)
5. [Performance Issues](#performance-issues)
6. [Error Messages](#error-messages)
7. [Debugging](#debugging)
8. [Log Analysis](#log-analysis)

---

## Quick Diagnostics

### Check Installation

Verify that all dependencies are installed correctly:

```bash
poetry show
```

Expected output should include:
- `livekit` >= 1.0.19
- `livekit-agents` >= 1.0.23
- `deepgram-sdk` (via livekit-plugins-deepgram)
- `cartesia` (via livekit-plugins-cartesia)

### Verify Configuration

Test that configuration loads correctly:

```bash
python -c "
from nora_livekit.config import Config
try:
    config = Config.from_env()
    print('✓ Configuration loaded successfully')
    print(f'  - LiveKit URL: {config.livekit_url}')
    print(f'  - Voice Config: {config.voice is not None}')
except Exception as e:
    print(f'✗ Configuration error: {e}')
"
```

### Check Python Version

Ensure you're using Python 3.12 or higher:

```bash
python --version
# Should output: Python 3.12.x or higher
```

### Verify API Keys

Check that API keys are set (without displaying them):

```bash
python -c "
import os
keys_ok = True
for key in ['DEEPGRAM_API_KEY', 'CARTESIA_API_KEY', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET']:
    if not os.getenv(key):
        print(f'✗ Missing: {key}')
        keys_ok = False
    else:
        print(f'✓ Set: {key}')
if keys_ok:
    print('\n✓ All API keys are configured')
"
```

---

## Configuration Issues

### Error: `ValueError: API key cannot be empty`

**Cause**: Deepgram, Cartesia, or LiveKit API key is missing or empty

**Solutions**:

1. **Check .env file exists**:
   ```bash
   ls -la .env
   ```
   If missing, create from template:
   ```bash
   cp .env.template .env
   ```

2. **Verify key is set**:
   ```bash
   grep DEEPGRAM_API_KEY .env
   grep CARTESIA_API_KEY .env
   ```

3. **Check for whitespace**:
   ```bash
   # Bad: Key with spaces
   DEEPGRAM_API_KEY= your-key

   # Good: No spaces around =
   DEEPGRAM_API_KEY=your-key
   ```

4. **Reload environment**:
   ```bash
   # If using direnv
   direnv reload

   # Or create new shell session
   source .env  # Not recommended for production
   ```

### Error: `Missing required environment variable: LIVEKIT_URL`

**Cause**: Required LiveKit configuration is missing

**Solutions**:

1. **Check .env file**:
   ```bash
   cat .env | grep LIVEKIT
   ```

2. **Set missing variables**:
   ```bash
   export LIVEKIT_URL=wss://your-livekit-server.com
   export LIVEKIT_API_KEY=your-api-key
   export LIVEKIT_API_SECRET=your-api-secret
   ```

3. **Required variables**:
   - `LIVEKIT_URL`: WebSocket URL (e.g., `wss://livekit.example.com`)
   - `LIVEKIT_API_KEY`: API key from LiveKit console
   - `LIVEKIT_API_SECRET`: API secret from LiveKit console

### Error: `Invalid configuration: sample_rate must be positive`

**Cause**: Invalid voice configuration parameter

**Solutions**:

1. **Check VOICE_SAMPLE_RATE**:
   ```bash
   grep VOICE_SAMPLE_RATE .env
   ```
   Should be: `16000` (16 kHz)

2. **Valid values**:
   - `VOICE_SAMPLE_RATE`: 8000, 16000, 44100, 48000 (16000 recommended)
   - `VOICE_CHANNELS`: 1 (mono) or 2 (stereo)
   - `VAD_THRESHOLD`: 0.0 to 1.0 (0.5 recommended)

---

## API Connectivity

### Error: `Connection refused to Deepgram API`

**Cause**: Network connectivity issue or invalid Deepgram API key

**Solutions**:

1. **Check network**:
   ```bash
   curl -I https://api.deepgram.com/
   # Should return HTTP 200 or 401 (not connection refused)
   ```

2. **Verify API key**:
   - Go to https://console.deepgram.com
   - Copy API key and verify it matches `DEEPGRAM_API_KEY`
   - Check key hasn't expired

3. **Test API directly**:
   ```bash
   python -c "
   import asyncio
   from livekit.plugins.deepgram import STT

   async def test():
       stt = STT(api_key='your-key')
       print('✓ Deepgram STT initialized')

   asyncio.run(test())
   "
   ```

### Error: `401 Unauthorized - Invalid Deepgram API key`

**Cause**: API key is invalid, expired, or revoked

**Solutions**:

1. **Verify key format**:
   - Deepgram keys start with `dgsk_`
   - Check for typos or extra spaces

2. **Generate new key**:
   - Go to https://console.deepgram.com/keys
   - Create new API key
   - Update `DEEPGRAM_API_KEY` in .env

3. **Check key permissions**:
   - Verify key has STT transcription permissions
   - Check key scopes in console

### Error: `Connection refused to Cartesia API`

**Cause**: Network connectivity issue or invalid Cartesia API key

**Solutions**:

1. **Check Cartesia API endpoint**:
   ```bash
   curl -I https://api.cartesia.ai/
   ```

2. **Verify API key**:
   - Go to https://play.cartesia.ai/settings/api-keys
   - Copy API key and verify format
   - Check key is active

3. **Test Cartesia directly**:
   ```bash
   python -c "
   import asyncio
   from livekit.plugins.cartesia import TTS

   async def test():
       tts = TTS(api_key='your-key')
       print('✓ Cartesia TTS initialized')

   asyncio.run(test())
   "
   ```

### Error: `503 Service Unavailable` (intermittent)

**Cause**: Temporary API outage or rate limiting

**Solutions**:

1. **Check API status**:
   - Deepgram: https://deepgram.statuspage.io/
   - Cartesia: Check their status page

2. **Implement retry logic** (already built-in):
   - Agent automatically retries with exponential backoff
   - Max 3 attempts with delays: 1s, 2s, 4s

3. **Check rate limits**:
   - Deepgram: Verify account doesn't exceed concurrent connections
   - Cartesia: Check monthly usage limits

### Error: `429 Too Many Requests`

**Cause**: Rate limit exceeded

**Solutions**:

1. **Check API usage**:
   - Deepgram: https://console.deepgram.com/analytics
   - Cartesia: Check account dashboard

2. **Implement request throttling**:
   ```python
   import asyncio

   async def throttled_transcribe(stt, audio_stream, delay=0.1):
       async for result in stt.transcribe_stream(audio_stream):
           await asyncio.sleep(delay)  # Add delay between requests
           yield result
   ```

3. **Upgrade plan**:
   - Check rate limits for your plan
   - Upgrade if necessary

---

## Audio Issues

### Issue: `No audio output from agent`

**Cause**: Audio not being published to LiveKit track

**Solutions**:

1. **Verify LiveKit room connection**:
   ```bash
   python -c "
   import asyncio
   from livekit import Room

   async def test():
       room = Room()
       # Attempt connection
       await room.connect('wss://livekit.example.com', 'token')
       print('✓ Connected to LiveKit')
       await room.disconnect()

   asyncio.run(test())
   "
   ```

2. **Check audio track permissions**:
   - Verify room token includes audio publish permissions
   - Check LiveKit access control settings

3. **Verify audio handler**:
   ```bash
   # Check if audio track is subscribed
   # Add debug logging to audio_handler.py
   ```

4. **Test audio publishing**:
   ```python
   async def test_publish():
       from nora_livekit.voice.audio_handler import AudioHandler

       audio_handler = AudioHandler(room)

       # Create dummy audio
       dummy_audio = b'\x00' * 1600  # 100ms of silence

       try:
           await audio_handler.publish_audio(dummy_audio)
           print("✓ Audio published successfully")
       except Exception as e:
           print(f"✗ Publishing failed: {e}")
   ```

### Issue: `Audio quality is poor or distorted`

**Cause**: Audio format mismatch or codec issues

**Solutions**:

1. **Verify audio format**:
   - Expected: 16-bit PCM, 16 kHz mono
   - Check sample rate: `VOICE_SAMPLE_RATE=16000`
   - Check channels: `VOICE_CHANNELS=1`

2. **Check audio buffering**:
   ```python
   # Verify buffer size is appropriate
   # Default: 100ms buffer = 1600 samples × 2 bytes = 3.2KB
   ```

3. **Reduce audio processing latency**:
   - Decrease buffer duration
   - Use interim results from STT
   - Process audio in smaller chunks

### Issue: `Audio dropout or stuttering`

**Cause**: Network latency or buffer underflow

**Solutions**:

1. **Check network**:
   ```bash
   # Measure latency to API servers
   ping api.deepgram.com
   ping api.cartesia.ai

   # Run network diagnostics
   mtr api.deepgram.com -c 100
   ```

2. **Increase buffer size**:
   ```bash
   # Increase audio buffer duration
   VOICE_BUFFER_DURATION_MS=200  # Default is 100ms
   ```

3. **Reduce concurrent operations**:
   - Limit number of simultaneous conversations
   - Reduce overall system load

---

## Performance Issues

### Issue: `High latency (>500ms)`

**Cause**: Network delays or processing bottlenecks

**Solutions**:

1. **Measure latency**:
   ```python
   import time

   async def measure_latency():
       start = time.time()
       # Perform STT transcription
       async for result in stt.transcribe_stream(audio):
           if result.is_final:
               latency_ms = (time.time() - start) * 1000
               print(f"Latency: {latency_ms:.0f}ms")
   ```

2. **Optimize network**:
   - Move agent closer to API servers (geographically)
   - Use CDN or proxy if available
   - Check for packet loss

3. **Optimize processing**:
   - Use interim results for early feedback
   - Process audio in parallel (STT + TTS)
   - Reduce buffer size

4. **Check resource usage**:
   ```bash
   # Monitor CPU and memory
   top -l 1 | head -20

   # On Linux
   ps aux | grep nora
   ```

### Issue: `High memory usage`

**Cause**: Audio buffer accumulation or memory leak

**Solutions**:

1. **Check memory usage**:
   ```bash
   python -c "
   import tracemalloc
   tracemalloc.start()

   # Run agent for a period
   # Then check:
   current, peak = tracemalloc.get_traced_memory()
   print(f'Current: {current / 10**6:.1f} MB')
   print(f'Peak: {peak / 10**6:.1f} MB')
   tracemalloc.stop()
   "
   ```

2. **Verify buffer cleanup**:
   - Check that audio buffers are properly garbage collected
   - Verify no circular references in audio processing

3. **Profile memory usage**:
   ```bash
   pip install memory-profiler
   python -m memory_profiler agent.py
   ```

### Issue: `CPU usage too high`

**Cause**: Continuous audio processing or inefficient algorithms

**Solutions**:

1. **Profile CPU usage**:
   ```bash
   pip install py-spy
   py-spy record -o profile.svg -- python -m nora_livekit.agent
   ```

2. **Check for blocking operations**:
   - Ensure no synchronous I/O in async code
   - Use async versions of libraries

3. **Reduce audio processing**:
   - Decrease sample rate if acceptable
   - Process audio in larger chunks
   - Limit concurrent conversations

---

## Error Messages

### Error: `RuntimeError: Voice pipeline not running`

**Cause**: Attempting to use pipeline before calling `start()`

**Solutions**:
```python
# Always call start() before using pipeline
await pipeline.start()
await pipeline.process_audio_stream()
await pipeline.stop()
```

### Error: `asyncio.CancelledError`

**Cause**: Task cancelled during operation

**Solutions**:
```python
# Wrap in try/except to handle cancellation
try:
    await pipeline.process_audio_stream()
except asyncio.CancelledError:
    await pipeline.stop()
    raise
```

### Error: `WebSocket connection closed`

**Cause**: Network disconnection or timeout

**Solutions**:
1. Check network connectivity
2. Verify API key is valid
3. Implement reconnection logic:
   ```python
   async def reconnect_with_retry(stt, max_retries=3):
       for attempt in range(max_retries):
           try:
               await stt.connect()
               return
           except Exception as e:
               if attempt < max_retries - 1:
                   wait_time = 2 ** attempt  # Exponential backoff
                   await asyncio.sleep(wait_time)
   ```

---

## Debugging

### Enable Debug Logging

Set log level to DEBUG:

```bash
export LOG_LEVEL=DEBUG
poetry run python -m nora_livekit.agent
```

Or in code:

```python
from nora_livekit.config import Config

config = Config.from_env()
config.log_level = "DEBUG"
```

### Log Output Example

```json
{
  "event": "voice.stt.connected",
  "timestamp": "2025-11-25T12:34:56.789Z",
  "level": "info",
  "model": "nova-2"
}
```

### Add Debug Statements

```python
import structlog

logger = structlog.get_logger(__name__)

async def process():
    logger.debug("processing.start", participant_id=participant_id)
    try:
        result = await operation()
        logger.debug("processing.success", result=result)
    except Exception as e:
        logger.debug("processing.error", error=str(e), exc_info=True)
        raise
```

### Test Individual Components

**Test STT**:
```bash
python -c "
import asyncio
from nora_livekit.voice.stt import DeepgramSTT

async def test_stt():
    stt = DeepgramSTT(api_key='your-key')
    await stt.connect()
    # Test with dummy audio
    dummy_audio = [b'\x00' * 1600]  # 100ms silence
    async for result in stt.transcribe_stream(dummy_audio.__iter__().__anext__):
        print(result)
    await stt.disconnect()

asyncio.run(test_stt())
"
```

**Test TTS**:
```bash
python -c "
import asyncio
from nora_livekit.voice.tts import CartesiaTTS

async def test_tts():
    tts = CartesiaTTS(api_key='your-key')
    await tts.connect()
    async for chunk in tts.synthesize('Hello world'):
        print(f'Audio chunk: {len(chunk)} bytes')
    await tts.disconnect()

asyncio.run(test_tts())
"
```

### Use pytest for Testing

```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test
poetry run pytest tests/voice/test_stt.py::test_deepgram_connect -v

# Run with print output
poetry run pytest tests/ -v -s

# Run with coverage
poetry run pytest tests/ --cov=src/nora_livekit --cov-report=html
```

---

## Log Analysis

### View Recent Logs

```bash
# Show last 50 lines
tail -50 logs/agent.log

# Follow logs in real-time
tail -f logs/agent.log
```

### Filter Logs by Event

```bash
# Search for errors
grep '"level":"error"' logs/agent.log

# Search for specific events
grep 'voice.stt.transcription' logs/agent.log

# Count occurrences
grep 'voice.stt.transcription' logs/agent.log | wc -l
```

### Parse JSON Logs

```bash
# Pretty-print JSON logs
python -c "
import json
import sys
for line in sys.stdin:
    try:
        print(json.dumps(json.loads(line), indent=2))
    except:
        print(line)
" < logs/agent.log
```

### Monitor in Real-time

```bash
# Watch for errors
watch -n 1 'grep error logs/agent.log | tail -5'

# Monitor specific metric
grep 'voice.pipeline' logs/agent.log | tail -20
```

---

## Getting Help

### Community Resources

- Check [Architecture Documentation](ARCHITECTURE.md)
- See [API Reference](API_REFERENCE.md)
- Review [README](../README.md) for overview

### Diagnostic Bundle

Collect information for support:

```bash
#!/bin/bash
echo "=== System Info ==="
python --version
uname -a

echo -e "\n=== Dependencies ==="
poetry show

echo -e "\n=== Configuration ==="
# DON'T output actual keys!
grep -E '^[A-Z_]+=' .env | sed 's/=.*/=***/'

echo -e "\n=== Recent Logs ==="
tail -100 logs/agent.log

echo -e "\n=== Test Results ==="
poetry run pytest tests/ -q
```

### Report Issues

When reporting issues, include:
1. Error message and stack trace
2. Steps to reproduce
3. Configuration (without API keys)
4. Diagnostic bundle output
5. System information (OS, Python version)

---

## FAQ

### Q: How do I switch between STT models?

A: Set `DEEPGRAM_MODEL` environment variable:
```bash
export DEEPGRAM_MODEL=nova-3  # or nova-3-general, nova-3-financial
```

### Q: Can I use a different TTS provider?

A: Currently only Cartesia is supported. Extensibility for other providers is planned in future SPECs.

### Q: How do I reduce API costs?

A:
- Use lower-quality models for non-critical conversations
- Implement VAD to skip silent periods
- Cache common responses
- Monitor usage closely

### Q: What's the minimum latency I can achieve?

A: Typical latency is 200-400ms:
- Network: 20-50ms
- STT: 100-200ms
- TTS: 50-150ms
- Processing: 30-100ms

### Q: How many concurrent conversations can one agent handle?

A: Currently designed for 1 conversation per agent instance. For multiple conversations, deploy multiple agent instances.

---

**Document Version**: 1.0
**Last Updated**: November 25, 2025
**Status**: Complete
