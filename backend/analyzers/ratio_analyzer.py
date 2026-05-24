from __future__ import annotations

from typing import Dict, List, Optional

from models.database import ALL_FINANCIAL_FIELDS


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    if b == 0:
        return None
    return a / b


def pct(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value * 100, 2)


def _num(v) -> float:
    return float(v or 0.0)


def period_days_for_report(r, single_quarter_mode: bool = False) -> int:
    if single_quarter_mode:
        return {1: 90, 2: 91, 3: 92, 0: 92}.get(getattr(r, "quarter", 0), 365)
    return {1: 90, 2: 181, 3: 273, 0: 365}.get(getattr(r, "quarter", 0), 365)


def _avg(current: float, base: Optional[float]) -> float:
    if base is None:
        return current
    return (current + base) / 2


def _field(report, field: str) -> float:
    return _num(getattr(report, field, 0.0)) if report is not None else 0.0


def analyze_single_report(r, base_report=None, period_days: Optional[int] = None) -> Dict:
    period_days = period_days or period_days_for_report(r)
    annual_factor = 365 / period_days if period_days > 0 else 1

    total_assets = _num(r.total_assets)
    total_liabilities = _num(r.total_liabilities)
    total_equity = _num(r.total_equity)
    interest_bearing_debt = _num(r.short_term_borrowings) + _num(r.long_term_borrowings) + _num(r.bonds_payable)
    base_interest_bearing_debt = _field(base_report, "short_term_borrowings") + _field(base_report, "long_term_borrowings") + _field(base_report, "bonds_payable") if base_report else None

    avg_total_assets = _avg(total_assets, _field(base_report, "total_assets") if base_report else None)
    avg_total_equity = _avg(total_equity, _field(base_report, "total_equity") if base_report else None)
    avg_total_equity_parent = _avg(_num(r.total_equity_parent), _field(base_report, "total_equity_parent") if base_report else None)
    avg_interest_bearing_debt = _avg(interest_bearing_debt, base_interest_bearing_debt)

    investment_assets = (_num(r.trading_financial_assets) + _num(r.available_for_sale_assets)
                         + _num(r.held_to_maturity) + _num(r.long_term_equity_investment)
                         + _num(r.investment_property))
    operating_assets = (_num(r.notes_receivable) + _num(r.accounts_receivable)
                        + _num(r.prepayments) + _num(r.other_receivables) + _num(r.inventory)
                        + _num(r.contract_assets))
    production_assets = (_num(r.fixed_assets) + _num(r.construction_in_progress)
                         + _num(r.intangible_assets) + _num(r.long_term_deferred_expenses)
                         + _num(r.right_of_use_assets))
    operating_liabilities = (_num(r.notes_payable) + _num(r.accounts_payable)
                             + _num(r.advance_receipts) + _num(r.other_payables))
    bargaining_power = safe_div(operating_liabilities + _num(r.advance_receipts),
                                operating_assets - _num(r.inventory) + _num(r.prepayments))

    current_ratio = safe_div(_num(r.total_current_assets), _num(r.total_current_liabilities))
    quick_ratio = safe_div(_num(r.total_current_assets) - _num(r.inventory), _num(r.total_current_liabilities))
    cash_debt_ratio = safe_div(_num(r.cash_and_equivalents), interest_bearing_debt)
    cash_short_debt_ratio = safe_div(_num(r.cash_and_equivalents), _num(r.short_term_borrowings))
    net_debt_ratio = safe_div(interest_bearing_debt - _num(r.cash_and_equivalents), total_equity)
    interest_expense_val = _num(r.interest_expense)
    if interest_expense_val == 0 and _num(r.finance_expenses) > 0:
        interest_expense_val = _num(r.finance_expenses)
    ebit = _num(r.total_profit) + interest_expense_val
    interest_coverage = safe_div(ebit, interest_expense_val) if interest_expense_val > 0 else None

    avg_cash = _avg(_num(r.cash_and_equivalents), _field(base_report, "cash_and_equivalents") if base_report else None)
    interest_income_to_avg_cash = safe_div(_num(r.interest_income), avg_cash) if avg_cash > 0 else None
    
    equity_liability_ratio = safe_div(total_liabilities, total_equity)
    ocf_to_debt = safe_div(_num(r.net_cash_from_operations), interest_bearing_debt)
    ocf_to_current_liabilities = safe_div(_num(r.net_cash_from_operations), _num(r.total_current_liabilities))
    ocf_to_all_debt = safe_div(_num(r.net_cash_from_operations), total_liabilities)

    gross_margin = safe_div(_num(r.revenue) - _num(r.cost_of_revenue), _num(r.revenue))
    operating_margin = safe_div(_num(r.operating_profit), _num(r.revenue))
    net_margin = safe_div(_num(r.net_profit), _num(r.revenue))
    net_margin_parent = safe_div(_num(r.net_profit_parent), _num(r.revenue))
    annualized_net_profit_parent = _num(r.net_profit_parent) * annual_factor
    annualized_net_profit = _num(r.net_profit) * annual_factor
    annualized_operating_profit = _num(r.operating_profit) * annual_factor
    annualized_revenue = _num(r.revenue) * annual_factor
    annualized_cost = _num(r.cost_of_revenue) * annual_factor

    roe = safe_div(annualized_net_profit_parent, avg_total_equity_parent)
    roa = safe_div(annualized_net_profit, avg_total_assets)

    tax_rate = safe_div(_num(r.income_tax_expense), _num(r.total_profit))
    if tax_rate is None:
        tax_rate = 0.25
    nopat = annualized_operating_profit * (1 - tax_rate)
    roic = safe_div(nopat, avg_total_equity + avg_interest_bearing_debt)
    
    avg_internal_assets = avg_total_assets - _avg(_num(r.long_term_equity_investment), _field(base_report, "long_term_equity_investment") if base_report else None)
    internal_roa = safe_div(annualized_operating_profit, avg_internal_assets)
    equity_cash_recovery = safe_div(_num(r.net_cash_from_operations) * annual_factor, avg_total_equity)

    eps = safe_div(_num(r.net_profit_parent), _num(r.total_shares) * 10000)

    avg_minority_interest = _avg(_num(r.minority_interest), _field(base_report, "minority_interest") if base_report else None)
    minority_roe = safe_div(_num(r.net_profit_minority) * annual_factor, avg_minority_interest)
    parent_roe_detail = safe_div(_num(r.net_profit_parent) * annual_factor, avg_total_equity_parent)

    non_recurring_items = (_num(r.investment_income) + _num(r.fair_value_change_income)
                           + _num(r.other_income) + _num(r.asset_disposal_income))
    operating_profit_val = _num(r.operating_profit)
    non_recurring_ratio = safe_div(non_recurring_items, abs(operating_profit_val)) if operating_profit_val != 0 else None
    profit_structure = {
        "investment_income_ratio": pct(safe_div(_num(r.investment_income), abs(operating_profit_val))) if operating_profit_val != 0 else None,
        "fair_value_change_ratio": pct(safe_div(_num(r.fair_value_change_income), abs(operating_profit_val))) if operating_profit_val != 0 else None,
        "other_income_ratio": pct(safe_div(_num(r.other_income), abs(operating_profit_val))) if operating_profit_val != 0 else None,
        "asset_disposal_ratio": pct(safe_div(_num(r.asset_disposal_income), abs(operating_profit_val))) if operating_profit_val != 0 else None,
        "non_recurring_ratio": pct(non_recurring_ratio),
    }

    if _num(r.non_recurring_profit) != 0:
        non_recurring_diff = _num(r.net_profit) - _num(r.non_recurring_profit)
        non_recurring_impact = safe_div(abs(non_recurring_diff), abs(_num(r.net_profit))) if _num(r.net_profit) != 0 else None
    else:
        non_recurring_impact = None

    total_expense_ratio = safe_div(
        _num(r.selling_expenses) + _num(r.admin_expenses) + _num(r.rd_expenses) + _num(r.finance_expenses),
        _num(r.revenue),
    )

    asset_turnover = safe_div(annualized_revenue, avg_total_assets)
    equity_multiplier = safe_div(avg_total_assets, avg_total_equity)
    roe_dupont = None
    if net_margin is not None and asset_turnover is not None and equity_multiplier is not None:
        roe_dupont = net_margin * asset_turnover * equity_multiplier

    free_cash_flow = _num(r.net_cash_from_operations) - _num(r.cash_paid_for_assets)
    ocf_to_net_profit = safe_div(_num(r.net_cash_from_operations), _num(r.net_profit))
    sales_cash_to_revenue = safe_div(_num(r.cash_from_sales), _num(r.revenue))
    dividend_payout = safe_div(_num(r.dividends_paid), _num(r.net_profit_parent))
    ocf_margin = safe_div(_num(r.net_cash_from_operations), _num(r.revenue))
    capex_to_ocf = safe_div(_num(r.cash_paid_for_assets), _num(r.net_cash_from_operations))
    capex_to_revenue = safe_div(_num(r.cash_paid_for_assets), _num(r.revenue))

    portrait_map = {
        (True, True, True): ("蛮牛型", "🐂", "经营、投资、筹资现金流全为正，现金流全面扩张", "low"),
        (True, True, False): ("老母鸡型", "🐔", "经营与投资回款稳定，筹资净流出", "low"),
        (True, False, True): ("奶牛型", "🐄", "经营稳健并持续投资，适度融资支持", "low"),
        (True, False, False): ("妖精型", "👻", "经营现金流强，投资与融资均净流出", "low"),
        (False, True, True): ("大出血型", "🩸", "经营失血，依靠处置资产和融资维持", "high"),
        (False, False, True): ("赌徒型", "🎰", "经营与投资双负，依赖融资续命", "high"),
        (False, True, False): ("混吃等死型", "💀", "经营差且无新增融资，持续萎缩", "high"),
        (False, False, False): ("骗吃骗喝型", "🤥", "三大现金流全负，经营质量极弱", "critical"),
    }
    portrait_key = (_num(r.net_cash_from_operations) > 0, _num(r.net_cash_from_investing) > 0, _num(r.net_cash_from_financing) > 0)
    p_type, p_emoji, p_desc, p_risk = portrait_map[portrait_key]

    current_receivables = _num(r.accounts_receivable) + _num(r.notes_receivable)
    base_receivables = (_field(base_report, "accounts_receivable") + _field(base_report, "notes_receivable")) if base_report else None
    avg_receivables = _avg(current_receivables, base_receivables)
    avg_inventory = _avg(_num(r.inventory), _field(base_report, "inventory") if base_report else None)
    avg_payables = _avg(_num(r.accounts_payable), _field(base_report, "accounts_payable") if base_report else None)
    avg_fixed_assets = _avg(_num(r.fixed_assets), _field(base_report, "fixed_assets") if base_report else None)

    receivable_turnover = safe_div(annualized_revenue, avg_receivables)
    inventory_turnover = safe_div(annualized_cost, avg_inventory)
    payable_turnover = safe_div(annualized_cost, avg_payables)

    score_items = {
        "roe_gt_15": {"pass": (roe or 0) > 0.15, "value": pct(roe)},
        "gross_margin_gt_40": {"pass": (gross_margin or 0) > 0.4, "value": pct(gross_margin)},
        "net_margin_gt_15": {"pass": (net_margin or 0) > 0.15, "value": pct(net_margin)},
        "ocf_gt_profit": {"pass": _num(r.net_cash_from_operations) > _num(r.net_profit), "value": round(_num(r.net_cash_from_operations) - _num(r.net_profit), 2)},
    }
    score = sum(25 for i in score_items.values() if i["pass"])

    return {
        "asset_structure": {
            "cash_ratio": pct(safe_div(_num(r.cash_and_equivalents), total_assets)),
            "investment_assets": round(investment_assets, 2),
            "operating_assets": round(operating_assets, 2),
            "production_assets": round(production_assets, 2),
            "current_asset_ratio": pct(safe_div(_num(r.total_current_assets), total_assets)),
            "non_current_asset_ratio": pct(safe_div(_num(r.total_non_current_assets), total_assets)),
            "investment_assets_ratio": pct(safe_div(investment_assets, total_assets)),
            "operating_assets_ratio": pct(safe_div(operating_assets, total_assets)),
            "production_assets_ratio": pct(safe_div(production_assets, total_assets)),
            "operating_liabilities": round(operating_liabilities, 2),
            "bargaining_power": round(bargaining_power, 4) if bargaining_power is not None else None,
        },
        "liability_structure": {
            "interest_bearing_debt": round(interest_bearing_debt, 2),
            "non_interest_bearing_debt": round(total_liabilities - interest_bearing_debt, 2),
            "interest_bearing_ratio": pct(safe_div(interest_bearing_debt, total_liabilities)),
            "current_liability_ratio": pct(safe_div(_num(r.total_current_liabilities), total_liabilities)),
            "short_term_debt_ratio": pct(safe_div(_num(r.short_term_borrowings), interest_bearing_debt)),
        },
        "safety": {
            "current_ratio": round(current_ratio, 4) if current_ratio is not None else None,
            "quick_ratio": round(quick_ratio, 4) if quick_ratio is not None else None,
            "cash_debt_ratio": round(cash_debt_ratio, 4) if cash_debt_ratio is not None else None,
            "cash_short_debt_ratio": round(cash_short_debt_ratio, 4) if cash_short_debt_ratio is not None else None,
            "net_debt_ratio": pct(net_debt_ratio),
            "interest_coverage": round(interest_coverage, 4) if interest_coverage is not None else None,
            "interest_bearing_debt_ratio": pct(safe_div(interest_bearing_debt, total_assets)),
            "debt_to_asset_ratio": pct(safe_div(total_liabilities, total_assets)),
            "equity_ratio": pct(safe_div(total_equity, total_assets)),
            "equity_multiplier": round(equity_multiplier, 4) if equity_multiplier is not None else None,
            "equity_liability_ratio": round(equity_liability_ratio, 4) if equity_liability_ratio is not None else None,
            "ocf_to_interest_debt": round(ocf_to_debt, 4) if ocf_to_debt is not None else None,
            "ocf_to_current_liabilities": round(ocf_to_current_liabilities, 4) if ocf_to_current_liabilities is not None else None,
            "ocf_to_all_debt": round(ocf_to_all_debt, 4) if ocf_to_all_debt is not None else None,
        },
        "asset_quality": {
            "receivable_to_revenue": pct(safe_div(_num(r.accounts_receivable), _num(r.revenue))),
            "inventory_to_revenue": pct(safe_div(_num(r.inventory), _num(r.revenue))),
            "goodwill_to_equity": pct(safe_div(_num(r.goodwill), total_equity)),
            "construction_to_fixed": pct(safe_div(_num(r.construction_in_progress), _num(r.fixed_assets))),
            "heavy_asset_ratio": pct(safe_div(_num(r.fixed_assets) + _num(r.construction_in_progress), total_assets)),
        },
        "profitability": {
            "gross_margin": pct(gross_margin),
            "operating_margin": pct(operating_margin),
            "net_margin": pct(net_margin),
            "net_margin_parent": pct(net_margin_parent),
            "roe": pct(roe),
            "roa": pct(roa),
            "eps": round(eps, 6) if eps is not None else None,
            "roic": pct(roic),
            "internal_roa": pct(internal_roa),
            "equity_cash_recovery": pct(equity_cash_recovery),
            "ebit": round(ebit, 2),
            "interest_income_to_avg_cash": pct(interest_income_to_avg_cash),
            "parent_roe": pct(parent_roe_detail),
            "minority_roe": pct(minority_roe),
            "roe_gap": pct(parent_roe_detail - minority_roe) if parent_roe_detail is not None and minority_roe is not None else None,
            "non_recurring_impact": pct(non_recurring_impact),
        },
        "profit_structure": profit_structure,
        "expense_ratios": {
            "selling_expense_ratio": pct(safe_div(_num(r.selling_expenses), _num(r.revenue))),
            "admin_expense_ratio": pct(safe_div(_num(r.admin_expenses), _num(r.revenue))),
            "rd_expense_ratio": pct(safe_div(_num(r.rd_expenses), _num(r.revenue))),
            "finance_expense_ratio": pct(safe_div(_num(r.finance_expenses), _num(r.revenue))),
            "total_expense_ratio": pct(total_expense_ratio),
        },
        "dupont": {
            "net_profit_rate": pct(net_margin),
            "asset_turnover": round(asset_turnover, 4) if asset_turnover is not None else None,
            "equity_multiplier": round(equity_multiplier, 4) if equity_multiplier is not None else None,
            "roe_dupont": pct(roe_dupont),
        },
        "cash_flow": {
            "free_cash_flow": round(free_cash_flow, 2),
            "ocf_to_net_profit": round(ocf_to_net_profit, 4) if ocf_to_net_profit is not None else None,
            "sales_cash_to_revenue": round(sales_cash_to_revenue, 4) if sales_cash_to_revenue is not None else None,
            "ocf_margin": pct(ocf_margin),
            "capex_to_ocf": round(capex_to_ocf, 4) if capex_to_ocf is not None else None,
            "capex_to_revenue": round(capex_to_revenue, 4) if capex_to_revenue is not None else None,
            "net_cash_operations": round(_num(r.net_cash_from_operations), 2),
            "net_cash_investing": round(_num(r.net_cash_from_investing), 2),
            "net_cash_financing": round(_num(r.net_cash_from_financing), 2),
            "cash_at_end": round(_num(r.cash_at_end), 2),
            "dividend_payout_ratio": pct(dividend_payout),
            "portrait": {"type": p_type, "emoji": p_emoji, "desc": p_desc, "risk": p_risk},
            "quality_checks": {
                "ocf_gt_net_profit": _num(r.net_cash_from_operations) > _num(r.net_profit),
                "sales_cash_gte_revenue": _num(r.cash_from_sales) >= _num(r.revenue),
                "investing_negative": _num(r.net_cash_from_investing) < 0,
                "cash_gte_interest_debt": _num(r.cash_and_equivalents) >= interest_bearing_debt,
                "dividend_reasonable": _num(r.net_profit_parent) > 0 and 0.2 <= (dividend_payout or -1) <= 0.7,
            },
        },
        "turnover": {
            "receivable_turnover": round(receivable_turnover, 4) if receivable_turnover is not None else None,
            "receivable_days": round(365 / receivable_turnover, 2) if receivable_turnover and receivable_turnover > 0 else None,
            "inventory_turnover": round(inventory_turnover, 4) if inventory_turnover is not None else None,
            "inventory_days": round(365 / inventory_turnover, 2) if inventory_turnover and inventory_turnover > 0 else None,
            "payable_turnover": round(payable_turnover, 4) if payable_turnover is not None else None,
            "payable_days": round(365 / payable_turnover, 2) if payable_turnover and payable_turnover > 0 else None,
            "fixed_asset_turnover": round(safe_div(annualized_revenue, avg_fixed_assets) or 0, 4) if avg_fixed_assets else None,
            "total_asset_turnover": round(asset_turnover, 4) if asset_turnover is not None else None,
            "cash_conversion_cycle": _calculate_cash_conversion_cycle(receivable_turnover, inventory_turnover, payable_turnover),
        },
        "good_company_score": {
            "score": score,
            "items": score_items,
        },
        "period_context": {
            "days": period_days,
            "annualization_factor": round(annual_factor, 4),
            "uses_average_balance": base_report is not None,
        },
    }


