import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db.models import OutboxEvent
from app.db.session import SessionLocal
from app.messaging import broker


async def publish_outbox_once(batch_size: int = 100) -> None:
    async with SessionLocal() as db:
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.id.asc())
            .limit(batch_size)
        )
        events = (await db.execute(query)).scalars().all()
        for event in events:
            try:
                await broker.publish(
                    event.payload,
                    queue=settings.payments_queue,
                )
                event.published_at = datetime.now(timezone.utc)
            except Exception as exc:  # noqa: BLE001
                event.attempts += 1
                event.last_error = str(exc)
        await db.commit()


async def run_outbox_relay(poll_interval_seconds: float = 1.0) -> None:
    await broker.start()
    try:
        while True:
            await publish_outbox_once()
            await asyncio.sleep(poll_interval_seconds)
    finally:
        await broker.close()
