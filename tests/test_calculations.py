from app.utils.calculations import calculate_financial_ratios


def test_calculate_financial_ratios_from_statements():
    income = {
        "revenue": 1000,
        "grossProfit": 400,
        "operatingIncome": 250,
        "netIncome": 180,
        "ebit": 240,
        "incomeTaxExpense": 48,
    }
    balance = {
        "totalAssets": 2000,
        "totalLiabilities": 800,
        "totalStockholdersEquity": 1200,
        "totalDebt": 300,
        "totalCurrentAssets": 700,
        "totalCurrentLiabilities": 350,
    }
    cashflow = {"operatingCashFlow": 220, "capitalExpenditure": -60}

    ratios = calculate_financial_ratios(income, balance, cashflow)

    assert ratios["roe"] == 0.15
    assert ratios["roa"] == 0.09
    assert ratios["gross_margin"] == 0.4
    assert ratios["operating_margin"] == 0.25
    assert ratios["net_margin"] == 0.18
    assert ratios["current_ratio"] == 2.0
    assert ratios["free_cash_flow"] == 160
    assert ratios["fcf_margin"] == 0.16
    assert "roe" in ratios["calculation_method"]

