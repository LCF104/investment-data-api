from abc import ABC, abstractmethod
from typing import Any


class EquityProvider(ABC):
    @abstractmethod
    async def get_snapshot(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_financials(self, symbol: str, period_type: str, limit: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_ratios(self, symbol: str, period: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_valuation(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_filings(self, symbol: str, filing_type: str, limit: int) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_industry(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

