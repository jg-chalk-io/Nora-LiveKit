#!/usr/bin/env python3
"""Fetch and display Langfuse traces for Nora voice agent."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import httpx
from datetime import datetime

def main():
    # Use the API client directly
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    print("=" * 70)
    print("LANGFUSE TRACES - Nora Voice Agent")
    print(f"Host: {host}")
    print("=" * 70)

    try:
        # Use REST API directly
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
            tags = trace.get("tags", [])
            metadata = trace.get("metadata", {})
            output = trace.get("output", {})

            print(f"📞 Trace: {trace_name}")
            print(f"   ID: {trace_id[:16]}...")
            print(f"   Created: {timestamp}")

            if tags:
                print(f"   Tags: {', '.join(tags)}")

            if metadata:
                print(f"   Metadata:")
                for k, v in metadata.items():
                    print(f"     {k}: {v}")

            if output:
                print(f"   Output:")
                if isinstance(output, dict):
                    for k, v in output.items():
                        if k == "metrics" and isinstance(v, dict):
                            print(f"     📊 Metrics:")
                            for mk, mv in v.items():
                                print(f"       {mk}: {mv}")
                        else:
                            print(f"     {k}: {v}")
                else:
                    print(f"     {output}")

            # Fetch observations (spans/generations) for this trace
            try:
                obs_url = f"{host}/api/public/observations"
                obs_response = httpx.get(
                    obs_url,
                    auth=(public_key, secret_key),
                    params={"traceId": trace_id, "limit": 50},
                    timeout=30.0,
                )
                obs_response.raise_for_status()
                obs_data = obs_response.json()
                observations = obs_data.get("data", [])

                if observations:
                    print(f"   Observations ({len(observations)}):")

                    # Group by type
                    stt_obs = [o for o in observations if "stt" in o.get("name", "").lower()]
                    llm_obs = [o for o in observations if "llm" in o.get("name", "").lower() or o.get("type") == "GENERATION"]
                    tts_obs = [o for o in observations if "tts" in o.get("name", "").lower()]
                    pipeline_obs = [o for o in observations if "pipeline" in o.get("name", "").lower()]

                    if stt_obs:
                        print(f"     🎤 STT ({len(stt_obs)} calls):")
                        for o in stt_obs[:3]:
                            latency = _calc_latency_dict(o)
                            print(f"        - {latency}")

                    if llm_obs:
                        print(f"     🧠 LLM ({len(llm_obs)} calls):")
                        for o in llm_obs[:3]:
                            latency = _calc_latency_dict(o)
                            usage = o.get("usage", {})
                            tokens = ""
                            if usage:
                                total = usage.get("totalTokens") or usage.get("total_tokens", 0)
                                tokens = f" | {total} tokens"
                            model = o.get("model", "")
                            if model:
                                tokens += f" | {model}"
                            print(f"        - {latency}{tokens}")

                    if tts_obs:
                        print(f"     🔊 TTS ({len(tts_obs)} calls):")
                        for o in tts_obs[:3]:
                            latency = _calc_latency_dict(o)
                            meta = o.get("metadata", {})
                            ttfb = meta.get("ttfb_ms", "")
                            if ttfb:
                                latency += f" (TTFB: {ttfb:.0f}ms)"
                            print(f"        - {latency}")

                    if pipeline_obs:
                        print(f"     ⏱️  Pipeline ({len(pipeline_obs)} turns):")
                        for o in pipeline_obs[:3]:
                            meta = o.get("metadata", {})
                            e2e = meta.get("e2e_latency_ms", 0)
                            stt_lat = meta.get("stt_latency_ms", 0)
                            llm_lat = meta.get("llm_latency_ms", 0)
                            tts_lat = meta.get("tts_latency_ms", 0)
                            print(f"        - E2E: {e2e:.0f}ms (STT: {stt_lat:.0f} | LLM: {llm_lat:.0f} | TTS: {tts_lat:.0f})")

            except Exception as obs_e:
                print(f"   (Could not fetch observations: {obs_e})")

            print("-" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def _calc_latency_dict(obs):
    """Calculate latency from observation dict."""
    start = obs.get("startTime")
    end = obs.get("endTime")
    if start and end:
        try:
            # Parse ISO format timestamps
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            delta = (end_dt - start_dt).total_seconds() * 1000
            return f"{delta:.0f}ms"
        except Exception:
            pass
    return "N/A"


if __name__ == "__main__":
    main()
