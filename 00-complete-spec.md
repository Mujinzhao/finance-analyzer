# 财报全景分析平台 - 完整项目规格（Part 1: 总览 + 数据库 + 字段映射）

> 本文档的目标：任何 AI 或开发者仅凭此文档即可 100% 复刻整个项目。

---

## 一、项目简介

基于 Web 的中国 A 股财务报表全景分析平台。用户上传公司财报（Excel 或 PDF），系统自动解析数据、计算 30+ 财务指标、检测 12 条风险规则、生成可视化分析报告。支持 AI 智能分析（Claude API）和 PDF 自动解析（Claude Vision）。

核心方法论来自《手把手教你读财报》一书。

---

## 二、技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | React + TypeScript | React 19, TS 4.9 |
| UI 组件库 | Ant Design | 6.x |
| 图表库 | ECharts + echarts-for-react | ECharts 6 |
| HTTP 客户端 | Axios | 1.x |
| 后端框架 | FastAPI (Python) | 0.115+ |
| 数据库 | SQLite (via SQLAlchemy) | SQLAlchemy 2.0 |
| Excel 解析 | openpyxl | 3.1 |
| PDF 解析 | PyMuPDF (fitz) | 1.25+ |
| AI 能力 | Anthropic Claude API | anthropic SDK 0.40+ |
| 数据计算 | pandas + numpy | pandas 2.2, numpy 2.1 |

### 后端依赖 (requirements.txt)
```
fastapi==0.115.0
uvicorn==0.30.6
python-multipart==0.0.9
openpyxl==3.1.5
pandas==2.2.2
numpy==2.1.1
pydantic==2.9.1
aiosqlite==0.20.0
sqlalchemy==2.0.35
anthropic>=0.40.0
PyMuPDF>=1.25.0
```

### 前端依赖 (package.json)
```json
{
  "@ant-design/icons": "^6.1.0",
  "antd": "^6.3.3",
  "axios": "^1.13.6",
  "echarts": "^6.0.0",
  "echarts-for-react": "^3.0.6",
  "react": "^19.2.4",
  "react-dom": "^19.2.4",
  "react-router-dom": "^7.13.1",
  "react-scripts": "5.0.1",
  "typescript": "^4.9.5"
}
```

---

## 三、目录结构

```
finance-analyzer/
├── start.sh                           # 一键启动脚本
├── docs/                              # 项目文档
├── backend/                           # Python FastAPI 后端
│   ├── main.py                        # FastAPI 主应用（所有路由）
│   ├── config.py                      # 环境变量配置（API Key/模型名）
│   ├── requirements.txt
│   ├── create_sample_data.py          # 贵州茅台 2019-2023 样例数据
│   ├── models/
│   │   └── database.py                # SQLAlchemy 模型（Company, FinancialReport, AISummary）
│   ├── parsers/
│   │   ├── excel_parser.py            # Excel 解析器 + 模板生成 + 三大映射字典
│   │   └── pdf_parser.py             # PDF 解析器（Claude Vision 两阶段提取）
│   ├── analyzers/
│   │   ├── ratio_analyzer.py          # 核心指标计算引擎（30+ 指标）
│   │   ├── risk_detector.py           # 风险检测引擎（12 条规则）
│   │   ├── valuation.py               # 估值模块（DCF/相对估值/经济商誉）
│   │   └── ai_summary.py             # AI 分析报告生成（Claude API）
│   ├── db/finance.db                  # SQLite 数据库（运行时生成）
│   ├── uploads/                       # 上传文件存储
│   └── templates/                     # Excel 模板（运行时生成）
│
└── frontend/                          # React TypeScript 前端
    ├── package.json
    ├── public/index.html
    └── src/
        ├── App.tsx                    # 主应用（布局 + 路由 + 状态管理）
        ├── App.css
        ├── index.tsx
        ├── types/index.ts             # TypeScript 类型定义
        ├── utils/
        │   ├── api.ts                 # Axios API 调用封装
        │   └── format.ts             # 格式化工具函数
        └── pages/
            ├── Upload/UploadPage.tsx           # 数据上传 + 报表编辑
            ├── Dashboard/DashboardPage.tsx     # 综合仪表盘
            ├── BalanceSheet/BalanceSheetPage.tsx
            ├── IncomeStatement/IncomeStatementPage.tsx
            ├── CashFlow/CashFlowPage.tsx
            ├── RiskAlert/RiskAlertPage.tsx
            ├── Trend/TrendPage.tsx
            ├── Valuation/ValuationPage.tsx
            ├── Compare/ComparePage.tsx
            └── AIAnalysis/AIAnalysisPage.tsx   # AI 智能分析
```

---

## 四、配置文件

### backend/config.py
```python
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN", "") or os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", None)
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")
```

---

## 五、数据库设计

数据库文件：`backend/db/finance.db`（SQLite）

### 表 1: companies

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK, AUTO INCREMENT | 公司 ID |
| name | String(200) | NOT NULL | 公司名称 |
| industry | String(100) | 可空 | 所属行业 |
| stock_code | String(20) | 可空 | 股票代码 |
| created_at | DateTime | 默认当前时间 | 创建时间 |

关系：`reports` → 一对多关联 FinancialReport

### 表 2: financial_reports

#### 基本信息字段
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer, PK | 报表 ID |
| company_id | Integer, FK(companies.id) | 所属公司 |
| year | Integer, NOT NULL | 报告年度 |
| quarter | Integer, 默认 0 | 0=年报, 1-4=季报 |
| report_type | String(20) | "annual" 或 "quarterly" |
| file_path | String(500) | 上传文件路径 |
| created_at | DateTime | 创建时间 |

#### 资产负债表字段（全部 Float, 默认 0，单位：元）

