#!/usr/bin/env python3
"""Fetch and display Langfuse traces for Nora voice agent.

Usage:
    python scripts/fetch_langfuse_traces.py                    # List recent traces
    python scripts/fetch_langfuse_traces.py <trace_id>         # Show specific trace detail
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from datetime import datetime


def fetch_trace_detail(trace_id: str, host: str, public_key: str, secret_key: str):
    """Fetch and display detailed information for a specific trace."""
    print("=" * 80)
    print(f"LANGFUSE TRACE ANALYSIS: {trace_id}")
    print("=" * 80)

    # Fetch the trace
    trace_url = f"{host}/api/public/traces/{trace_id}"
    response = httpx.get(
        trace_url,
        auth=(public_key, secret_key),
        timeout=30.0,
    )
    response.raise_for_status()
    trace = response.json()

    print(f"\n📞 Trace: {trace.get('name', 'unknown')}")
    print(f"   ID: {trace_id}")
    print(f"   Created: {trace.get('timestamp', 'N/A')}")

    # Fetch all observations for this trace
    obs_url = f"{host}/api/public/observations"
    obs_response = httpx.get(
        obs_url,
        auth=(public_key, secret_key),
        params={"traceId": trace_id, "limit": 100},
        timeout=30.0,
    )
    obs_response.raise_for_status()
    observations = obs_response.json().get("data", [])

    # Sort by start time
    observations.sort(key=lambda x: x.get("startTime", ""))

    print(f"\n📊 OBSERVATIONS ({len(observations)} total)")
    print("-" * 80)

    # Track conversation flow
    conversation = []

    for i, obs in enumerate(observations):
        name = obs.get("name", "unknown")
        obs_type = obs.get("type", "")
        latency = _calc_latency_dict(obs)
        model = obs.get("model", "")

        # Get input/output
        inp = obs.get("input")
        out = obs.get("output")

        # For LLM generations, show conversation
        if obs_type == "GENERATION" or "llm" in name.lower():
            print(f"\n[{i}] 🧠 LLM: {name}")
            print(f"    Model: {model or 'N/A'} | Latency: {latency}")

            # Show messages
            if inp and isinstance(inp, dict):
                messages = inp.get("messages", [])
                if messages:
                    print(f"    📥 Input ({len(messages)} messages):")
                    for msg in messages:
                        role = msg.get("role", "?")
                        content = msg.get("content", "")
                        # Truncate long system prompts
                        if role == "system" and len(content) > 200:
                            content = content[:200] + "... [truncated]"
                        elif len(content) > 500:
                            content = content[:500] + "..."
                        print(f"       [{role}]: {content[:100]}{'...' if len(content) > 100 else ''}")

            # Show output
            if out:
                if isinstance(out, dict):
                    content = out.get("content", str(out))
                else:
                    content = str(out)
                print(f"    📤 Output: {content[:300]}{'...' if len(content) > 300 else ''}")
                conversation.append({"role": "assistant", "content": content})

        elif "tts" in name.lower():
            print(f"\n[{i}] 🔊 TTS: {name} | Latency: {latency}")
            if inp:
                text = inp if isinstance(inp, str) else inp.get("text", str(inp))[:100]
                print(f"    Text: {text}...")

        elif "stt" in name.lower():
            print(f"\n[{i}] 🎤 STT: {name} | Latency: {latency}")
            if out:
                transcript = out if isinstance(out, str) else out.get("text", str(out))
                print(f"    Transcript: {transcript}")
                conversation.append({"role": "user", "content": transcript})

        elif "user-speech" in name.lower():
            print(f"\n[{i}] 🗣️ USER SPEECH: {name}")
            if out:
                transcript = out.get("transcript", str(out)) if isinstance(out, dict) else str(out)
                print(f"    Said: \"{transcript}\"")

        elif "agent-turn" in name.lower() or "pipeline" in name.lower():
            print(f"\n[{i}] ⏱️ {name} | Latency: {latency}")
            meta = obs.get("metadata", {})
            if meta:
                print(f"    Metadata: {meta}")

    # Print conversation summary
    print("\n" + "=" * 80)
    print("💬 CONVERSATION SUMMARY")
    print("=" * 80)

    # Look for generations with actual content
    turn_num = 0
    for obs in observations:
        obs_type = obs.get("type", "")
        out = obs.get("output")

        if (obs_type == "GENERATION" or "llm" in obs.get("name", "").lower()) and out:
            turn_num += 1
            content = out.get("content", str(out)) if isinstance(out, dict) else str(out)
            if content and len(content) > 5:
                print(f"\n[{turn_num}] AGENT: {content[:200]}{'...' if len(content) > 200 else ''}")


def list_traces(host: str, public_key: str, secret_key: str):
    """List recent traces."""
    print("=" * 70)
    print("LANGFUSE TRACES - Nora Voice Agent")
    print(f"Host: {host}")
    print("=" * 70)

    api_url = f"{host}/api/public/traces"
    response = httpx.get(
        api_url,
        auth=(public_key, secret_key),
        params={"limit": 10},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    traces = data.get("data", [])

    if not traces:
        print("\nNo traces found yet. Make a test call first!")
        return

    print(f"\nFound {len(traces)} traces:\n")

    for trace in traces:
        trace_name = trace.get("name", "unknown")
        trace_id = trace.get("id", "")
        timestamp = trace.get("timestamp", "")
        metadata = trace.get("metadata", {})

        print(f"📞 Trace: {trace_name}")
        print(f"   ID: {trace_id}")
        print(f"   Created: {timestamp}")

        if metadata:
            print(f"   Metadata:")
            for k, v in metadata.items():
                print(f"     {k}: {v}")

        # Fetch observations summary
        try:
            obs_url = f"{host}/api/public/observations"
            obs_response = httpx.get(
                obs_url,
                auth=(public_key, secret_key),
                params={"traceId": trace_id, "limit": 50},
                timeout=30.0,
            )
            obs_response.raise_for_status()
            observations = obs_response.json().get("data", [])

            if observations:
                print(f"   Observations ({len(observations)}):")
                llm_obs = [o for o in observations if "llm" in o.get("name", "").lower() or o.get("type") == "GENERATION"]
                tts_obs = [o for o in observations if "tts" in o.get("name", "").lower()]

                if llm_obs:
                    print(f"     🧠 LLM ({len(llm_obs)} calls):")
                    for o in llm_obs[:3]:
                        latency = _calc_latency_dict(o)
                        model = o.get("model", "")
                        print(f"        - {latency}{' | ' + model if model else ''}")

                if tts_obs:
                    print(f"     🔊 TTS ({len(tts_obs)} calls):")
                    for o in tts_obs[:3]:
                        latency = _calc_latency_dict(o)
                        print(f"        - {latency}")

        except Exception as obs_e:
            print(f"   (Could not fetch observations: {obs_e})")

        print("-" * 70)


def _calc_latency_dict(obs):
    """Calculate latency from observation dict."""
    start = obs.get("startTime")
    end = obs.get("endTime")
    if start and end:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            delta = (end_dt - start_dt).total_seconds() * 1000
            return f"{delta:.0f}ms"
        except Exception:
            pass
    return "N/A"


def main():
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("Error: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be set")
        sys.exit(1)

    try:
        # Check if a trace ID was provided
        if len(sys.argv) > 1:
            trace_id = sys.argv[1]
            fetch_trace_detail(trace_id, host, public_key, secret_key)
        else:
            list_traces(host, public_key, secret_key)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
