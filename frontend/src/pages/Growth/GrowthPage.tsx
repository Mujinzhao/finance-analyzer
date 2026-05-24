import React from 'react';
import { Card, Col, Empty, Row, Statistic } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent } from '../../utils/format';

const GrowthPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];
  const revenueYoy = m.revenue?.yoy || [];
  const profitYoy = m.net_profit_parent?.yoy || [];
  const ocfYoy = m.net_cash_from_operations?.yoy || [];
  const assetsYoy = m.total_assets?.yoy || [];
  const equityYoy = m.total_equity?.yoy || [];
  const roeYoy = m.roe?.yoy || [];

  const yoyOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收同比', '归母净利同比', '经营现金流同比', '总资产同比'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '营收同比', type: 'bar', data: revenueYoy, itemStyle: { color: '#5470c6' } },
      { name: '归母净利同比', type: 'bar', data: profitYoy, itemStyle: { color: '#91cc75' } },
      { name: '经营现金流同比', type: 'line', smooth: true, data: ocfYoy, lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
      { name: '总资产同比', type: 'line', smooth: true, data: assetsYoy, lineStyle: { color: '#d97706', type: 'dashed' }, itemStyle: { color: '#d97706' } },
    ],
  };

  const marginTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['毛利率', '净利率', '毛利率同比', '净利率同比'] },
    xAxis: { type: 'category', data: periods },
    yAxis: [{ type: 'value', name: '%', axisLabel: { formatter: '{value}%' } }, { type: 'value', name: '变动' }],
    series: [
      { name: '毛利率', type: 'line', smooth: true, yAxisIndex: 0, data: m.gross_margin?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '净利率', type: 'line', smooth: true, yAxisIndex: 0, data: m.net_margin?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '毛利率同比', type: 'bar', yAxisIndex: 1, data: m.gross_margin?.yoy || [], itemStyle: { color: '#52c41a', opacity: 0.4 }, barWidth: '30%' },
      { name: '净利率同比', type: 'bar', yAxisIndex: 1, data: m.net_margin?.yoy || [], itemStyle: { color: '#1677ff', opacity: 0.4 }, barWidth: '30%' },
    ],
  } : null;

  const scaleOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis', formatter: (params: any) => params.map((p: any) => `${p.marker} ${p.seriesName}: ${formatMoney(p.value)}`).join('<br/>') },
    legend: { data: ['营收', '归母净利润', '经营现金流'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatMoney(v) } },
    series: [
      { name: '营收', type: 'bar', data: m.revenue?.values || [], barWidth: '35%', itemStyle: { color: '#91cc75', opacity: 0.7 } },
      { name: '归母净利润', type: 'line', smooth: true, data: m.net_profit_parent?.values || [], lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
      { name: '经营现金流', type: 'line', smooth: true, data: m.net_cash_from_operations?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
    ],
  } : null;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} lg={4}><Card><Statistic title="营收增长率" value={formatPercent(data.growth.revenue_growth)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="归母净利增长率" value={formatPercent(data.growth.net_profit_parent_growth)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="经营现金流增率" value={formatPercent(data.growth.net_cash_from_operations_growth)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="总资产增长率" value={formatPercent(data.growth.total_assets_growth)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="净资产增长率" value={formatPercent(data.growth.total_equity_growth)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="ROE变化" value={formatPercent(m.roe?.yoy?.[m.roe?.yoy.length - 1] ?? data.growth.net_margin_change)} /></Card></Col>

      <Col span={24}><Card title="收入利润趋势"><ReactECharts option={scaleOption} style={{ height: 320 }} /></Card></Col>
      <Col span={24}><Card title="同比增长率"><ReactECharts option={yoyOption} style={{ height: 320 }} /></Card></Col>

      {marginTrendOption && (
        <Col span={24}><Card title="利润率趋势与同比变动"><ReactECharts option={marginTrendOption} style={{ height: 320 }} /></Card></Col>
      )}

      <Col span={24}>
        <Card title="增长质量判断">
          <span style={{ fontSize: 16, fontWeight: 600, color: data.growth.growth_quality.includes('高质量') ? '#16a34a' : data.growth.growth_quality.includes('低质量') ? '#dc2626' : '#d97706' }}>
            {data.growth.growth_quality}
          </span>
        </Card>
      </Col>
    </Row>
  );
};

export default GrowthPage;