**资产类：**
| 字段名 | 中文科目 |
|--------|----------|
| cash_and_equivalents | 货币资金 |
| trading_financial_assets | 交易性金融资产 |
| notes_receivable | 应收票据 |
| accounts_receivable | 应收账款 |
| prepayments | 预付款项 |
| other_receivables | 其他应收款 |
| inventory | 存货 |
| other_current_assets | 其他流动资产 |
| total_current_assets | 流动资产合计 |
| available_for_sale_assets | 可供出售金融资产/其他权益工具投资 |
| held_to_maturity | 持有至到期投资/其他债权投资 |
| long_term_equity_investment | 长期股权投资 |
| fixed_assets | 固定资产 |
| construction_in_progress | 在建工程 |
| intangible_assets | 无形资产 |
| goodwill | 商誉 |
| deferred_tax_assets | 递延所得税资产 |
| other_non_current_assets | 其他非流动资产 |
| total_non_current_assets | 非流动资产合计 |
| total_assets | 资产总计 |

**负债类：**
| 字段名 | 中文科目 |
|--------|----------|
| short_term_borrowings | 短期借款 |
| notes_payable | 应付票据 |
| accounts_payable | 应付账款 |
| advance_receipts | 预收款项/合同负债 |
| employee_compensation_payable | 应付职工薪酬 |
| taxes_payable | 应交税费 |
| other_current_liabilities | 其他流动负债 |
| total_current_liabilities | 流动负债合计 |
| long_term_borrowings | 长期借款 |
| bonds_payable | 应付债券 |
| deferred_tax_liabilities | 递延所得税负债 |
| other_non_current_liabilities | 其他非流动负债 |
| total_non_current_liabilities | 非流动负债合计 |
| total_liabilities | 负债合计 |

**所有者权益类：**
| 字段名 | 中文科目 |
|--------|----------|
| paid_in_capital | 实收资本/股本 |
| capital_reserve | 资本公积 |
| surplus_reserve | 盈余公积 |
| undistributed_profit | 未分配利润 |
| total_equity_parent | 归属于母公司所有者权益合计 |
| minority_interest | 少数股东权益 |
| total_equity | 所有者权益合计 |

#### 利润表字段
| 字段名 | 中文科目 |
|--------|----------|
| revenue | 营业收入 |
| cost_of_revenue | 营业成本 |
| taxes_and_surcharges | 税金及附加 |
| selling_expenses | 销售费用 |
| admin_expenses | 管理费用 |
| rd_expenses | 研发费用 |
| finance_expenses | 财务费用 |
| asset_impairment_loss | 资产减值损失 |
| credit_impairment_loss | 信用减值损失 |
| other_income | 其他收益 |
| investment_income | 投资收益 |
| fair_value_change_income | 公允价值变动收益 |
| asset_disposal_income | 资产处置收益 |
| operating_profit | 营业利润 |
| non_operating_income | 营业外收入 |
| non_operating_expenses | 营业外支出 |
| total_profit | 利润总额 |
| income_tax_expense | 所得税费用 |
| net_profit | 净利润 |
| net_profit_parent | 归属于母公司股东的净利润 |
| net_profit_minority | 少数股东损益 |
| total_shares | 总股本（万股） |
| dividends_paid | 分红总额 |

#### 现金流量表 - 经营活动
| 字段名 | 中文科目 |
|--------|----------|
| cash_from_sales | 销售商品、提供劳务收到的现金 |
| tax_refunds | 收到的税费返还 |
| other_cash_from_operations | 收到其他与经营活动有关的现金 |
| total_cash_from_operations | 经营活动现金流入小计 |
| cash_paid_for_goods | 购买商品、接受劳务支付的现金 |
| cash_paid_to_employees | 支付给职工以及为职工支付的现金 |
| taxes_paid | 支付的各项税费 |
| other_cash_paid_for_operations | 支付其他与经营活动有关的现金 |
| total_cash_paid_for_operations | 经营活动现金流出小计 |
| net_cash_from_operations | 经营活动产生的现金流量净额 |

#### 现金流量表 - 投资活动
| 字段名 | 中文科目 |
|--------|----------|
| cash_from_investment_withdrawal | 收回投资收到的现金 |
| cash_from_investment_income | 取得投资收益收到的现金 |
| cash_from_asset_disposal | 处置固定资产等收到的现金净额 |
| other_cash_from_investing | 收到其他与投资活动有关的现金 |
| total_cash_from_investing | 投资活动现金流入小计 |
| cash_paid_for_assets | 购建固定资产、无形资产等支付的现金 |
| cash_paid_for_investments | 投资支付的现金 |
| other_cash_paid_for_investing | 支付其他与投资活动有关的现金 |
| total_cash_paid_for_investing | 投资活动现金流出小计 |
| net_cash_from_investing | 投资活动产生的现金流量净额 |

#### 现金流量表 - 筹资活动
| 字段名 | 中文科目 |
|--------|----------|
| cash_from_borrowings | 取得借款收到的现金 |
| cash_from_equity_issuance | 吸收投资收到的现金 |
| other_cash_from_financing | 收到其他与筹资活动有关的现金 |
| total_cash_from_financing | 筹资活动现金流入小计 |
| cash_paid_for_debt | 偿还债务支付的现金 |
| cash_paid_for_dividends | 分配股利、利润或偿付利息支付的现金 |
| other_cash_paid_for_financing | 支付其他与筹资活动有关的现金 |
| total_cash_paid_for_financing | 筹资活动现金流出小计 |
| net_cash_from_financing | 筹资活动产生的现金流量净额 |
| net_increase_in_cash | 现金及现金等价物净增加额 |
| cash_at_beginning | 期初现金及现金等价物余额 |
| cash_at_end | 期末现金及现金等价物余额 |

### 表 3: ai_summaries

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer, PK | 摘要 ID |
| company_id | Integer, FK(companies.id) | 所属公司 |
| year | Integer, NOT NULL | 年度 |
| quarter | Integer, 默认 0 | 季度 |
| summary_text | Text, NOT NULL | AI 生成的 markdown 分析文本 |
| created_at | DateTime | 生成时间 |

---

## 六、Excel 字段映射字典

解析 Excel/PDF 时，中文科目名 → 英文数据库字段名的映射。一个英文字段可能对应多个中文名（兼容不同报表格式）。

