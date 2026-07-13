from datetime import datetime, timezone
import re
from typing import Any

import httpx
from fastapi import status

from app.utils.errors import APIError, ErrorCode


CNINFO_CATEGORY_MAP = {
    "annual_report": "category_ndbg_szsh",
    "semi_annual_report": "category_bndbg_szsh",
    "quarterly_report": "category_yjdbg_szsh;category_sjdbg_szsh",
    "current_report": "",
    "all": "",
}


class CNInfoProvider:
    base_url = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
    pdf_base_url = "https://static.cninfo.com.cn/"

    @staticmethod
    def _column(symbol: str) -> str:
        symbol_upper = symbol.upper()
        if symbol_upper.endswith(".SH") or symbol_upper.startswith(("6", "9")):
            return "sse"
        if symbol_upper.endswith(".BJ"):
            return "bj"
        return "szse"

    @staticmethod
    def _code(symbol: str) -> str:
        return symbol.split(".")[0]

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        return re.sub(r"<[^>]+>", "", str(value))

    @staticmethod
    def _date_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, int | float):
            return datetime.fromtimestamp(value / 1000, timezone.utc).date().isoformat()
        return str(value)

    @staticmethod
    def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
        adjunct_url = item.get("adjunctUrl") or ""
        url = adjunct_url if adjunct_url.startswith("http") else f"{CNInfoProvider.pdf_base_url}{adjunct_url.lstrip('/')}" if adjunct_url else None
        return {
            "filing_date": CNInfoProvider._date_text(item.get("announcementTime") or item.get("announcementDate")),
            "report_period": None,
            "form_type": CNInfoProvider._clean_text(item.get("announcementTypeName") or item.get("category") or item.get("announcementType")),
            "title": CNInfoProvider._clean_text(item.get("announcementTitle")),
            "url": url,
            "source": "CNInfo",
        }

    async def get_filings(self, symbol: str, filing_type: str, limit: int) -> dict[str, Any]:
        code = self._code(symbol)
        category = CNINFO_CATEGORY_MAP.get(filing_type, "")
        payload = {
            "pageNum": 1,
            "pageSize": min(max(limit, 1), 30),
            "column": self._column(symbol),
            "tabName": "fulltext",
            "plate": "",
            "stock": "",
            "searchkey": code,
            "secid": "",
            "category": category,
            "trade": "",
            "seDate": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 investment-data-api contact@example.com",
            "Referer": "https://www.cninfo.com.cn/new/commonUrl/pageOfSearch?url=disclosure/list/search",
            "Accept": "application/json, text/plain, */*",
        }
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            response = await client.post(self.base_url, data=payload)
        if response.status_code in {401, 403, 429}:
            raise APIError(
                ErrorCode.DATA_SOURCE_UNAVAILABLE,
                "CNInfo announcement request was blocked or rate limited.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider_status_code": response.status_code, "provider": "CNInfo"},
                "Retry later, reduce frequency, or use an authorized announcement data provider.",
            )
        if response.status_code >= 400:
            raise APIError(
                ErrorCode.DATA_SOURCE_UNAVAILABLE,
                "CNInfo announcement request failed.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider_status_code": response.status_code, "provider": "CNInfo"},
                "Check CNInfo availability or use an authorized announcement data provider.",
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise APIError(
                ErrorCode.PROVIDER_RESPONSE_INVALID,
                "CNInfo returned non-JSON content.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider": "CNInfo"},
                "Check whether CNInfo changed its public query interface.",
            ) from exc

        if "announcements" not in data:
            raise APIError(
                ErrorCode.PROVIDER_RESPONSE_INVALID,
                "CNInfo response does not include an announcements list.",
                status.HTTP_502_BAD_GATEWAY,
                {"provider": "CNInfo", "keys": list(data.keys())},
                "Check whether CNInfo changed its response structure.",
            )
        announcements = data.get("announcements") or []
        announcements = [item for item in announcements if str(item.get("secCode") or "") == code]
        filings = [self._normalize_item(item) for item in announcements[:limit]]
        status_text = "ok" if filings else "no_matching_filings"
        return {
            "filings": filings,
            "status": status_text,
            "source": "CNInfo",
            "source_type": "official_filing",
            "provider_as_of": filings[0]["filing_date"] if filings else datetime.now(timezone.utc).date().isoformat(),
            "warnings": [
                "CNInfo public query interfaces can change or rate-limit automated access; use authorized data providers for production-grade coverage.",
                "Treat no_matching_filings separately from provider errors.",
            ],
            "retrieved_at": datetime.now(timezone.utc),
        }
