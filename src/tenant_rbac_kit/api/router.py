from fastapi import APIRouter

from tenant_rbac_kit.api.routes import health, invoices

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(invoices.router)
