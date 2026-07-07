from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.config import Settings
from app.models.schemas import (
    DataQualityReport,
    EquityFilings,
    EquityRatios,
    EquitySnapshot,
    EquityValuation,
    FinancialStatements,
    IndustryData,
    Metadata,
    ResearchPack,
)
from app.providers.cninfo_provider import CNInfoProvider
from app.providers.fmp_provider import FMPProvider
from app.providers.sec_provider import SECProvider
from app.providers.tushare_provider import TushareProvider
from app.utils.calculations import calculate_financial_ratios
from app.utils.errors import APIError
from app.utils.freshness import check_filings_freshness, check_market_data_freshness, check_statement_freshness


def _metadata(
    source: str,
    source_type: str,
    provider_as_of: str | None,
    currency: str | None = None,
    unit: str | None = None,
    freshness: dict[str, object] | None = None,
    warnings: list[str] | None = None,
) -> Metadata:
    freshness = freshness or {
        "is_latest_available": False,
        "staleness_check": "unknown",
        "warnings": ["Unable to verify data freshness."],
    }
    combined_warnings = list(freshness.get("warnings", [])) + list(warnings or [])
    return Metadata(
        source=source,
        source_type=source_type,
        retrieved_at=datetime.now(timezone.utc),
        provider_as_of=provider_as_of,
        currency=currency,
        unit=unit,
        is_latest_available=bool(freshness.get("is_latest_available")),
        staleness_check=str(freshness.get("staleness_check")),
        warnings=combined_warnings,
    )


