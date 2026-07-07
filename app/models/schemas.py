from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Market = Literal["US", "CN"]
PeriodType = Literal["annual", "quarterly", "ttm"]


class Metadata(BaseModel):
    source: str
    source_type: str
    retrieved_at: datetime
    provider_as_of: str | None = None
    currency: str | None = None
    unit: str | None = None
    is_latest_available: bool = False
    staleness_check: str = "unknown"
    warnings: list[str] = Field(default_factory=list)


class EquitySnapshot(BaseModel):
    market: Market
    symbol: str
    name: str | None = None
    currency: str | None = None
    price: float | None = None
    market_cap: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps_ttm: float | None = None
    dividend_yield: float | None = None
    trade_date: str | None = None
    as_of: str | None = None
    source: str
    metadata: Metadata


class FinancialStatements(BaseModel):
    market: Market
    symbol: str
    period_type: PeriodType
    income_statement: list[dict[str, Any]] = Field(default_factory=list)
    balance_sheet: list[dict[str, Any]] = Field(default_factory=list)
    cash_flow_statement: list[dict[str, Any]] = Field(default_factory=list)
    report_period: str | None = None
    filing_date: str | None = None
    source: str
    metadata: Metadata


class EquityRatios(BaseModel):
    market: Market
    symbol: str
    period: str
    roe: float | None = None
    roic: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    asset_liability_ratio: float | None = None
    operating_cash_flow: float | None = None
    free_cash_flow: float | None = None
    fcf_margin: float | None = None
    calculation_method: dict[str, str] = Field(default_factory=dict)
    source: str
    metadata: Metadata


class EquityValuation(BaseModel):
    market: Market
    symbol: str
    price: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    pe_ttm: float | None = None
    pe_forward: float | None = None
    pb: float | None = None
    ps_ttm: float | None = None
    ev_ebitda: float | None = None
    fcf_yield: float | None = None
    earnings_yield: float | None = None
    dividend_yield: float | None = None
    valuation_date: str | None = None
    source: str
    metadata: Metadata


class FilingItem(BaseModel):
    filing_date: str | None = None
    report_period: str | None = None
    form_type: str | None = None
    title: str | None = None
    url: str | None = None
    source: str


class EquityFilings(BaseModel):
    market: Market
    symbol: str
    filing_type: str
    filings: list[FilingItem] = Field(default_factory=list)
    status: str = "ok"
    source: str
    metadata: Metadata


class IndustryData(BaseModel):
    market: Market
    symbol: str
    industry_system: str | None = None
    industry: str | None = None
    sub_industry: str | None = None
    industry_pe_median: float | None = None
    industry_pb_median: float | None = None
    industry_roe_median: float | None = None
    comparable_companies: list[dict[str, Any]] = Field(default_factory=list)
    as_of: str | None = None
    source: str
    metadata: Metadata


class DataQualityReport(BaseModel):
    can_analyze: bool
    successful_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)
    stale_sections: list[str] = Field(default_factory=list)
    non_official_sources: list[str] = Field(default_factory=list)
    source_conflicts: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_user_action: list[str] = Field(default_factory=list)


class ResearchPack(BaseModel):
    market: Market
    symbol: str
    snapshot: dict[str, Any] | None = None
    valuation: dict[str, Any] | None = None
    financials: dict[str, Any] | None = None
    ratios: dict[str, Any] | None = None
    filings: dict[str, Any] | None = None
    industry: dict[str, Any] | None = None
    data_quality_report: DataQualityReport