### BALANCE_SHEET_MAP（55 条映射）
```python
{
    "货币资金": "cash_and_equivalents",
    "交易性金融资产": "trading_financial_assets",
    "应收票据": "notes_receivable",
    "应收账款": "accounts_receivable",
    "预付款项": "prepayments",
    "其他应收款": "other_receivables",
    "存货": "inventory",
    "其他流动资产": "other_current_assets",
    "流动资产合计": "total_current_assets",
    "可供出售金融资产": "available_for_sale_assets",
    "其他权益工具投资": "available_for_sale_assets",       # 同义映射
    "持有至到期投资": "held_to_maturity",
    "其他债权投资": "held_to_maturity",                    # 同义映射
    "长期股权投资": "long_term_equity_investment",
    "固定资产": "fixed_assets",
    "在建工程": "construction_in_progress",
    "无形资产": "intangible_assets",
    "商誉": "goodwill",
    "递延所得税资产": "deferred_tax_assets",
    "其他非流动资产": "other_non_current_assets",
    "非流动资产合计": "total_non_current_assets",
    "资产总计": "total_assets",
    "短期借款": "short_term_borrowings",
    "应付票据": "notes_payable",
    "应付账款": "accounts_payable",
    "预收款项": "advance_receipts",
    "合同负债": "advance_receipts",                        # 同义映射
    "应付职工薪酬": "employee_compensation_payable",
    "应交税费": "taxes_payable",
    "其他流动负债": "other_current_liabilities",
    "流动负债合计": "total_current_liabilities",
    "长期借款": "long_term_borrowings",
    "应付债券": "bonds_payable",
    "递延所得税负债": "deferred_tax_liabilities",
    "其他非流动负债": "other_non_current_liabilities",
    "非流动负债合计": "total_non_current_liabilities",
    "负债合计": "total_liabilities",
    "实收资本": "paid_in_capital",
    "股本": "paid_in_capital",                             # 同义映射
    "资本公积": "capital_reserve",
    "盈余公积": "surplus_reserve",
    "未分配利润": "undistributed_profit",
    "归属于母公司所有者权益合计": "total_equity_parent",
    "归属于母公司股东权益合计": "total_equity_parent",      # 同义映射
    "少数股东权益": "minority_interest",
    "所有者权益合计": "total_equity",
    "股东权益合计": "total_equity",                         # 同义映射
}
```

### INCOME_STATEMENT_MAP（24 条映射）
```python
{
    "营业收入": "revenue",
    "营业成本": "cost_of_revenue",
    "税金及附加": "taxes_and_surcharges",
    "销售费用": "selling_expenses",
    "管理费用": "admin_expenses",
    "研发费用": "rd_expenses",
    "财务费用": "finance_expenses",
    "资产减值损失": "asset_impairment_loss",
    "信用减值损失": "credit_impairment_loss",
    "其他收益": "other_income",
    "投资收益": "investment_income",
    "公允价值变动收益": "fair_value_change_income",
    "资产处置收益": "asset_disposal_income",
    "营业利润": "operating_profit",
    "营业外收入": "non_operating_income",
    "营业外支出": "non_operating_expenses",
    "利润总额": "total_profit",
    "所得税费用": "income_tax_expense",
    "净利润": "net_profit",
    "归属于母公司股东的净利润": "net_profit_parent",
    "归属于母公司所有者的净利润": "net_profit_parent",      # 同义映射
    "少数股东损益": "net_profit_minority",
    "总股本(万股)": "total_shares",
    "总股本": "total_shares",                               # 同义映射
    "分红总额": "dividends_paid",
}
```

### CASH_FLOW_MAP（34 条映射）
```python
{
    "销售商品、提供劳务收到的现金": "cash_from_sales",
    "收到的税费返还": "tax_refunds",
    "收到其他与经营活动有关的现金": "other_cash_from_operations",
    "经营活动现金流入小计": "total_cash_from_operations",
    "购买商品、接受劳务支付的现金": "cash_paid_for_goods",
    "支付给职工以及为职工支付的现金": "cash_paid_to_employees",
    "支付的各项税费": "taxes_paid",
    "支付其他与经营活动有关的现金": "other_cash_paid_for_operations",
    "经营活动现金流出小计": "total_cash_paid_for_operations",
    "经营活动产生的现金流量净额": "net_cash_from_operations",
    "收回投资收到的现金": "cash_from_investment_withdrawal",
    "取得投资收益收到的现金": "cash_from_investment_income",
    "处置固定资产等收到的现金净额": "cash_from_asset_disposal",
    "处置固定资产、无形资产和其他长期资产收回的现金净额": "cash_from_asset_disposal",  # 同义
    "收到其他与投资活动有关的现金": "other_cash_from_investing",
    "投资活动现金流入小计": "total_cash_from_investing",
    "购建固定资产、无形资产和其他长期资产支付的现金": "cash_paid_for_assets",
    "投资支付的现金": "cash_paid_for_investments",
    "支付其他与投资活动有关的现金": "other_cash_paid_for_investing",
    "投资活动现金流出小计": "total_cash_paid_for_investing",
    "投资活动产生的现金流量净额": "net_cash_from_investing",
    "取得借款收到的现金": "cash_from_borrowings",
    "吸收投资收到的现金": "cash_from_equity_issuance",
    "收到其他与筹资活动有关的现金": "other_cash_from_financing",
    "筹资活动现金流入小计": "total_cash_from_financing",
    "偿还债务支付的现金": "cash_paid_for_debt",
    "分配股利、利润或偿付利息支付的现金": "cash_paid_for_dividends",
    "支付其他与筹资活动有关的现金": "other_cash_paid_for_financing",
    "筹资活动现金流出小计": "total_cash_paid_for_financing",
    "筹资活动产生的现金流量净额": "net_cash_from_financing",
    "现金及现金等价物净增加额": "net_increase_in_cash",
    "期初现金及现金等价物余额": "cash_at_beginning",
    "期末现金及现金等价物余额": "cash_at_end",
}
```

