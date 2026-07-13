from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import status

from app.config import Settings
from app.utils.errors import APIError, ErrorCode


class TushareProvider:
    base_url = "https://api.tushare.pro"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _require_token(self) -> str:
        if not self.settings.tushare_token:
            raise APIError(
                ErrorCode.MISSING_PROVIDER_KEY,
                "Tushare token is missing.",
                status.HTTP_424_FAILED_DEPENDENCY,
                {"provider": "Tushare Pro"},
                "Configure TUSHARE_TOKEN in environment variables.",
            )
        return self.settings.tushare_token

    async def _call(self, api_name: str, params: dict[str, Any], fields: str = "") -> list[dict[str, Any]]:
        payload = {
            "api_name": api_name,
            "token": self._require_token(),
            "params": params,
            "fields": fields,
        }
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(self.base_url, json=payload)
        if response.status_code == 429:
            raise APIError(ErrorCode.PROVIDER_RATE_LIMITED, "Tushare rate limit reached.", status.HTTP_429_TOO_MANY_REQUESTS)
        if response.status_code >= 400:
            raise APIError(ErrorCode.DATA_SOURCE_UNAVAILABLE, "Tushare provider request failed.", status.HTTP_502_BAD_GATEWAY)
        data = response.json()
        if data.get("code") != 0:
            raise APIError(
                ErrorCode.DATA_SOURCE_UNAVAILABLE,
                data.get("msg") or "Tushare returned an error.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider_code": data.get("code")},
                "Verify TUSHARE_TOKEN and endpoint permissions.",
            )
        fields_list = data.get("data", {}).get("fields", [])
        items = data.get("data", {}).get("items", [])
        return [dict(zip(fields_list, item)) for item in items]

    async def get_snapshot(self, symbol: str) -> dict[str, Any]:
        rows = await self._call(
            "daily_basic",
            {"ts_code": symbol.upper()},
            "ts_code,trade_date,close,total_mv,pe_ttm,pb,ps_ttm,dv_ttm",
        )
        if not rows:
            raise APIError(ErrorCode.INVALID_SYMBOL, "Tushare returned no daily_basic data.", details={"symbol": symbol})
        row = rows[0]
        basic = await self._call("stock_basic", {"ts_code": symbol.upper()}, "ts_code,name")
        name = basic[0].get("name") if basic else None
        return {
            "market": "CN",
            "symbol": row.get("ts_code", symbol.upper()),
            "name": name,
            "currency": "CNY",
            "price": row.get("close"),
            "market_cap": (row.get("total_mv") or 0) * 10000 if row.get("total_mv") is not None else None,
            "pe_ttm": row.get("pe_ttm"),
            "pb": row.get("pb"),
            "ps_ttm": row.get("ps_ttm"),
            "dividend_yield": row.get("dv_ttm"),
            "trade_date": row.get("trade_date"),
            "as_of": row.get("trade_date"),
            "source": "Tushare Pro",
            "provider_as_of": row.get("trade_date"),
            "source_type": "third_party_structured",
        }

    async def get_financials(self, symbol: str, period_type: str, limit: int) -> dict[str, Any]:
        params = {"ts_code": symbol.upper(), "limit": limit}
        income = await self._call("income", params)
        balance = await self._call("balancesheet", params)
        cashflow = await self._call("cashflow", params)
        latest = income[0] if income else {}
        return {
            "income_statement": income,
            "balance_sheet": balance,
            "cash_flow_statement": cashflow,
            "report_period": latest.get("end_date"),
            "filing_date": latest.get("ann_date") or latest.get("f_ann_date"),
            "source": "Tushare Pro",
            "source_type": "third_party_structured",
            "provider_as_of": latest.get("ann_date") or latest.get("end_date"),
            "warnings": ["Tushare financial statements are third-party structured data, not official source filings."],
        }

    async def get_ratios(self, symbol: str, period: str) -> dict[str, Any]:
        rows = await self._call("fina_indicator", {"ts_code": symbol.upper(), "limit": 1})
        row = rows[0] if rows else {}
        return {
            "ratios": row,
            "source": "Tushare Pro",
            "source_type": "third_party_structured",
            "provider_as_of": row.get("ann_date") or row.get("end_date"),
            "warnings": ["Tushare ratio definitions may differ from locally calculated formulas."],
        }

    async def get_valuation(self, symbol: str) -> dict[str, Any]:
        snap = await self.get_snapshot(symbol)
        return {
            "price": snap.get("price"),
            "market_cap": snap.get("market_cap"),
            "enterprise_value": None,
            "pe_ttm": snap.get("pe_ttm"),
            "pe_forward": None,
            "pb": snap.get("pb"),
            "ps_ttm": snap.get("ps_ttm"),
            "ev_ebitda": None,
            "fcf_yield": None,
            "earnings_yield": 1 / snap["pe_ttm"] if snap.get("pe_ttm") else None,
            "dividend_yield": snap.get("dividend_yield"),
            "valuation_date": snap.get("trade_date"),
            "source": "Tushare Pro",
            "source_type": "third_party_structured",
            "provider_as_of": snap.get("trade_date") or datetime.now(timezone.utc).date().isoformat(),
        }

    async def get_industry(self, symbol: str) -> dict[str, Any]:
        rows = await self._call("stock_basic", {"ts_code": symbol.upper()}, "ts_code,name,industry,market")
        row = rows[0] if rows else {}
        return {
            "industry_system": "Tushare stock_basic industry",
            "industry": row.get("industry"),
            "sub_industry": row.get("market"),
            "comparable_companies": [],
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "source": "Tushare Pro",
            "source_type": "third_party_structured",
            "warnings": ["A-share industry valuation medians require Wind, Choice, iFinD, Tushare Pro extensions, or a maintained comparable universe."],
        }

