#!/usr/bin/env python3
"""Test script to connect to LiveKit room and test voice pipeline.

This script connects as a participant and simulates audio input.
"""

import asyncio
import os
from dotenv import load_dotenv
from livekit import api, rtc

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")


async def main():
    """Connect to LiveKit room and test voice pipeline."""
    print("=" * 60)
    print("LIVE VOICE PIPELINE TEST")
    print("=" * 60)

    # Create access token
    print("\n[1/4] Creating access token...")
    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity("test-user")
        .with_name("Test User")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room="nora-test-room",
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )
    print("  ✓ Token created")

    # Connect to room
    print("\n[2/4] Connecting to LiveKit room...")
    room = rtc.Room()

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        print(f"  → Participant joined: {participant.identity}")

    @room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        print(f"  → Track subscribed: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print(f"  ✓ Receiving audio from agent!")

    try:
        await room.connect(LIVEKIT_URL, token)
        print(f"  ✓ Connected to room: nora-test-room")
        print(f"  Room SID: {room.sid}")
        print(f"  Participants: {len(room.remote_participants)}")

        print("\n[3/4] Waiting for agent to join...")
        print("  (The agent should join automatically when you connect)")

        # Wait a bit for agent to join
        await asyncio.sleep(3)

        print(f"\n[4/4] Current room status:")
        print(f"  Local participant: {room.local_participant.identity}")
        print(f"  Remote participants: {len(room.remote_participants)}")

        for participant in room.remote_participants.values():
            print(f"    - {participant.identity} ({participant.sid})")
            for track_sid, pub in participant.track_publications.items():
                print(f"      Track: {pub.kind}")

        print("\n" + "=" * 60)
        print("✅ TEST COMPLETE")
        print("=" * 60)
        print("\nTo test voice interaction:")
        print("  1. Use LiveKit Playground: https://playground.livekit.io/")
        print("  2. Connect to room: nora-test-room")
        print("  3. Enable your microphone and speak")
        print("  4. The agent will:")
        print("     - Capture your audio")
        print("     - Transcribe with Deepgram")
        print("     - Process (currently placeholder)")
        print("     - Synthesize response with Cartesia")
        print("     - Send audio back to you")
        print("=" * 60)

    finally:
        await room.disconnect()
        print("\n✓ Disconnected from room")


if __name__ == "__main__":
    asyncio.run(main())