### 解析规则
- 遍历 Excel 所有 Sheet 所有行，A 列为科目名，B 列为金额
- 匹配映射字典，转为 float
- **优先第一次出现的值**，不覆盖（`if field not in data`）
- "基本信息" Sheet 单独处理，提取 total_shares 和 dividends_paid
# 财报全景分析平台 - 完整项目规格（Part 2: 计算引擎 + 风险检测 + 估值 + AI）

---

## 七、指标计算引擎

文件：`backend/analyzers/ratio_analyzer.py`

### 通用函数
```python
def safe_div(a, b):     # b为0或None时返回None
def pct(value):          # 小数×100保留2位，如0.9203→92.03
```

### analyze_single_report(r) → dict

输入：FinancialReport ORM 对象。输出包含 10 个分析模块：

#### 1. asset_structure（资产结构）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 货币资金占比 | cash_ratio | 货币资金 ÷ 总资产 × 100 |
| 投资类资产 | investment_assets | 交易性金融资产 + 可供出售 + 持有至到期 + 长期股权投资 |
| 经营类资产 | operating_assets | 应收票据 + 应收账款 + 预付 + 其他应收 + 存货 |
| 生产类资产 | production_assets | 固定资产 + 在建工程 + 无形资产 |
| 流动资产占比 | current_asset_ratio | 流动资产合计 ÷ 总资产 × 100 |
| 非流动资产占比 | non_current_asset_ratio | 非流动资产合计 ÷ 总资产 × 100 |
| 投资类占比 | investment_assets_ratio | 投资类 ÷ 总资产 × 100 |
| 经营类占比 | operating_assets_ratio | 经营类 ÷ 总资产 × 100 |
| 生产类占比 | production_assets_ratio | 生产类 ÷ 总资产 × 100 |

#### 2. liability_structure（负债结构）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 有息负债 | interest_bearing_debt | 短期借款 + 长期借款 + 应付债券 |
| 无息负债 | non_interest_bearing_debt | 负债合计 - 有息负债 |
| 有息负债占比 | interest_bearing_ratio | 有息负债 ÷ 负债合计 × 100 |
| 流动负债占比 | current_liability_ratio | 流动负债合计 ÷ 负债合计 × 100 |

#### 3. safety（安全性）
| 指标 | 字段名 | 公式 | 达标条件 |
|------|--------|------|----------|
| 流动比率 | current_ratio | 流动资产 ÷ 流动负债 | ≥ 2 |
| 速动比率 | quick_ratio | (流动资产-存货) ÷ 流动负债 | ≥ 1 |
| 现金债务比 | cash_debt_ratio | 货币资金 ÷ 有息负债 | ≥ 1 |
| 资产负债率 | debt_to_asset_ratio | 负债合计 ÷ 总资产 × 100 | - |
| 净资产率 | equity_ratio | 所有者权益 ÷ 总资产 × 100 | - |
| 权益乘数 | equity_multiplier | 总资产 ÷ 所有者权益 | - |

#### 4. asset_quality（资产质量）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 应收/营收 | receivable_to_revenue | 应收账款 ÷ 营收 × 100 |
| 存货/营收 | inventory_to_revenue | 存货 ÷ 营收 × 100 |
| 商誉/净资产 | goodwill_to_equity | 商誉 ÷ 所有者权益 × 100 |
| 在建/固定 | construction_to_fixed | 在建工程 ÷ 固定资产 × 100 |
| 重资产率 | heavy_asset_ratio | (固定+在建) ÷ 总资产 × 100 |

#### 5. profitability（盈利能力）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 毛利率 | gross_margin | (营收-成本) ÷ 营收 × 100 |
| 营业利润率 | operating_margin | 营业利润 ÷ 营收 × 100 |
| 净利率 | net_margin | 净利润 ÷ 营收 × 100 |
| 归母净利率 | net_margin_parent | 归母净利润 ÷ 营收 × 100 |
| ROE | roe | 归母净利润 ÷ 归母净资产 × 100 |
| ROA | roa | 净利润 ÷ 总资产 × 100 |
| EPS | eps | 归母净利润 ÷ (总股本×10000) |
| ROIC | roic | NOPAT ÷ (权益+有息负债) × 100 |

ROIC 中 NOPAT = 营业利润 × (1 - 实际税率)，实际税率 = 所得税 ÷ 利润总额

#### 6. expense_ratios（费用率）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 销售费用率 | selling_expense_ratio | 销售费用 ÷ 营收 × 100 |
| 管理费用率 | admin_expense_ratio | 管理费用 ÷ 营收 × 100 |
| 研发费用率 | rd_expense_ratio | 研发费用 ÷ 营收 × 100 |
| 财务费用率 | finance_expense_ratio | 财务费用 ÷ 营收 × 100 |
| 总费用率 | total_expense_ratio | 四费之和 ÷ 营收 × 100 |

#### 7. dupont（杜邦分析）
```
ROE = 净利润率 × 总资产周转率 × 权益乘数
    = (净利润/营收) × (营收/总资产) × (总资产/权益)
```
| 指标 | 字段名 |
|------|--------|
| 净利润率 | net_profit_rate |
| 总资产周转率 | asset_turnover |
| 权益乘数 | equity_multiplier |
| 杜邦 ROE | roe_dupont |

#### 8. cash_flow（现金流分析）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 自由现金流 | free_cash_flow | 经营现金流净额 - 购建资产支出 |
| 经营/净利润 | ocf_to_net_profit | 经营现金流 ÷ 净利润 |
| 销售收现率 | sales_cash_to_revenue | 销售收现 ÷ 营收 |
| 分红率 | dividend_payout_ratio | 分红 ÷ 归母净利润 × 100 |

**企业画像（portrait）** — 根据三大现金流正负号分 8 种类型：
| 经营 | 投资 | 筹资 | 类型 | emoji | 风险 |
|------|------|------|------|-------|------|
| + | + | + | 蛮牛型 | 🐂 | low |
| + | + | - | 老母鸡型 | 🐔 | low |
| + | - | + | 奶牛型 | 🐄 | low |
| + | - | - | 妖精型 | 👻 | low |
| - | + | + | 大出血型 | 🩸 | high |
| - | - | + | 赌徒型 | 🎰 | high |
| - | + | - | 混吃等死型 | 💀 | high |
| - | - | - | 骗吃骗喝型 | 🤥 | critical |

