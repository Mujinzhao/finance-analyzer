import React from 'react';
import { Card, Col, Descriptions, Empty, Row, Statistic, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent } from '../../utils/format';

const IncomeStatementPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const p = data.analysis.profitability;
  const e = data.analysis.expense_ratios;
  const d = data.analysis.dupont;
  const ps = data.analysis.profit_structure;
  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const gauge = (name: string, v: number | null | undefined) => ({
    series: [{
      type: 'gauge',
      min: 0, max: 100,
      startAngle: 200, endAngle: -20,
      detail: { formatter: '{value}%' },
      data: [{ value: Number(v || 0), name }],
    }],
  });

  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [{
      type: 'pie', radius: '70%',
      data: [
        { name: '销售费用率', value: Number(e.selling_expense_ratio || 0) },
        { name: '管理费用率', value: Number(e.admin_expense_ratio || 0) },
        { name: '研发费用率', value: Number(e.rd_expense_ratio || 0) },
        { name: '财务费用率', value: Math.abs(Number(e.finance_expense_ratio || 0)) },
      ],
    }],
  };

  const marginTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['毛利率', '营业利润率', '净利率'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '毛利率', type: 'line', smooth: true, data: m.gross_margin?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '营业利润率', type: 'line', smooth: true, data: m.operating_margin?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '净利率', type: 'line', smooth: true, data: m.net_margin?.values || [], lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
    ],
  } : null;

  const profitTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis', formatter: (params: any) => params.map((p: any) => `${p.marker} ${p.seriesName}: ${formatMoney(p.value)}`).join('<br/>') },
    legend: { data: ['营收', '营业利润', '归母净利润'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatMoney(v) } },
    series: [
      { name: '营收', type: 'bar', data: m.revenue?.values || [], barWidth: '30%', itemStyle: { color: '#91cc75', opacity: 0.8 } },
      { name: '营业利润', type: 'line', smooth: true, data: m.operating_profit?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '归母净利润', type: 'line', smooth: true, data: m.net_profit_parent?.values || [], lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
    ],
  } : null;

  const expenseTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['销售费用率', '管理费用率', '研发费用率', '财务费用率'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '销售费用率', type: 'line', smooth: true, data: m.selling_expense_ratio?.values || [], lineStyle: { color: '#5470c6' }, itemStyle: { color: '#5470c6' } },
      { name: '管理费用率', type: 'line', smooth: true, data: m.admin_expense_ratio?.values || [], lineStyle: { color: '#91cc75' }, itemStyle: { color: '#91cc75' } },
      { name: '研发费用率', type: 'line', smooth: true, data: m.rd_expense_ratio?.values || [], lineStyle: { color: '#fac858' }, itemStyle: { color: '#fac858' } },
      { name: '财务费用率', type: 'line', smooth: true, data: m.finance_expense_ratio?.values || [], lineStyle: { color: '#ee6664' }, itemStyle: { color: '#ee6664' } },
    ],
  } : null;

  const nonRecurringItems = [
    { label: '投资收益占比', value: ps?.investment_income_ratio },
    { label: '公允价值变动占比', value: ps?.fair_value_change_ratio },
    { label: '其他收益(政府补助)占比', value: ps?.other_income_ratio },
    { label: '资产处置收益占比', value: ps?.asset_disposal_ratio },
    { label: '非经常性合计占比', value: ps?.non_recurring_ratio },
  ];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}><Card title="毛利率"><ReactECharts option={gauge('毛利率', p.gross_margin)} style={{ height: 220 }} /></Card></Col>
      <Col xs={24} lg={8}><Card title="营业利润率"><ReactECharts option={gauge('营业利润率', p.operating_margin)} style={{ height: 220 }} /></Card></Col>
      <Col xs={24} lg={8}><Card title="净利率"><ReactECharts option={gauge('净利率', p.net_margin)} style={{ height: 220 }} /></Card></Col>

      <Col xs={12} lg={4}><Card><Statistic title="ROE" value={formatPercent(p.roe)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="ROA" value={formatPercent(p.roa)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="ROIC" value={formatPercent(p.roic)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="EPS" value={p.eps || 0} precision={4} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="EBIT" value={formatMoney(p.ebit)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="利息收入/货币资金" value={formatPercent(p.interest_income_to_avg_cash)} /></Card></Col>

      {marginTrendOption && (
        <Col span={24}><Card title="利润率趋势"><ReactECharts option={marginTrendOption} style={{ height: 320 }} /></Card></Col>
      )}
      {profitTrendOption && (
        <Col span={24}><Card title="收入利润趋势"><ReactECharts option={profitTrendOption} style={{ height: 320 }} /></Card></Col>
      )}

      <Col xs={24} lg={12}><Card title="费用率构成"><ReactECharts option={pieOption} style={{ height: 260 }} /></Card></Col>
      <Col xs={24} lg={12}>
        <Card title="杜邦分析">
          <Descriptions column={1}>
            <Descriptions.Item label="ROE 分解">
              {formatPercent(d.net_profit_rate)} × {d.asset_turnover} × {d.equity_multiplier} = {formatPercent(d.roe_dupont)}
            </Descriptions.Item>
            <Descriptions.Item label="净利率">{formatPercent(d.net_profit_rate)}</Descriptions.Item>
            <Descriptions.Item label="总资产周转率">{d.asset_turnover}</Descriptions.Item>
            <Descriptions.Item label="权益乘数">{d.equity_multiplier}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>

      {expenseTrendOption && (
        <Col span={24}><Card title="费用率趋势"><ReactECharts option={expenseTrendOption} style={{ height: 300 }} /></Card></Col>
      )}

      <Col xs={24} lg={12}>
        <Card title="营业利润结构分析">
          <Descriptions column={1} size="small">
            {nonRecurringItems.map((item) => (
              <Descriptions.Item key={item.label} label={item.label}>
                {item.value != null ? `${item.value}%` : '-'}
              </Descriptions.Item>
            ))}
          </Descriptions>
          <Tag color={(ps?.non_recurring_ratio ?? 0) > 50 ? 'red' : (ps?.non_recurring_ratio ?? 0) > 30 ? 'orange' : 'green'} style={{ marginTop: 8 }}>
            {(ps?.non_recurring_ratio ?? 0) > 50 ? '非经常性收益占比过高，盈利质量偏弱' : (ps?.non_recurring_ratio ?? 0) > 30 ? '非经常性收益占比较高，需关注' : '盈利以经常性收益为主'}
          </Tag>
        </Card>
      </Col>

      <Col xs={24} lg={12}>
        <Card title="少数股东权益分析">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="归母ROE">{formatPercent(p.parent_roe)}</Descriptions.Item>
            <Descriptions.Item label="少数股东ROE">{formatPercent(p.minority_roe)}</Descriptions.Item>
            <Descriptions.Item label="ROE差异">{formatPercent(p.roe_gap)}</Descriptions.Item>
          </Descriptions>
          <Tag color={(p.roe_gap ?? 0) > 20 ? 'orange' : 'green'} style={{ marginTop: 8 }}>
            {(p.roe_gap ?? 0) > 20 ? '归母ROE显著高于少数股东ROE，关注是否存在利益倾斜' : '归母与少数股东回报基本匹配'}
          </Tag>
        </Card>
      </Col>

      <Col span={24}>
        <Card title="盈利质量指标">
          <Descriptions column={2}>
            <Descriptions.Item label="扣非净利润偏离度">{formatPercent(p.non_recurring_impact)}</Descriptions.Item>
            <Descriptions.Item label="说明">|净利润-扣非净利润|/|净利润|，越大盈利质量越差</Descriptions.Item>
            <Descriptions.Item label="内部资产收益率">{formatPercent(p.internal_roa)}</Descriptions.Item>
            <Descriptions.Item label="说明">经营利润/(总资产-长期股权投资)，衡量核心资产收益能力</Descriptions.Item>
            <Descriptions.Item label="净资产现金回收率">{formatPercent(p.equity_cash_recovery)}</Descriptions.Item>
            <Descriptions.Item label="说明">经营现金流/净资产，衡量净资产产生现金的能力</Descriptions.Item>
            <Descriptions.Item label="利息收入/货币资金">{formatPercent(p.interest_income_to_avg_cash)}</Descriptions.Item>
            <Descriptions.Item label="说明">利息收入/平均货币资金余额，过低(&lt;0.3%)可能资金被占用</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );
};

export default IncomeStatementPage;
