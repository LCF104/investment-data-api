from datetime import datetime, timezone

from fastapi import FastAPI

from app.config import get_settings
from app.routers.equity import router as equity_router
from app.utils.errors import APIError, api_error_handler, unhandled_error_handler


settings = get_settings()

app = FastAPI(
    title="Investment Data API",
    description="Financial data middleware API for GPT Actions.",
    version=settings.version,
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(equity_router)


@app.get("/health", operation_id="getHealth", tags=["system"])
async def health():
    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
        "time": datetime.now(timezone.utc).isoformat(),
    }
