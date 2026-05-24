from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
DB_DIR = BASE_DIR / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'finance.db'}"


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


BALANCE_FIELDS: Dict[str, str] = {
    "cash_and_equivalents": "货币资金",
    "trading_financial_assets": "交易性金融资产",
    "notes_receivable": "应收票据",
    "accounts_receivable": "应收账款",
    "prepayments": "预付款项",
    "other_receivables": "其他应收款",
    "inventory": "存货",
    "other_current_assets": "其他流动资产",
    "contract_assets": "合同资产",
    "total_current_assets": "流动资产合计",
    "available_for_sale_assets": "可供出售金融资产/其他权益工具投资",
    "held_to_maturity": "持有至到期投资/其他债权投资",
    "investment_property": "投资性房地产",
    "right_of_use_assets": "使用权资产",
    "long_term_equity_investment": "长期股权投资",
    "fixed_assets": "固定资产",
    "construction_in_progress": "在建工程",
    "intangible_assets": "无形资产",
    "goodwill": "商誉",
    "long_term_deferred_expenses": "长期待摊费用",
    "deferred_tax_assets": "递延所得税资产",
    "other_non_current_assets": "其他非流动资产",
    "total_non_current_assets": "非流动资产合计",
    "total_assets": "资产总计",
    "short_term_borrowings": "短期借款",
    "notes_payable": "应付票据",
    "accounts_payable": "应付账款",
    "advance_receipts": "预收款项/合同负债",
    "employee_compensation_payable": "应付职工薪酬",
    "taxes_payable": "应交税费",
    "other_current_liabilities": "其他流动负债",
    "non_current_liabilities_due_within_one_year": "一年内到期的非流动负债",
    "other_payables": "其他应付款",
    "total_current_liabilities": "流动负债合计",
    "long_term_borrowings": "长期借款",
    "bonds_payable": "应付债券",
    "deferred_tax_liabilities": "递延所得税负债",
    "other_non_current_liabilities": "其他非流动负债",
    "long_term_payables": "长期应付款",
    "lease_liabilities": "租赁负债",
    "deferred_income": "递延收益",
    "total_non_current_liabilities": "非流动负债合计",
    "total_liabilities": "负债合计",
    "paid_in_capital": "实收资本/股本",
    "capital_reserve": "资本公积",
    "surplus_reserve": "盈余公积",
    "undistributed_profit": "未分配利润",
    "total_equity_parent": "归属于母公司所有者权益合计",
    "other_comprehensive_income": "其他综合收益",
    "minority_interest": "少数股东权益",
    "total_equity": "所有者权益合计",
}

INCOME_FIELDS: Dict[str, str] = {
    "revenue": "营业收入",
    "cost_of_revenue": "营业成本",
    "taxes_and_surcharges": "税金及附加",
    "selling_expenses": "销售费用",
    "admin_expenses": "管理费用",
    "rd_expenses": "研发费用",
    "finance_expenses": "财务费用",
    "interest_expense": "利息费用",
    "interest_income": "利息收入",
    "asset_impairment_loss": "资产减值损失",
    "credit_impairment_loss": "信用减值损失",
    "other_income": "其他收益",
    "investment_income": "投资收益",
    "fair_value_change_income": "公允价值变动收益",
    "asset_disposal_income": "资产处置收益",
    "operating_profit": "营业利润",
    "non_operating_income": "营业外收入",
    "non_operating_expenses": "营业外支出",
    "total_profit": "利润总额",
    "income_tax_expense": "所得税费用",
    "net_profit": "净利润",
    "net_profit_parent": "归属于母公司股东的净利润",
    "non_recurring_profit": "扣非净利润",
    "net_profit_minority": "少数股东损益",
    "total_shares": "总股本（万股）",
    "dividends_paid": "分红总额",
}

CASH_FLOW_FIELDS: Dict[str, str] = {
    "cash_from_sales": "销售商品、提供劳务收到的现金",
    "tax_refunds": "收到的税费返还",
    "other_cash_from_operations": "收到其他与经营活动有关的现金",
    "total_cash_from_operations": "经营活动现金流入小计",
    "cash_paid_for_goods": "购买商品、接受劳务支付的现金",
    "cash_paid_to_employees": "支付给职工以及为职工支付的现金",
    "taxes_paid": "支付的各项税费",
    "other_cash_paid_for_operations": "支付其他与经营活动有关的现金",
    "total_cash_paid_for_operations": "经营活动现金流出小计",
    "net_cash_from_operations": "经营活动产生的现金流量净额",
    "cash_from_investment_withdrawal": "收回投资收到的现金",
    "cash_from_investment_income": "取得投资收益收到的现金",
    "cash_from_asset_disposal": "处置固定资产等收到的现金净额",
    "other_cash_from_investing": "收到其他与投资活动有关的现金",
    "total_cash_from_investing": "投资活动现金流入小计",
    "cash_paid_for_assets": "购建固定资产、无形资产等支付的现金",
    "cash_paid_for_investments": "投资支付的现金",
    "other_cash_paid_for_investing": "支付其他与投资活动有关的现金",
    "total_cash_paid_for_investing": "投资活动现金流出小计",
    "net_cash_from_investing": "投资活动产生的现金流量净额",
    "cash_from_borrowings": "取得借款收到的现金",
    "cash_from_equity_issuance": "吸收投资收到的现金",
    "other_cash_from_financing": "收到其他与筹资活动有关的现金",
    "total_cash_from_financing": "筹资活动现金流入小计",
    "cash_paid_for_debt": "偿还债务支付的现金",
    "cash_paid_for_dividends": "分配股利、利润或偿付利息支付的现金",
    "other_cash_paid_for_financing": "支付其他与筹资活动有关的现金",
    "total_cash_paid_for_financing": "筹资活动现金流出小计",
    "net_cash_from_financing": "筹资活动产生的现金流量净额",
    "net_increase_in_cash": "现金及现金等价物净增加额",
    "cash_at_beginning": "期初现金及现金等价物余额",
    "cash_at_end": "期末现金及现金等价物余额",
}

