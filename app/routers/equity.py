from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.auth import require_bearer_token
from app.config import Settings, get_settings
from app.services.equity_service import EquityService


router = APIRouter(prefix="/v1/equity", tags=["equity"], dependencies=[Depends(require_bearer_token)])


def get_service(settings: Settings = Depends(get_settings)) -> EquityService:
    return EquityService(settings)


@router.get("/snapshot", operation_id="getEquitySnapshot")
async def get_equity_snapshot(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    service: EquityService = Depends(get_service),
):
    return await service.snapshot(market, symbol)


@router.get("/financials", operation_id="getEquityFinancials")
async def get_equity_financials(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    period_type: Literal["annual", "quarterly", "ttm"] = Query("annual"),
    limit: int = Query(8, ge=1, le=40),
    service: EquityService = Depends(get_service),
):
    return await service.financials(market, symbol, period_type, limit)


@router.get("/ratios", operation_id="getEquityRatios")
async def get_equity_ratios(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    period: Literal["latest", "ttm", "annual"] = Query("latest"),
    service: EquityService = Depends(get_service),
):
    return await service.ratios(market, symbol, period)


@router.get("/valuation", operation_id="getEquityValuation")
async def get_equity_valuation(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    service: EquityService = Depends(get_service),
):
    return await service.valuation(market, symbol)


@router.get("/filings", operation_id="getEquityFilings")
async def get_equity_filings(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    filing_type: Literal["annual_report", "quarterly_report", "semi_annual_report", "current_report", "all"] = Query("all"),
    limit: int = Query(10, ge=1, le=50),
    service: EquityService = Depends(get_service),
):
    return await service.filings(market, symbol, filing_type, limit)


@router.get("/industry", operation_id="getEquityIndustry")
async def get_equity_industry(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    service: EquityService = Depends(get_service),
):
    return await service.industry(market, symbol)


@router.get("/research-pack", operation_id="getEquityResearchPack")
async def get_equity_research_pack(
    market: Literal["US", "CN"] = Query(...),
    symbol: str = Query(..., min_length=1),
    service: EquityService = Depends(get_service),
):
    return await service.research_pack(market, symbol)
