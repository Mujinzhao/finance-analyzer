export interface ReportMeta {
  id: number;
  year: number;
  quarter: number;
  report_type: string;
}

export interface Company {
  id: number;
  name: string;
  industry?: string;
  stock_code?: string;
  reports?: ReportMeta[];
}

export interface RiskItem {
  category: string;
  name: string;
  severity: string;
  detail: string;
  threshold: string;
}

export interface RiskResult {
  score: number;
  level: 'safe' | 'warning' | 'danger';
  risks: RiskItem[];
  risk_count: Record<string, number>;
}

export interface CashFlowAnalysis {
  free_cash_flow: number;
  ocf_to_net_profit: number | null;
  sales_cash_to_revenue: number | null;
  ocf_margin?: number | null;
  capex_to_ocf?: number | null;
  capex_to_revenue?: number | null;
  net_cash_operations: number;
  net_cash_investing: number;
  net_cash_financing: number;
  cash_at_end: number;
  dividend_payout_ratio: number | null;
  portrait: { type: string; emoji: string; desc: string; risk: string };
  quality_checks: Record<string, boolean>;
}

export interface ProfitStructure {
  investment_income_ratio: number | null;
  fair_value_change_ratio: number | null;
  other_income_ratio: number | null;
  asset_disposal_ratio: number | null;
  non_recurring_ratio: number | null;
}

export interface RelativeValuation {
  eps: number | null;
  bvps: number | null;
  sps: number | null;
}

export interface ValuationData {
  relative: RelativeValuation;
  economic_goodwill: number;
  fcf: number;
  total_shares: number;
}

export interface DCFResult {
  enterprise_value: number;
  pv_forecast_period: number;
  pv_terminal_value: number;
  quick_fair_value: number;
  discount_rate: number;
  perpetual_growth: number;
  forecast_growth: number;
  forecast_years: number;
  fair_price_per_share?: number;
  quick_price_per_share?: number;
  buy_price_per_share?: number;
  sell_price_per_share?: number;
  current_price?: number;
  temperature?: number;
  advice?: string;
}

export interface SingleAnalysis {
  asset_structure: Record<string, number | null>;
  liability_structure: Record<string, number | null>;
  safety: Record<string, number | null>;
  asset_quality: Record<string, number | null>;
  profitability: Record<string, number | null>;
  expense_ratios: Record<string, number | null>;
  dupont: Record<string, number | null>;
  cash_flow: CashFlowAnalysis;
  turnover: Record<string, number | null>;
  good_company_score: { score: number; items: Record<string, { pass: boolean; value: number | null }> };
  profit_structure?: ProfitStructure;
  period_context?: { days: number; annualization_factor: number; uses_average_balance: boolean };
}

export interface GrowthAnalysis {
  revenue_growth: number | null;
  net_profit_parent_growth: number | null;
  net_cash_from_operations_growth: number | null;
  total_assets_growth: number | null;
  total_equity_growth: number | null;
  gross_margin_change: number | null;
  net_margin_change: number | null;
  growth_quality: string;
}

export interface FinancialQuality {
  total_score: number;
  sections: Record<string, { score: number; label: string }>;
  highlights: string[];
}

export interface AnalysisResult {
  company: Company;
  period: { year: number; quarter: number };
  analysis: SingleAnalysis;
  growth: GrowthAnalysis;
  financial_quality: FinancialQuality;
  risks: RiskResult;
  valuation: ValuationData;
  view_mode: "cumulative" | "single_quarter";
}

export interface TrendResult {
  company: Company;
  periods: { year: number; quarter: number }[];
  trend: {
    periods: string[];
    metrics: Record<string, { values: (number | null)[]; yoy: (number | null)[]; qoq: (number | null)[] }>;
  };
  view_mode: "cumulative" | "single_quarter";
}

export interface ReportField {
  field: string;
  label: string;
  value: number;
}

export interface ReportDetail {
  id: number;
  company_name: string;
  year: number;
  quarter: number;
  balance_sheet: ReportField[];
  income_statement: ReportField[];
  cash_flow: ReportField[];
}

export interface AISummaryResult {
  company: Company;
  period: { year: number; quarter: number };
  summary: string;
  cached: boolean;
  generated_at: string | null;
}
