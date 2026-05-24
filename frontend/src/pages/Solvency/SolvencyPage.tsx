import React from 'react';
import { Card, Col, Empty, Row, Statistic, Table } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { formatPercent } from '../../utils/format';

const SolvencyPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const safety = data.analysis.safety;
  const liability = data.analysis.liability_structure;
  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const pieOption = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      data: [
        { name: '有息负债', value: liability.interest_bearing_debt || 0 },
        { name: '无息负债', value: liability.non_interest_bearing_debt || 0 },
      ],
    }],
  };

  const debtTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['资产负债率', '权益比率', '有息负债率', '净负债率'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '资产负债率', type: 'line', smooth: true, data: m.debt_to_asset_ratio?.values || [], lineStyle: { color: '#ff4d4f' }, itemStyle: { color: '#ff4d4f' } },
      { name: '权益比率', type: 'line', smooth: true, data: m.equity_ratio?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '有息负债率', type: 'line', smooth: true, data: m.interest_bearing_debt_ratio?.values || [], lineStyle: { color: '#faad14', type: 'dashed' }, itemStyle: { color: '#faad14' } },
      { name: '净负债率', type: 'line', smooth: true, data: m.net_debt_ratio?.values || [], lineStyle: { color: '#722ed1', type: 'dashed' }, itemStyle: { color: '#722ed1' } },
    ],
  } : null;

  const coverageTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['流动比率', '速动比率', '现金短债比'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value' },
    series: [
      { name: '流动比率', type: 'line', smooth: true, data: m.current_ratio?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '速动比率', type: 'line', smooth: true, data: m.quick_ratio?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '现金短债比', type: 'line', smooth: true, data: m.cash_short_debt_ratio?.values || [], lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
      { name: '利息保障倍数', type: 'line', smooth: true, data: m.interest_coverage?.values || [], lineStyle: { color: '#d97706', type: 'dashed' }, itemStyle: { color: '#d97706' } },
    ],
  } : null;

  const tableData = periods.map((p, idx) => ({
    key: p, period: p,
    dta: m.debt_to_asset_ratio?.values?.[idx], dta_yoy: m.debt_to_asset_ratio?.yoy?.[idx],
    cr: m.current_ratio?.values?.[idx], cr_yoy: m.current_ratio?.yoy?.[idx],
    qr: m.quick_ratio?.values?.[idx], qr_yoy: m.quick_ratio?.yoy?.[idx],
    csd: m.cash_short_debt_ratio?.values?.[idx], csd_yoy: m.cash_short_debt_ratio?.yoy?.[idx],
    ic: m.interest_coverage?.values?.[idx], ic_yoy: m.interest_coverage?.yoy?.[idx],
  }));

  const yoyColumns = [
    { title: '期间', dataIndex: 'period', key: 'period', fixed: 'left' as const },
    { title: '资产负债率', dataIndex: 'dta', key: 'dta', render: formatPercent },
    { title: '同比', dataIndex: 'dta_yoy', key: 'dta_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '流动比率', dataIndex: 'cr', key: 'cr', render: (v: any) => v?.toFixed(2) ?? '-' },
    { title: '同比', dataIndex: 'cr_yoy', key: 'cr_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '速动比率', dataIndex: 'qr', key: 'qr', render: (v: any) => v?.toFixed(2) ?? '-' },
    { title: '同比', dataIndex: 'qr_yoy', key: 'qr_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '现金短债比', dataIndex: 'csd', key: 'csd', render: (v: any) => v?.toFixed(2) ?? '-' },
    { title: '同比', dataIndex: 'csd_yoy', key: 'csd_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '利息保障倍数', dataIndex: 'ic', key: 'ic', render: (v: any) => v?.toFixed(2) ?? '-' },
    { title: '同比', dataIndex: 'ic_yoy', key: 'ic_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
  ];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} lg={4}><Card><Statistic title="资产负债率" value={formatPercent(safety.debt_to_asset_ratio)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="流动比率" value={safety.current_ratio || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="现金短债比" value={safety.cash_short_debt_ratio || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="利息保障倍数" value={safety.interest_coverage || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="速动比率" value={safety.quick_ratio || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="权益比率" value={formatPercent(safety.equity_ratio)} /></Card></Col>

      {debtTrendOption && (
        <Col span={24}><Card title="债务指标趋势"><ReactECharts option={debtTrendOption} style={{ height: 340 }} /></Card></Col>
      )}
      {coverageTrendOption && (
        <Col span={24}><Card title="偿债能力趋势"><ReactECharts option={coverageTrendOption} style={{ height: 340 }} /></Card></Col>
      )}

      <Col xs={24} lg={12}><Card title="债务结构"><ReactECharts option={pieOption} style={{ height: 300 }} /></Card></Col>
      <Col xs={24} lg={12}>
        <Card title="现金流债务覆盖">
          <Row gutter={[12, 12]}>
            <Col span={12}><Statistic title="现金债务比" value={safety.cash_debt_ratio?.toFixed(2) || '-'} /></Col>
            <Col span={12}><Statistic title="净负债率" value={formatPercent(safety.net_debt_ratio)} /></Col>
            <Col span={12}><Statistic title="权益乘数" value={safety.equity_multiplier?.toFixed(2) || '-'} /></Col>
            <Col span={12}><Statistic title="权益负债比" value={safety.equity_liability_ratio?.toFixed(2) || '-'} /></Col>
            <Col span={12}><Statistic title="有息负债率" value={formatPercent(safety.interest_bearing_debt_ratio)} /></Col>
            <Col span={12}><Statistic title="短期债务占比" value={formatPercent(liability.short_term_debt_ratio)} /></Col>
          </Row>
        </Card>
      </Col>

      {tableData.length > 0 && (
        <Col span={24}>
          <Card title="偿债指标同比">
            <Table scroll={{ x: 'max-content' }} size="small" columns={yoyColumns} dataSource={tableData} pagination={false} />
          </Card>
        </Col>
      )}
    </Row>
  );
};

export default SolvencyPage;
