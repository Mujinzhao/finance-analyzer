from __future__ import annotations

import json
import httpx

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL


SYSTEM_PROMPT = (
    "你是一位资深中国A股财务分析师，擅长撰写深度投资研究报告。"
    "你的分析风格严格遵循《手把手教你读财报(新准则升级版)》的方法论，核心分析框架包括：\n"
    "1. 现金流肖像分析：通过经营/投资/筹资三大现金流正负组合判断企业所处阶段（蛮牛型/奶牛型/妖精型等）\n"
    "2. 存贷双高排查：货币资金和有息负债同时很高是财务造假的典型信号，需关注利息收入/货币资金比例是否过低(<0.3%)\n"
    "3. 毛利率异常：毛利率异常高(>80%)或大幅波动(>10pp)需分析原因，毛利率提升伴随存货激增可能通过生产摊薄成本\n"
    "4. 非经常性损益分析：区分经常性利润与非经常性利润，投资/公允价值变动/其他收益/资产处置占营业利润比例过高说明盈利质量偏弱\n"
    "5. 资产结构分析：按生产类/经营类/投资类三种资产分类，分析企业模式是重资产还是轻资产\n"
    "6. 上下游议价能力：(应付+预收)/(应收+预付)比例 >1 说明占用上下游资金\n"
    "7. 现金转换周期：应收天数+存货天数-应付天数，越短越好\n"
    "8. 利息保障倍数：EBIT/利息支出，衡量偿债安全性\n"
    "9. 在建工程异常：在建工程/固定资产过高且长期不转固可能是延迟计提折旧\n"
    "10. 扣非净利润偏离：|净利润-扣非净利润|/|净利润| >50%表示盈利质量很差\n"
    "请用专业但易懂的中文撰写分析报告，必须引用具体数据，明确指出风险信号。"
)


def _fallback_summary(company_name, period, analysis, risks, valuation, trend=None) -> str:
    p = analysis.get("profitability", {})
    aq = analysis.get("asset_quality", {})
    cash = analysis.get("cash_flow", {})
    safety = analysis.get("safety", {})
    asset = analysis.get("asset_structure", {})
    ps = analysis.get("profit_structure", {})
    risk_level = risks.get("level", "unknown")
    risk_score = risks.get("score", 0)
    risk_count = risks.get("risk_count", {})
    portrait = cash.get("portrait", {})

    lines = ["## 企业概况总结",
             f"{company_name} 在 {period} 的财务表现分析如下。风险评级 {risk_level}（{risk_score}分），"
             f"共检测高风险{risk_count.get('high', 0)}项、中风险{risk_count.get('medium', 0)}项、严重风险{risk_count.get('critical', 0)}项。",
             f"现金流画像：{portrait.get('type', '-')} {portrait.get('emoji', '')} — {portrait.get('desc', '')}。",
             "",
             "## 盈利能力分析",
             f"ROE={p.get('roe')}%，毛利率={p.get('gross_margin')}%，净利率={p.get('net_margin')}%，"
             f"营业利润率={p.get('operating_margin')}%。ROIC={p.get('roic')}%，ROA={p.get('roa')}%。",
             f"EBIT={p.get('ebit')}，利息保障倍数={safety.get('interest_coverage')}。",
             f"非经常性收益占营业利润={ps.get('non_recurring_ratio', '-')}%，"
             f"扣非净利润偏离度={p.get('non_recurring_impact', '-')}%。",
             "",
             "## 资产质量评估",
             f"生产类/投资类/经营类资产占比：{asset.get('production_assets_ratio')}%/{asset.get('investment_assets_ratio')}%/{asset.get('operating_assets_ratio')}%。",
             f"应收/营收={aq.get('receivable_to_revenue')}%，存货/营收={aq.get('inventory_to_revenue')}%，商誉/净资产={aq.get('goodwill_to_equity')}%。",
             f"在建工程/固定资产={aq.get('construction_to_fixed')}%，重资产率={aq.get('heavy_asset_ratio')}%。",
             f"上下游议价能力={asset.get('bargaining_power', '-')}（>1为优），利息收入/货币资金={p.get('interest_income_to_avg_cash')}%。",
             "",
             "## 现金流健康度",
             f"自由现金流={cash.get('free_cash_flow')}，经营现金流/净利润={cash.get('ocf_to_net_profit')}。",
             f"销售收现/营收={cash.get('sales_cash_to_revenue')}，经营现金流率={cash.get('ocf_margin')}%。",
             f"资本开支/经营现金流={cash.get('capex_to_ocf')}，分红率={cash.get('dividend_payout_ratio')}%。",
             "",
             "## 风险提示"]
    for risk in risks.get("risks", [])[:8]:
        lines.append(f"- [{risk.get('severity', '-')}] {risk.get('name', '')}: {risk.get('detail', '')}（{risk.get('threshold', '')}）")
    if len(risks.get("risks", [])) > 8:
        lines.append(f"- ...共{len(risks.get('risks', []))}条风险")
    if not risks.get("risks"):
        lines.append("未检测到明显风险信号。")

    lines.extend(["",
                  "## 投资建议",
                  "综上分析，投资决策应以企业长期现金创造能力为核心，结合估值区间分批操作。"
                  "若估值温度处于低位且基本面未恶化，可考虑逐步配置；若风险信号密集，建议等待明确改善后再决策。"])

    return "\n".join(lines)


def generate_ai_summary(company_name, period, analysis, risks, valuation, trend=None) -> str:
    if not DEEPSEEK_API_KEY:
        return _fallback_summary(company_name, period, analysis, risks, valuation, trend)

    payload = {
        "company_name": company_name,
        "period": period,
        "analysis": analysis,
        "risks": risks,
        "valuation": valuation,
        "trend": trend,
    }

    user_prompt = (
        "请基于以下JSON数据输出Markdown格式分析报告，长度1500-2000字，严格包含6个章节标题：\n"
        "## 企业概况总结\n"
        "## 盈利能力分析\n"
        "## 资产质量评估\n"
        "## 现金流健康度\n"
        "## 风险提示\n"
        "## 投资建议\n\n"
        "分析要点（必须覆盖）：\n"
        "- 引用具体指标数值（ROE、毛利率、净利率、资产负债率等）\n"
        "- 分析现金流肖像（经营/投资/筹资三大现金流组合含义）\n"
        "- 检查存贷双高信号：货币资金/总资产>20%且有息负债/总资产>30%需重点预警\n"
        "- 检查利息收入/货币资金比例，若<0.3%说明资金可能被占用或虚构\n"
        "- 分析营业利润结构：非经常性项目（投资+公允价值+其他收益+资产处置）占营业利润比例\n"
        "- 分析上下游议价能力：(应付+预收)/(应收+预付)比例\n"
        "- 若扣非净利润与净利润偏离>50%，需明确提示盈利质量差\n"
        "- 若毛利率与存货联动异常（毛利率↑>5pp且存货↑>30%），提示可能通过生产摊薄成本\n"
        "- 检查在建工程/固定资产是否过高，是否存在延迟转固嫌疑\n"
        "- 比较归母ROE与少数股东ROE差异，判断利益倾斜\n"
        "- 结合趋势数据分析指标变化方向\n"
        "- 给出明确的估值参考和投资建议\n\n"
        "不要输出JSON。\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )

    try:
        endpoint = f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions"
        response = httpx.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEEPSEEK_MODEL,
                "max_tokens": 4096,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=90.0,
        )
        response.raise_for_status()
        data = response.json()
        summary = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
    except Exception:
        summary = ""

    if not summary:
        return _fallback_summary(company_name, period, analysis, risks, valuation, trend)
    return summary
