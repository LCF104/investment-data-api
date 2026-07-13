from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Query

from app.auth import require_bearer_token
from app.config import Settings, get_settings
from app.models.schemas import ProviderStatusItem, ProviderStatusResponse
from app.providers.cninfo_provider import CNInfoProvider
from app.providers.fmp_provider import FMPProvider
from app.providers.sec_provider import SECProvider
from app.providers.tushare_provider import TushareProvider
from app.utils.errors import APIError


router = APIRouter(prefix="/v1/system", tags=["system"], dependencies=[Depends(require_bearer_token)])


async def _check_provider(name: str, configured: bool, source_type: str, required_env: list[str], call):
    checked_at = datetime.now(timezone.utc)
    if not configured:
        return ProviderStatusItem(
            name=name,
            configured=False,
            status="not_configured",
            source_type=source_type,
            required_env=required_env,
            last_check=checked_at,
            user_action=f"Configure {', '.join(required_env)} in deployment environment.",
        )
    try:
        details = await call()
        return ProviderStatusItem(
            name=name,
            configured=True,
            status="ok",
            source_type=source_type,
            required_env=required_env,
            last_check=checked_at,
            details=details or {},
        )
    except APIError as exc:
        return ProviderStatusItem(
            name=name,
            configured=True,
            status=exc.code,
            source_type=source_type,
            required_env=required_env,
            last_check=checked_at,
            details=exc.details,
            user_action=exc.user_action,
            warnings=[exc.message],
        )
    except httpx.RequestError as exc:
        return ProviderStatusItem(
            name=name,
            configured=True,
            status="DATA_SOURCE_UNAVAILABLE",
            source_type=source_type,
            required_env=required_env,
            last_check=checked_at,
            details={"type": exc.__class__.__name__},
            user_action="Check outbound network access and provider availability.",
            warnings=["Provider request could not connect."],
        )
    except Exception as exc:
        return ProviderStatusItem(
            name=name,
            configured=True,
            status="UNEXPECTED_ERROR",
            source_type=source_type,
            required_env=required_env,
            last_check=checked_at,
            details={"type": exc.__class__.__name__},
            user_action="Check server logs and provider availability.",
            warnings=["Unexpected provider status check failure."],
        )


@router.get("/provider-status", operation_id="getProviderStatus")
async def get_provider_status(
    live: bool = Query(False, description="Run lightweight live checks against providers when true."),
    settings: Settings = Depends(get_settings),
):
    checked_at = datetime.now(timezone.utc)
    sec = SECProvider(settings)
    fmp = FMPProvider(settings)
    tushare = TushareProvider(settings)
    cninfo = CNInfoProvider()
    if not live:
        return ProviderStatusResponse(
            service=settings.service_name,
            checked_at=checked_at,
            live_check=False,
            providers=[
                ProviderStatusItem(name="SEC EDGAR", configured=bool(settings.sec_user_agent), status="configured" if settings.sec_user_agent else "not_configured", source_type="official_filing", required_env=["SEC_USER_AGENT"]),
                ProviderStatusItem(name="Financial Modeling Prep", configured=bool(settings.fmp_api_key), status="configured" if settings.fmp_api_key else "not_configured", source_type="third_party_structured", required_env=["FMP_API_KEY"]),
                ProviderStatusItem(name="Tushare Pro", configured=bool(settings.tushare_token), status="configured" if settings.tushare_token else "not_configured", source_type="third_party_structured", required_env=["TUSHARE_TOKEN"]),
                ProviderStatusItem(name="CNInfo", configured=True, status="configured_public_interface", source_type="official_filing", required_env=[]),
            ],
        )

    providers = [
        await _check_provider("SEC EDGAR", bool(settings.sec_user_agent), "official_filing", ["SEC_USER_AGENT"], lambda: sec.get_company_profile("AAPL")),
        await _check_provider("Financial Modeling Prep", bool(settings.fmp_api_key), "third_party_structured", ["FMP_API_KEY"], lambda: fmp.get_snapshot("AAPL")),
        await _check_provider("Tushare Pro", bool(settings.tushare_token), "third_party_structured", ["TUSHARE_TOKEN"], lambda: tushare.get_industry("600519.SH")),
        await _check_provider("CNInfo", True, "official_filing", [], lambda: cninfo.get_filings("600519.SH", "annual_report", 1)),
    ]
    return ProviderStatusResponse(service=settings.service_name, checked_at=checked_at, live_check=True, providers=providers)
