def safe_divide(numerator: float | int | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def first_number(record: dict, keys: list[str]) -> float | None:
    for key in keys:
        value = record.get(key)
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
    return None


def calculate_financial_ratios(
    income_statement: dict,
    balance_sheet: dict,
    cash_flow_statement: dict,
) -> dict:
    revenue = first_number(income_statement, ["revenue", "totalRevenue", "total_revenue", "biz_income"])
    gross_profit = first_number(income_statement, ["grossProfit", "gross_profit"])
    operating_income = first_number(income_statement, ["operatingIncome", "operating_income", "operate_profit"])
    net_income = first_number(income_statement, ["netIncome", "net_income", "n_income", "net_profit"])
    ebit = first_number(income_statement, ["ebit", "incomeBeforeTax", "total_profit"])
    tax_expense = first_number(income_statement, ["incomeTaxExpense", "tax_expense", "income_tax"])

    total_assets = first_number(balance_sheet, ["totalAssets", "total_assets", "total_assets_end"])
    total_liabilities = first_number(balance_sheet, ["totalLiabilities", "total_liabilities", "total_liab"])
    total_equity = first_number(balance_sheet, ["totalStockholdersEquity", "total_equity", "total_hldr_eqy_exc_min_int"])
    total_debt = first_number(balance_sheet, ["totalDebt", "shortTermDebt", "total_debt", "interest_bearing_debt"])
    current_assets = first_number(balance_sheet, ["totalCurrentAssets", "current_assets", "total_cur_assets"])
    current_liabilities = first_number(balance_sheet, ["totalCurrentLiabilities", "current_liabilities", "total_cur_liab"])

    operating_cash_flow = first_number(cash_flow_statement, ["operatingCashFlow", "netCashProvidedByOperatingActivities", "n_cashflow_act"])
    capex = first_number(cash_flow_statement, ["capitalExpenditure", "capital_expenditure", "capex"])
    if capex is not None:
        capex = abs(capex)
    free_cash_flow = first_number(cash_flow_statement, ["freeCashFlow", "free_cash_flow"])
    if free_cash_flow is None and operating_cash_flow is not None:
        free_cash_flow = operating_cash_flow - (capex or 0)

    nopat = None
    if ebit is not None:
        if tax_expense is not None and ebit:
            tax_rate = max(0.0, min(0.6, tax_expense / ebit))
            nopat = ebit * (1 - tax_rate)
        else:
            nopat = ebit
    invested_capital = None
    if total_debt is not None and total_equity is not None:
        invested_capital = total_debt + total_equity

    return {
        "roe": safe_divide(net_income, total_equity),
        "roic": safe_divide(nopat, invested_capital),
        "roa": safe_divide(net_income, total_assets),
        "gross_margin": safe_divide(gross_profit, revenue),
        "operating_margin": safe_divide(operating_income, revenue),
        "net_margin": safe_divide(net_income, revenue),
        "debt_to_equity": safe_divide(total_debt or total_liabilities, total_equity),
        "current_ratio": safe_divide(current_assets, current_liabilities),
        "asset_liability_ratio": safe_divide(total_liabilities, total_assets),
        "operating_cash_flow": operating_cash_flow,
        "free_cash_flow": free_cash_flow,
        "fcf_margin": safe_divide(free_cash_flow, revenue),
        "calculation_method": {
            "roe": "net income / ending total equity; not average-equity ROE unless provider explicitly says so",
            "roic": "NOPAT / (total debt + total equity), with NOPAT estimated from EBIT after tax when available",
            "roa": "net income / ending total assets",
            "gross_margin": "gross profit / revenue",
            "operating_margin": "operating income / revenue",
            "net_margin": "net income / revenue",
            "debt_to_equity": "total debt / total equity when debt is available; otherwise total liabilities / total equity",
            "current_ratio": "current assets / current liabilities",
            "asset_liability_ratio": "total liabilities / total assets",
            "free_cash_flow": "operating cash flow - capital expenditure when provider free cash flow is unavailable",
            "fcf_margin": "free cash flow / revenue",
        },
    }
