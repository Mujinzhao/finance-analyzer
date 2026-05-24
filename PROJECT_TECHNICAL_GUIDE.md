# Finance Analyzer Technical Guide

Last updated: 2026-04-26

## 1. Project Overview

Finance Analyzer is a full-stack financial statement analysis platform for Chinese A-share companies.

- **Backend** : FastAPI + SQLAlchemy + SQLite, port 8000
- **Frontend**: React 19 + TypeScript + Ant Design 6 + ECharts 6, port 3000
- **AI**: DeepSeek API for PDF parsing and narrative report generation
- **Core use case**: Upload company reports (Excel/PDF), parse data, compute 40+ financial indicators, display multi-page analysis dashboard, support cumulative vs. single-quarter views, AI-generated investment reports.

Core methodology from《手把手教你读财报》(唐朝).

---

## 2. Repository Structure

```
finance-analyzer/
├── start.sh                              # Start backend + frontend
├── stop.sh                               # Stop both services via PID file + port fallback
├── 00-complete-spec.md                   # Original full spec (may be stale vs. current code)
├── PROJECT_TECHNICAL_GUIDE.md            # This document
├── ENHANCEMENT_SUMMARY.md                # Enhancement changelog (v1.0, 2026-04-19)
├── TODO.md
├── backend/
│   ├── main.py                           # FastAPI app, all API routes, service orchestration
│   ├── config.py                         # DeepSeek API key / base URL / model config
│   ├── models/
│   │   └── database.py                   # SQLAlchemy models + field-label dictionaries
│   ├── parsers/
│   │   ├── excel_parser.py               # Excel extraction: Chinese→English field mapping
│   │   └── pdf_parser.py                # PDF extraction: DeepSeek Vision + heuristic fallback
│   ├── analyzers/
│   │   ├── ratio_analyzer.py             # 40+ financial metrics, single-period + multi-period
│   │   ├── quarter_deriver.py            # Single-quarter derivation from cumulative reports
│   │   ├── risk_detector.py              # 12 risk rules with scoring
│   │   ├── valuation.py                  # DCF, relative valuation, economic goodwill
│   │   └── ai_summary.py                # DeepSeek-generated 6-section markdown report
│   ├── db/finance.db                     # SQLite database (auto-created)
│   ├── uploads/                          # Uploaded report files
│   ├── templates/                        # Excel upload template (auto-generated)
│   ├── logs/                             # pdf_parser.log
│   └── tests/test_core.py               # Backend integration tests
├── frontend/
│   ├── public/index.html
│   ├── src/
│   │   ├── App.tsx                       # Layout + menu + routing + global state
│   │   ├── App.css
│   │   ├── index.tsx
│   │   ├── types/index.ts                # TypeScript type definitions
│   │   ├── utils/
│   │   │   ├── api.ts                    # Axios API client wrappers
│   │   │   └── format.ts                # Money/percent formatting, labels, colors
│   │   └── pages/
│   │       ├── Upload/UploadPage.tsx
│   │       ├── Overview/OverviewPage.tsx          # Executive dashboard
│   │       ├── Growth/GrowthPage.tsx              # Growth analysis
│   │       ├── Solvency/SolvencyPage.tsx          # Solvency & debt coverage
│   │       ├── Efficiency/EfficiencyPage.tsx      # Turnover & cash conversion cycle
│   │       ├── QualityScore/QualityScorePage.tsx  # 5-dimension financial quality score
│   │       ├── BalanceSheet/BalanceSheetPage.tsx
│   │       ├── IncomeStatement/IncomeStatementPage.tsx
│   │       ├── CashFlow/CashFlowPage.tsx
│   │       ├── RiskAlert/RiskAlertPage.tsx
│   │       ├── Trend/TrendPage.tsx
│   │       ├── Valuation/ValuationPage.tsx
│   │       ├── Compare/ComparePage.tsx
│   │       └── AIAnalysis/AIAnalysisPage.tsx
│   └── tsconfig.json
└── logs/                                 # Runtime logs (backend.log, frontend.log)
```

---

## 3. Startup and Runtime

### 3.1 Startup

```bash
bash start.sh     # starts backend on :8000, frontend on :3000
bash stop.sh      # kills both services (PID file + port fallback)
```

The scripts auto-detect bash vs. sh and re-exec with bash if needed. PIDs are saved to `.run/services.pid`.

