from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.db.models import PaymentStatus


class PaymentCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(..., pattern="^(RUB|USD|EUR)$")
    description: str = Field(..., min_length=1, max_length=500)
    metadata: dict = Field(default_factory=dict)
    webhook_url: HttpUrl


class PaymentCreateResponse(BaseModel):
    payment_id: UUID
    status: PaymentStatus
    created_at: datetime


class PaymentDetailsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    amount: Decimal
    currency: str
    description: str
    metadata_json: dict = Field(validation_alias="metadata_json", serialization_alias="metadata")
    webhook_url: str
    status: PaymentStatus
    created_at: datetime
    processed_at: datetime | None
    last_error: str | None
