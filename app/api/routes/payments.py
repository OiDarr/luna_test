from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_api_key
from app.db.models import Payment
from app.db.session import get_db_session
from app.schemas.payments import PaymentCreateRequest, PaymentCreateResponse, PaymentDetailsResponse
from app.services.payments import create_payment

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_payment_endpoint(
    payload: PaymentCreateRequest,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    _: None = Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> PaymentCreateResponse:
    payment, is_new = await create_payment(db, idempotency_key=idempotency_key, payload=payload)
    if not is_new:
        response.status_code = status.HTTP_200_OK

    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get("/{payment_id}", response_model=PaymentDetailsResponse)
async def get_payment_endpoint(
    payment_id: UUID,
    _: None = Depends(require_api_key),
    db: AsyncSession = Depends(get_db_session),
) -> PaymentDetailsResponse:
    payment = await db.scalar(select(Payment).where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return PaymentDetailsResponse.model_validate(payment)
