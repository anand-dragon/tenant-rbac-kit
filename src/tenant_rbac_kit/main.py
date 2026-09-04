from fastapi import FastAPI

from tenant_rbac_kit.api.router import api_router
from tenant_rbac_kit.logging_config import configure_logging
from tenant_rbac_kit.middleware import CorrelationIdMiddleware


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="tenant-rbac-kit")
    app.add_middleware(CorrelationIdMiddleware)
    app.include_router(api_router)
    return app


app = create_app()
