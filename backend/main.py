from __future__ import annotations

import logging
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from analyzers.ai_summary import generate_ai_summary
from analyzers.quarter_deriver import (
    derive_all_single_quarter_reports,
    derive_for_analysis,
    get_prev_annual_report,
)
from analyzers.ratio_analyzer import analyze_multi_period, analyze_single_report, period_days_for_report
from analyzers.risk_detector import detect_risks
from analyzers.valuation import dcf_simple, economic_goodwill, relative_valuation
from models.database import (
    AISummary,
    ALL_FINANCIAL_FIELDS,
    BALANCE_FIELDS,
    CASH_FLOW_FIELDS,
    INCOME_FIELDS,
    Company,
    FinancialReport,
    SessionLocal,
    create_tables,
)
from parsers.excel_parser import generate_template, parse_excel
from parsers.pdf_parser import parse_pdf
from scrapers import scrape_company

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATE_DIR = BASE_DIR / "templates"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_scrape_log_path = LOG_DIR / "scrape.log"

logger = logging.getLogger("finance_analyzer")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(_scrape_log_path, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())  # also print to console

create_tables()

app = FastAPI(title="财报全景分析平台 API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CompanyCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    stock_code: Optional[str] = None


class ReportUpdate(BaseModel):
    fields: Dict[str, float]


class DCFRequest(BaseModel):
    free_cash_flow_year3: float
    discount_rate: float = 0.09
    perpetual_growth: float = 0.03
    current_price: Optional[float] = None
    total_shares: Optional[float] = None
    forecast_growth: Optional[float] = None
    forecast_years: int = 5


class CompareQuery(BaseModel):
    company_ids: List[int] = Field(default_factory=list)
    year: int


def _clear_ai_cache(db: Session, company_id: int, year: Optional[int] = None, quarter: Optional[int] = None) -> None:
    q = db.query(AISummary).filter(AISummary.company_id == company_id)
    if year is not None:
        q = q.filter(AISummary.year == year)
    if quarter is not None:
        q = q.filter(AISummary.quarter == quarter)
    q.delete(synchronize_session=False)
    db.commit()


def _period_label(year: int, quarter: int, view: str = "cumulative") -> str:
    if view == "single_quarter":
        if quarter == 0:
            return f"{year}年Q4单季"
        return f"{year}年Q{quarter}单季"
    if quarter == 0:
        return f"{year}年"
    return f"{year}年Q{quarter}"


def _growth_rate(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 2)


def _analysis_base_report(db: Session, report: Any, view: str = "cumulative") -> Optional[Any]:
    attached = getattr(report, "_analysis_base_report", None)
    if attached is not None:
        return attached
    company_id = getattr(report, "company_id", None)
    year = getattr(report, "year", None)
    if company_id is None or year is None:
        return None
    if view == "single_quarter":
        if getattr(report, "quarter", 0) == 1:
            return get_prev_annual_report(db, company_id, year)
        return None
    return get_prev_annual_report(db, company_id, year)


def _analyze_report(db: Session, report: Any, view: str = "cumulative") -> Dict[str, Any]:
    return analyze_single_report(
        report,
        base_report=_analysis_base_report(db, report, view=view),
        period_days=period_days_for_report(report, single_quarter_mode=view == "single_quarter"),
    )


def _build_growth_analysis(report: FinancialReport, prev_report: Optional[FinancialReport], analysis: Dict[str, Any], prev_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not prev_report:
        return {
            "revenue_growth": None,
            "net_profit_parent_growth": None,
            "net_cash_from_operations_growth": None,
            "total_assets_growth": None,
            "total_equity_growth": None,
            "gross_margin_change": None,
            "net_margin_change": None,
            "growth_quality": "缺少上期数据，暂无法判断增长质量",
        }

    revenue_growth = _growth_rate(float(report.revenue or 0.0), float(prev_report.revenue or 0.0))
    net_profit_parent_growth = _growth_rate(float(report.net_profit_parent or 0.0), float(prev_report.net_profit_parent or 0.0))
    net_cash_from_operations_growth = _growth_rate(float(report.net_cash_from_operations or 0.0), float(prev_report.net_cash_from_operations or 0.0))
    total_assets_growth = _growth_rate(float(report.total_assets or 0.0), float(prev_report.total_assets or 0.0))
    total_equity_growth = _growth_rate(float(report.total_equity or 0.0), float(prev_report.total_equity or 0.0))

    prev_gross_margin = prev_analysis.get("profitability", {}).get("gross_margin") if prev_analysis else None
    prev_net_margin = prev_analysis.get("profitability", {}).get("net_margin") if prev_analysis else None
    current_gross_margin = analysis.get("profitability", {}).get("gross_margin")
    current_net_margin = analysis.get("profitability", {}).get("net_margin")

    gross_margin_change = round((current_gross_margin or 0) - (prev_gross_margin or 0), 2) if prev_gross_margin is not None and current_gross_margin is not None else None
    net_margin_change = round((current_net_margin or 0) - (prev_net_margin or 0), 2) if prev_net_margin is not None and current_net_margin is not None else None

    if revenue_growth is not None and net_profit_parent_growth is not None and net_cash_from_operations_growth is not None:
        if revenue_growth > 0 and net_profit_parent_growth > 0 and net_cash_from_operations_growth > 0:
            growth_quality = "收入、利润、经营现金流同步增长，增长质量较高"
        elif revenue_growth > 0 and net_profit_parent_growth > revenue_growth and net_cash_from_operations_growth is not None and net_cash_from_operations_growth <= 0:
            growth_quality = "利润增速快于收入，但经营现金流未同步改善，需关注利润兑现质量"
        elif revenue_growth <= 0 and net_profit_parent_growth > 0:
            growth_quality = "利润增长缺少收入支撑，需排查一次性收益或费用波动"
        else:
            growth_quality = "增长结构存在分化，建议结合现金流与利润率变化进一步判断"
    else:
        growth_quality = "增长数据不完整，暂无法给出稳定判断"

    return {
        "revenue_growth": revenue_growth,
        "net_profit_parent_growth": net_profit_parent_growth,
        "net_cash_from_operations_growth": net_cash_from_operations_growth,
        "total_assets_growth": total_assets_growth,
        "total_equity_growth": total_equity_growth,
        "gross_margin_change": gross_margin_change,
        "net_margin_change": net_margin_change,
        "growth_quality": growth_quality,
    }


def _score_section(score: int, label: str) -> Dict[str, Any]:
    return {"score": score, "label": label}


def _build_financial_quality(analysis: Dict[str, Any], growth: Dict[str, Any], risks: Dict[str, Any]) -> Dict[str, Any]:
    profitability_score = 0
    if (analysis.get("profitability", {}).get("roe") or 0) >= 15:
        profitability_score += 40
    if (analysis.get("profitability", {}).get("gross_margin") or 0) >= 25:
        profitability_score += 30
    if (analysis.get("profitability", {}).get("net_margin") or 0) >= 10:
        profitability_score += 30

    growth_score = 0
    if (growth.get("revenue_growth") or 0) > 10:
        growth_score += 35
    if (growth.get("net_profit_parent_growth") or 0) > 10:
        growth_score += 35
    if (growth.get("net_cash_from_operations_growth") or 0) > 0:
        growth_score += 30

    cash_flow_score = 0
    if (analysis.get("cash_flow", {}).get("ocf_to_net_profit") or 0) >= 1:
        cash_flow_score += 40
    if (analysis.get("cash_flow", {}).get("free_cash_flow") or 0) > 0:
        cash_flow_score += 30
    if (analysis.get("cash_flow", {}).get("sales_cash_to_revenue") or 0) >= 0.9:
        cash_flow_score += 30

    solvency_score = 0
    if (analysis.get("safety", {}).get("current_ratio") or 0) >= 1.5:
        solvency_score += 30
    if (analysis.get("safety", {}).get("cash_short_debt_ratio") or 0) >= 1:
        solvency_score += 35
    debt_to_asset_ratio = analysis.get("safety", {}).get("debt_to_asset_ratio")
    if debt_to_asset_ratio is not None and debt_to_asset_ratio <= 60:
        solvency_score += 35

    efficiency_score = 0
    if (analysis.get("turnover", {}).get("receivable_days") or 999) <= 90:
        efficiency_score += 35
    if (analysis.get("turnover", {}).get("inventory_days") or 999) <= 120:
        efficiency_score += 35
    if (analysis.get("turnover", {}).get("total_asset_turnover") or 0) >= 0.5:
        efficiency_score += 30

    total_score = round((profitability_score + growth_score + cash_flow_score + solvency_score + efficiency_score) / 5, 2)
    highlights = []
    if profitability_score >= 70:
        highlights.append("盈利能力处于较优区间")
    if cash_flow_score < 60:
        highlights.append("现金流质量偏弱，需要结合净利润核验")
    if solvency_score < 60:
        highlights.append("短债或杠杆压力值得重点关注")
    if risks.get("score", 100) < 80:
        highlights.append("风险安全分下降，建议优先处理异常项")
    if not highlights:
        highlights.append("当前财务结构总体均衡，但仍需结合行业比较判断")

    return {
        "total_score": total_score,
        "sections": {
            "profitability": _score_section(profitability_score, "盈利质量"),
            "growth": _score_section(growth_score, "成长质量"),
            "cash_flow": _score_section(cash_flow_score, "现金流质量"),
            "solvency": _score_section(solvency_score, "偿债安全"),
            "efficiency": _score_section(efficiency_score, "营运效率"),
        },
        "highlights": highlights,
    }


def _report_detail(report: FinancialReport, company_name: str) -> Dict[str, Any]:
    def group_data(group: Dict[str, str]) -> List[Dict[str, Any]]:
        return [
            {"field": field, "label": label, "value": float(getattr(report, field, 0.0) or 0.0)}
            for field, label in group.items()
        ]

    return {
        "id": report.id,
        "company_name": company_name,
        "year": report.year,
        "quarter": report.quarter,
        "balance_sheet": group_data(BALANCE_FIELDS),
        "income_statement": group_data(INCOME_FIELDS),
        "cash_flow": group_data(CASH_FLOW_FIELDS),
    }


def _remove_report_file(file_path: Optional[str]) -> None:
    if not file_path:
        return
    path = Path(file_path)
    if not path.exists():
        return
    try:
        path.unlink()
    except Exception:
        pass


def _field_label(field: str) -> str:
    return BALANCE_FIELDS.get(field) or INCOME_FIELDS.get(field) or CASH_FLOW_FIELDS.get(field) or field


def _parse_report_source(report: FinancialReport) -> Dict[str, Any]:
    if not report.file_path:
        raise HTTPException(status_code=400, detail="报表缺少文件路径，无法对照")

    source_path = Path(report.file_path)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="原始报表文件不存在，无法对照")

    ext = source_path.suffix.lower()
    if ext == ".pdf":
        payload, _warnings = parse_pdf(source_path, company_id=report.company_id, year=report.year, quarter=report.quarter)
        return payload
    if ext in {".xlsx", ".xls"}:
        return parse_excel(source_path, company_id=report.company_id, year=report.year, quarter=report.quarter)

    raise HTTPException(status_code=400, detail="仅支持 xlsx/xls/pdf 报表对照")


def _build_extraction_comparison(report: FinancialReport, source_payload: Dict[str, Any], top_n: int) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    non_zero_rows = 0

    for field in ALL_FINANCIAL_FIELDS:
        extracted_value = float(getattr(report, field, 0.0) or 0.0)
        source_value = float(source_payload.get(field, 0.0) or 0.0)
        if extracted_value == 0.0 and source_value == 0.0:
            continue
        non_zero_rows += 1

        diff = extracted_value - source_value
        abs_diff = abs(diff)
        relative_diff_pct = None if source_value == 0 else round(diff / abs(source_value) * 100, 4)

        rows.append(
            {
                "field": field,
                "label": _field_label(field),
                "extracted_value": round(extracted_value, 2),
                "source_value": round(source_value, 2),
                "diff": round(diff, 2),
                "abs_diff": round(abs_diff, 2),
                "relative_diff_pct": relative_diff_pct,
                "matched": abs_diff < 1e-6,
            }
        )

    rows.sort(key=lambda x: x["abs_diff"], reverse=True)
    mismatches = [r for r in rows if not r["matched"]]

    return {
        "report": {
            "id": report.id,
            "company_id": report.company_id,
            "year": report.year,
            "quarter": report.quarter,
            "file_path": report.file_path,
        },
        "summary": {
            "total_compared_fields": non_zero_rows,
            "mismatch_count": len(mismatches),
            "match_count": non_zero_rows - len(mismatches),
        },
        "top_deviations": mismatches[:top_n],
    }


def _upsert_report(db: Session, payload: Dict[str, Any], file_path: Optional[str] = None) -> FinancialReport:
    company_id = int(payload["company_id"])
    year = int(payload["year"])
    quarter = int(payload.get("quarter", 0))

    report = (
        db.query(FinancialReport)
        .filter(and_(FinancialReport.company_id == company_id, FinancialReport.year == year, FinancialReport.quarter == quarter))
        .first()
    )

    if report is None:
        report = FinancialReport(
            company_id=company_id,
            year=year,
            quarter=quarter,
            report_type=payload.get("report_type", "annual"),
            file_path=file_path or "",
        )
        db.add(report)

    if file_path:
        report.file_path = file_path
    report.report_type = payload.get("report_type", "annual")
    for field in ALL_FINANCIAL_FIELDS:
        if field in payload:
            setattr(report, field, float(payload[field] or 0.0))

    db.commit()
    db.refresh(report)
    _clear_ai_cache(db, company_id=company_id, year=year, quarter=quarter)
    return report


@app.get("/")
def root():
    return {"message": "财报全景分析平台 API 运行中"}


@app.post("/api/companies")
def create_company(body: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(name=body.name, industry=body.industry, stock_code=body.stock_code)
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name, "industry": company.industry, "stock_code": company.stock_code}


@app.get("/api/companies")
def list_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    output = []
    for company in companies:
        reports = [
            {
                "id": r.id,
                "year": r.year,
                "quarter": r.quarter,
                "report_type": r.report_type,
            }
            for r in sorted(company.reports, key=lambda x: (x.year, x.quarter), reverse=True)
        ]
        output.append({
            "id": company.id,
            "name": company.name,
            "industry": company.industry,
            "stock_code": company.stock_code,
            "reports": reports,
        })
    return output


@app.delete("/api/companies/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")
    _clear_ai_cache(db, company_id=company_id)
    for report in company.reports:
        _remove_report_file(report.file_path)
    db.delete(company)
    db.commit()
    return {"message": "删除成功"}


@app.put("/api/companies/{company_id}")
def update_company(company_id: int, body: CompanyCreate, db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")
    company.name = body.name
    company.industry = body.industry
    company.stock_code = body.stock_code
    db.commit()
    db.refresh(company)
    return {"id": company.id, "name": company.name, "industry": company.industry, "stock_code": company.stock_code}


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(FinancialReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    company_id = report.company_id
    year = report.year
    quarter = report.quarter

    _remove_report_file(report.file_path)
    db.delete(report)
    db.commit()
    _clear_ai_cache(db, company_id=company_id, year=year, quarter=quarter)

    return {
        "message": "报表删除成功",
        "deleted": {"report_id": report_id, "company_id": company_id, "year": year, "quarter": quarter},
    }


@app.delete("/api/companies/{company_id}/reports")
def delete_company_reports_by_year(company_id: int, year: int = Query(...), db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    reports = (
        db.query(FinancialReport)
        .filter(FinancialReport.company_id == company_id, FinancialReport.year == year)
        .order_by(FinancialReport.quarter.asc())
        .all()
    )
    if not reports:
        return {"message": "未找到可删除的报表", "company_id": company_id, "year": year, "deleted_count": 0}

    deleted_quarters = sorted({r.quarter for r in reports})
    for report in reports:
        _remove_report_file(report.file_path)
        db.delete(report)
    db.commit()

    for q in deleted_quarters:
        _clear_ai_cache(db, company_id=company_id, year=year, quarter=q)

    return {
        "message": "年度报表删除成功",
        "company_id": company_id,
        "year": year,
        "deleted_count": len(reports),
        "deleted_quarters": deleted_quarters,
    }


@app.get("/api/template")
def download_template():
    template_path = TEMPLATE_DIR / "财报上传模板.xlsx"
    if not template_path.exists():
        generate_template(template_path)
    return FileResponse(path=template_path, filename="财报上传模板.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _parse_report_period(filename: str) -> tuple[str, int, int]:
    """Extract (base_name, year, quarter) from a filename like "2024年年报.pdf".

    Supported naming patterns for quarter detection (case-insensitive):
      - 年报 / 年度 / Q4 / year only → quarter=0 (annual report)
      - 一季 / 1季 / Q1 / 一季度 → quarter=1
      - 半年 / 中报 / 二季 / 2季 / Q2 / 二季度 → quarter=2
      - 三季 / 3季 / Q3 / 三季度 → quarter=3

    Raises ValueError when year or quarter cannot be determined."""
    name = Path(filename).stem

    year_match = re.search(r"(20\d{2})", name)
    if not year_match:
        raise ValueError(f"无法从文件名识别年份: {filename}")
    year = int(year_match.group(1))

    base = name.lower()
    # NOTE: order matters — "半年报" is checked before "年报" to avoid substring match.
    if any(kw in base for kw in ("一季", "1季", "q1", "一季度")):
        quarter = 1
    elif any(kw in base for kw in ("半年", "中报", "二季", "2季", "q2", "二季度", "semi")):
        quarter = 2
    elif any(kw in base for kw in ("三季", "3季", "q3", "三季度")):
        quarter = 3
    elif any(kw in base for kw in ("年报", "年度", "q4", "annual")):
        quarter = 0
    else:
        raise ValueError(
            f"无法从文件名识别报告期: {filename}。"
            "请在文件名中包含 年报/一季报/半年报/三季报 或 Q1/Q2/Q3/Q4"
        )

    return name, year, quarter


@app.post("/api/upload")
async def upload_report(
    file: UploadFile = File(...),
    company_id: int = Query(...),
    year: int = Query(...),
    quarter: int = Query(0),
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".xlsx", ".xls", ".pdf"}:
        raise HTTPException(status_code=400, detail="仅支持 xlsx/xls/pdf")

    save_name = f"{company_id}_{year}_{quarter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
    save_path = UPLOAD_DIR / save_name
    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        warnings: list[str] = []
        if ext == ".pdf":
            payload, warnings = parse_pdf(save_path, company_id=company_id, year=year, quarter=quarter)
        else:
            payload = parse_excel(save_path, company_id=company_id, year=year, quarter=quarter)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")

    report = _upsert_report(db, payload, str(save_path))
    return {
        "message": "上传并解析成功",
        "report": {"id": report.id, "year": report.year, "quarter": report.quarter, "report_type": report.report_type},
        "warnings": warnings,
    }


@app.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    company_id: int = Query(...),
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    results: List[Dict[str, Any]] = []
    for file in files:
        item: Dict[str, Any] = {
            "filename": file.filename,
            "success": False,
        }
        save_path = None
        try:
            base_name, year, quarter = _parse_report_period(file.filename or "")

            ext = Path(file.filename or "").suffix.lower()
            if ext not in {".xlsx", ".xls", ".pdf"}:
                raise ValueError(f"不支持的文件格式: {ext}")

            save_name = f"{company_id}_{year}_{quarter}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(results)}{ext}"
            save_path = UPLOAD_DIR / save_name
            with save_path.open("wb") as f:
                shutil.copyfileobj(file.file, f)

            warnings: list[str] = []
            if ext == ".pdf":
                payload, warnings = parse_pdf(save_path, company_id=company_id, year=year, quarter=quarter)
            else:
                payload = parse_excel(save_path, company_id=company_id, year=year, quarter=quarter)

            report = _upsert_report(db, payload, str(save_path))
            item["success"] = True
            item["year"] = year
            item["quarter"] = quarter
            item["report_id"] = report.id
            if warnings:
                item["warnings"] = warnings
        except ValueError as e:
            item["message"] = str(e)
        except Exception as e:
            item["message"] = f"解析失败: {e}"
            if save_path and save_path.exists():
                try:
                    save_path.unlink()
                except OSError:
                    pass

        results.append(item)

    success_count = sum(1 for r in results if r["success"])
    return {
        "results": results,
        "total": len(results),
        "success": success_count,
        "failed": len(results) - success_count,
    }


@app.get("/api/reports/{report_id}")
def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    report = db.get(FinancialReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")
    company = db.get(Company, report.company_id)
    return _report_detail(report, company_name=company.name if company else "")


@app.put("/api/reports/{report_id}")
def update_report(report_id: int, body: ReportUpdate, db: Session = Depends(get_db)):
    report = db.get(FinancialReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    for field, value in body.fields.items():
        if field not in ALL_FINANCIAL_FIELDS:
            continue
        setattr(report, field, float(value or 0.0))

    db.commit()
    db.refresh(report)
    _clear_ai_cache(db, company_id=report.company_id, year=report.year, quarter=report.quarter)
    return {"message": "更新成功"}


@app.get("/api/reports/{report_id}/extraction-compare")
def compare_extraction_with_source(report_id: int, top_n: int = Query(20, ge=1, le=200), db: Session = Depends(get_db)):
    report = db.get(FinancialReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报表不存在")

    source_payload = _parse_report_source(report)
    return _build_extraction_comparison(report, source_payload, top_n=top_n)


@app.get("/api/analysis/{company_id}")
def get_analysis(
    company_id: int,
    year: Optional[int] = None,
    quarter: int = 0,
    view: str = "cumulative",
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    if view == "single_quarter":
        derived, prev_derived = derive_for_analysis(db, company_id, year, quarter)
        if derived is None:
            raise HTTPException(status_code=404, detail="未找到对应报表，无法派生单季数据")
        report = derived
        prev_report = prev_derived
    else:
        q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id)
        if year is not None:
            q = q.filter(FinancialReport.year == year)
        q = q.filter(FinancialReport.quarter == quarter)
        report = q.order_by(FinancialReport.year.desc()).first()
        if not report and quarter == 0:
            fallback_q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id)
            if year is not None:
                fallback_q = fallback_q.filter(FinancialReport.year == year)
            report = fallback_q.order_by(FinancialReport.year.desc(), FinancialReport.quarter.desc()).first()
        if not report:
            raise HTTPException(status_code=404, detail="未找到对应报表")

        prev_report = (
            db.query(FinancialReport)
            .filter(FinancialReport.company_id == company_id, FinancialReport.quarter == report.quarter, FinancialReport.year < report.year)
            .order_by(FinancialReport.year.desc())
            .first()
        )

    analysis = _analyze_report(db, report, view=view)
    prev_analysis = _analyze_report(db, prev_report, view=view) if prev_report else None
    risks = detect_risks(report, prev_report=prev_report)
    growth = _build_growth_analysis(report, prev_report, analysis, prev_analysis)
    financial_quality = _build_financial_quality(analysis, growth, risks)

    rel = relative_valuation(report)
    roe = (analysis.get("profitability", {}).get("roe") or 0) / 100
    goodwill = economic_goodwill(roe, float(report.total_equity_parent or 0.0))
    valuation = {
        "relative": rel,
        "economic_goodwill": round(goodwill, 2),
        "fcf": analysis.get("cash_flow", {}).get("free_cash_flow"),
        "total_shares": float(report.total_shares or 0.0),
    }

    return {
        "company": {"id": company.id, "name": company.name, "industry": company.industry, "stock_code": company.stock_code},
        "period": {"year": report.year, "quarter": report.quarter},
        "analysis": analysis,
        "growth": growth,
        "financial_quality": financial_quality,
        "risks": risks,
        "valuation": valuation,
        "view_mode": view,
    }


@app.get("/api/trend/{company_id}")
def get_trend(company_id: int, view: str = "cumulative", db: Session = Depends(get_db)):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    if view == "single_quarter":
        derived_reports = derive_all_single_quarter_reports(db, company_id)
        trend = analyze_multi_period(derived_reports, single_quarter_mode=True)
        periods = [{"year": r.year, "quarter": r.quarter} for r in derived_reports]
    else:
        reports = db.query(FinancialReport).filter(FinancialReport.company_id == company_id).all()
        reports = sorted(reports, key=lambda r: (r.year, 4 if r.quarter == 0 else r.quarter))
        trend = analyze_multi_period(reports)
        periods = [{"year": r.year, "quarter": r.quarter} for r in reports]

    return {
        "company": {"id": company.id, "name": company.name, "industry": company.industry, "stock_code": company.stock_code},
        "periods": periods,
        "trend": trend,
        "view_mode": view,
    }


@app.post("/api/valuation/dcf")
def post_dcf(body: DCFRequest):
    return dcf_simple(
        free_cash_flow_year3=body.free_cash_flow_year3,
        discount_rate=body.discount_rate,
        perpetual_growth=body.perpetual_growth,
        current_price=body.current_price,
        total_shares=body.total_shares,
        forecast_growth=body.forecast_growth,
        forecast_years=body.forecast_years,
    )


@app.get("/api/valuation/{company_id}")
def get_company_valuation(
    company_id: int,
    year: Optional[int] = None,
    quarter: int = 0,
    view: str = "cumulative",
    db: Session = Depends(get_db),
):
    if view == "single_quarter":
        derived, _prev_derived = derive_for_analysis(db, company_id, year, quarter)
        if derived is None:
            raise HTTPException(status_code=404, detail="未找到估值所需报表")
        report = derived
    else:
        q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id, FinancialReport.quarter == quarter)
        if year is not None:
            q = q.filter(FinancialReport.year == year)
        report = q.order_by(FinancialReport.year.desc()).first()
        if not report and quarter == 0:
            fallback_q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id)
            if year is not None:
                fallback_q = fallback_q.filter(FinancialReport.year == year)
            report = fallback_q.order_by(FinancialReport.year.desc(), FinancialReport.quarter.desc()).first()
        if not report:
            raise HTTPException(status_code=404, detail="未找到估值所需报表")

    analysis = _analyze_report(db, report, view=view)
    rel = relative_valuation(report)
    roe = (analysis.get("profitability", {}).get("roe") or 0) / 100
    goodwill = economic_goodwill(roe, float(report.total_equity_parent or 0.0))

    return {
        "relative": rel,
        "economic_goodwill": round(goodwill, 2),
        "fcf": analysis.get("cash_flow", {}).get("free_cash_flow"),
        "total_shares": float(report.total_shares or 0.0),
        "year": report.year,
        "quarter": report.quarter,
    }


@app.get("/api/ai-summary/{company_id}")
def get_ai_summary(
    company_id: int,
    year: Optional[int] = None,
    quarter: int = 0,
    regenerate: bool = False,
    view: str = "cumulative",
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")

    if view == "single_quarter":
        derived, _prev_derived = derive_for_analysis(db, company_id, year, quarter)
        if derived is None:
            raise HTTPException(status_code=404, detail="未找到对应报表，无法派生单季数据")
        report = derived
        cache = None
    else:
        q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id, FinancialReport.quarter == quarter)
        if year is not None:
            q = q.filter(FinancialReport.year == year)
        report = q.order_by(FinancialReport.year.desc()).first()
        if not report and quarter == 0:
            fallback_q = db.query(FinancialReport).filter(FinancialReport.company_id == company_id)
            if year is not None:
                fallback_q = fallback_q.filter(FinancialReport.year == year)
            report = fallback_q.order_by(FinancialReport.year.desc(), FinancialReport.quarter.desc()).first()
        if not report:
            raise HTTPException(status_code=404, detail="未找到对应报表")

        cache = (
            db.query(AISummary)
            .filter(AISummary.company_id == company_id, AISummary.year == report.year, AISummary.quarter == report.quarter)
            .order_by(AISummary.created_at.desc())
            .first()
        )

    if cache and not regenerate:
        return {
            "company": {"id": company.id, "name": company.name},
            "period": {"year": report.year, "quarter": report.quarter},
            "summary": cache.summary_text,
            "cached": True,
            "generated_at": cache.created_at.isoformat() if cache.created_at else None,
            "view_mode": view,
        }

    analysis = _analyze_report(db, report, view=view)
    if view == "single_quarter":
        _derived_current, prev_report = derive_for_analysis(db, company_id, year, quarter)
    else:
        prev_report = (
            db.query(FinancialReport)
            .filter(FinancialReport.company_id == company_id, FinancialReport.quarter == report.quarter, FinancialReport.year < report.year)
            .order_by(FinancialReport.year.desc())
            .first()
        )
    risks = detect_risks(report, prev_report=prev_report)
    valuation = {
        "relative": relative_valuation(report),
        "economic_goodwill": round(
            economic_goodwill((analysis.get("profitability", {}).get("roe") or 0) / 100, float(report.total_equity_parent or 0.0)),
            2,
        ),
        "fcf": analysis.get("cash_flow", {}).get("free_cash_flow"),
        "total_shares": float(report.total_shares or 0.0),
    }

    reports = (
        db.query(FinancialReport)
        .filter(FinancialReport.company_id == company_id)
        .order_by(FinancialReport.year.asc(), FinancialReport.quarter.asc())
        .all()
    )
    trend = analyze_multi_period(reports) if len(reports) >= 2 else None

    summary_text = generate_ai_summary(
        company_name=company.name,
        period=_period_label(report.year, report.quarter, view),
        analysis=analysis,
        risks=risks,
        valuation=valuation,
        trend=trend,
    )

    if view == "single_quarter":
        db.rollback()
        return {
            "company": {"id": company.id, "name": company.name},
            "period": {"year": report.year, "quarter": report.quarter},
            "summary": summary_text,
            "cached": False,
            "generated_at": datetime.utcnow().isoformat(),
            "view_mode": view,
        }

    if cache:
        cache.summary_text = summary_text
        cache.created_at = datetime.utcnow()
        obj = cache
    else:
        obj = AISummary(
            company_id=company_id,
            year=report.year,
            quarter=report.quarter,
            summary_text=summary_text,
            created_at=datetime.utcnow(),
        )
        db.add(obj)

    db.commit()
    db.refresh(obj)

    return {
        "company": {"id": company.id, "name": company.name},
        "period": {"year": report.year, "quarter": report.quarter},
        "summary": obj.summary_text,
        "cached": False,
        "generated_at": obj.created_at.isoformat() if obj.created_at else None,
        "view_mode": view,
    }


@app.get("/api/compare")
def compare_companies(company_ids: str, year: Optional[int] = None, db: Session = Depends(get_db)):
    ids = [int(x) for x in company_ids.split(",") if x.strip().isdigit()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="至少选择2家公司")

    result = []
    for cid in ids:
        company = db.get(Company, cid)
        if not company:
            continue

        q = db.query(FinancialReport).filter(FinancialReport.company_id == cid, FinancialReport.quarter == 0)
        if year is not None:
            q = q.filter(FinancialReport.year == year)
        report = q.order_by(FinancialReport.year.desc()).first()
        if not report:
            continue

        analysis = _analyze_report(db, report)
        risks = detect_risks(report)
        result.append({
            "company": {"id": company.id, "name": company.name},
            "period": {"year": report.year, "quarter": report.quarter},
            "metrics": {
                # 盈利能力
                "gross_margin": analysis["profitability"].get("gross_margin"),
                "net_margin": analysis["profitability"].get("net_margin"),
                "operating_margin": analysis["profitability"].get("operating_margin"),
                "roe": analysis["profitability"].get("roe"),
                "roa": analysis["profitability"].get("roa"),
                "roic": analysis["profitability"].get("roic"),
                # 安全性
                "debt_to_asset_ratio": analysis["safety"].get("debt_to_asset_ratio"),
                "current_ratio": analysis["safety"].get("current_ratio"),
                "quick_ratio": analysis["safety"].get("quick_ratio"),
                "interest_coverage": analysis["safety"].get("interest_coverage"),
                "cash_short_debt_ratio": analysis["safety"].get("cash_short_debt_ratio"),
                "equity_ratio": analysis["safety"].get("equity_ratio"),
                # 现金流
                "free_cash_flow": analysis["cash_flow"].get("free_cash_flow"),
                "ocf_to_net_profit": analysis["cash_flow"].get("ocf_to_net_profit"),
                "sales_cash_to_revenue": analysis["cash_flow"].get("sales_cash_to_revenue"),
                "ocf_margin": analysis["cash_flow"].get("ocf_margin"),
                "net_cash_operations": analysis["cash_flow"].get("net_cash_operations"),
                "net_cash_investing": analysis["cash_flow"].get("net_cash_investing"),
                "net_cash_financing": analysis["cash_flow"].get("net_cash_financing"),
                "cash_portrait_type": analysis["cash_flow"]["portrait"].get("type"),
                "cash_portrait_emoji": analysis["cash_flow"]["portrait"].get("emoji"),
                # 营运效率
                "total_asset_turnover": analysis["turnover"].get("total_asset_turnover"),
                "inventory_days": analysis["turnover"].get("inventory_days"),
                "receivable_days": analysis["turnover"].get("receivable_days"),
                "payable_days": analysis["turnover"].get("payable_days"),
                "cash_conversion_cycle": analysis["turnover"].get("cash_conversion_cycle"),
                "fixed_asset_turnover": analysis["turnover"].get("fixed_asset_turnover"),
                # 费用结构
                "selling_expense_ratio": analysis["expense_ratios"].get("selling_expense_ratio"),
                "admin_expense_ratio": analysis["expense_ratios"].get("admin_expense_ratio"),
                "rd_expense_ratio": analysis["expense_ratios"].get("rd_expense_ratio"),
                "finance_expense_ratio": analysis["expense_ratios"].get("finance_expense_ratio"),
                "total_expense_ratio": analysis["expense_ratios"].get("total_expense_ratio"),
                # 资产结构
                "cash_ratio": analysis["asset_structure"].get("cash_ratio"),
                "operating_assets_ratio": analysis["asset_structure"].get("operating_assets_ratio"),
                "production_assets_ratio": analysis["asset_structure"].get("production_assets_ratio"),
                "investment_assets_ratio": analysis["asset_structure"].get("investment_assets_ratio"),
                # 综合评价
                "score": analysis["good_company_score"].get("score"),
                "risk_score": risks.get("score"),
                "risk_level": risks.get("level"),
                "risk_count_high": risks.get("risk_count", {}).get("high"),
                "risk_count_medium": risks.get("risk_count", {}).get("medium"),
                "risk_count_critical": risks.get("risk_count", {}).get("critical"),
            },
        })

    return {"year": year, "results": result}


@app.post("/api/scrape/{company_id}")
def scrape_company_data(company_id: int, db: Session = Depends(get_db)):
    """从东方财富自动采集该公司所有历史财报数据"""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="公司不存在")
    if not company.stock_code:
        raise HTTPException(status_code=400, detail="该公司未设置股票代码，无法自动采集")

    logger.info(f"[采集] 开始: {company.name} ({company.stock_code})")

    try:
        result = scrape_company(company.stock_code, company_id)
    except Exception as e:
        logger.error(f"[采集] 失败: {company.name} ({company.stock_code}) - {e}")
        raise HTTPException(status_code=500, detail=f"数据采集失败: {e}")

    for err in result.get("errors", []):
        logger.warning(f"[采集] {company.name} 部分失败: {err}")

    created = 0
    updated = 0
    skipped = 0
    detail: List[Dict[str, Any]] = []

    for r in result["reports"]:
        year, quarter = r["year"], r["quarter"]
        existed = (
            db.query(FinancialReport)
            .filter(
                and_(
                    FinancialReport.company_id == company_id,
                    FinancialReport.year == year,
                    FinancialReport.quarter == quarter,
                )
            )
            .first()
        )
        status = "updated" if existed else "created"
        if existed:
            updated += 1
        else:
            created += 1

        fields: Dict[str, float] = r.get("fields", {})
        if not fields:
            if existed:
                updated -= 1
            else:
                created -= 1
            skipped += 1
            continue

        payload: Dict[str, Any] = {
            "company_id": company_id,
            "year": year,
            "quarter": quarter,
            "report_type": "annual" if quarter == 0 else "quarterly",
        }
        payload.update(fields)

        try:
            report = _upsert_report(db, payload)
            detail.append({
                "year": year,
                "quarter": quarter,
                "fields_count": len(fields),
                "status": status,
                "report_id": report.id,
            })
        except Exception:
            detail.append({
                "year": year,
                "quarter": quarter,
                "fields_count": len(fields),
                "status": "failed",
            })
            if status == "created":
                created -= 1
            else:
                updated -= 1

    logger.info(
        f"[采集] 完成: {company.name} | 共 {len(result['reports'])} 期, "
        f"新增 {created}, 更新 {updated}, 跳过 {skipped}"
    )
    if result.get("errors"):
        logger.warning(f"[采集] {company.name} 采集错误: {result['errors']}")

    return {
        "company_id": company_id,
        "stock_code": company.stock_code,
        "total_periods": len(result["reports"]),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "detail": detail,
        "errors": result.get("errors", []),
    }


@app.post("/api/scrape/batch")
def scrape_batch(company_ids: List[int], db: Session = Depends(get_db)):
    """批量自动采集多家公司的财报数据"""
    logger.info(f"[批量采集] 开始: {len(company_ids)} 家公司")
    results: List[Dict[str, Any]] = []
    total_created = 0
    total_updated = 0

    for cid in company_ids:
        try:
            company = db.get(Company, cid)
            if not company or not company.stock_code:
                logger.warning(f"[批量采集] 跳过公司 {cid}: 不存在或无股票代码")
                results.append({"company_id": cid, "success": False, "error": "公司不存在或无股票代码"})
                continue

            logger.info(f"[批量采集] 正在处理: {company.name} ({company.stock_code})")
            result = scrape_company(company.stock_code, cid)
            batch_created = 0
            batch_updated = 0

            for r in result["reports"]:
                year, quarter = r["year"], r["quarter"]
                existed = (
                    db.query(FinancialReport)
                    .filter(
                        and_(
                            FinancialReport.company_id == cid,
                            FinancialReport.year == year,
                            FinancialReport.quarter == quarter,
                        )
                    )
                    .first()
                )
                if existed:
                    batch_updated += 1
                else:
                    batch_created += 1

                fields = r.get("fields", {})
                if not fields:
                    continue

                payload: Dict[str, Any] = {
                    "company_id": cid,
                    "year": year,
                    "quarter": quarter,
                    "report_type": "annual" if quarter == 0 else "quarterly",
                }
                payload.update(fields)
                _upsert_report(db, payload)

            total_created += batch_created
            total_updated += batch_updated
            logger.info(
                f"[批量采集] {company.name} 完成: "
                f"新增 {batch_created}, 更新 {batch_updated}"
            )
            results.append({
                "company_id": cid,
                "stock_code": company.stock_code,
                "success": True,
                "created": batch_created,
                "updated": batch_updated,
            })
        except Exception as e:
            logger.error(f"[批量采集] 公司 {cid} 失败: {e}")
            results.append({"company_id": cid, "success": False, "error": str(e)})

    logger.info(
        f"[批量采集] 全部完成: {len(company_ids)} 家, "
        f"总计新增 {total_created}, 更新 {total_updated}"
    )

    return {
        "results": results,
        "total_created": total_created,
        "total_updated": total_updated,
    }


@app.get("/api/logs")
def list_logs():
    """列出所有可用的日志文件及其元数据"""
    import os
    from datetime import datetime

    files = []
    for entry in sorted(LOG_DIR.iterdir(), key=lambda e: e.stat().st_mtime, reverse=True):
        if not entry.is_file() or not entry.suffix in {".log", ".txt"}:
            continue
        stat = entry.stat()
        files.append({
            "name": entry.name,
            "size": stat.st_size,
            "size_display": f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024 * 1024 else f"{stat.st_size / (1024 * 1024):.1f} MB",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return {"files": files, "total": len(files)}


@app.get("/api/logs/{filename:path}")
def read_log(
    filename: str,
    lines: int = Query(200, ge=10, le=5000, description="返回最近N行"),
    offset: int = Query(0, ge=0, le=100000, description="从末尾跳过N行"),
    level: Optional[str] = Query(None, description="按日志级别过滤: DEBUG/INFO/WARNING/ERROR"),
    search: Optional[str] = Query(None, description="关键词搜索"),
):
    """读取指定日志文件的内容，支持分页、级别过滤和搜索"""
    import os

    safe_name = os.path.basename(filename)
    if safe_name != filename or ".." in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    file_path = LOG_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="日志文件不存在")

    if not safe_name.endswith((".log", ".txt")):
        raise HTTPException(status_code=400, detail="仅支持 .log / .txt 文件")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取日志文件失败: {e}")

    total_lines = len(all_lines)

    # Reverse to get latest lines first, apply offset, then take requested count
    all_lines.reverse()
    if offset > 0:
        all_lines = all_lines[offset:]
    all_lines = all_lines[:lines]

    # Apply level filter
    if level:
        level_upper = level.upper()
        all_lines = [l for l in all_lines if level_upper in l]

    # Apply search filter
    if search:
        all_lines = [l for l in all_lines if search.lower() in l.lower()]

    # Reverse back to chronological order
    all_lines.reverse()

    return {
        "filename": safe_name,
        "total_lines": total_lines,
        "returned_lines": len(all_lines),
        "lines": all_lines,
    }
