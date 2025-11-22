#!/usr/bin/env python3
"""
Test script for AMI Listener
Run independently to test AMI event reception
"""
import asyncio
import logging
from ami_listener import AMIEventListener

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def custom_event_handler(event: dict):
    """Custom event handler for testing"""
    print(f"\n=== Custom Event Handler ===")
    print(f"Event Type: {event.get('event')}")
    print(f"Full Event: {event}")
    print("=" * 50 + "\n")


async def main():
    print("Starting AMI Listener Test...")
    print("Press Ctrl+C to stop\n")

    listener = AMIEventListener(on_event_callback=custom_event_handler)

    try:
        await listener.listen()
    except KeyboardInterrupt:
        print("\nStopping listener...")
        await listener.stop()
        print("Listener stopped")


if __name__ == "__main__":
    asyncio.run(main())
