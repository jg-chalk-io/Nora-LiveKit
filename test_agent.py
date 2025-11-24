#!/usr/bin/env python3
"""Test script to debug agent startup."""

import sys
import os

print("=" * 60)
print("AGENT STARTUP DEBUG")
print("=" * 60)

# Step 1: Load environment
print("\n[1/6] Loading .env file...")
try:
    from dotenv import load_dotenv
    load_dotenv()
    print(f"  ✓ .env loaded")
    print(f"  LIVEKIT_URL: {os.getenv('LIVEKIT_URL', 'NOT SET')}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Step 2: Import config
print("\n[2/6] Importing config module...")
try:
    from nora_livekit.config import Config, setup_logging
    print("  ✓ Config imported")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Load config from environment
print("\n[3/6] Loading config from environment...")
try:
    config = Config.from_env()
    print(f"  ✓ Config loaded: {config.livekit_url}")
    setup_logging(config)
    print("  ✓ Logging configured")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Import agent
print("\n[4/6] Importing agent module...")
try:
    from nora_livekit.agent import NoraAgent
    print("  ✓ Agent imported")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 5: Create agent instance
print("\n[5/6] Creating agent instance...")
try:
    agent = NoraAgent(config)
    print(f"  ✓ Agent created")
    print(f"  Agent shutdown event: {agent._shutdown_event}")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 6: Start agent
print("\n[6/6] Starting agent...")
try:
    import asyncio

    async def run_agent():
        print("  → Calling agent.start()...")
        await agent.start()
        print(f"  ✓ Agent started! Room: {agent.room}")
        print(f"  Shutdown event: {agent._shutdown_event}")
        print(f"  Event is_set: {agent._shutdown_event.is_set()}")

        print("\n" + "=" * 60)
        print("AGENT IS RUNNING")
        print("=" * 60)
        print("The agent should now be waiting for shutdown signal...")
        print("Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        # Wait for shutdown
        await agent._shutdown_event.wait()

        print("\n  → Shutdown signal received, stopping...")
        await agent.stop()
        print("  ✓ Agent stopped")

    asyncio.run(run_agent())

except KeyboardInterrupt:
    print("\n  ✓ Interrupted by user")
except Exception as e:
    print(f"\n  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("AGENT SHUTDOWN COMPLETE")
print("=" * 60)
