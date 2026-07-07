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
