from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import status

from app.config import Settings
from app.utils.errors import APIError, ErrorCode


class FMPProvider:
    base_url = "https://financialmodelingprep.com/api/v3"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _require_key(self) -> str:
        if not self.settings.fmp_api_key:
            raise APIError(
                ErrorCode.MISSING_PROVIDER_KEY,
                "FMP API key is missing.",
                status.HTTP_424_FAILED_DEPENDENCY,
                {"provider": "Financial Modeling Prep"},
                "Configure FMP_API_KEY in environment variables.",
            )
        return self.settings.fmp_api_key

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        api_key = self._require_key()
        query = dict(params or {})
        query["apikey"] = api_key
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.get(f"{self.base_url}/{path.lstrip('/')}", params=query)
        if response.status_code == 429:
            raise APIError(
                ErrorCode.PROVIDER_RATE_LIMITED,
                "FMP rate limit reached.",
                status.HTTP_429_TOO_MANY_REQUESTS,
                {"provider": "FMP"},
                "Wait and retry, or upgrade/check the FMP plan.",
            )
        if response.status_code >= 400:
            raise APIError(
                ErrorCode.DATA_SOURCE_UNAVAILABLE,
                "FMP provider request failed.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider_status_code": response.status_code},
                "Verify FMP_API_KEY and provider availability.",
            )
        try:
            return response.json()
        except ValueError as exc:
            raise APIError(
                ErrorCode.PROVIDER_RESPONSE_INVALID,
                "FMP returned invalid JSON.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider": "FMP"},
                "Retry later or check provider status.",
            ) from exc

    async def get_snapshot(self, symbol: str) -> dict[str, Any]:
        data = await self._get(f"quote/{symbol.upper()}")
        if not isinstance(data, list) or not data:
            raise APIError(ErrorCode.INVALID_SYMBOL, "FMP returned no quote for symbol.", details={"symbol": symbol})
        row = data[0]
        return {
            "market": "US",
            "symbol": row.get("symbol", symbol.upper()),
            "name": row.get("name"),
            "currency": row.get("currency") or "USD",
            "price": row.get("price"),
            "market_cap": row.get("marketCap"),
            "pe_ttm": row.get("pe"),
            "pb": row.get("priceToBookRatio"),
            "ps_ttm": row.get("priceToSalesRatio"),
            "dividend_yield": row.get("dividendYield"),
            "trade_date": row.get("timestamp") or row.get("earningsAnnouncement"),
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "source": "FMP",
            "provider_as_of": datetime.now(timezone.utc).date().isoformat(),
            "source_type": "third_party_structured",
        }

    async def get_financials(self, symbol: str, period_type: str, limit: int) -> dict[str, Any]:
        period = "quarter" if period_type in ("quarterly", "ttm") else "annual"
        params = {"period": period, "limit": limit}
        income = await self._get(f"income-statement/{symbol.upper()}", params)
        balance = await self._get(f"balance-sheet-statement/{symbol.upper()}", params)
        cashflow = await self._get(f"cash-flow-statement/{symbol.upper()}", params)
        latest = income[0] if isinstance(income, list) and income else {}
        return {
            "income_statement": income if isinstance(income, list) else [],
            "balance_sheet": balance if isinstance(balance, list) else [],
            "cash_flow_statement": cashflow if isinstance(cashflow, list) else [],
            "report_period": latest.get("period"),
            "filing_date": latest.get("fillingDate") or latest.get("date"),
            "source": "FMP",
            "source_type": "third_party_structured",
            "provider_as_of": latest.get("date"),
            "warnings": ["FMP financial statements are third-party structured data, not official source filings."],
        }

    async def get_ratios(self, symbol: str, period: str) -> dict[str, Any]:
        endpoint = "ratios-ttm" if period == "ttm" else "ratios"
        params = {"limit": 1}
        data = await self._get(f"{endpoint}/{symbol.upper()}", params)
        row = data[0] if isinstance(data, list) and data else {}
        return {
            "ratios": row,
            "source": "FMP",
            "source_type": "third_party_structured",
            "provider_as_of": row.get("date"),
            "warnings": ["Provider ratio definitions may differ from locally calculated formulas."],
        }

    async def get_valuation(self, symbol: str) -> dict[str, Any]:
        quote = await self._get(f"quote/{symbol.upper()}")
        metrics = await self._get(f"key-metrics-ttm/{symbol.upper()}")
        q = quote[0] if isinstance(quote, list) and quote else {}
        m = metrics[0] if isinstance(metrics, list) and metrics else {}
        return {
            "price": q.get("price"),
            "market_cap": q.get("marketCap"),
            "enterprise_value": m.get("enterpriseValueTTM") or q.get("enterpriseValue"),
            "pe_ttm": q.get("pe") or m.get("peRatioTTM"),
            "pe_forward": q.get("epsEstimatedNextQuarter"),
            "pb": m.get("pbRatioTTM") or q.get("priceToBookRatio"),
            "ps_ttm": m.get("priceToSalesRatioTTM") or q.get("priceToSalesRatio"),
            "ev_ebitda": m.get("enterpriseValueOverEBITDATTM"),
            "fcf_yield": m.get("freeCashFlowYieldTTM"),
            "earnings_yield": m.get("earningsYieldTTM"),
            "dividend_yield": q.get("dividendYield"),
            "valuation_date": datetime.now(timezone.utc).date().isoformat(),
            "source": "FMP",
            "source_type": "third_party_structured",
            "provider_as_of": datetime.now(timezone.utc).date().isoformat(),
        }

    async def get_industry(self, symbol: str) -> dict[str, Any]:
        profile = await self._get(f"profile/{symbol.upper()}")
        row = profile[0] if isinstance(profile, list) and profile else {}
        return {
            "industry_system": "FMP company profile",
            "industry": row.get("industry"),
            "sub_industry": row.get("sector"),
            "comparable_companies": [],
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "source": "FMP",
            "source_type": "third_party_structured",
            "warnings": ["Industry valuation medians require a paid market data source or a separately maintained comparable universe."],
        }
