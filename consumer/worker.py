import random
from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.db.models import Payment, PaymentStatus
from app.db.session import SessionLocal
from app.messaging import broker
from app.services.payments import mark_payment_processed
from app.services.webhook import send_webhook_with_retry


async def _emulate_gateway() -> PaymentStatus:
    import asyncio

    await asyncio.sleep(random.uniform(2, 5))
    return PaymentStatus.succeeded if random.random() <= 0.9 else PaymentStatus.failed


@broker.subscriber(settings.payments_queue)
async def process_payment(message: dict) -> None:
    payment_id = UUID(message["payment_id"])
    async with SessionLocal() as db:
        payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
        if payment is None:
            return

        if payment.status != PaymentStatus.pending:
            return

        final_status = await _emulate_gateway()
        error_text = None if final_status == PaymentStatus.succeeded else "Gateway rejected payment"
        await mark_payment_processed(db, payment=payment, status_value=final_status, error_text=error_text)

        webhook_payload = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "processed_at": payment.processed_at.isoformat() if payment.processed_at else None,
            "error": payment.last_error,
        }
        try:
            await send_webhook_with_retry(webhook_url=payment.webhook_url, payload=webhook_payload)
        except Exception as exc:  # noqa: BLE001
            await broker.publish(
                {
                    "payment_id": str(payment.id),
                    "error": str(exc),
                },
                queue=settings.payments_dlq,
            )