def _calculate_cash_conversion_cycle(receivable_turnover, inventory_turnover, payable_turnover) -> Optional[float]:
    """计算现金转换周期 = 应收账款周转天数 + 存货周转天数 - 应付账款周转天数"""
    if not receivable_turnover or not inventory_turnover or not payable_turnover:
        return None
    if receivable_turnover <= 0 or inventory_turnover <= 0 or payable_turnover <= 0:
        return None
    receivable_days = 365 / receivable_turnover
    inventory_days = 365 / inventory_turnover
    payable_days = 365 / payable_turnover
    return round(receivable_days + inventory_days - payable_days, 2)


def _series_value(report, metric: str, base_report=None, period_days: Optional[int] = None) -> Optional[float]:
    m = analyze_single_report(report, base_report=base_report, period_days=period_days)
    if metric == "gross_margin":
        return m["profitability"]["gross_margin"]
    if metric == "net_margin":
        return m["profitability"]["net_margin"]
    if metric == "roe":
        return m["profitability"]["roe"]
    if metric == "roa":
        return m["profitability"]["roa"]
    if metric == "roic":
        return m["profitability"]["roic"]
    if metric == "operating_margin":
        return m["profitability"]["operating_margin"]
    if metric == "current_ratio":
        return m["safety"]["current_ratio"]
    if metric == "quick_ratio":
        return m["safety"]["quick_ratio"]
    if metric == "cash_debt_ratio":
        return m["safety"]["cash_debt_ratio"]
    if metric == "cash_short_debt_ratio":
        return m["safety"]["cash_short_debt_ratio"]
    if metric == "net_debt_ratio":
        return m["safety"]["net_debt_ratio"]
    if metric == "interest_coverage":
        return m["safety"]["interest_coverage"]
    if metric == "debt_to_asset_ratio":
        return m["safety"]["debt_to_asset_ratio"]
    if metric == "free_cash_flow":
        return m["cash_flow"]["free_cash_flow"]
    if metric == "ocf_to_net_profit":
        return m["cash_flow"]["ocf_to_net_profit"]
    if metric == "ocf_margin":
        return m["cash_flow"]["ocf_margin"]
    if metric == "capex_to_ocf":
        return m["cash_flow"]["capex_to_ocf"]
    if metric == "asset_turnover":
        return m["dupont"]["asset_turnover"]
    if metric == "equity_multiplier":
        return m["dupont"]["equity_multiplier"]
    if metric == "receivable_to_revenue":
        return m["asset_quality"]["receivable_to_revenue"]
    if metric == "inventory_turnover":
        return m["turnover"]["inventory_turnover"]
    if metric == "receivable_days":
        return m["turnover"]["receivable_days"]
    if metric == "inventory_days":
        return m["turnover"]["inventory_days"]
    if metric == "payable_days":
        return m["turnover"]["payable_days"]
    if metric == "selling_expense_ratio":
        return m["expense_ratios"]["selling_expense_ratio"]
    if metric == "admin_expense_ratio":
        return m["expense_ratios"]["admin_expense_ratio"]
    if metric == "rd_expense_ratio":
        return m["expense_ratios"]["rd_expense_ratio"]
    if metric == "score":
        return m["good_company_score"]["score"]
    if metric == "internal_roa":
        return m["profitability"]["internal_roa"]
    if metric == "equity_cash_recovery":
        return m["profitability"]["equity_cash_recovery"]
    if metric == "interest_income_to_avg_cash":
        return m["profitability"]["interest_income_to_avg_cash"]
    if metric == "ebit":
        return m["profitability"]["ebit"]
    if metric == "cash_conversion_cycle":
        return m["turnover"]["cash_conversion_cycle"]
    if metric == "equity_ratio":
        return m["safety"]["equity_ratio"]
    if metric == "interest_bearing_debt_ratio":
        return m["safety"]["interest_bearing_debt_ratio"]
    if metric == "heavy_asset_ratio":
        return m["asset_quality"]["heavy_asset_ratio"]
    if metric == "cash_ratio":
        return m["asset_structure"]["cash_ratio"]
    if metric == "total_expense_ratio":
        return m["expense_ratios"]["total_expense_ratio"]
    if metric == "finance_expense_ratio":
        return m["expense_ratios"]["finance_expense_ratio"]
    if metric == "total_asset_turnover":
        return m["turnover"]["total_asset_turnover"]
    if metric == "fixed_asset_turnover":
        return m["turnover"]["fixed_asset_turnover"]
    if metric == "eps":
        return m["profitability"]["eps"]
    if metric == "bargaining_power":
        return m["asset_structure"]["bargaining_power"]
    return float(getattr(report, metric, 0.0) or 0.0)


