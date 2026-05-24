from __future__ import annotations

from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models.database import (
    ALL_FINANCIAL_FIELDS,
    BALANCE_FIELDS,
    CASH_FLOW_FIELDS,
    INCOME_FIELDS,
    FinancialReport,
)

INCOME_POINT_IN_TIME_FIELDS: set = {"total_shares"}

# Fields that should be copied as-is (NOT differenced):
# - All balance sheet fields (point-in-time snapshots)
# - total_shares (point-in-time, in INCOME_FIELDS)
_DIFFERENCED_FIELDS: set = set(INCOME_FIELDS.keys()) | set(CASH_FLOW_FIELDS.keys())
_DIFFERENCED_FIELDS -= INCOME_POINT_IN_TIME_FIELDS

# Fields that should simply be copied from the current cumulative report.
_COPIED_FIELDS: set = set(BALANCE_FIELDS.keys()) | INCOME_POINT_IN_TIME_FIELDS


def _copy_attrs(report: FinancialReport, target: dict, field_list: set) -> None:
    for field in field_list:
        target[field] = float(getattr(report, field, 0.0) or 0.0)


def derive_single_quarter(
    report: FinancialReport,
    prev_cumulative: Optional[FinancialReport],
    balance_base: Optional[FinancialReport] = None,
) -> SimpleNamespace:
    """Derive single-quarter data from a cumulative report.

    balance sheet fields and ``total_shares`` are copied as-is.
    income statement and cash flow fields are differenced: report - prev_cumulative.
    Q1 (no predecessor) is returned unchanged. Q2/Q3/Q4 must have the
    immediately preceding cumulative report; otherwise the caller should not
    derive a single-quarter value.
    """
    if report.quarter != 1 and prev_cumulative is None:
        raise ValueError("缺少上一期累计报表，无法派生单季数据")

    data: dict = {}

    if prev_cumulative is None:
        _copy_attrs(report, data, _COPIED_FIELDS | _DIFFERENCED_FIELDS)
    else:
        _copy_attrs(report, data, _COPIED_FIELDS)
        for field in _DIFFERENCED_FIELDS:
            current = float(getattr(report, field, 0.0) or 0.0)
            previous = float(getattr(prev_cumulative, field, 0.0) or 0.0)
            data[field] = current - previous

    data["year"] = report.year
    data["quarter"] = report.quarter
    data["company_id"] = report.company_id
    data["_analysis_base_report"] = balance_base or prev_cumulative
    return SimpleNamespace(**data)


def get_prev_cumulative(
    db: Session, report: FinancialReport
) -> Optional[FinancialReport]:
    """Return the immediately preceding cumulative report in the same fiscal year."""
    prev_quarter: Optional[int] = None
    if report.quarter == 1:
        return None
    elif report.quarter == 2:
        prev_quarter = 1
    elif report.quarter == 3:
        prev_quarter = 2
    elif report.quarter == 0:
        prev_quarter = 3

    if prev_quarter is None:
        return None

    return (
        db.query(FinancialReport)
        .filter(
            and_(
                FinancialReport.company_id == report.company_id,
                FinancialReport.year == report.year,
                FinancialReport.quarter == prev_quarter,
            )
        )
        .first()
    )


def get_prev_annual_report(
    db: Session, company_id: int, year: int
) -> Optional[FinancialReport]:
    """Return the latest annual report before the given fiscal year."""
    return (
        db.query(FinancialReport)
        .filter(
            and_(
                FinancialReport.company_id == company_id,
                FinancialReport.year < year,
                FinancialReport.quarter == 0,
            )
        )
        .order_by(FinancialReport.year.desc())
        .first()
    )


def derive_for_analysis(
    db: Session,
    company_id: int,
    year: Optional[int],
    quarter: int,
) -> Tuple[Optional[SimpleNamespace], Optional[SimpleNamespace]]:
    """Derive single-quarter for a single-period analysis endpoint.

    Returns (derived_report, prev_year_derived_or_none).
    """
    from sqlalchemy import and_

    q = db.query(FinancialReport).filter(
        and_(
            FinancialReport.company_id == company_id,
            FinancialReport.quarter == quarter,
        )
    )
    if year is not None:
        q = q.filter(FinancialReport.year == year)
    report = q.order_by(FinancialReport.year.desc()).first()

    if not report and quarter == 0:
        q = db.query(FinancialReport).filter(
            FinancialReport.company_id == company_id
        )
        if year is not None:
            q = q.filter(FinancialReport.year == year)
        report = q.order_by(
            FinancialReport.year.desc(), FinancialReport.quarter.desc()
        ).first()

    if not report:
        return None, None

    prev_cumulative = get_prev_cumulative(db, report)
    if report.quarter != 1 and prev_cumulative is None:
        return None, None

    balance_base = prev_cumulative or get_prev_annual_report(db, company_id, report.year)
    derived = derive_single_quarter(report, prev_cumulative, balance_base=balance_base)

    # Derive same quarter from previous year for growth comparison
    prev_year_report = (
        db.query(FinancialReport)
        .filter(
            and_(
                FinancialReport.company_id == company_id,
                FinancialReport.quarter == report.quarter,
                FinancialReport.year < report.year,
            )
        )
        .order_by(FinancialReport.year.desc())
        .first()
    )

    prev_year_derived = None
    if prev_year_report:
        prev_year_cum = get_prev_cumulative(db, prev_year_report)
        if prev_year_report.quarter == 1 or prev_year_cum is not None:
            prev_year_base = prev_year_cum or get_prev_annual_report(db, company_id, prev_year_report.year)
            prev_year_derived = derive_single_quarter(prev_year_report, prev_year_cum, balance_base=prev_year_base)

    return derived, prev_year_derived


def derive_all_single_quarter_reports(
    db: Session, company_id: int
) -> List[SimpleNamespace]:
    """Derive single-quarter data for all quarters, for trend analysis.

    Processes each fiscal year independently: Q1→Q2→Q3→Q4.
    Skips quarters whose predecessor is missing.
    """
    all_reports = (
        db.query(FinancialReport)
        .filter(FinancialReport.company_id == company_id)
        .all()
    )

    by_year: Dict[int, Dict[int, FinancialReport]] = {}
    for r in all_reports:
        by_year.setdefault(r.year, {})[r.quarter] = r

    quarter_order = [1, 2, 3, 0]  # Q1→Q2→Q3→Q4
    derived_list: List[SimpleNamespace] = []

    for year in sorted(by_year.keys()):
        year_reports = by_year[year]
        prev_year_annual = by_year.get(year - 1, {}).get(0)
        for q in quarter_order:
            if q not in year_reports:
                continue
            report = year_reports[q]
            prev_cum = get_prev_cumulative(db, report)
            if q != 1 and prev_cum is None:
                continue
            balance_base = prev_cum or prev_year_annual
            derived = derive_single_quarter(report, prev_cum, balance_base=balance_base)
            derived_list.append(derived)

    return derived_list
