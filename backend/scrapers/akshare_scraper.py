"""AKShare-based scraper for A-share financial statements.

Uses eastmoney's JSON API wrapped by akshare to fetch balance sheet,
profit sheet (income statement), and cash flow statement for a given
stock code, then upserts them into the local database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import akshare as ak
import pandas as pd


def _market_prefix(stock_code: str) -> str:
    """Determine the eastmoney market prefix (SH/SZ/BJ) for a stock code."""
    code = str(stock_code).zfill(6)
    if code.startswith(("8", "9", "4")):
        return "BJ" + code
    if code.startswith(("6", "5")):
        return "SH" + code
    return "SZ" + code


def _parse_period(report_date: Any) -> Tuple[int, int]:
    """Parse a REPORT_DATE value into (year, quarter).

    Date format examples:
      "2024-12-31" -> annual report, quarter=0
      "2024-03-31" -> Q1, quarter=1
      "2024-06-30" -> Q2 (semi-annual), quarter=2
      "2024-09-30" -> Q3, quarter=3
    """
    if isinstance(report_date, pd.Timestamp):
        d = report_date
    elif isinstance(report_date, datetime):
        d = report_date
    else:
        d = pd.Timestamp(str(report_date))

    year = d.year
    month = d.month
    if month == 3:
        return year, 1
    if month == 6:
        return year, 2
    if month == 9:
        return year, 3
    return year, 0


# ── Eastmoney column name → internal field name ──────────────────────────────

BALANCE_SHEET_FIELD_MAP: Dict[str, str] = {
    "MONETARYFUNDS": "cash_and_equivalents",
    "TRADE_FINASSET_NOTFVTPL": "trading_financial_assets",
    "FVTPL_FINASSET": "trading_financial_assets",
    "TRADE_FINASSET": "trading_financial_assets",
    "NOTE_ACCOUNTS_RECE": "notes_receivable",
    "NOTE_RECE": "notes_receivable",
    "ACCOUNTS_RECE": "accounts_receivable",
    "PREPAYMENT": "prepayments",
    "TOTAL_OTHER_RECE": "other_receivables",
    "OTHER_RECE": "other_receivables",
    "INVENTORY": "inventory",
    "OTHER_CURRENT_ASSET": "other_current_assets",
    "CONTRACT_ASSET": "contract_assets",
    "TOTAL_CURRENT_ASSETS": "total_current_assets",
    "AVAILABLE_SALE_FINASSET": "available_for_sale_assets",
    "OTHER_EQUITY_INVEST": "available_for_sale_assets",
    "FVTOCI_FINASSET": "available_for_sale_assets",
    "FVTOCI_NCFINASSET": "available_for_sale_assets",
    "HOLD_MATURITY_INVEST": "held_to_maturity",
    "OTHER_CREDITOR_INVEST": "held_to_maturity",
    "AMORTIZE_COST_FINASSET": "held_to_maturity",
    "AMORTIZE_COST_NCFINASSET": "held_to_maturity",
    "INVEST_REALESTATE": "investment_property",
    "USERIGHT_ASSET": "right_of_use_assets",
    "LONG_EQUITY_INVEST": "long_term_equity_investment",
    "FIXED_ASSET": "fixed_assets",
    "CIP": "construction_in_progress",
    "INTANGIBLE_ASSET": "intangible_assets",
    "GOODWILL": "goodwill",
    "LONG_PREPAID_EXPENSE": "long_term_deferred_expenses",
    "DEFER_TAX_ASSET": "deferred_tax_assets",
    "OTHER_NONCURRENT_ASSET": "other_non_current_assets",
    "TOTAL_NONCURRENT_ASSETS": "total_non_current_assets",
    "TOTAL_ASSETS": "total_assets",
    "SHORT_LOAN": "short_term_borrowings",
    "SHORT_BOND_PAYABLE": "short_term_borrowings",
    "NOTE_ACCOUNTS_PAYABLE": "notes_payable",
    "NOTE_PAYABLE": "notes_payable",
    "ACCOUNTS_PAYABLE": "accounts_payable",
    "ADVANCE_RECEIVABLES": "advance_receipts",
    "CONTRACT_LIAB": "advance_receipts",
    "STAFF_SALARY_PAYABLE": "employee_compensation_payable",
    "TAX_PAYABLE": "taxes_payable",
    "OTHER_CURRENT_LIAB": "other_current_liabilities",
    "NONCURRENT_LIAB_1YEAR": "non_current_liabilities_due_within_one_year",
    "TOTAL_OTHER_PAYABLE": "other_payables",
    "OTHER_PAYABLE": "other_payables",
    "TOTAL_CURRENT_LIAB": "total_current_liabilities",
    "LONG_LOAN": "long_term_borrowings",
    "BOND_PAYABLE": "bonds_payable",
    "DEFER_TAX_LIAB": "deferred_tax_liabilities",
    "OTHER_NONCURRENT_LIAB": "other_non_current_liabilities",
    "LONG_PAYABLE": "long_term_payables",
    "LEASE_LIAB": "lease_liabilities",
    "DEFER_INCOME": "deferred_income",
    "DEFER_INCOME_1YEAR": "deferred_income",
    "TOTAL_NONCURRENT_LIAB": "total_non_current_liabilities",
    "TOTAL_LIABILITIES": "total_liabilities",
    "SHARE_CAPITAL": "paid_in_capital",
    "CAPITAL_RESERVE": "capital_reserve",
    "SURPLUS_RESERVE": "surplus_reserve",
    "UNASSIGN_RPOFIT": "undistributed_profit",
    "TOTAL_PARENT_EQUITY": "total_equity_parent",
    "OTHER_COMPRE_INCOME": "other_comprehensive_income",
    "MINORITY_EQUITY": "minority_interest",
    "TOTAL_EQUITY": "total_equity",
}

INCOME_STATEMENT_FIELD_MAP: Dict[str, str] = {
    "OPERATE_INCOME": "revenue",
    "TOTAL_OPERATE_INCOME": "revenue",
    "OPERATE_COST": "cost_of_revenue",
    "OPERATE_TAX_ADD": "taxes_and_surcharges",
    "SALE_EXPENSE": "selling_expenses",
    "MANAGE_EXPENSE": "admin_expenses",
    "RESEARCH_EXPENSE": "rd_expenses",
    "ME_RESEARCH_EXPENSE": "rd_expenses",
    "FINANCE_EXPENSE": "finance_expenses",
    "INTEREST_EXPENSE": "interest_expense",
    "FE_INTEREST_EXPENSE": "interest_expense",
    "INTEREST_INCOME": "interest_income",
    "FE_INTEREST_INCOME": "interest_income",
    "ASSET_IMPAIRMENT_INCOME": "asset_impairment_loss",
    "ASSET_IMPAIRMENT_LOSS": "asset_impairment_loss",
    "CREDIT_IMPAIRMENT_INCOME": "credit_impairment_loss",
    "CREDIT_IMPAIRMENT_LOSS": "credit_impairment_loss",
    "OTHER_INCOME": "other_income",
    "INVEST_INCOME": "investment_income",
    "FAIRVALUE_CHANGE_INCOME": "fair_value_change_income",
    "ASSET_DISPOSAL_INCOME": "asset_disposal_income",
    "OPERATE_PROFIT": "operating_profit",
    "NONBUSINESS_INCOME": "non_operating_income",
    "NONBUSINESS_EXPENSE": "non_operating_expenses",
    "TOTAL_PROFIT": "total_profit",
    "INCOME_TAX": "income_tax_expense",
    "NETPROFIT": "net_profit",
    "PARENT_NETPROFIT": "net_profit_parent",
    "DEDUCT_PARENT_NETPROFIT": "non_recurring_profit",
    "MINORITY_INTEREST": "net_profit_minority",
}

CASH_FLOW_FIELD_MAP: Dict[str, str] = {
    "SALES_SERVICES": "cash_from_sales",
    "RECEIVE_TAX_REFUND": "tax_refunds",
    "RECEIVE_OTHER_OPERATE": "other_cash_from_operations",
    "TOTAL_OPERATE_INFLOW": "total_cash_from_operations",
    "BUY_SERVICES": "cash_paid_for_goods",
    "PAY_STAFF_CASH": "cash_paid_to_employees",
    "PAY_ALL_TAX": "taxes_paid",
    "PAY_OTHER_OPERATE": "other_cash_paid_for_operations",
    "TOTAL_OPERATE_OUTFLOW": "total_cash_paid_for_operations",
    "NETCASH_OPERATE": "net_cash_from_operations",
    "WITHDRAW_INVEST": "cash_from_investment_withdrawal",
    "RECEIVE_INVEST_INCOME": "cash_from_investment_income",
    "DISPOSAL_LONG_ASSET": "cash_from_asset_disposal",
    "RECEIVE_OTHER_INVEST": "other_cash_from_investing",
    "TOTAL_INVEST_INFLOW": "total_cash_from_investing",
    "CONSTRUCT_LONG_ASSET": "cash_paid_for_assets",
    "INVEST_PAY_CASH": "cash_paid_for_investments",
    "PAY_OTHER_INVEST": "other_cash_paid_for_investing",
    "TOTAL_INVEST_OUTFLOW": "total_cash_paid_for_investing",
    "NETCASH_INVEST": "net_cash_from_investing",
    "ACCEPT_INVEST_CASH": "cash_from_equity_issuance",
    "RECEIVE_LOAN_CASH": "cash_from_borrowings",
    "ISSUE_BOND": "cash_from_borrowings",
    "RECEIVE_OTHER_FINANCE": "other_cash_from_financing",
    "TOTAL_FINANCE_INFLOW": "total_cash_from_financing",
    "PAY_DEBT_CASH": "cash_paid_for_debt",
    "ASSIGN_DIVIDEND_PORFIT": "cash_paid_for_dividends",
    "PAY_OTHER_FINANCE": "other_cash_paid_for_financing",
    "TOTAL_FINANCE_OUTFLOW": "total_cash_paid_for_financing",
    "NETCASH_FINANCE": "net_cash_from_financing",
    "CCE_ADD": "net_increase_in_cash",
    "BEGIN_CASH_EQUIVALENTS": "cash_at_beginning",
    "BEGIN_CASH": "cash_at_beginning",
    "BEGIN_CCE": "cash_at_beginning",
    "END_CASH_EQUIVALENTS": "cash_at_end",
    "END_CASH": "cash_at_end",
    "END_CCE": "cash_at_end",
}


def _map_df_to_periods(
    df: pd.DataFrame,
    field_map: Dict[str, str],
) -> Dict[Tuple[int, int], Dict[str, float]]:
    """Convert an eastmoney DataFrame into per-period payload dicts.

    Each row in *df* is one report period. We transpose to iterate over
    field columns, map them to our internal names, and group values by
    (year, quarter).
    """
    periods: Dict[Tuple[int, int], Dict[str, float]] = {}
    if df.empty or "REPORT_DATE" not in df.columns:
        return periods

    for _, row in df.iterrows():
        year, quarter = _parse_period(row["REPORT_DATE"])

        # The report_date column might be NaT for delisted stocks
        if pd.isna(year) or pd.isna(row.get("REPORT_DATE")):
            continue

        key = (int(year), int(quarter))
        if key not in periods:
            periods[key] = {}

        for em_field, internal_field in field_map.items():
            if em_field not in df.columns:
                continue
            val = row[em_field]
            if pd.isna(val):
                continue
            try:
                num = float(val)
                # IMPAIRMENT_INCOME uses negative for loss; flip to positive loss
                if em_field.endswith("_IMPAIRMENT_INCOME"):
                    num = -num
                periods[key][internal_field] = num
            except (ValueError, TypeError):
                pass

    return periods


def _fetch_and_map(
    fetch_fn,
    symbol: str,
    field_map: Dict[str, str],
) -> Dict[Tuple[int, int], Dict[str, float]]:
    """Call an AKShare fetch function and map its result to period payloads."""
    try:
        df = fetch_fn(symbol)
        return _map_df_to_periods(df, field_map)
    except Exception as e:
        raise RuntimeError(f"采集失败 ({symbol}): {e}") from e


def scrape_company(
    stock_code: str, company_id: int
) -> Dict[str, Any]:
    """Scrape all three financial statements for a stock.

    Returns a dict:
      {stock_code, company_id, reports: [{year, quarter, fields: {...}}, ...], errors: [...]}
    """
    symbol = _market_prefix(stock_code)
    errors: List[str] = []

    try:
        bs = _fetch_and_map(
            ak.stock_balance_sheet_by_report_em,
            symbol,
            BALANCE_SHEET_FIELD_MAP,
        )
    except Exception as e:
        errors.append(f"资产负债表: {e}")
        bs = {}

    try:
        ps = _fetch_and_map(
            ak.stock_profit_sheet_by_report_em,
            symbol,
            INCOME_STATEMENT_FIELD_MAP,
        )
    except Exception as e:
        errors.append(f"利润表: {e}")
        ps = {}

    try:
        cf = _fetch_and_map(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol,
            CASH_FLOW_FIELD_MAP,
        )
    except Exception as e:
        errors.append(f"现金流量表: {e}")
        cf = {}

    all_periods = set(bs.keys()) | set(ps.keys()) | set(cf.keys())

    reports: List[Dict[str, Any]] = []
    for year, quarter in sorted(all_periods, key=lambda x: (x[0], 4 if x[1] == 0 else x[1])):
        fields: Dict[str, float] = {}
        fields.update(bs.get((year, quarter), {}))
        fields.update(ps.get((year, quarter), {}))
        fields.update(cf.get((year, quarter), {}))
        reports.append({
            "year": year,
            "quarter": quarter,
            "fields": fields,
        })

    return {
        "stock_code": stock_code,
        "company_id": company_id,
        "reports": reports,
        "errors": errors,
    }


def _test() -> None:
    result = scrape_company("000001", 0)
    print(f"Stock: {result['stock_code']}")
    print(f"Reports: {len(result['reports'])}")
    print(f"Errors: {result['errors']}")
    for r in result["reports"][:5]:
        print(f"  {r['year']} Q{r['quarter']}: {len(r['fields'])} fields")
    if result["reports"]:
        last = result["reports"][-1]
        print(f"  ... latest: {last['year']} Q{last['quarter']}: {list(last['fields'].keys())[:10]}")


if __name__ == "__main__":
    _test()
