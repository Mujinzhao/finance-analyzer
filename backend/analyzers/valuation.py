from __future__ import annotations

from typing import Dict, Optional


def dcf_simple(
    free_cash_flow_year3: float,
    discount_rate: float = 0.09,
    perpetual_growth: float = 0.03,
    current_price: float | None = None,
    total_shares: float | None = None,
    forecast_growth: float | None = None,
    forecast_years: int = 5,
) -> Dict:
    discount_rate = discount_rate or 0.09
    perpetual_growth = min(perpetual_growth, discount_rate - 0.01)

    growth = forecast_growth or max(perpetual_growth * 2, 0.05)

    pv_explicit = 0.0
    fcf = free_cash_flow_year3 * (1 + growth)
    for i in range(1, forecast_years + 1):
        pv_explicit += fcf / ((1 + discount_rate) ** i)
        fcf *= (1 + growth)

    fcf_terminal = fcf / (1 + growth)
    terminal_value = fcf_terminal * (1 + perpetual_growth) / (discount_rate - perpetual_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** forecast_years)

    enterprise_value = pv_explicit + pv_terminal
    reasonable_pe = 1 / discount_rate
    quick_fair_value = free_cash_flow_year3 * reasonable_pe

    result = {
        "enterprise_value": round(enterprise_value, 2),
        "pv_forecast_period": round(pv_explicit, 2),
        "pv_terminal_value": round(pv_terminal, 2),
        "quick_fair_value": round(quick_fair_value, 2),
        "discount_rate": discount_rate,
        "perpetual_growth": perpetual_growth,
        "forecast_growth": growth,
        "forecast_years": forecast_years,
    }

    if total_shares and total_shares > 0:
        shares = total_shares * 10000
        fair_price = enterprise_value / shares
        quick_price = quick_fair_value / shares
        buy_price = fair_price * 0.5
        sell_price = fair_price * 1.5

        result.update({
            "fair_price_per_share": round(fair_price, 4),
            "quick_price_per_share": round(quick_price, 4),
            "buy_price_per_share": round(buy_price, 4),
            "sell_price_per_share": round(sell_price, 4),
        })

        if current_price is not None:
            if sell_price > buy_price:
                temperature = max(0.0, min(100.0, (current_price - buy_price) / (sell_price - buy_price) * 100))
            else:
                temperature = None
            advice = "合理区间"
            if current_price <= buy_price:
                advice = "严重低估"
            elif current_price <= fair_price:
                advice = "低估区间"
            elif current_price > sell_price:
                advice = "高估"

            result.update({
                "current_price": current_price,
                "temperature": round(temperature, 2) if temperature is not None else None,
                "advice": advice,
            })

    return result


def relative_valuation(report) -> Dict[str, Optional[float]]:
    shares = float(report.total_shares or 0.0) * 10000
    if shares <= 0:
        return {"eps": None, "bvps": None, "sps": None}
    return {
        "eps": round(float(report.net_profit_parent or 0.0) / shares, 6),
        "bvps": round(float(report.total_equity_parent or 0.0) / shares, 6),
        "sps": round(float(report.revenue or 0.0) / shares, 6),
    }


def economic_goodwill(roe: float, equity: float, market_avg_return: float = 0.09) -> float:
    if market_avg_return == 0:
        return 0.0
    return (roe / market_avg_return - 1) * equity
