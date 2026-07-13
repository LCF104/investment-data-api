from datetime import datetime, timezone

from app.utils.freshness import check_filings_freshness, check_market_data_freshness, check_statement_freshness


def test_market_freshness_unknown_when_date_missing():
    result = check_market_data_freshness("US", None)
    assert result["is_latest_available"] is False
    assert result["staleness_check"] == "unknown"
    assert result["warnings"] == ["Unable to verify data freshness."]


def test_market_freshness_recent_us_date_is_latest():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    result = check_market_data_freshness("US", "2026-07-06", now)
    assert result["is_latest_available"] is True
    assert result["warnings"] == []


def test_market_freshness_old_date_warns():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    result = check_market_data_freshness("CN", "2026-06-01", now)
    assert result["is_latest_available"] is False
    assert "stale" in result["warnings"][0].lower()


def test_filings_freshness_checks_90_days():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    result = check_filings_freshness("2026-04-01", now=now)
    assert result["is_latest_available"] is False


def test_statement_freshness_checks_period_age():
    now = datetime(2026, 7, 7, tzinfo=timezone.utc)
    result = check_statement_freshness("2026-05-01", "quarterly", now)
    assert result["is_latest_available"] is True

