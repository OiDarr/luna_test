import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OutboxEvent, Payment, PaymentStatus
from app.schemas.payments import PaymentCreateRequest


def _fingerprint_payload(payload: PaymentCreateRequest) -> str:
    normalized = {
        "amount": str(payload.amount),
        "currency": payload.currency,
        "description": payload.description,
        "metadata": payload.metadata,
        "webhook_url": str(payload.webhook_url),
    }
    body = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


async def create_payment(
    db: AsyncSession,
    *,
    idempotency_key: str,
    payload: PaymentCreateRequest,
) -> tuple[Payment, bool]:
    fingerprint = _fingerprint_payload(payload)

    existing = await db.scalar(select(Payment).where(Payment.idempotency_key == idempotency_key))
    if existing:
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key already used with different payload",
            )
        return existing, False

    payment = Payment(
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        amount=payload.amount,
        currency=payload.currency,
        description=payload.description,
        metadata_json=payload.metadata,
        webhook_url=str(payload.webhook_url),
        status=PaymentStatus.pending,
    )
    db.add(payment)
    await db.flush()

    outbox = OutboxEvent(
        event_type="payment.created",
        aggregate_id=payment.id,
        payload={
            "payment_id": str(payment.id),
            "webhook_url": payment.webhook_url,
        },
    )
    db.add(outbox)
    await db.commit()
    await db.refresh(payment)
    return payment, True


async def mark_payment_processed(
    db: AsyncSession,
    *,
    payment: Payment,
    status_value: PaymentStatus,
    error_text: str | None,
) -> None:
    payment.status = status_value
    payment.last_error = error_text
    payment.processed_at = datetime.now(timezone.utc)
    await db.commit()