**5 项快速检验（quality_checks）：**
| key | 检验内容 | 条件 |
|-----|----------|------|
| ocf_gt_net_profit | 经营现金流 > 净利润 | 直接比较 |
| sales_cash_gte_revenue | 销售收现 ≥ 营收 | 直接比较 |
| investing_negative | 投资活动为负（在扩张） | < 0 |
| cash_gte_interest_debt | 现金 ≥ 有息负债 | 直接比较 |
| dividend_reasonable | 分红率 20%-70% | 且归母净利润 > 0 |

#### 9. turnover（周转率）
| 指标 | 字段名 | 公式 |
|------|--------|------|
| 应收周转率 | receivable_turnover | 营收 ÷ 应收账款 |
| 应收天数 | receivable_days | 365 ÷ 应收周转率 |
| 存货周转率 | inventory_turnover | 营业成本 ÷ 存货 |
| 存货天数 | inventory_days | 365 ÷ 存货周转率 |
| 固定资产周转率 | fixed_asset_turnover | 营收 ÷ 固定资产 |
| 总资产周转率 | total_asset_turnover | 营收 ÷ 总资产 |

#### 10. good_company_score（好企业评分）
满分 100，4 个维度各 25 分：

| 维度 | key | 达标条件 |
|------|-----|----------|
| ROE > 15% | roe_gt_15 | 归母净利润/归母净资产 > 0.15 |
| 毛利率 > 40% | gross_margin_gt_40 | 毛利/营收 > 0.4 |
| 净利率 > 15% | net_margin_gt_15 | 净利润/营收 > 0.15 |
| 经营现金流 > 净利润 | ocf_gt_profit | 经营现金流 > 净利润 |

每项含 `pass`(bool) 和 `value`(实际值)。

### analyze_multi_period(reports) → dict

输入：按时间升序排列的 FinancialReport 列表。要求 ≥ 2 条记录，否则返回 `{}`。

输出：
```json
{
  "periods": ["2019", "2020", ...],
  "metrics": {
    "gross_margin": {"values": [...], "yoy": [...], "qoq": [...]},
    "revenue": {"values": [...], "yoy": [...], "qoq": [...]},
    ...
  }
}
```

跟踪的指标（21 个计算指标 + 13 个原始数值）：

**计算指标：** gross_margin, net_margin, roe, roa, roic, operating_margin, current_ratio, quick_ratio, cash_debt_ratio, debt_to_asset_ratio, free_cash_flow, ocf_to_net_profit, asset_turnover, equity_multiplier, receivable_to_revenue, inventory_turnover, selling_expense_ratio, admin_expense_ratio, rd_expense_ratio, score

**原始数值：** revenue, cost_of_revenue, net_profit, net_profit_parent, operating_profit, total_assets, total_liabilities, total_equity, net_cash_from_operations, net_cash_from_investing, net_cash_from_financing, accounts_receivable, inventory, cash_and_equivalents

---

## 八、风险检测引擎

文件：`backend/analyzers/risk_detector.py`

函数：`detect_risks(report, prev_report=None) → dict`

### 12 条检测规则

#### 收入端 (category="revenue")

| # | 规则 | 条件 | 严重度 |
|---|------|------|--------|
| 1 | 应收增速远超营收增速 | 需上期数据；应收增速 > 营收增速×1.5 且 > 10% | high |
| 2 | 经营现金流远低于净利润 | 经营现金流/净利润 < 0.5 且净利润 > 0 | high |
| 3 | 毛利率异常高 | 毛利率 > 80% | medium |
| 4 | 毛利率大幅波动 | 需上期；\|本期-上期\| > 10 个百分点 | medium |

#### 费用端 (category="expense")

| # | 规则 | 条件 | 严重度 |
|---|------|------|--------|
| 5 | 在建工程/固定资产过高 | 在建/固定 > 50% | medium |
| 6 | 资产减值占净利润过高 | \|减值\|/\|净利润\| > 30% | medium |

#### 现金流端 (category="cash_flow")

| # | 规则 | 条件 | 严重度 |
|---|------|------|--------|
| 7 | 销售收现率过低 | 销售收现/营收 < 0.8 且营收 > 0 | high |
| 8 | 其他应收款占比异常 | 其他应收/总资产 > 10% | medium |

#### 安全性 (category="safety")

| # | 规则 | 条件 | 严重度 |
|---|------|------|--------|
| 9 | 资产负债率过高 | > 85% → high；70%-85% → medium | high/medium |
| 10 | 流动比率过低 | 流动比率 < 1 | high |
| 11 | 货币资金不足覆盖有息负债 | 货币资金/有息负债 < 0.3 且有息负债 > 0 | high |
| 12 | 商誉占净资产过高 | 商誉/归母净资产 > 30% | medium |

### 风险评分

初始 100 分，每触发一条扣分：
- high: -15 分
- medium: -8 分
- critical: -25 分
- 最低 0 分

评级：score ≥ 80 → "safe" | ≥ 50 → "warning" | 其他 → "danger"

输出：
```json
{
  "score": 84,
  "level": "safe",
  "risks": [{"category": "...", "name": "...", "severity": "...", "detail": "...", "threshold": "..."}],
  "risk_count": {"high": 0, "medium": 2, "critical": 0}
}
```

---

## 九、估值模块

文件：`backend/analyzers/valuation.py`

### 1. DCF 简化估值法（老唐法）

```python
def dcf_simple(free_cash_flow_year3, discount_rate=0.09, perpetual_growth=0.03,
               current_price=None, total_shares=None) → dict
```

公式：
```
合理PE = 1 ÷ 折现率
合理估值 = 三年后自由现金流 × 合理PE
买点 = 合理估值 ÷ 2
卖点 = 合理估值 × 1.5
```

若提供 total_shares（万股）：
```
每股价 = 估值 ÷ (总股本 × 10000)
```

