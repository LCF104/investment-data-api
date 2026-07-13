from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import status

from app.config import Settings
from app.utils.errors import APIError, ErrorCode


SEC_FORM_MAP = {
    "annual_report": {"10-K", "20-F", "40-F"},
    "quarterly_report": {"10-Q"},
    "current_report": {"8-K", "6-K"},
    "all": None,
}


class SECProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        if not self.settings.sec_user_agent:
            raise APIError(
                ErrorCode.MISSING_PROVIDER_KEY,
                "SEC_USER_AGENT is missing.",
                status.HTTP_424_FAILED_DEPENDENCY,
                {"provider": "SEC EDGAR"},
                "Set SEC_USER_AGENT to 'APP_NAME CONTACT_EMAIL'.",
            )
        return {"User-Agent": self.settings.sec_user_agent, "Accept-Encoding": "gzip, deflate"}

    async def _get_json(self, url: str) -> Any:
        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds, headers=self._headers()) as client:
            response = await client.get(url)
        if response.status_code == 429:
            raise APIError(
                ErrorCode.PROVIDER_RATE_LIMITED,
                "SEC rate limit reached.",
                status.HTTP_429_TOO_MANY_REQUESTS,
                {"provider": "SEC EDGAR"},
                "Wait and retry with a compliant User-Agent.",
            )
        if response.status_code >= 400:
            raise APIError(
                ErrorCode.DATA_SOURCE_UNAVAILABLE,
                "SEC provider request failed.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider_status_code": response.status_code},
                "Verify SEC_USER_AGENT and SEC availability.",
            )
        return response.json()

    async def get_cik(self, symbol: str) -> str:
        companies = await self._get_json("https://www.sec.gov/files/company_tickers.json")
        symbol_upper = symbol.upper()
        for item in companies.values():
            if item.get("ticker", "").upper() == symbol_upper:
                return str(item["cik_str"]).zfill(10)
        raise APIError(ErrorCode.INVALID_SYMBOL, "SEC CIK not found for ticker.", details={"symbol": symbol})

    async def get_company_profile(self, symbol: str) -> dict[str, Any]:
        cik = await self.get_cik(symbol)
        data = await self._get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
        tickers = data.get("tickers") or []
        exchanges = data.get("exchanges") or []
        return {
            "symbol": symbol.upper(),
            "cik": cik,
            "name": data.get("name"),
            "tickers": tickers,
            "exchanges": exchanges,
            "sic": data.get("sic"),
            "sic_description": data.get("sicDescription"),
            "fiscal_year_end": data.get("fiscalYearEnd"),
            "source": "SEC EDGAR",
            "source_type": "official_filing",
            "provider_as_of": datetime.now(timezone.utc).date().isoformat(),
        }

    async def get_companyfacts(self, symbol: str) -> dict[str, Any]:
        cik = await self.get_cik(symbol)
        return await self._get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")

    @staticmethod
    def _facts_for_tag(companyfacts: dict[str, Any], tag_candidates: list[str], preferred_units: list[str]) -> list[dict[str, Any]]:
        facts = companyfacts.get("facts", {}).get("us-gaap", {})
        for tag in tag_candidates:
            concept = facts.get(tag)
            if not concept:
                continue
            units = concept.get("units", {})
            for unit in preferred_units:
                rows = units.get(unit)
                if rows:
                    output = []
                    for row in rows:
                        item = dict(row)
                        item["taxonomy"] = "us-gaap"
                        item["tag"] = tag
                        item["unit"] = unit
                        item["label"] = concept.get("label")
                        output.append(item)
                    return output
        return []

    @staticmethod
    def _period_key(row: dict[str, Any], period_type: str) -> tuple[str, str, str]:
        end = str(row.get("end") or "")
        fp = str(row.get("fp") or "")
        filed = str(row.get("filed") or "")
        if period_type == "annual":
            return end, "FY", filed
        return end, fp, filed

    async def get_financials(self, symbol: str, period_type: str, limit: int) -> dict[str, Any]:
        companyfacts = await self.get_companyfacts(symbol)
        form_filter = {"10-K", "20-F", "40-F"} if period_type == "annual" else {"10-Q", "10-K", "20-F", "40-F"}
        fields = {
            "revenue": (["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"], ["USD"]),
            "gross_profit": (["GrossProfit"], ["USD"]),
            "operating_income": (["OperatingIncomeLoss"], ["USD"]),
            "net_income": (["NetIncomeLoss", "ProfitLoss"], ["USD"]),
            "assets": (["Assets"], ["USD"]),
            "liabilities": (["Liabilities"], ["USD"]),
            "equity": (["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"], ["USD"]),
            "cash": (["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"], ["USD"]),
            "operating_cash_flow": (["NetCashProvidedByUsedInOperatingActivities"], ["USD"]),
            "capital_expenditure": (["PaymentsToAcquirePropertyPlantAndEquipment"], ["USD"]),
            "diluted_shares": (["WeightedAverageNumberOfDilutedSharesOutstanding"], ["shares"]),
            "basic_shares": (["WeightedAverageNumberOfSharesOutstandingBasic"], ["shares"]),
        }
        by_period: dict[tuple[int, str, str], dict[str, Any]] = {}
        sources: dict[tuple[int, str, str], list[dict[str, Any]]] = {}
        for field_name, (tags, units) in fields.items():
            for fact in self._facts_for_tag(companyfacts, tags, units):
                if fact.get("form") not in form_filter:
                    continue
                if period_type == "annual" and fact.get("fp") != "FY":
                    continue
                key = self._period_key(fact, period_type)
                by_period.setdefault(
                    key,
                    {
                        "fiscal_year": int(str(fact.get("end") or "0")[:4] or 0),
                        "sec_fy": fact.get("fy"),
                        "fiscal_period": fact.get("fp"),
                        "period_end_date": fact.get("end"),
                        "filing_date": fact.get("filed"),
                        "form": fact.get("form"),
                        "accession": fact.get("accn"),
                    },
                )
                by_period[key][field_name] = fact.get("val")
                sources.setdefault(key, []).append(
                    {
                        "field": field_name,
                        "taxonomy": fact.get("taxonomy"),
                        "tag": fact.get("tag"),
                        "unit": fact.get("unit"),
                        "form": fact.get("form"),
                        "filed": fact.get("filed"),
                        "accession": fact.get("accn"),
                    }
                )

        rows = list(by_period.values())
        rows.sort(key=lambda item: (item.get("period_end_date") or "", item.get("filing_date") or ""), reverse=True)
        rows = rows[:limit]
        for row in rows:
            key = (str(row.get("period_end_date") or ""), str(row.get("fiscal_period") or ""), str(row.get("filing_date") or ""))
            seen_sources = set()
            unique_sources = []
            for source in sources.get(key, []):
                source_key = (source.get("field"), source.get("tag"), source.get("unit"), source.get("form"), source.get("filed"), source.get("accession"))
                if source_key in seen_sources:
                    continue
                seen_sources.add(source_key)
                unique_sources.append(source)
            row["source_facts"] = unique_sources

        return {
            "income_statement": [
                {k: row.get(k) for k in ["fiscal_year", "sec_fy", "fiscal_period", "period_end_date", "filing_date", "form", "accession", "revenue", "gross_profit", "operating_income", "net_income", "diluted_shares", "basic_shares", "source_facts"]}
                for row in rows
            ],
            "balance_sheet": [
                {k: row.get(k) for k in ["fiscal_year", "sec_fy", "fiscal_period", "period_end_date", "filing_date", "form", "accession", "assets", "liabilities", "equity", "cash", "source_facts"]}
                for row in rows
            ],
            "cash_flow_statement": [
                {k: row.get(k) for k in ["fiscal_year", "sec_fy", "fiscal_period", "period_end_date", "filing_date", "form", "accession", "operating_cash_flow", "capital_expenditure", "source_facts"]}
                for row in rows
            ],
            "report_period": rows[0].get("period_end_date") if rows else None,
            "filing_date": rows[0].get("filing_date") if rows else None,
            "source": "SEC EDGAR XBRL companyfacts",
            "source_type": "official_filing",
            "provider_as_of": rows[0].get("filing_date") if rows else None,
            "warnings": [
                "SEC XBRL facts use standardized tags only; company-specific tags may require separate review.",
                "Use source_facts to tie each field back to taxonomy, tag, unit, form, filing date, and accession.",
            ],
        }

    async def get_filings(self, symbol: str, filing_type: str, limit: int) -> dict[str, Any]:
        cik = await self.get_cik(symbol)
        data = await self._get_json(f"https://data.sec.gov/submissions/CIK{cik}.json")
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        reports = recent.get("reportDate", [])
        accession_numbers = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        allowed_forms = SEC_FORM_MAP.get(filing_type)
        filings = []
        for form, filing_date, report_date, accession, doc in zip(forms, dates, reports, accession_numbers, primary_docs):
            if allowed_forms is not None and form not in allowed_forms:
                continue
            accession_clean = accession.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{doc}"
            filings.append(
                {
                    "filing_date": filing_date,
                    "report_period": report_date,
                    "form_type": form,
                    "title": f"{symbol.upper()} {form}",
                    "url": url,
                    "source": "SEC EDGAR",
                }
            )
            if len(filings) >= limit:
                break

        return {
            "filings": filings,
            "source": "SEC EDGAR",
            "source_type": "official_filing",
            "provider_as_of": filings[0]["filing_date"] if filings else None,
        }
