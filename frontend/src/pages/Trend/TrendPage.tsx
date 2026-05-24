import React, { useMemo, useState } from 'react';
import { Alert, Card, Col, Empty, Row, Select, Table } from 'antd';
import ReactECharts from 'echarts-for-react';
import { TrendResult } from '../../types';
import { reportPeriodLabel } from '../../utils/format';

const metricLabels: Record<string, string> = {
  gross_margin: '毛利率', operating_margin: '营业利润率', net_margin: '净利率', roe: 'ROE', roa: 'ROA', roic: 'ROIC',
  current_ratio: '流动比率', quick_ratio: '速动比率', cash_debt_ratio: '现金债务比', cash_short_debt_ratio: '现金短债比', net_debt_ratio: '净负债率', interest_coverage: '利息保障倍数', debt_to_asset_ratio: '资产负债率',
  equity_ratio: '权益比率', interest_bearing_debt_ratio: '有息负债率', heavy_asset_ratio: '重资产率',
  free_cash_flow: '自由现金流', ocf_to_net_profit: '经营/净利', ocf_margin: '经营现金流率', capex_to_ocf: '资本开支/经营现金流',
  asset_turnover: '总资产周转率(杜邦)', total_asset_turnover: '总资产周转率', fixed_asset_turnover: '固定资产周转率', inventory_turnover: '存货周转率',
  receivable_days: '应收天数', inventory_days: '存货天数', payable_days: '应付天数',
  selling_expense_ratio: '销售费用率', admin_expense_ratio: '管理费用率', rd_expense_ratio: '研发费用率',
  finance_expense_ratio: '财务费用率', total_expense_ratio: '费用率合计',
  revenue: '营收', net_profit: '净利润', net_profit_parent: '归母净利润', operating_profit: '营业利润',
  total_assets: '总资产', total_equity: '净资产', total_liabilities: '总负债',
  cash_and_equivalents: '货币资金', accounts_receivable: '应收账款', inventory: '存货',
  internal_roa: '内部资产收益率', equity_cash_recovery: '净资产现金回收率',
  interest_income_to_avg_cash: '利息收入/货币资金', ebit: 'EBIT',
  receivable_to_revenue: '应收/营收', score: '好企业评分',
  cash_conversion_cycle: '现金转换周期', cash_ratio: '货币资金占比', eps: 'EPS',
  bargaining_power: '议价能力指数',
  net_cash_from_operations: '经营现金流', net_cash_from_investing: '投资现金流', net_cash_from_financing: '筹资现金流',
};

const scaleMetrics = new Set([
  'free_cash_flow', 'revenue', 'net_profit', 'net_profit_parent', 'operating_profit',
  'total_assets', 'total_equity', 'total_liabilities',
  'cash_and_equivalents', 'accounts_receivable', 'inventory', 'ebit',
  'net_cash_from_operations', 'net_cash_from_investing', 'net_cash_from_financing',
]);

const toPeriodLabel = (period: string, view?: string) => {
  const m = period.match(/^(\d{4})(?:Q(\d))?$/);
  if (!m) return period;
  const year = Number(m[1]);
  const quarter = m[2] ? Number(m[2]) : 0;
  return reportPeriodLabel(year, quarter, view);
};

const TrendPage: React.FC<{ trendData: TrendResult | null; loading: boolean }> = ({ trendData }) => {
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['gross_margin', 'net_margin', 'roe']);

  if (!trendData?.trend?.metrics) return <Empty />;

  const view = trendData.view_mode;
  const periods = trendData.trend.periods;
  const periodLabels = periods.map((p) => toPeriodLabel(p, view));
  const option = useMemo(() => ({
    tooltip: { trigger: 'axis' },
    legend: { data: selectedMetrics.map((m) => metricLabels[m] || m) },
    xAxis: { type: 'category', data: periodLabels },
    yAxis: [{ type: 'value', name: '比率' }, { type: 'value', name: '金额' }],
    series: selectedMetrics.map((m) => ({
      name: metricLabels[m] || m,
      type: 'line',
      smooth: true,
      yAxisIndex: scaleMetrics.has(m) ? 1 : 0,
      data: trendData.trend.metrics[m]?.values || [],
    })),
  }), [periodLabels, selectedMetrics, trendData]);

  const tableData = periods.map((p, idx) => {
    const row: any = { period: toPeriodLabel(p, view), key: p };
    selectedMetrics.forEach((m) => {
      row[`${m}_yoy`] = trendData.trend.metrics[m]?.yoy?.[idx];
      row[`${m}_qoq`] = trendData.trend.metrics[m]?.qoq?.[idx];
    });
    return row;
  });

  const columns: any[] = [{ title: '期间', dataIndex: 'period', key: 'period', fixed: 'left' }];
  selectedMetrics.forEach((m) => {
    columns.push({
      title: `${metricLabels[m] || m}同比`,
      dataIndex: `${m}_yoy`,
      key: `${m}_yoy`,
      render: (v: number | null) => v === null || v === undefined ? '-' : <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span>,
    });
    columns.push({
      title: `${metricLabels[m] || m}环比`,
      dataIndex: `${m}_qoq`,
      key: `${m}_qoq`,
      render: (v: number | null) => v === null || v === undefined ? '-' : <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span>,
    });
  });

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title="指标选择">
          <Select
            mode="multiple"
            style={{ width: '100%' }}
            value={selectedMetrics}
            onChange={setSelectedMetrics}
            options={Object.keys(metricLabels).map((k) => ({ label: metricLabels[k], value: k }))}
          />
        </Card>
      </Col>
      <Col span={24}><Card title="趋势图"><ReactECharts option={option} style={{ height: 360 }} notMerge={true} /></Card></Col>
      <Col span={24}>
        <Card title="同比/环比">
          <Alert type="info" showIcon style={{ marginBottom: 12 }} message={
            view === 'single_quarter'
              ? "环比为单季度环比，展示逐季变动趋势；同比为相同单季度的年度对比。"
              : "环比仅在可比口径下展示（当前为年报对年报）；累计口径季度（Q1/半年报/三季报）环比以 - 表示。"
          } />
          <Table scroll={{ x: true }} columns={columns} dataSource={tableData} pagination={false} />
        </Card>
      </Col>
    </Row>
  );
};

export default TrendPage;