若提供 current_price，温度计：
```
温度(0-100) = (当前价 - 买入价) ÷ (卖出价 - 买入价) × 100
建议: ≤买入价→"严重低估" | ≤合理价→"低估区间" | ≤卖出价→"合理区间" | >卖出价→"高估"
```

### 2. 相对估值

```python
def relative_valuation(report) → dict  # {"eps", "bvps", "sps"}
```
- EPS = 归母净利润 ÷ (总股本 × 10000)
- BVPS = 归母净资产 ÷ (总股本 × 10000)
- SPS = 营收 ÷ (总股本 × 10000)

### 3. 经济商誉

```python
def economic_goodwill(roe, equity, market_avg_return=0.09) → float
```
G = (ROE ÷ 全社会平均回报率 - 1) × 净资产

---

## 十、PDF 解析器

文件：`backend/parsers/pdf_parser.py`

### 两阶段架构

**阶段 1 — 页面定位** `_find_statement_pages()`
- PyMuPDF 将全部页面渲染为 100 DPI 缩略图
- 每批 10 页发送给 Claude Vision
- 要求返回：`{"balance_sheet": [页码], "income_statement": [页码], "cash_flow": [页码]}`
- 只识别"合并"报表，忽略母公司单独报表

**阶段 2 — 数据提取** `_extract_statement_data()`
- 将定位页面以 300 DPI 高清渲染
- Prompt 中列出所有中文科目名（从 excel_parser 映射字典获取）
- 要求返回 JSON，key 为中文科目名，value 为数值（元）或 null
- 处理：万元/元单位转换、括号负数、千分位、"本期"列

**入口函数：**
```python
def parse_pdf(file_path, company_id, year, quarter=0) → dict
# 返回格式与 parse_excel() 完全一致
```

---

## 十一、AI 分析报告生成器

文件：`backend/analyzers/ai_summary.py`

```python
def generate_ai_summary(company_name, period, analysis, risks, valuation, trend=None) → str
```

**系统提示词：**
> 你是一位资深中国A股财务分析师，擅长撰写深度投资研究报告。你的分析风格参考《手把手教你读财报》一书的方法论，注重现金流分析和企业质地评估。请用专业但易懂的中文撰写分析报告。

**输出要求：**
- Markdown 格式，6 个章节（每个用 `##` 标题）：
  1. 企业概况总结
  2. 盈利能力分析
  3. 资产质量评估
  4. 现金流健康度
  5. 风险提示
  6. 投资建议
- 引用具体指标数值
- 总字数 1500-2000 字
- 输入为全部计算指标 JSON

**缓存机制：**
- 结果存入 `ai_summaries` 表
- 按 (company_id, year, quarter) 缓存
- 上传新数据或删除公司时自动清除缓存
- 前端可通过 `regenerate=true` 强制重新生成
# 财报全景分析平台 - 完整项目规格（Part 3: API + 前端）

---

## 十二、后端 API 端点

基础：FastAPI，端口 8000，CORS 全开放。

### 公司管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/companies | 创建公司。Body: `{name, industry?, stock_code?}` |
| GET | /api/companies | 获取所有公司及报表列表 |
| DELETE | /api/companies/{id} | 删除公司及所有报表和 AI 缓存 |

### 模板与上传

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/template | 下载 Excel 上传模板（4 个 Sheet） |
| POST | /api/upload | 上传报表。multipart: file + company_id + year + quarter。自动检测 .pdf/.xlsx 分发解析器 |

### 报表详情与编辑

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/reports/{id} | 获取单条报表全部字段，按三大报表分组返回（含中文标签） |
| PUT | /api/reports/{id} | 更新报表字段。Body: `{fields: {field_name: value, ...}}`。同时清除 AI 缓存 |

GET 响应格式：
```json
{
  "id": 5, "company_name": "贵州茅台", "year": 2023, "quarter": 0,
  "balance_sheet": [{"field": "cash_and_equivalents", "label": "货币资金", "value": 210500000000}, ...],
  "income_statement": [...],
  "cash_flow": [...]
}
```

### 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/analysis/{company_id}?year=&quarter= | 单期全景分析（analysis + risks + valuation） |
| GET | /api/trend/{company_id} | 多期趋势分析（periods + trend.metrics） |

### 估值

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/valuation/dcf | DCF 计算。Body: `{free_cash_flow_year3, discount_rate?, perpetual_growth?, current_price?, total_shares?}` |
| GET | /api/valuation/{company_id}?year= | 公司估值数据（relative + economic_goodwill + fcf） |

### AI 分析

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/ai-summary/{company_id}?year=&quarter=&regenerate=false | 获取 AI 分析报告，有缓存直接返回，无缓存或 regenerate=true 时生成 |

响应：
```json
{
  "company": {...}, "period": {...},
  "summary": "## 企业概况总结\n...",
  "cached": true,
  "generated_at": "2026-03-27T15:30:00"
}
```

### 多公司对比

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/compare?company_ids=1,2,3&year= | 多公司对比分析 |

---

## 十三、前端架构

### App.tsx 状态管理

```typescript
const [currentPage, setCurrentPage] = useState('upload');
const [companies, setCompanies] = useState<Company[]>([]);
const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
const [selectedYear, setSelectedYear] = useState<number | null>(null);
const [analysisData, setAnalysisData] = useState<AnalysisResult | null>(null);
const [trendData, setTrendData] = useState<TrendResult | null>(null);
const [loading, setLoading] = useState(false);
```

### 数据加载流程
1. 组件挂载 → `loadCompanies()` → GET /api/companies
2. 选择公司 → 清空 analysisData/trendData → 并行请求 analysis + trend
3. 选择年度 → 重新请求 analysis（带 year 参数）+ trend
4. analysisData/trendData 通过 props 传递给各页面

### 布局
```
┌──────────────────────────────────────────────┐
│ Sider(200px,dark)  │ Header(白底,公司/年度选择) │
│                    ├───────────────────────────│
│ 10 个菜单项         │ Content(灰底, 当前页面)    │
└──────────────────────────────────────────────┘
```

