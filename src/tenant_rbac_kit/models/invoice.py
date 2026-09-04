import uuid

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from tenant_rbac_kit.db.base import Base


class Invoice(Base):
    """Demo tenant-scoped resource, shows the pattern the kit expects:
    every row carries a tenant_id so queries can be scoped alongside the
    Casbin domain check performed by require_permission.
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