### 3.2 Service Endpoints

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://127.0.0.1:3000`
- `GET /` on backend returns `{"message": "财报全景分析平台 API 运行中"}`

---

## 4. Configuration

### 4.1 Backend Dependencies

```
fastapi, uvicorn, python-multipart, openpyxl, pandas, numpy,
pydantic, aiosqlite, sqlalchemy, httpx, PyMuPDF
```

### 4.2 AI Provider Config (`backend/config.py`)

Priority chain:
1. `DEEPSEEK_API_KEY` → `OPENAI_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY`
2. `DEEPSEEK_BASE_URL` → `OPENAI_BASE_URL` → `ANTHROPIC_BASE_URL` → `https://api.deepseek.com`
3. `DEEPSEEK_MODEL` → `OPENAI_MODEL` → `CLAUDE_MODEL` → `deepseek-chat`

**Known issue**: A hardcoded fallback DeepSeek API key exists in config.py. Should be migrated to env-only.

---

## 5. Database Design

**File**: `backend/models/database.py`

Three tables:

| Table | Purpose |
|-------|---------|
| `companies` | Company info: name, industry, stock_code |
| `financial_reports` | ~100 columns covering all 3 statements (balance sheet, income, cash flow) |
| `ai_summaries` | Cached AI-generated markdown reports, keyed by (company_id, year, quarter) |

### 5.1 Key Constants

```python
BALANCE_FIELDS : Dict[str, str]   # ~40 fields, e.g. "货币资金" → "cash_and_equivalents"
INCOME_FIELDS  : Dict[str, str]   # ~22 fields
CASH_FLOW_FIELDS: Dict[str, str]  # ~30 fields
ALL_FINANCIAL_FIELDS: List[str]   # All ~100 field keys concatenated
INCOME_POINT_IN_TIME_FIELDS: set  # {"total_shares"} — not differenced in single-quarter mode
```

### 5.2 Report Quarters

- `quarter=0`: Annual report (Jan-Dec cumulative)
- `quarter=1`: Q1 report (Jan-Mar cumulative)
- `quarter=2`: Semi-annual report (Jan-Jun cumulative)
- `quarter=3`: Q3 report (Jan-Sep cumulative)

All are cumulative within the fiscal year, per Chinese accounting standards.

---

## 6. Backend Architecture

### 6.1 API Endpoints (`backend/main.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/api/companies` | Create company |
| GET | `/api/companies` | List all companies + reports |
| DELETE | `/api/companies/{id}` | Delete company, reports, AI cache |
| GET | `/api/template` | Download Excel upload template |
| POST | `/api/upload` | Upload report (.xlsx/.pdf), auto-parse |
| GET | `/api/reports/{id}` | Report detail (grouped by statement) |
| PUT | `/api/reports/{id}` | Update report fields, clear AI cache |
| DELETE | `/api/reports/{id}` | Delete single report |
| DELETE | `/api/companies/{id}/reports?year=` | Delete all reports in a year |
| GET | `/api/reports/{id}/extraction-compare` | Compare extracted vs. source values |
| GET | `/api/analysis/{id}?year=&quarter=&view=` | **Single-period analysis** (40+ metrics) |
| GET | `/api/trend/{id}?view=` | **Multi-period trend** (30+ metrics × time) |
| POST | `/api/valuation/dcf` | DCF calculation |
| GET | `/api/valuation/{id}?year=&view=` | Company valuation (relative + goodwill + FCF) |
| GET | `/api/ai-summary/{id}?year=&quarter=&regenerate=&view=` | AI markdown report (cached) |
| GET | `/api/compare?company_ids=1,2&year=` | Multi-company comparison |

### 6.2 View Mode (Cumulative / Single-Quarter)

All analysis endpoints accept `?view=cumulative` (default) or `?view=single_quarter`.

#### Background

Chinese A-share quarterly reports are **cumulative** (year-to-date). To see true single-quarter performance, data must be differenced:

| Single Quarter | Derivation |
|----------------|-----------|
| Q1 | Q1 cumulative (no predecessor) |
| Q2 | H1 cumulative − Q1 cumulative |
| Q3 | Q3 cumulative − H1 cumulative |
| Q4 | Annual cumulative − Q3 cumulative |

**Critical rule**: Balance sheet fields (point-in-time snapshots) and `total_shares` are **copied as-is**, not differenced. Only income statement and cash flow fields are differenced.

