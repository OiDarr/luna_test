import asyncio

import httpx


async def send_webhook_with_retry(
    *,
    webhook_url: str,
    payload: dict,
    max_attempts: int = 3,
) -> None:
    delays = [1, 2, 4]

    last_error = None
    async with httpx.AsyncClient(timeout=10) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.post(webhook_url, json=payload)
                if 200 <= response.status_code < 300:
                    return
                last_error = RuntimeError(f"Webhook returned status {response.status_code}")
            except Exception as exc:  # noqa: BLE001
                last_error = exc

            if attempt < max_attempts:
                await asyncio.sleep(delays[attempt - 1])

    raise RuntimeError(f"Webhook failed after retries: {last_error}")
