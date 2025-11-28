#!/usr/bin/env python3
"""Dispatch the nora-v2 agent to a room for testing.

Usage:
    python scripts/dispatch_agent.py [room_name]        # Create dispatch
    python scripts/dispatch_agent.py --delete [room]    # Delete all dispatches in room
    python scripts/dispatch_agent.py --list [room]      # List dispatches in room

If room_name is not provided, uses 'nora-test-room'.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()


async def delete_dispatches(room_name: str = "nora-test-room"):
    """Delete all dispatches in a room."""
    from livekit import api

    print(f"Deleting all dispatches in room '{room_name}'...")

    lkapi = api.LiveKitAPI()

    try:
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
        print(f"  Found {len(dispatches)} dispatch(es)")

        for dispatch in dispatches:
            dispatch_id = dispatch.id
            await lkapi.agent_dispatch.delete_dispatch(
                dispatch_id=dispatch_id,
                room_name=room_name
            )
            print(f"  ✓ Deleted: {dispatch_id}")

        print(f"\n✓ All dispatches in '{room_name}' deleted")

    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        await lkapi.aclose()


async def list_dispatches(room_name: str = "nora-test-room"):
    """List all dispatches in a room."""
    from livekit import api

    print(f"Listing dispatches in room '{room_name}'...")

    lkapi = api.LiveKitAPI()

    try:
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
        print(f"  Found {len(dispatches)} dispatch(es):\n")

        for dispatch in dispatches:
            print(f"  ID: {dispatch.id}")
            print(f"  Agent: {dispatch.agent_name}")
            print(f"  Room: {dispatch.room}")
            print()

    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        await lkapi.aclose()

async def create_dispatch(room_name: str = "nora-test-room", agent_name: str = "nora-v2"):
    """Create an explicit dispatch for the nora-v2 agent."""
    from livekit import api

    print(f"Creating dispatch for agent '{agent_name}' to room '{room_name}'...")

    lkapi = api.LiveKitAPI()

    try:
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
                metadata='{"test": true}'
            )
        )
        print(f"✓ Dispatch created: {dispatch}")

        # List dispatches to confirm
        dispatches = await lkapi.agent_dispatch.list_dispatch(room_name=room_name)
        print(f"  There are {len(dispatches)} dispatches in {room_name}")

        # Generate a token to join the room
        token = (
            api.AccessToken()
            .with_identity("test-user")
            .with_name("Test User")
            .with_grants(api.VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )

        livekit_url = os.getenv("LIVEKIT_URL", "").replace("wss://", "https://")
        playground_url = f"https://agents-playground.livekit.io/?tab=connection&url={livekit_url}&token={token}"

        # Extract dispatch ID
        dispatch_id = dispatch.id if hasattr(dispatch, 'id') else str(dispatch).split('"')[1]

        print(f"\n✓ Room: {room_name}")
        print(f"✓ Agent: {agent_name}")

        # Full values for copy-paste
        wss_url = os.getenv("LIVEKIT_URL", "")

        print(f"\n--- Copy-Paste Values ---")
        print(f"URL:")
        print(wss_url)
        print(f"\nAgentID:")
        print(dispatch_id)
        print(f"\nToken:")
        print(token)

        print(f"\n--- Playground URL ---")
        print(playground_url)

    except Exception as e:
        print(f"✗ Error: {e}")
        raise
    finally:
        await lkapi.aclose()


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        room_name = sys.argv[2] if len(sys.argv) > 2 else "nora-test-room"
        asyncio.run(delete_dispatches(room_name))
    elif len(sys.argv) > 1 and sys.argv[1] == "--list":
        room_name = sys.argv[2] if len(sys.argv) > 2 else "nora-test-room"
        asyncio.run(list_dispatches(room_name))
    else:
        room_name = sys.argv[1] if len(sys.argv) > 1 else "nora-test-room"
        asyncio.run(create_dispatch(room_name))


if __name__ == "__main__":
    main()
