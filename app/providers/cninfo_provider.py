from datetime import datetime, timezone
from typing import Any


class CNInfoProvider:
    async def get_filings(self, symbol: str, filing_type: str, limit: int) -> dict[str, Any]:
        return {
            "filings": [],
            "status": "not_implemented",
            "source": "CNInfo / exchange announcements",
            "source_type": "official_filing_placeholder",
            "provider_as_of": None,
            "warnings": [
                "A-share official filing search is not implemented in v1 because public CNInfo/search interfaces can change and may require anti-bot handling.",
                "Do not treat this as an empty announcement result.",
            ],
            "retrieved_at": datetime.now(timezone.utc),
        }