#### Implementation (`backend/analyzers/quarter_deriver.py`)

- `derive_single_quarter(report, prev_cumulative) → SimpleNamespace` — core derivation
- `get_prev_cumulative(db, report) → FinancialReport|None` — predecessor lookup
- `derive_for_analysis(db, company_id, year, quarter) → (derived, prev_year_derived)` — for single-period endpoints
- `derive_all_single_quarter_reports(db, company_id) → list[SimpleNamespace]` — for trend endpoint

Derivation happens at the API layer (on-the-fly, no database storage). `SimpleNamespace` proxies mimic `FinancialReport` attribute access so all downstream analyzers work unchanged.

When `view=single_quarter`:
- `/api/analysis` uses `derive_for_analysis` instead of direct report query
- `/api/trend` uses `derive_all_single_quarter_reports` and computes QoQ for all consecutive periods
- `/api/ai-summary` derives report on-the-fly, skips caching
- `/api/valuation` derives report before computing relative valuation metrics

### 6.3 Parsing Pipeline

#### Excel Parser (`backend/parsers/excel_parser.py`)
- Reads all sheets, matches A-column Chinese item names → DB field names
- Handles thousand separators, bracket negatives, "万元" → 元 conversion
- "基本信息" sheet extracts `total_shares` and `dividends_paid`
- Generates upload template with 4 sheets (基本信息, 资产负债表, 利润表, 现金流量表)

#### PDF Parser (`backend/parsers/pdf_parser.py`)
- **Phase 1 — Page Detection**: PyMuPDF renders pages at 100 DPI, batches of 10 sent to DeepSeek Vision
- **Phase 2 — Data Extraction**: Detected pages rendered at 300 DPI, DeepSeek extracts Chinese-named items as JSON
- **Refinement**: `_refine_statement_pages()` scores candidates, filters non-table pages (TOC, etc.)
- **Expansion**: `_expand_adjacent_pages()` includes spillover pages (next 1-2 pages with financial data)
- **Fallback**: `_heuristic_extract()` uses regex to find items + numbers when DeepSeek returns non-JSON

### 6.4 Analysis Layer (`backend/analyzers/ratio_analyzer.py`)

#### `analyze_single_report(r)` — 10 sections:

| Section | Metrics |
|---------|---------|
| `asset_structure` | cash_ratio, investment/operating/production assets + ratios, current/non-current ratios |
| `liability_structure` | interest-bearing debt, non-interest-bearing debt, ratios |
| `safety` | current_ratio, quick_ratio, cash_debt_ratio, cash_short_debt_ratio, net_debt_ratio, interest_coverage, debt_to_asset_ratio, equity_ratio, equity_multiplier, equity_liability_ratio, ocf_to_interest_debt, ocf_to_current_liabilities, ocf_to_all_debt |
| `asset_quality` | receivable/revenue%, inventory/revenue%, goodwill/equity%, construction/fixed%, heavy_asset_ratio |
| `profitability` | gross_margin, operating_margin, net_margin, net_margin_parent, ROE, ROA, EPS, ROIC, internal_roa, equity_cash_recovery |
| `expense_ratios` | selling/admin/rd/finance expense ratios + total |
| `dupont` | net_profit_rate × asset_turnover × equity_multiplier = roe_dupont |
| `cash_flow` | free_cash_flow, ocf_to_net_profit, sales_cash_to_revenue, ocf_margin, capex_to_ocf, capex_to_revenue, 3-way cash totals, dividend_payout, portrait (8-type), quality_checks (5-item) |
| `turnover` | receivable/inventory/payable turnover + days, fixed_asset_turnover, total_asset_turnover, cash_conversion_cycle |
| `good_company_score` | 0-100: ROE>15%, gross_margin>40%, net_margin>15%, OCF>net_profit (25 each) |

#### `analyze_multi_period(reports, single_quarter_mode=False)` — time-series
Tracks 35+ metrics across all periods with YoY and QoQ.
- Cumulative mode: QoQ only for annual-to-annual
- Single-quarter mode: QoQ for all consecutive periods

### 6.5 Risk Detection (`backend/analyzers/risk_detector.py`)

12 rules across 4 categories:

| Category | Rules |
|----------|-------|
| Revenue (4) | AR growth >> revenue growth, OCF << net profit, gross margin > 80%, margin swing > 10pp |
| Expense (2) | Construction/fixed > 50%, impairment/net profit > 30% |
| Cash Flow (2) | Sales cash/revenue < 0.8, other receivables/total assets > 10% |
| Safety (4) | Debt ratio > 85% (high) / > 70% (medium), current ratio < 1, cash < 30% of interest debt, goodwill/equity > 30% |

Scoring: start 100, deduct 15 (high) / 8 (medium) / 25 (critical). Level: ≥80 safe, ≥50 warning, <50 danger.

### 6.6 Valuation (`backend/analyzers/valuation.py`)

- **DCF (老唐法)**: fair_value = FCF_year3 × (1/discount_rate), buy = fair/2, sell = fair×1.5
- **Relative**: EPS, BVPS, SPS (per-share metrics)
- **Economic Goodwill**: G = (ROE / market_return − 1) × equity
- **Temperature**: 0-100 scale with buy/sell/fair marks + advice tag

### 6.7 AI Summary (`backend/analyzers/ai_summary.py`)

- Sends full analysis JSON to DeepSeek `chat/completions`
- Requests 6-section markdown: 企业概况, 盈利能力, 资产质量, 现金流, 风险, 投资建议
- Cached in `ai_summaries` table by (company_id, year, quarter)
- Falls back to template text when API is unavailable
- Single-quarter mode skips caching (always regenerates)

---

## 7. Frontend Architecture

### 7.1 Global State (`frontend/src/App.tsx`)

```typescript
selectedCompanyId  // company selector
selectedYear       // year selector
selectedQuarter    // quarter selector
viewMode           // "cumulative" | "single_quarter" — Segmented toggle
analysisData       // single-period AnalysisResult
trendData          // multi-period TrendResult
loading            // global loading state
```

Data flow: selector change → `loadAnalysis()` → `Promise.all([getSingle, getTrend])` → set state → pages re-render via props.

### 7.2 Menu Structure (14 Pages)

| # | Key | Page | Icon | Purpose |
|---|-----|------|------|---------|
| 1 | upload | UploadPage | UploadOutlined | Company CRUD, report upload/edit/delete |
| 2 | dashboard | OverviewPage | DashboardOutlined | KPI cards, core trend, quality score dashboard |
| 3 | growth | GrowthPage | RiseOutlined | Revenue/profit/OCF growth rates, YoY bar chart |
| 4 | solvency | SolvencyPage | SafetyCertificateOutlined | Debt structure, cash flow debt coverage |
| 5 | efficiency | EfficiencyPage | ThunderboltOutlined | Turnover days, cash conversion cycle trend |
| 6 | quality | QualityScorePage | AuditOutlined | 5-dimension radar chart, system highlights |
| 7 | balance | BalanceSheetPage | BankOutlined | Asset/liability structure, safety, asset quality |
| 8 | income | IncomeStatementPage | FundOutlined | 3-margin gauges, expense pie, DuPont |
| 9 | cashflow | CashFlowPage | MoneyCollectOutlined | 3-way cash bars, portrait, 5-item quality checks |
| 10 | risk | RiskAlertPage | AlertOutlined | Risk score gauge, risk list table |
| 11 | trend | TrendPage | LineChartOutlined | Multi-metric trend lines, YoY/QoQ table |
| 12 | valuation | ValuationPage | DollarOutlined | DCF calculator, relative valuation, temperature |
| 13 | compare | ComparePage | ApartmentOutlined | Multi-company radar chart, comparison table |
| 14 | ai-analysis | AIAnalysisPage | RobotOutlined | AI markdown report, cached with regenerate |

### 7.3 API Client (`frontend/src/utils/api.ts`)

```
companyApi  : list / create / delete
reportApi   : upload / downloadTemplate / getDetail / update / delete / deleteByYear
analysisApi : getSingle(companyId, year?, quarter?, viewMode?) / getTrend(companyId, viewMode?) / compare(ids, year?)
valuationApi: getDCF(data) / getCompanyValuation(companyId, year?, viewMode?)
aiApi       : getSummary(companyId, year?, quarter?, regenerate?, viewMode?)
```

### 7.4 Format Utilities (`frontend/src/utils/format.ts`)