ALL_FINANCIAL_FIELDS: List[str] = list(BALANCE_FIELDS.keys()) + list(INCOME_FIELDS.keys()) + list(CASH_FLOW_FIELDS.keys())

INCOME_POINT_IN_TIME_FIELDS: set = {"total_shares"}


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stock_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    reports: Mapped[List[FinancialReport]] = relationship("FinancialReport", back_populates="company", cascade="all, delete-orphan")


class FinancialReport(Base):
    __tablename__ = "financial_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quarter: Mapped[int] = mapped_column(Integer, default=0)
    report_type: Mapped[str] = mapped_column(String(20), default="annual")
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cash_and_equivalents: Mapped[float] = mapped_column(Float, default=0.0)
    trading_financial_assets: Mapped[float] = mapped_column(Float, default=0.0)
    notes_receivable: Mapped[float] = mapped_column(Float, default=0.0)
    accounts_receivable: Mapped[float] = mapped_column(Float, default=0.0)
    prepayments: Mapped[float] = mapped_column(Float, default=0.0)
    other_receivables: Mapped[float] = mapped_column(Float, default=0.0)
    inventory: Mapped[float] = mapped_column(Float, default=0.0)
    other_current_assets: Mapped[float] = mapped_column(Float, default=0.0)
    contract_assets: Mapped[float] = mapped_column(Float, default=0.0)
    total_current_assets: Mapped[float] = mapped_column(Float, default=0.0)
    available_for_sale_assets: Mapped[float] = mapped_column(Float, default=0.0)
    held_to_maturity: Mapped[float] = mapped_column(Float, default=0.0)
    investment_property: Mapped[float] = mapped_column(Float, default=0.0)
    right_of_use_assets: Mapped[float] = mapped_column(Float, default=0.0)
    long_term_equity_investment: Mapped[float] = mapped_column(Float, default=0.0)
    fixed_assets: Mapped[float] = mapped_column(Float, default=0.0)
    construction_in_progress: Mapped[float] = mapped_column(Float, default=0.0)
    intangible_assets: Mapped[float] = mapped_column(Float, default=0.0)
    goodwill: Mapped[float] = mapped_column(Float, default=0.0)
    long_term_deferred_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    deferred_tax_assets: Mapped[float] = mapped_column(Float, default=0.0)
    other_non_current_assets: Mapped[float] = mapped_column(Float, default=0.0)
    total_non_current_assets: Mapped[float] = mapped_column(Float, default=0.0)
    total_assets: Mapped[float] = mapped_column(Float, default=0.0)
    short_term_borrowings: Mapped[float] = mapped_column(Float, default=0.0)
    notes_payable: Mapped[float] = mapped_column(Float, default=0.0)
    accounts_payable: Mapped[float] = mapped_column(Float, default=0.0)
    advance_receipts: Mapped[float] = mapped_column(Float, default=0.0)
    employee_compensation_payable: Mapped[float] = mapped_column(Float, default=0.0)
    taxes_payable: Mapped[float] = mapped_column(Float, default=0.0)
    other_current_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    non_current_liabilities_due_within_one_year: Mapped[float] = mapped_column(Float, default=0.0)
    other_payables: Mapped[float] = mapped_column(Float, default=0.0)
    total_current_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    long_term_borrowings: Mapped[float] = mapped_column(Float, default=0.0)
    bonds_payable: Mapped[float] = mapped_column(Float, default=0.0)
    deferred_tax_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    other_non_current_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    long_term_payables: Mapped[float] = mapped_column(Float, default=0.0)
    lease_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    deferred_income: Mapped[float] = mapped_column(Float, default=0.0)
    total_non_current_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    total_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    paid_in_capital: Mapped[float] = mapped_column(Float, default=0.0)
    capital_reserve: Mapped[float] = mapped_column(Float, default=0.0)
    surplus_reserve: Mapped[float] = mapped_column(Float, default=0.0)
    undistributed_profit: Mapped[float] = mapped_column(Float, default=0.0)
    total_equity_parent: Mapped[float] = mapped_column(Float, default=0.0)
    other_comprehensive_income: Mapped[float] = mapped_column(Float, default=0.0)
    minority_interest: Mapped[float] = mapped_column(Float, default=0.0)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)

    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    cost_of_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    taxes_and_surcharges: Mapped[float] = mapped_column(Float, default=0.0)
    selling_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    admin_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    rd_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    finance_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    interest_expense: Mapped[float] = mapped_column(Float, default=0.0)
    interest_income: Mapped[float] = mapped_column(Float, default=0.0)
    asset_impairment_loss: Mapped[float] = mapped_column(Float, default=0.0)
    credit_impairment_loss: Mapped[float] = mapped_column(Float, default=0.0)
    other_income: Mapped[float] = mapped_column(Float, default=0.0)
    investment_income: Mapped[float] = mapped_column(Float, default=0.0)
    fair_value_change_income: Mapped[float] = mapped_column(Float, default=0.0)
    asset_disposal_income: Mapped[float] = mapped_column(Float, default=0.0)
    operating_profit: Mapped[float] = mapped_column(Float, default=0.0)
    non_operating_income: Mapped[float] = mapped_column(Float, default=0.0)
    non_operating_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    total_profit: Mapped[float] = mapped_column(Float, default=0.0)
    income_tax_expense: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit_parent: Mapped[float] = mapped_column(Float, default=0.0)
    non_recurring_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit_minority: Mapped[float] = mapped_column(Float, default=0.0)
    total_shares: Mapped[float] = mapped_column(Float, default=0.0)
    dividends_paid: Mapped[float] = mapped_column(Float, default=0.0)

    cash_from_sales: Mapped[float] = mapped_column(Float, default=0.0)
    tax_refunds: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_from_operations: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_from_operations: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_for_goods: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_to_employees: Mapped[float] = mapped_column(Float, default=0.0)
    taxes_paid: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_paid_for_operations: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_paid_for_operations: Mapped[float] = mapped_column(Float, default=0.0)
    net_cash_from_operations: Mapped[float] = mapped_column(Float, default=0.0)
    cash_from_investment_withdrawal: Mapped[float] = mapped_column(Float, default=0.0)
    cash_from_investment_income: Mapped[float] = mapped_column(Float, default=0.0)
    cash_from_asset_disposal: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_from_investing: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_from_investing: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_for_assets: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_for_investments: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_paid_for_investing: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_paid_for_investing: Mapped[float] = mapped_column(Float, default=0.0)
    net_cash_from_investing: Mapped[float] = mapped_column(Float, default=0.0)
    cash_from_borrowings: Mapped[float] = mapped_column(Float, default=0.0)
    cash_from_equity_issuance: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_from_financing: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_from_financing: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_for_debt: Mapped[float] = mapped_column(Float, default=0.0)
    cash_paid_for_dividends: Mapped[float] = mapped_column(Float, default=0.0)
    other_cash_paid_for_financing: Mapped[float] = mapped_column(Float, default=0.0)
    total_cash_paid_for_financing: Mapped[float] = mapped_column(Float, default=0.0)
    net_cash_from_financing: Mapped[float] = mapped_column(Float, default=0.0)
    net_increase_in_cash: Mapped[float] = mapped_column(Float, default=0.0)
    cash_at_beginning: Mapped[float] = mapped_column(Float, default=0.0)
    cash_at_end: Mapped[float] = mapped_column(Float, default=0.0)

    company: Mapped[Company] = relationship("Company", back_populates="reports")


