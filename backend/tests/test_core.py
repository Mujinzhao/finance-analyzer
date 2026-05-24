from fastapi.testclient import TestClient
from pathlib import Path

from main import app
from models.database import FinancialReport, SessionLocal
from parsers.excel_parser import INCOME_STATEMENT_MAP
from parsers.pdf_parser import PDFParser


client = TestClient(app)


class _FakePage:
    def __init__(self, text: str):
        self.text = text

    def get_text(self, *_args):
        return self.text


class _FakeDoc:
    def __init__(self, pages):
        self.pages = [_FakePage(text) for text in pages]

    def __len__(self):
        return len(self.pages)

    def __getitem__(self, index):
        return self.pages[index]


def _seed_report(company_id: int, year: int, quarter: int = 0):
    db = SessionLocal()
    try:
        report = FinancialReport(
            company_id=company_id,
            year=year,
            quarter=quarter,
            report_type='annual' if quarter == 0 else 'quarterly',
            revenue=100000000,
            cost_of_revenue=40000000,
            net_profit=20000000,
            net_profit_parent=19000000,
            operating_profit=26000000,
            total_assets=300000000,
            total_liabilities=120000000,
            total_equity=180000000,
            total_equity_parent=160000000,
            total_current_assets=150000000,
            total_non_current_assets=150000000,
            total_current_liabilities=80000000,
            total_non_current_liabilities=40000000,
            cash_and_equivalents=80000000,
            accounts_receivable=10000000,
            inventory=12000000,
            fixed_assets=50000000,
            construction_in_progress=10000000,
            intangible_assets=6000000,
            short_term_borrowings=10000000,
            long_term_borrowings=20000000,
            bonds_payable=5000000,
            selling_expenses=5000000,
            admin_expenses=6000000,
            rd_expenses=4000000,
            finance_expenses=1000000,
            total_profit=25000000,
            income_tax_expense=5000000,
            net_cash_from_operations=22000000,
            net_cash_from_investing=-12000000,
            net_cash_from_financing=-8000000,
            cash_from_sales=98000000,
            cash_paid_for_assets=9000000,
            cash_at_end=85000000,
            total_shares=100000,
            dividends_paid=10000000,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report.id
    finally:
        db.close()


def test_company_and_analysis_flow():
    company = client.post('/api/companies', json={'name': '测试公司', 'industry': '测试', 'stock_code': '000001'}).json()
    cid = company['id']

    _seed_report(cid, 2022)
    _seed_report(cid, 2023)

    resp = client.get(f'/api/analysis/{cid}?year=2023')
    assert resp.status_code == 200
    payload = resp.json()
    assert 'analysis' in payload
    assert 'growth' in payload
    assert 'financial_quality' in payload
    assert 'risks' in payload
    assert 'valuation' in payload
    assert 'revenue_growth' in payload['growth']
    assert 'total_score' in payload['financial_quality']

    trend = client.get(f'/api/trend/{cid}')
    assert trend.status_code == 200
    assert 'trend' in trend.json()

    dcf = client.post('/api/valuation/dcf', json={'free_cash_flow_year3': 100000000, 'total_shares': 100000, 'current_price': 1200})
    assert dcf.status_code == 200
    assert 'fair_value' in dcf.json()

    ai = client.get(f'/api/ai-summary/{cid}?year=2023')
    assert ai.status_code == 200
    assert 'summary' in ai.json()

    delete_resp = client.delete(f'/api/companies/{cid}')
    assert delete_resp.status_code == 200


def test_trend_period_order_places_annual_after_q3():
    company = client.post('/api/companies', json={'name': '趋势排序测试', 'industry': '测试', 'stock_code': '000004'}).json()
    cid = company['id']

    _seed_report(cid, 2025, quarter=0)
    _seed_report(cid, 2025, quarter=1)
    _seed_report(cid, 2025, quarter=2)
    _seed_report(cid, 2025, quarter=3)

    trend_resp = client.get(f'/api/trend/{cid}')
    assert trend_resp.status_code == 200
    trend_payload = trend_resp.json()

    assert trend_payload['periods'] == [
        {'year': 2025, 'quarter': 1},
        {'year': 2025, 'quarter': 2},
        {'year': 2025, 'quarter': 3},
        {'year': 2025, 'quarter': 0},
    ]
    assert trend_payload['trend']['periods'] == ['2025Q1', '2025Q2', '2025Q3', '2025']

    delete_resp = client.delete(f'/api/companies/{cid}')
    assert delete_resp.status_code == 200


def test_delete_single_report_and_delete_year_reports(tmp_path: Path):
    company = client.post('/api/companies', json={'name': '删除测试公司', 'industry': '测试', 'stock_code': '000003'}).json()
    cid = company['id']

    report_q1_id = _seed_report(cid, 2025, quarter=1)
    _seed_report(cid, 2025, quarter=2)
    _seed_report(cid, 2024, quarter=0)

    db = SessionLocal()
    try:
        report_q1 = db.get(FinancialReport, report_q1_id)
        assert report_q1 is not None
        temp_file = tmp_path / '2025q1.xlsx'
        temp_file.write_text('placeholder', encoding='utf-8')
        report_q1.file_path = str(temp_file)
        db.commit()
    finally:
        db.close()

    del_one = client.delete(f'/api/reports/{report_q1_id}')
    assert del_one.status_code == 200
    assert del_one.json()['deleted']['report_id'] == report_q1_id
    assert not temp_file.exists()

    del_year = client.delete(f'/api/companies/{cid}/reports?year=2025')
    assert del_year.status_code == 200
    assert del_year.json()['deleted_count'] == 1

    db = SessionLocal()
    try:
        remain_2025 = (
            db.query(FinancialReport)
            .filter(FinancialReport.company_id == cid, FinancialReport.year == 2025)
            .count()
        )
        remain_2024 = (
            db.query(FinancialReport)
            .filter(FinancialReport.company_id == cid, FinancialReport.year == 2024)
            .count()
        )
        assert remain_2025 == 0
        assert remain_2024 == 1
    finally:
        db.close()

    delete_resp = client.delete(f'/api/companies/{cid}')
    assert delete_resp.status_code == 200


def test_extraction_compare_output(monkeypatch, tmp_path: Path):
    company = client.post('/api/companies', json={'name': '对照测试公司', 'industry': '测试', 'stock_code': '000002'}).json()
    cid = company['id']

    _seed_report(cid, 2024)

    db = SessionLocal()
    try:
        report = (
            db.query(FinancialReport)
            .filter(FinancialReport.company_id == cid, FinancialReport.year == 2024, FinancialReport.quarter == 0)
            .first()
        )
        assert report is not None

        fake_source = tmp_path / 'source.xlsx'
        fake_source.write_text('placeholder', encoding='utf-8')
        report.file_path = str(fake_source)
        db.commit()
        report_id = report.id
    finally:
        db.close()

    def _fake_parse_excel(file_path, company_id, year, quarter):
        return {
            'company_id': company_id,
            'year': year,
            'quarter': quarter,
            'report_type': 'annual',
            'revenue': 80000000,
            'net_profit': 18000000,
            'cash_at_end': 83000000,
        }

    monkeypatch.setattr('main.parse_excel', _fake_parse_excel)

    resp = client.get(f'/api/reports/{report_id}/extraction-compare?top_n=50')
    assert resp.status_code == 200
    payload = resp.json()

    assert payload['summary']['total_compared_fields'] > 0
    assert payload['summary']['mismatch_count'] >= 1
    assert len(payload['top_deviations']) >= 1
    assert any(item['field'] == 'revenue' for item in payload['top_deviations'])

    delete_resp = client.delete(f'/api/companies/{cid}')
    assert delete_resp.status_code == 200


def test_pdf_parser_scores_consolidated_pages_above_parent_pages():
    parser = PDFParser()
    parent_text = '母公司资产负债表 单位：万元 资产总计 10,000.00 负债合计 4,000.00 所有者权益合计 6,000.00'
    consolidated_text = '合并资产负债表 单位：万元 资产总计 10,000.00 负债合计 4,000.00 所有者权益合计 6,000.00'

    assert parser._score_statement_page('balance_sheet', consolidated_text) > parser._score_statement_page('balance_sheet', parent_text)


def test_pdf_heuristic_extract_handles_unit_and_note_numbers():
    parser = PDFParser()
    parser.enabled = False
    doc = _FakeDoc([
        '''
        合并资产负债表
        单位：万元
        货币资金 七、1 1,200.50 900.00
        资产总计 十七、2 10,000.00 8,000.00
        负债合计 4,000.00 3,000.00
        所有者权益合计 6,000.00 5,000.00
        '''
    ])

    result = parser._extract_statement_data(doc, [1], {
        '货币资金': 'cash_and_equivalents',
        '资产总计': 'total_assets',
        '负债合计': 'total_liabilities',
        '所有者权益合计': 'total_equity',
    })

    assert result['cash_and_equivalents'] == 12005000
    assert result['total_assets'] == 100000000
    assert result['total_liabilities'] == 40000000
    assert result['total_equity'] == 60000000


def test_pdf_ai_extraction_is_chunked(monkeypatch):
    parser = PDFParser()
    parser.enabled = True
    doc = _FakeDoc(['合并利润表 单位：万元 营业收入 100.00 营业成本 40.00 净利润 20.00'])
    calls = []
    responses = iter([
        '{"营业收入":"100万元","营业成本":"40万元"}',
        '{"净利润":"20万元"}',
    ])

    def fake_chat(prompt, max_tokens):
        calls.append((prompt, max_tokens))
        return next(responses)

    monkeypatch.setattr(parser, '_chat_completion', fake_chat)
    result = parser._extract_statement_data(doc, [1], INCOME_STATEMENT_MAP)

    assert len(calls) == 2
    assert result['revenue'] == 1000000
    assert result['cost_of_revenue'] == 400000
    assert result['net_profit'] == 200000
