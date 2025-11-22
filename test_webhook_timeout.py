#!/usr/bin/env python3
"""
Test webhook timeout and error handling
"""
import asyncio
import httpx
from app.config import settings

async def test_webhook_scenarios():
    """Test various webhook scenarios"""

    test_cases = [
        {
            "name": "Valid webhook (fast)",
            "url": "http://localhost:8000/webhook/incoming",
            "should_work": True
        },
        {
            "name": "Timeout (slow endpoint)",
            "url": "http://httpbin.org/delay/10",  # 10 second delay
            "should_work": False
        },
        {
            "name": "Connection refused",
            "url": "http://localhost:9999/webhook",
            "should_work": False
        },
        {
            "name": "Invalid domain",
            "url": "http://this-domain-does-not-exist-12345.com/webhook",
            "should_work": False
        }
    ]

    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {test['name']}")
        print(f"URL: {test['url']}")
        print(f"{'='*60}")

        start = asyncio.get_event_loop().time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    test['url'],
                    json={"test": "data"},
                    timeout=settings.webhook_timeout
                )
                elapsed = asyncio.get_event_loop().time() - start
                print(f"✓ SUCCESS: {response.status_code} (took {elapsed:.2f}s)")

        except httpx.TimeoutException:
            elapsed = asyncio.get_event_loop().time() - start
            print(f"✗ TIMEOUT after {elapsed:.2f}s (max: {settings.webhook_timeout}s)")

        except httpx.ConnectError as e:
            elapsed = asyncio.get_event_loop().time() - start
            print(f"✗ CONNECTION ERROR: {e} (took {elapsed:.2f}s)")

        except Exception as e:
            elapsed = asyncio.get_event_loop().time() - start
            print(f"✗ ERROR: {type(e).__name__}: {e} (took {elapsed:.2f}s)")

    print(f"\n{'='*60}")
    print("All tests completed")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("Testing webhook timeout and error handling")
    print(f"Configured timeout: {settings.webhook_timeout}s")
    print(f"Configured retries: {settings.webhook_retry}")

    asyncio.run(test_webhook_scenarios())