### 菜单项（10 个）
| key | icon | label | 组件 |
|-----|------|-------|------|
| upload | UploadOutlined | 数据上传 | UploadPage |
| dashboard | DashboardOutlined | 综合仪表盘 | DashboardPage |
| balance | BankOutlined | 资产负债表 | BalanceSheetPage |
| income | FundOutlined | 利润表 | IncomeStatementPage |
| cashflow | MoneyCollectOutlined | 现金流量表 | CashFlowPage |
| risk | AlertOutlined | 风险预警 | RiskAlertPage |
| trend | LineChartOutlined | 趋势分析 | TrendPage |
| valuation | DollarOutlined | 估值分析 | ValuationPage |
| compare | SwapOutlined | 多公司对比 | ComparePage |
| ai-analysis | RobotOutlined | AI 分析 | AIAnalysisPage |

### TypeScript 类型定义 (types/index.ts)

```typescript
interface Company { id: number; name: string; industry?: string; stock_code?: string; reports?: ReportMeta[] }
interface ReportMeta { id: number; year: number; quarter: number; report_type: string }
interface AnalysisResult { company: Company; period: {year, quarter}; analysis: SingleAnalysis; risks: RiskResult; valuation: any }
interface SingleAnalysis { asset_structure, liability_structure, safety, asset_quality, profitability, expense_ratios, dupont, cash_flow: CashFlowAnalysis, turnover, good_company_score }
interface CashFlowAnalysis { free_cash_flow, ocf_to_net_profit, sales_cash_to_revenue, net_cash_operations/investing/financing, cash_at_end, dividend_payout_ratio, portrait: {type, emoji, desc, risk}, quality_checks }
interface RiskResult { score: number; level: 'safe'|'warning'|'danger'; risks: RiskItem[]; risk_count }
interface RiskItem { category, name, severity, detail, threshold }
interface TrendResult { company, periods: PeriodAnalysis[], trend: {periods: string[], metrics} }
interface ReportField { field: string; label: string; value: number }
interface ReportDetail { id, company_name, year, quarter, balance_sheet/income_statement/cash_flow: ReportField[] }
interface AISummaryResult { company, period, summary: string, cached: boolean, generated_at: string|null }
```

### API 调用 (utils/api.ts)

```typescript
const api = axios.create({ baseURL: 'http://localhost:8000' });

companyApi.list/create/delete
reportApi.upload(formData, timeout:120000) / downloadTemplate / getDetail(id) / update(id, fields)
analysisApi.getSingle(companyId, year?) / getTrend(companyId) / compare(ids[], year?)
valuationApi.getDCF(data) / getCompanyValuation(companyId, year?)
aiApi.getSummary(companyId, year?, regenerate?, timeout:120000)
```

### 工具函数 (utils/format.ts)

```typescript
formatMoney(val)    // ≥1亿→"X.XX亿", ≥1万→"X.XX万", 否则"X.XX"
formatPercent(val)  // "X.XX%", null→"-"
formatNumber(val, decimals=2)
riskColor(level)    // safe→#52c41a, warning→#faad14, danger→#ff4d4f
scoreColor(score)   // ≥75→绿, ≥50→黄, 其他→红
```

---

## 十四、10 个页面组件规格

### 页面 1: UploadPage
**Props:** `{ companies, onRefresh }`

**功能：**
- 公司表格：名称/代码/行业/已上传报表(蓝色 Tag)/操作(上传/删除)
- 新建公司 Modal：name(必填)/industry/stock_code
- 上传报表 Modal：company_id/year/quarter/文件(.xlsx,.xls,.pdf)
  - PDF 时显示 Alert："PDF 文件将使用 AI 自动解析，处理时间约 30-60 秒"
- 下载 Excel 模板
- **报表编辑 Drawer**：点击报表 Tag 打开 720px Drawer
  - 3 个 Tabs：资产负债表/利润表/现金流量表
  - 每个 Tab 为 Table（科目名 | 金额），金额可点击编辑（InputNumber）
  - 修改项高亮蓝色，右上角显示修改数量 + 保存按钮
  - 关闭时如有未保存修改弹出确认对话框

### 页面 2: DashboardPage
**Props:** `{ data, trendData, loading }`

**布局：**
```
Row 1: [好企业评分卡(圆形进度+4项✅❌)] [企业现金流画像(大emoji+类型描述)]
Row 2: [ROE] [毛利率] [净利率] [资产负债率] [自由现金流] [经营/净利]  ← 6个Statistic卡
Row 3: [资产结构环形饼图(5类)] [三年趋势折线图(营收/净利/经营现金流)]
```

评分卡判断：ROE>15%, 毛利率>40%, 净利率>15%, 经营现金流>净利润

趋势图判断：`trendData?.trend?.metrics` 存在时才渲染图表，否则显示 Empty

### 页面 3: BalanceSheetPage
**Props:** `{ data, loading }`

1. 资产结构水平堆叠条形图（4 类资产占比）
2. 负债结构双饼图（有息 vs 无息、流动 vs 非流动）
3. 安全性 4 指标卡（流动比率≥2, 速动比率≥1, 现金债务比≥1, 资产负债率）
4. 资产质量 Descriptions 表（5 项百分比）

### 页面 4: IncomeStatementPage
**Props:** `{ data, loading }`

1. 盈利三率仪表盘（3 个 ECharts gauge：毛利率/营业利润率/净利率）
   - gauge: min=0, max=100, startAngle=200, endAngle=-20
2. 费用率饼图（4 费用率，财务费用取绝对值）
3. 杜邦分析 Card 布局：ROE = 净利率 × 周转率 × 权益乘数
4. 其他指标：ROA, ROIC, EPS

### 页面 5: CashFlowPage
**Props:** `{ data, loading }`

1. 三大活动柱状图（正绿 #52c41a，负红 #ff4d4f）
2. 企业画像卡（大 emoji 64px + 类型名 + 描述，背景色按 risk：low→#f6ffed, medium→#fffbe6, high→#fff2f0）
3. 自由现金流 Statistic（formatMoney，正绿负红）
4. 5 项检验 List（✅ CheckCircle 绿/❌ CloseCircle 红 + 文字）

