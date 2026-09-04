import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tenant_rbac_kit.auth.schemas import TokenClaims
from tenant_rbac_kit.db.session import get_session
from tenant_rbac_kit.models.invoice import Invoice
from tenant_rbac_kit.rbac.dependencies import require_permission
from tenant_rbac_kit.schemas.invoice import InvoiceCreate, InvoiceRead

log = structlog.get_logger()

router = APIRouter(prefix="/invoices", tags=["invoices"])

_require_read = require_permission("invoices:read")
_require_create = require_permission("invoices:create")
_require_delete = require_permission("invoices:delete")


@router.get("", response_model=list[InvoiceRead])
async def list_invoices(
    claims: TokenClaims = Depends(_require_read),
    session: AsyncSession = Depends(get_session),
) -> list[Invoice]:
    result = await session.scalars(select(Invoice).where(Invoice.tenant_id == claims.tenant_id))
    return list(result)


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    claims: TokenClaims = Depends(_require_create),
    session: AsyncSession = Depends(get_session),
) -> Invoice:
    invoice = Invoice(tenant_id=claims.tenant_id, **body.model_dump())
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    log.info(
        "invoice_created",
        invoice_id=str(invoice.id),
        tenant_id=claims.tenant_id,
        user_id=claims.sub,
    )
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: uuid.UUID,
    claims: TokenClaims = Depends(_require_delete),
    session: AsyncSession = Depends(get_session),
) -> None:
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.tenant_id != claims.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await session.delete(invoice)
    await session.commit()
    log.info(
        "invoice_deleted",
        invoice_id=str(invoice_id),
        tenant_id=claims.tenant_id,
        user_id=claims.sub,
    )