class AISummary(Base):
    __tablename__ = "ai_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quarter: Mapped[int] = mapped_column(Integer, default=0)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Add new columns to financial_reports if they don't exist."""
    import sqlite3
    conn = sqlite3.connect(str(DB_DIR / "finance.db"))
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(financial_reports)")}
        new_columns = [
            ("interest_expense", "FLOAT DEFAULT 0.0"),
            ("interest_income", "FLOAT DEFAULT 0.0"),
            ("long_term_deferred_expenses", "FLOAT DEFAULT 0.0"),
            ("investment_property", "FLOAT DEFAULT 0.0"),
            ("right_of_use_assets", "FLOAT DEFAULT 0.0"),
            ("contract_assets", "FLOAT DEFAULT 0.0"),
            ("non_current_liabilities_due_within_one_year", "FLOAT DEFAULT 0.0"),
            ("other_payables", "FLOAT DEFAULT 0.0"),
            ("long_term_payables", "FLOAT DEFAULT 0.0"),
            ("lease_liabilities", "FLOAT DEFAULT 0.0"),
            ("deferred_income", "FLOAT DEFAULT 0.0"),
            ("other_comprehensive_income", "FLOAT DEFAULT 0.0"),
            ("non_recurring_profit", "FLOAT DEFAULT 0.0"),
        ]
        for col_name, col_def in new_columns:
            if col_name not in existing:
                conn.execute(f"ALTER TABLE financial_reports ADD COLUMN {col_name} {col_def}")
        conn.commit()
    finally:
        conn.close()


def report_to_dict(report: FinancialReport) -> Dict[str, float]:
    data: Dict[str, float] = {}
    for field in ALL_FINANCIAL_FIELDS:
        data[field] = float(getattr(report, field, 0.0) or 0.0)
    return data