### 页面 6: RiskAlertPage
**Props:** `{ data, trendData, loading }`

1. 综合风险评分圆环（0-100，颜色分级）
2. 风险分布统计 Tags（高/中/严重数量）
3. 风险清单 Table（类别/风险项/严重程度/详情/阈值）
4. 无风险时显示 Result 组件 "未检测到明显风险信号"

category 中文：revenue→收入端, expense→费用端, cash_flow→现金流端, safety→安全性

### 页面 7: TrendPage
**Props:** `{ trendData, loading }`

**内部状态：** `selectedMetrics: string[] = ['gross_margin', 'net_margin', 'roe']`

指标分 6 组（metricLabels 映射）：
- 盈利能力: gross_margin, operating_margin, net_margin, roe, roa, roic
- 安全性: current_ratio, quick_ratio, cash_debt_ratio, debt_to_asset_ratio
- 现金流: free_cash_flow, ocf_to_net_profit
- 效率: asset_turnover, inventory_turnover
- 费用: selling_expense_ratio, admin_expense_ratio, rd_expense_ratio
- 规模: revenue, net_profit, total_assets

**双 Y 轴：** scaleMetrics(free_cash_flow, revenue, net_profit, total_assets) 用金额轴，其他用比率轴

**同比/环比表：** 正值绿 #52c41a，负值红 #ff4d4f

### 页面 8: ValuationPage
**Props:** `{ data, companyId, loading }`

1. 相对估值指标（EPS/BVPS/SPS）
2. DCF 表单：future_fcf(必填)/discount_rate(0.09)/perpetual_growth_rate(0.03)/current_price/total_shares
3. 结果卡片：合理估值/买点(绿)/卖点(红)/合理PE + 每股价格
4. 温度计 ECharts（bar 渐变绿→黄→红 + scatter 三角标当前价 + markLine 买卖点）
5. 建议 Tag：低估→绿, 高估→红, 其他→蓝

### 页面 9: ComparePage
**Props:** `{ companies }`

**内部状态：** selectedIds(max 4), year, compareData, loading

1. 公司多选器（2-4 家）+ 年度选择
2. 雷达图 6 维度：毛利率(max100), 净利率(max100), ROE(max50), ROA(max30), 安全性=100-负债率(max100), 流动比率(max5)
3. 对比表（分组：盈利/安全/效率/评分，行合并 rowSpan）

颜色：`['#5470c6', '#91cc75', '#fac858', '#ee6666']`

### 页面 10: AIAnalysisPage
**Props:** `{ companyId, selectedYear }`

**内部状态：** data(AISummaryResult), loading, regenerating

**功能：**
- 无公司→Empty，加载中→Spin "AI 正在生成分析报告，首次约 10-20 秒..."
- 按 `## ` 分割 markdown 为多个 Card
- 每段 Card 标题带 emoji：企业概况🏢, 盈利📈, 资产🏦, 现金流💰, 风险⚠️, 投资💡
- 简易 markdown 渲染：`**bold**` → Text strong, `- ` → 缩进圆点
- 右上角：生成时间 + 缓存标签 + "重新生成"按钮

---

## 十五、启动脚本 (start.sh)

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/backend" && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
cd "$SCRIPT_DIR/frontend" && PORT=3000 npm start &
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
```

环境变量要求：
- `ANTHROPIC_AUTH_TOKEN` 或 `ANTHROPIC_API_KEY`：Claude API 密钥
- `ANTHROPIC_BASE_URL`（可选）：API 代理地址
- `CLAUDE_MODEL`（可选，默认 claude-opus-4-6）

初始化样例数据：`cd backend && python create_sample_data.py`（贵州茅台 2019-2023）

---

## 十六、设计原则

1. **全中文界面** — 所有文本、标签、提示均为中文
2. **安全除法** — 所有除法通过 `safe_div()` 处理，避免除零
3. **百分比统一** — 比率指标 ×100 转百分比（如 92.03 表示 92.03%）
4. **金额格式化** — 前端自动将大数转"亿"或"万"
5. **颜色语义** — 绿=良好, 红=危险, 黄=警告
6. **空状态处理** — 无数据显示 Empty，加载中显示 Spin
7. **数据不丢失** — 同期报表重复上传执行更新而非插入
8. **缓存失效** — 上传新数据/删除公司自动清除 AI 分析缓存

---

## 十七、长远规划

### Phase 3 方向（未实现）
1. **数据源自动拉取** — 接入东方财富/同花顺 API 自动获取上市公司财报数据，替代手动上传
2. **行业对标分析** — 按行业分类，与同行平均值/中位数对比，生成行业排名
3. **报告导出 PDF** — 将分析结果（含图表）导出为 PDF 投资研究报告
4. **用户系统** — 登录注册、分析历史保存、多用户隔离
5. **自选股组合** — 创建股票组合，跟踪多家公司的关键指标变化
6. **实时股价接入** — 接入行情 API，自动计算估值温度计的当前位置
7. **财报预警推送** — 定期检查已关注公司的风险变化，邮件/微信推送
8. **更多估值模型** — DDM 股息折现、PEG 估值、EV/EBITDA 等
9. **AI 对话分析** — 基于已有数据的交互式 AI 问答（"茅台的ROE为什么下降了？"）
10. **移动端适配** — 响应式布局或独立小程序

---

## 十八、样例数据

贵州茅台 2019-2023 年报数据（通过 `create_sample_data.py` 生成）：

| 年度 | 营收(亿) | 净利润(亿) | ROE | 毛利率 | 好企业评分 |
|------|---------|-----------|-----|--------|-----------|
| 2019 | 888.6 | 464.7 | 30.7% | 91.4% | 100 |
| 2020 | 979.9 | 516.0 | 30.3% | 91.5% | 100 |
| 2021 | 1094.6 | 577.0 | 28.6% | 91.6% | 100 |
| 2022 | 1241.8 | 655.0 | 29.9% | 91.8% | 100 |
| 2023 | 1505.6 | 810.0 | 31.0% | 92.0% | 100 |
