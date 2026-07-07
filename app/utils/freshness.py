from datetime import date, datetime, timedelta, timezone


UNKNOWN_WARNING = "Unable to verify data freshness."


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def check_market_data_freshness(
    market: str,
    provider_as_of: str | None,
    now: datetime | None = None,
) -> dict[str, object]:
    now = now or utc_now()
    provider_date = parse_date(provider_as_of)
    if provider_date is None:
        return {
            "is_latest_available": False,
            "staleness_check": "unknown",
            "warnings": [UNKNOWN_WARNING],
        }

    age_days = (now.date() - provider_date).days
    if age_days < 0:
        return {
            "is_latest_available": False,
            "staleness_check": "provider_date_in_future",
            "warnings": ["Provider date is in the future; verify provider data."],
        }

    allowed_days = 4 if market == "US" else 7
    if age_days <= allowed_days:
        return {
            "is_latest_available": True,
            "staleness_check": f"provider date is {age_days} calendar days old",
            "warnings": [],
        }

    return {
        "is_latest_available": False,
        "staleness_check": f"provider date is {age_days} calendar days old",
        "warnings": ["Market data may be stale."],
    }


def check_filings_freshness(
    latest_filing_date: str | None,
    max_age_days: int = 90,
    now: datetime | None = None,
) -> dict[str, object]:
    now = now or utc_now()
    filing_date = parse_date(latest_filing_date)
    if filing_date is None:
        return {
            "is_latest_available": False,
            "staleness_check": "unknown",
            "warnings": [UNKNOWN_WARNING],
        }
    age_days = (now.date() - filing_date).days
    if age_days <= max_age_days:
        return {
            "is_latest_available": True,
            "staleness_check": f"latest filing is within {max_age_days} days",
            "warnings": [],
        }
    return {
        "is_latest_available": False,
        "staleness_check": f"latest filing is {age_days} days old",
        "warnings": [f"No filing found in the last {max_age_days} days."],
    }


def check_statement_freshness(
    filing_date: str | None,
    period_type: str,
    now: datetime | None = None,
) -> dict[str, object]:
    now = now or utc_now()
    filed = parse_date(filing_date)
    if filed is None:
        return {
            "is_latest_available": False,
            "staleness_check": "unknown",
            "warnings": [UNKNOWN_WARNING],
        }
    max_age = timedelta(days=550 if period_type == "annual" else 190)
    if now.date() - filed <= max_age:
        return {
            "is_latest_available": True,
            "staleness_check": f"{period_type} statement appears recent",
            "warnings": [],
        }
    return {
        "is_latest_available": False,
        "staleness_check": f"{period_type} statement may be outdated",
        "warnings": [f"Latest {period_type} statement appears stale."],
    }
