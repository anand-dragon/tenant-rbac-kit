import uuid

from pydantic import BaseModel, ConfigDict


class InvoiceCreate(BaseModel):
    customer_name: str
    amount: float


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_name: str
    amount: float