def _growth(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 2)


def _period_sort_key(report) -> tuple[int, int]:
    # quarter=0 means annual report; in a yearly timeline it should come after Q3.
    quarter_order = 4 if report.quarter == 0 else report.quarter
    return (report.year, quarter_order)


def _period_key(report) -> tuple[int, int]:
    return (int(report.year), int(report.quarter))


def _analysis_base_for_report(report, reports_by_period: Dict[tuple[int, int], object], single_quarter_mode: bool):
    attached_base = getattr(report, "_analysis_base_report", None)
    if attached_base is not None:
        return attached_base

    if single_quarter_mode:
        if report.quarter == 1:
            return reports_by_period.get((report.year - 1, 0))
        prev_quarter = {2: 1, 3: 2, 0: 3}.get(report.quarter)
        return reports_by_period.get((report.year, prev_quarter)) if prev_quarter is not None else None

    return reports_by_period.get((report.year - 1, 0))


def analyze_multi_period(reports: List, single_quarter_mode: bool = False) -> Dict:
    if len(reports) < 2:
        return {}

    reports = sorted(reports, key=_period_sort_key)
    reports_by_period = {_period_key(r): r for r in reports}
    if single_quarter_mode:
        periods = [f"{r.year}Q{r.quarter or 4}" for r in reports]
    else:
        periods = [f"{r.year}" if r.quarter == 0 else f"{r.year}Q{r.quarter}" for r in reports]

    base_metrics = [
        "gross_margin", "net_margin", "roe", "roa", "roic", "operating_margin", "current_ratio", "quick_ratio",
        "cash_debt_ratio", "cash_short_debt_ratio", "net_debt_ratio", "interest_coverage", "debt_to_asset_ratio",
        "equity_ratio", "interest_bearing_debt_ratio", "heavy_asset_ratio",
        "free_cash_flow", "ocf_to_net_profit", "ocf_margin", "capex_to_ocf",
        "asset_turnover", "total_asset_turnover", "fixed_asset_turnover", "equity_multiplier",
        "receivable_to_revenue", "inventory_turnover", "receivable_days", "inventory_days", "payable_days",
        "selling_expense_ratio", "admin_expense_ratio", "rd_expense_ratio", "finance_expense_ratio", "total_expense_ratio",
        "score", "cash_ratio", "bargaining_power",
        "revenue", "cost_of_revenue", "net_profit", "net_profit_parent", "operating_profit", "total_assets", "total_liabilities",
        "total_equity", "net_cash_from_operations", "net_cash_from_investing", "net_cash_from_financing", "accounts_receivable",
        "inventory", "cash_and_equivalents", "internal_roa", "equity_cash_recovery", "interest_income_to_avg_cash", "ebit",
        "cash_conversion_cycle", "eps",
    ]
    # Include all raw financial statement fields so every report line item can be trended
    metrics_to_track = list(dict.fromkeys(base_metrics + ALL_FINANCIAL_FIELDS))

    out = {"periods": periods, "metrics": {}}
    for metric in metrics_to_track:
        values = [
            _series_value(
                r,
                metric,
                base_report=_analysis_base_for_report(r, reports_by_period, single_quarter_mode),
                period_days=period_days_for_report(r, single_quarter_mode=single_quarter_mode),
            )
            for r in reports
        ]
        value_by_period = {_period_key(r): values[idx] for idx, r in enumerate(reports)}
        yoy = []
        qoq = []
        for i, report in enumerate(reports):
            previous_year_value = value_by_period.get((report.year - 1, report.quarter))
            yoy.append(_growth(values[i], previous_year_value))

            qoq_value = None
            if single_quarter_mode and i > 0:
                qoq_value = _growth(values[i], values[i - 1])
            elif report.quarter == 0:
                qoq_value = _growth(values[i], value_by_period.get((report.year - 1, 0)))
            qoq.append(qoq_value)
        out["metrics"][metric] = {"values": values, "yoy": yoy, "qoq": qoq}
    return out