class EquityService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.fmp = FMPProvider(settings)
        self.sec = SECProvider(settings)
        self.tushare = TushareProvider(settings)
        self.cninfo = CNInfoProvider()

    def _market_provider(self, market: str):
        return self.fmp if market == "US" else self.tushare

    async def snapshot(self, market: str, symbol: str) -> EquitySnapshot:
        provider = self._market_provider(market)
        data = await provider.get_snapshot(symbol)
        freshness = check_market_data_freshness(market, data.get("provider_as_of") or data.get("trade_date") or data.get("as_of"))
        metadata = _metadata(
            data["source"],
            data.get("source_type", "third_party_structured"),
            data.get("provider_as_of"),
            data.get("currency"),
            "reported by provider",
            freshness,
        )
        return EquitySnapshot(**{k: v for k, v in data.items() if k not in {"provider_as_of", "source_type"}}, metadata=metadata)

    async def financials(self, market: str, symbol: str, period_type: str, limit: int) -> FinancialStatements:
        provider = self._market_provider(market)
        data = await provider.get_financials(symbol, period_type, limit)
        freshness = check_statement_freshness(data.get("filing_date"), period_type)
        metadata = _metadata(
            data["source"],
            data.get("source_type", "third_party_structured"),
            data.get("provider_as_of"),
            unit="reported by provider",
            freshness=freshness,
            warnings=data.get("warnings", []),
        )
        return FinancialStatements(
            market=market,
            symbol=symbol.upper(),
            period_type=period_type,
            income_statement=data.get("income_statement", []),
            balance_sheet=data.get("balance_sheet", []),
            cash_flow_statement=data.get("cash_flow_statement", []),
            report_period=data.get("report_period"),
            filing_date=data.get("filing_date"),
            source=data["source"],
            metadata=metadata,
        )

    async def ratios(self, market: str, symbol: str, period: str) -> EquityRatios:
        provider = self._market_provider(market)
        provider_ratios = await provider.get_ratios(symbol, period)
        calculated: dict[str, Any] = {}
        warnings = list(provider_ratios.get("warnings", []))
        try:
            financials = await provider.get_financials(symbol, "ttm" if period == "ttm" else "annual", 4)
            if financials.get("income_statement") and financials.get("balance_sheet") and financials.get("cash_flow_statement"):
                calculated = calculate_financial_ratios(
                    financials["income_statement"][0],
                    financials["balance_sheet"][0],
                    financials["cash_flow_statement"][0],
                )
        except APIError as exc:
            warnings.append(f"Unable to calculate ratios from statements: {exc.code}.")

        raw = provider_ratios.get("ratios", {})
        values = {
            "roe": calculated.get("roe") or raw.get("returnOnEquity") or raw.get("roe"),
            "roic": calculated.get("roic") or raw.get("returnOnInvestedCapital") or raw.get("roic"),
            "roa": calculated.get("roa") or raw.get("returnOnAssets") or raw.get("roa"),
            "gross_margin": calculated.get("gross_margin") or raw.get("grossProfitMargin") or raw.get("grossprofit_margin"),
            "operating_margin": calculated.get("operating_margin") or raw.get("operatingProfitMargin") or raw.get("op_of_gr"),
            "net_margin": calculated.get("net_margin") or raw.get("netProfitMargin") or raw.get("netprofit_margin"),
            "debt_to_equity": calculated.get("debt_to_equity") or raw.get("debtEquityRatio"),
            "current_ratio": calculated.get("current_ratio") or raw.get("currentRatio"),
            "asset_liability_ratio": calculated.get("asset_liability_ratio") or raw.get("debt_to_assets"),
            "operating_cash_flow": calculated.get("operating_cash_flow") or raw.get("ocfps"),
            "free_cash_flow": calculated.get("free_cash_flow") or raw.get("freeCashFlowPerShare"),
            "fcf_margin": calculated.get("fcf_margin"),
            "calculation_method": calculated.get("calculation_method")
            or {"provider": "Provider-defined ratio fields; check provider documentation before relying on exact formulas."},
        }
        freshness = check_statement_freshness(provider_ratios.get("provider_as_of"), "quarterly" if period in {"latest", "ttm"} else "annual")
        metadata = _metadata(
            provider_ratios["source"],
            provider_ratios.get("source_type", "third_party_structured"),
            provider_ratios.get("provider_as_of"),
            unit="ratio/decimal unless provider says otherwise",
            freshness=freshness,
            warnings=warnings,
        )
        return EquityRatios(market=market, symbol=symbol.upper(), period=period, source=provider_ratios["source"], metadata=metadata, **values)

    async def valuation(self, market: str, symbol: str) -> EquityValuation:
        provider = self._market_provider(market)
        data = await provider.get_valuation(symbol)
        freshness = check_market_data_freshness(market, data.get("provider_as_of") or data.get("valuation_date"))
        metadata = _metadata(
            data["source"],
            data.get("source_type", "third_party_structured"),
            data.get("provider_as_of"),
            unit="reported by provider",
            freshness=freshness,
        )
        return EquityValuation(
            market=market,
            symbol=symbol.upper(),
            metadata=metadata,
            **{k: v for k, v in data.items() if k not in {"provider_as_of", "source_type"}},
        )

    async def filings(self, market: str, symbol: str, filing_type: str, limit: int) -> EquityFilings:
        if market == "US":
            data = await self.sec.get_filings(symbol, filing_type, limit)
            freshness = check_filings_freshness(data.get("provider_as_of"))
        else:
            data = await self.cninfo.get_filings(symbol, filing_type, limit)
            freshness = {
                "is_latest_available": False,
                "staleness_check": "not_implemented",
                "warnings": data.get("warnings", []),
            }
        metadata = _metadata(
            data["source"],
            data.get("source_type", "official_filing"),
            data.get("provider_as_of"),
            freshness=freshness,
            warnings=[] if market == "US" else data.get("warnings", []),
        )
        return EquityFilings(
            market=market,
            symbol=symbol.upper(),
            filing_type=filing_type,
            filings=data.get("filings", []),
            status=data.get("status", "ok"),
            source=data["source"],
            metadata=metadata,
        )

    async def industry(self, market: str, symbol: str) -> IndustryData:
        provider = self._market_provider(market)
        data = await provider.get_industry(symbol)
        freshness = check_market_data_freshness(market, data.get("as_of"))
        metadata = _metadata(
            data["source"],
            data.get("source_type", "third_party_structured"),
            data.get("as_of"),
            unit="reported by provider",
            freshness=freshness,
            warnings=data.get("warnings", []),
        )
        return IndustryData(
            market=market,
            symbol=symbol.upper(),
            metadata=metadata,
            **{k: v for k, v in data.items() if k not in {"provider_as_of", "source_type", "warnings"}},
        )

    async def _capture(self, name: str, call: Callable[[], Awaitable[Any]]) -> tuple[str, Any | None, dict[str, Any] | None]:
        try:
            result = await call()
            return name, result.model_dump(mode="json"), None
        except APIError as exc:
            return name, None, {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "user_action": exc.user_action,
            }

    async def research_pack(self, market: str, symbol: str) -> ResearchPack:
        sections = [
            await self._capture("snapshot", lambda: self.snapshot(market, symbol)),
            await self._capture("valuation", lambda: self.valuation(market, symbol)),
            await self._capture("financials", lambda: self.financials(market, symbol, "annual", 8)),
            await self._capture("ratios", lambda: self.ratios(market, symbol, "latest")),
            await self._capture("filings", lambda: self.filings(market, symbol, "all", 10)),
            await self._capture("industry", lambda: self.industry(market, symbol)),
        ]
        payload = {name: value for name, value, _ in sections}
        errors = {name: error for name, _, error in sections if error}
        successful = [name for name, value, _ in sections if value]
        missing = [name for name, value, error in sections if value is None or error]
        stale = [
            name
            for name, value, _ in sections
            if value and value.get("metadata") and value["metadata"].get("is_latest_available") is False
        ]
        warnings: list[str] = []
        non_official: list[str] = []
        for name, value, _ in sections:
            if not value:
                continue
            metadata = value.get("metadata", {})
            warnings.extend([f"{name}: {item}" for item in metadata.get("warnings", [])])
            if metadata.get("source_type") != "official_filing" and name in {"financials", "ratios", "snapshot", "valuation"}:
                non_official.append(name)

        blocking = []
        required_user_action = []
        if "snapshot" in errors:
            blocking.append("Snapshot data is unavailable.")
        if "financials" in errors:
            blocking.append("Financial statements are unavailable.")
        if "ratios" in errors:
            blocking.append("Financial ratios are unavailable.")
        for section, error in errors.items():
            if error.get("user_action"):
                required_user_action.append(f"{section}: {error['user_action']}")

        can_analyze = not blocking and "snapshot" not in stale and "financials" not in stale
        report = DataQualityReport(
            can_analyze=can_analyze,
            successful_sections=successful,
            missing_sections=missing,
            stale_sections=stale,
            non_official_sources=non_official,
            source_conflicts=[],
            blocking_issues=blocking,
            warnings=warnings + [f"{name}: {err['message']}" for name, err in errors.items()],
            required_user_action=required_user_action,
        )
        return ResearchPack(market=market, symbol=symbol.upper(), data_quality_report=report, **payload)
