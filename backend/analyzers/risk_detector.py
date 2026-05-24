from __future__ import annotations

from typing import Dict, Optional


def safe_div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _n(v):
    return float(v or 0.0)


def _growth(cur, prev):
    if prev == 0:
        return None
    return (cur - prev) / abs(prev)


def _risk_item(category: str, name: str, severity: str, detail: str, threshold: str):
    return {
        "category": category,
        "name": name,
        "severity": severity,
        "detail": detail,
        "threshold": threshold,
    }


def detect_risks(report, prev_report=None) -> Dict:
    risks = []

    if prev_report:
        recv_growth = _growth(_n(report.accounts_receivable), _n(prev_report.accounts_receivable))
        rev_growth = _growth(_n(report.revenue), _n(prev_report.revenue))
        if recv_growth is not None and rev_growth is not None and recv_growth > rev_growth * 1.5 and recv_growth > 0.1:
            risks.append(_risk_item("revenue", "应收增速远超营收增速", "high", f"应收增速{recv_growth*100:.2f}%，营收增速{rev_growth*100:.2f}%", "应收增速 > 营收增速1.5倍且 >10%"))

    ratio_ocf_profit = safe_div(_n(report.net_cash_from_operations), _n(report.net_profit))
    if _n(report.net_profit) > 0 and ratio_ocf_profit is not None and ratio_ocf_profit < 0.5:
        risks.append(_risk_item("revenue", "经营现金流远低于净利润", "high", f"经营现金流/净利润={ratio_ocf_profit:.2f}", "< 0.5"))

    gross_margin = safe_div(_n(report.revenue) - _n(report.cost_of_revenue), _n(report.revenue))
    if gross_margin is not None and gross_margin > 0.8:
        risks.append(_risk_item("revenue", "毛利率异常高", "medium", f"毛利率={gross_margin*100:.2f}%", "> 80%"))

    if prev_report:
        prev_gm = safe_div(_n(prev_report.revenue) - _n(prev_report.cost_of_revenue), _n(prev_report.revenue))
        if gross_margin is not None and prev_gm is not None and abs(gross_margin - prev_gm) > 0.1:
            risks.append(_risk_item("revenue", "毛利率大幅波动", "medium", f"本期{gross_margin*100:.2f}% vs 上期{prev_gm*100:.2f}%", "变化 > 10个百分点"))

    impairment = abs(_n(report.asset_impairment_loss) + _n(report.credit_impairment_loss))
    if abs(_n(report.net_profit)) > 0 and impairment / abs(_n(report.net_profit)) > 0.3:
        risks.append(_risk_item("expense", "资产减值占净利润过高", "medium", f"减值占比={impairment/abs(_n(report.net_profit))*100:.2f}%", "> 30%"))

    sales_cash_ratio = safe_div(_n(report.cash_from_sales), _n(report.revenue))
    if _n(report.revenue) > 0 and sales_cash_ratio is not None and sales_cash_ratio < 0.8:
        risks.append(_risk_item("cash_flow", "销售收现率过低", "high", f"销售收现率={sales_cash_ratio:.2f}", "< 0.8"))

    other_recv_ratio = safe_div(_n(report.other_receivables), _n(report.total_assets))
    if other_recv_ratio is not None and other_recv_ratio > 0.1:
        risks.append(_risk_item("cash_flow", "其他应收款占比异常", "medium", f"占比={other_recv_ratio*100:.2f}%", "> 10%"))

    debt_ratio = safe_div(_n(report.total_liabilities), _n(report.total_assets))
    if debt_ratio is not None:
        if debt_ratio > 0.85:
            risks.append(_risk_item("safety", "资产负债率过高", "high", f"资产负债率={debt_ratio*100:.2f}%", "> 85%"))
        elif debt_ratio >= 0.7:
            risks.append(_risk_item("safety", "资产负债率偏高", "medium", f"资产负债率={debt_ratio*100:.2f}%", "70%-85%"))

    current_ratio = safe_div(_n(report.total_current_assets), _n(report.total_current_liabilities))
    if current_ratio is not None and current_ratio < 1:
        risks.append(_risk_item("safety", "流动比率过低", "high", f"流动比率={current_ratio:.2f}", "< 1"))

    interest_debt = _n(report.short_term_borrowings) + _n(report.long_term_borrowings) + _n(report.bonds_payable)
    cash_cover = safe_div(_n(report.cash_and_equivalents), interest_debt)
    if interest_debt > 0 and cash_cover is not None and cash_cover < 0.3:
        risks.append(_risk_item("safety", "货币资金不足覆盖有息负债", "high", f"覆盖率={cash_cover:.2f}", "< 0.3"))

    goodwill_ratio = safe_div(_n(report.goodwill), _n(report.total_equity_parent))
    if goodwill_ratio is not None and goodwill_ratio > 0.3:
        risks.append(_risk_item("safety", "商誉占净资产过高", "medium", f"商誉占比={goodwill_ratio*100:.2f}%", "> 30%"))

    interest_debt = _n(report.short_term_borrowings) + _n(report.long_term_borrowings) + _n(report.bonds_payable)
    cash_to_assets = safe_div(_n(report.cash_and_equivalents), _n(report.total_assets))
    debt_to_assets = safe_div(interest_debt, _n(report.total_assets))
    if (cash_to_assets or 0) > 0.2 and (debt_to_assets or 0) > 0.3:
        risks.append(_risk_item("safety", "存贷双高风险（货币资金与有息负债均高）", "high",
            f"货币资金/总资产={cash_to_assets*100:.2f}%，有息负债/总资产={debt_to_assets*100:.2f}%",
            "货币资金>20%且有利负债>30%"))

    if _n(report.interest_income) > 0 and _n(report.cash_and_equivalents) > 0:
        avg_cash = _n(report.cash_and_equivalents)
        if prev_report:
            avg_cash = (avg_cash + _n(prev_report.cash_and_equivalents)) / 2
        interest_rate = safe_div(_n(report.interest_income), avg_cash)
        if interest_rate is not None and interest_rate < 0.003:
            risks.append(_risk_item("safety", "利息收入/货币资金过低（资金可能虚构或被占用）", "critical",
                f"利率={interest_rate*100:.2f}%",
                "< 0.3%"))

    other_recv_to_assets = safe_div(_n(report.other_receivables), _n(report.total_assets))
    if other_recv_to_assets is not None and other_recv_to_assets > 0.05:
        risks.append(_risk_item("cash_flow", "其他应收款占比过高", "high", f"其他应收款/总资产={other_recv_to_assets*100:.2f}%", "> 5%"))

    other_pay_to_liab = safe_div(_n(report.other_payables), _n(report.total_liabilities))
    if other_pay_to_liab is not None and other_pay_to_liab > 0.1:
        risks.append(_risk_item("safety", "其他应付款占比过高", "high", f"其他应付款/总负债={other_pay_to_liab*100:.2f}%", "> 10%"))

    ltd_expenses_to_assets = safe_div(_n(report.long_term_deferred_expenses), _n(report.total_assets))
    if ltd_expenses_to_assets is not None and ltd_expenses_to_assets > 0.03:
        risks.append(_risk_item("expense", "长期待摊费用占比过高", "high", f"长期待摊费用/总资产={ltd_expenses_to_assets*100:.2f}%", "> 3%"))

    construction_to_fixed = safe_div(_n(report.construction_in_progress), _n(report.fixed_assets))
    if construction_to_fixed is not None and construction_to_fixed > 0.5:
        detail = f"在建/固定={construction_to_fixed*100:.2f}%"
        if prev_report and _n(prev_report.construction_in_progress) > 0 and _n(prev_report.fixed_assets) > 0:
            prev_ratio = safe_div(_n(prev_report.construction_in_progress), _n(prev_report.fixed_assets))
            if prev_ratio is not None and prev_ratio > 0.5:
                if abs(_n(report.fixed_assets) - _n(prev_report.fixed_assets)) < _n(report.fixed_assets) * 0.05:
                    detail += "，且连续两期在建工程高企但固定资产未显著增加（可能延迟转固）"
        risks.append(_risk_item("expense", "在建工程/固定资产过高", "medium", detail, "> 50%"))

    if prev_report:
        current_gm = safe_div(_n(report.revenue) - _n(report.cost_of_revenue), _n(report.revenue))
        prev_gm = safe_div(_n(prev_report.revenue) - _n(prev_report.cost_of_revenue), _n(prev_report.revenue))
        gm_change = (current_gm or 0) - (prev_gm or 0)
        inventory_cost_cur = safe_div(_n(report.inventory), _n(report.cost_of_revenue))
        inventory_cost_prev = safe_div(_n(prev_report.inventory), _n(prev_report.cost_of_revenue))
        inv_cost_change = _growth(_n(report.inventory) * _n(prev_report.cost_of_revenue),
                                  _n(prev_report.inventory) * _n(report.cost_of_revenue)) if _n(prev_report.inventory) > 0 and _n(report.cost_of_revenue) > 0 else None
        if gm_change > 0.05 and inv_cost_change is not None and inv_cost_change > 0.3:
            risks.append(_risk_item("revenue", "毛利率提升伴随存货积压（疑通过生产摊薄成本）", "medium",
                f"毛利率变化+{gm_change*100:.2f}pp，存货/成本变化+{inv_cost_change*100:.2f}%",
                "毛利率↑>5pp且存货↑>30%"))

    non_recurring_diff = abs(_n(report.net_profit) - _n(report.non_recurring_profit))
    non_recurring_impact = safe_div(non_recurring_diff, abs(_n(report.net_profit))) if _n(report.net_profit) != 0 else None
    if non_recurring_impact is not None and non_recurring_impact > 0.5:
        risks.append(_risk_item("revenue", "扣非净利润与净利润偏离过大（盈利质量差）", "high",
            f"非经常性损益占比={non_recurring_impact*100:.2f}%",
            "> 50%"))

    non_recurring_items = (_n(report.investment_income) + _n(report.fair_value_change_income)
                           + _n(report.other_income) + _n(report.asset_disposal_income))
    if _n(report.operating_profit) > 0 and non_recurring_items / _n(report.operating_profit) > 0.5:
        risks.append(_risk_item("revenue", "非经常性项目占营业利润超半（盈利质量偏弱）", "medium",
            f"非经常性/营业利润={non_recurring_items/_n(report.operating_profit)*100:.2f}%",
            "> 50%"))

    score = 100
    risk_count = {"high": 0, "medium": 0, "critical": 0}
    penalties = {"high": 15, "medium": 8, "critical": 25}
    for risk in risks:
        sev = risk["severity"]
        risk_count[sev] = risk_count.get(sev, 0) + 1
        score -= penalties.get(sev, 0)
    score = max(0, score)

    if score >= 80:
        level = "safe"
    elif score >= 50:
        level = "warning"
    else:
        level = "danger"

    return {
        "score": score,
        "level": level,
        "risks": risks,
        "risk_count": risk_count,
    }
