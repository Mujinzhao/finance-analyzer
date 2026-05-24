from __future__ import annotations

from models.database import Company, FinancialReport, SessionLocal, create_tables


def main():
    create_tables()
    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.name == "贵州茅台").first()
        if not company:
            company = Company(name="贵州茅台", industry="白酒", stock_code="600519")
            db.add(company)
            db.commit()
            db.refresh(company)

        base_data = {
            2019: {"revenue": 88.86e9, "net_profit": 46.47e9, "net_profit_parent": 46.47e9, "gross_margin": 0.914, "roe": 0.307},
            2020: {"revenue": 97.99e9, "net_profit": 51.60e9, "net_profit_parent": 51.60e9, "gross_margin": 0.915, "roe": 0.303},
            2021: {"revenue": 109.46e9, "net_profit": 57.70e9, "net_profit_parent": 57.70e9, "gross_margin": 0.916, "roe": 0.286},
            2022: {"revenue": 124.18e9, "net_profit": 65.50e9, "net_profit_parent": 65.50e9, "gross_margin": 0.918, "roe": 0.299},
            2023: {"revenue": 150.56e9, "net_profit": 81.00e9, "net_profit_parent": 81.00e9, "gross_margin": 0.920, "roe": 0.310},
        }

        for year, d in base_data.items():
            report = (
                db.query(FinancialReport)
                .filter(FinancialReport.company_id == company.id, FinancialReport.year == year, FinancialReport.quarter == 0)
                .first()
            )
            if not report:
                report = FinancialReport(company_id=company.id, year=year, quarter=0, report_type="annual")
                db.add(report)

            revenue = d["revenue"]
            gross_margin = d["gross_margin"]
            net_profit_parent = d["net_profit_parent"]
            report.revenue = revenue
            report.cost_of_revenue = revenue * (1 - gross_margin)
            report.net_profit = d["net_profit"]
            report.net_profit_parent = net_profit_parent
            report.operating_profit = revenue * 0.65
            report.total_assets = revenue * 2.8
            report.total_liabilities = report.total_assets * 0.45
            report.total_equity = report.total_assets - report.total_liabilities
            report.total_equity_parent = net_profit_parent / d["roe"]
            report.total_current_assets = report.total_assets * 0.55
            report.total_non_current_assets = report.total_assets * 0.45
            report.total_current_liabilities = report.total_liabilities * 0.7
            report.total_non_current_liabilities = report.total_liabilities * 0.3
            report.cash_and_equivalents = revenue * 0.4
            report.accounts_receivable = revenue * 0.03
            report.inventory = revenue * 0.06
            report.fixed_assets = report.total_assets * 0.12
            report.construction_in_progress = report.total_assets * 0.03
            report.intangible_assets = report.total_assets * 0.02
            report.goodwill = report.total_assets * 0.01
            report.short_term_borrowings = report.total_liabilities * 0.12
            report.long_term_borrowings = report.total_liabilities * 0.18
            report.bonds_payable = report.total_liabilities * 0.05
            report.selling_expenses = revenue * 0.03
            report.admin_expenses = revenue * 0.04
            report.rd_expenses = revenue * 0.01
            report.finance_expenses = revenue * 0.003
            report.total_profit = report.net_profit / 0.85
            report.income_tax_expense = report.total_profit - report.net_profit
            report.net_cash_from_operations = report.net_profit * 1.08
            report.net_cash_from_investing = -revenue * 0.12
            report.net_cash_from_financing = -revenue * 0.08
            report.cash_from_sales = revenue * 1.02
            report.cash_paid_for_assets = revenue * 0.1
            report.cash_at_end = report.cash_and_equivalents
            report.total_shares = 125620.0
            report.dividends_paid = report.net_profit_parent * 0.52

        db.commit()
        print("样例数据已生成: 贵州茅台 2019-2023")
    finally:
        db.close()


if __name__ == "__main__":
    main()