- `formatMoney(val)` — ≥1亿→"X.XX亿", ≥1万→"X.XX万"
- `formatPercent(val)` — "X.XX%", null→"-"
- `riskColor(level)` — safe→green, warning→yellow, danger→red
- `scoreColor(score)` — ≥75→green, ≥50→yellow, else→red
- `reportPeriodLabel(year, quarter, view?)` — cumulative: "2024年报"/"2024一季报"/"2024半年报"/"2024三季报"; single_quarter: "2024Q1单季"/"2024Q4单季"

---

## 8. Key Features Summary

### Implemented

- [x] Company CRUD with multi-report management
- [x] Excel parsing (openpyxl) with Chinese→English field mapping
- [x] PDF parsing (PyMuPDF + DeepSeek Vision, 2-stage with heuristic fallback)
- [x] 40+ financial indicators across 10 analysis categories
- [x] 12 risk detection rules with composite scoring
- [x] DCF valuation (老唐法), relative valuation, economic goodwill
- [x] 8-type cash flow portrait (蛮牛/老母鸡/奶牛/妖精/大出血/赌徒/混吃等死/骗吃骗喝)
- [x] 5-item cash flow quality checks
- [x] Good company score (0-100 / 4 dimensions)
- [x] 5-dimension financial quality score (profitability/growth/cash flow/solvency/efficiency)
- [x] Multi-period trend analysis with YoY/QoQ
- [x] Multi-company comparison (radar chart, up to 4 companies)
- [x] AI-generated 6-section markdown investment report (cached)
- [x] Report value editing (Drawer with InputNumber)
- [x] Extraction vs. source comparison endpoint
- [x] **Cumulative vs. single-quarter view toggle** (2026-04-26)
- [x] Granular report deletion (single + by-year)
- [x] Quarter-period selector in header
- [x] Excel template auto-generation

### Planned (Phase 3, not implemented)

- [ ] Auto data pull from 东方财富/同花顺 API
- [ ] Industry benchmarking & ranking
- [ ] PDF report export
- [ ] User system (login/register, per-user isolation)
- [ ] Stock portfolio tracking
- [ ] Real-time stock price integration
- [ ] Alert/notification push
- [ ] More valuation models (DDM, PEG, EV/EBITDA)
- [ ] Interactive AI Q&A
- [ ] Mobile/responsive adaptation

---

## 9. Design Principles

1. **All-Chinese UI** — labels, prompts, AI reports in Chinese
2. **Safe division** — `safe_div()` handles zero/None denominators
3. **Percentage format** — ratios × 100, e.g. 92.03 = 92.03%
4. **Currency formatting** — auto-convert to 亿/万
5. **Color semantics** — green=good, red=danger, yellow=warning
6. **Empty states** — `<Empty />` when no data, `<Spin />` when loading
7. **Upsert on re-upload** — same (company, year, quarter) updates rather than inserting duplicate
8. **Cache invalidation** — upload/delete auto-clears AI cache
9. **Derivation at read time** — single-quarter data computed on-the-fly, never stored

---

## 10. Known Issues

1. **Hardcoded API key** in `backend/config.py` — security risk, migrate to env-only
2. **Quarter fallback** — some endpoints default to quarter=0; quarterly-only data may show "未找到对应报表"
3. **PDF extraction reliability** — depends on DeepSeek JSON output quality; heuristic fallback is less accurate
4. **No frontend tests** — TypeScript compilation passes but no Jest/Playwright test suites
5. **Single-quarter AI summary** — always regenerates (not cached), uses DeepSeek tokens each time

---

## 11. Development Commands

```bash
# Start/stop
bash start.sh
bash stop.sh

# Backend
cd backend && source venv/bin/activate
pytest -q                                # Run tests
python3 -c "import ast; ast.parse(open('main.py').read())"  # Syntax check

# Frontend
cd frontend
npx tsc --noEmit                         # TypeScript type check
npm test                                 # (no business tests currently)
```

---

## 12. Key Files for Future Work

| Task | Files to touch |
|------|---------------|
| Add new financial metric | `ratio_analyzer.py` → `types/index.ts` → page component |
| Add trend metric | `ratio_analyzer.py` `_series_value()` + `metrics_to_track` |
| Change parser behavior | `excel_parser.py` / `pdf_parser.py` (keep heuristic fallback) |
| Add API endpoint | `main.py` → `api.ts` → page component |
| Modify single-quarter logic | `quarter_deriver.py` |
| Change DB schema | `database.py` → `main.py` (create_tables auto-runs on startup) |

