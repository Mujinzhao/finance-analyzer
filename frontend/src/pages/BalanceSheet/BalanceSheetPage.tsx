import React from 'react';
import { Card, Col, Descriptions, Empty, Row, Statistic, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent } from '../../utils/format';

const BalanceSheetPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const asset = data.analysis.asset_structure;
  const liability = data.analysis.liability_structure;
  const safety = data.analysis.safety;
  const quality = data.analysis.asset_quality;
  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const assetSeries = [
    { name: '货币资金', value: asset.cash_ratio || 0 },
    { name: '投资类资产', value: asset.investment_assets_ratio || 0 },
    { name: '经营类资产', value: asset.operating_assets_ratio || 0 },
    { name: '生产类资产', value: asset.production_assets_ratio || 0 },
  ].filter((d) => d.value > 0);

  const stackOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    yAxis: { type: 'category', data: ['资产结构'] },
    series: assetSeries.map((d) => ({
      type: 'bar', stack: 'all', name: d.name, data: [d.value],
    })),
  };

  const pieOption = {
    tooltip: { trigger: 'item', formatter: (params: any) => `${params.name}: ${params.value.toFixed(2)}%` },
    series: [
      { type: 'pie', radius: ['40%', '65%'], center: ['30%', '50%'], label: { formatter: '{b}\n{d}%' },
        data: [
          { name: '有息负债', value: liability.interest_bearing_debt || 0 },
          { name: '无息负债', value: liability.non_interest_bearing_debt || 0 },
        ],
      },
      { type: 'pie', radius: ['40%', '65%'], center: ['72%', '50%'], label: { formatter: '{b}\n{d}%' },
        data: [
          { name: '流动负债', value: liability.current_liability_ratio || 0 },
          { name: '非流动负债', value: 100 - Number(liability.current_liability_ratio || 0) },
        ],
      },
    ],
  };

  const ratioTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['资产负债率', '权益比率', '流动比率', '速动比率'] },
    xAxis: { type: 'category', data: periods },
    yAxis: [{ type: 'value', name: '比率', axisLabel: { formatter: '{value}%' } }, { type: 'value', name: '倍数' }],
    series: [
      { name: '资产负债率', type: 'line', smooth: true, yAxisIndex: 0, data: m.debt_to_asset_ratio?.values || [], lineStyle: { color: '#ff4d4f' }, itemStyle: { color: '#ff4d4f' } },
      { name: '权益比率', type: 'line', smooth: true, yAxisIndex: 0, data: m.equity_ratio?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '流动比率', type: 'line', smooth: true, yAxisIndex: 1, data: m.current_ratio?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '速动比率', type: 'line', smooth: true, yAxisIndex: 1, data: m.quick_ratio?.values || [], lineStyle: { color: '#0f766e', type: 'dashed' }, itemStyle: { color: '#0f766e' } },
    ],
  } : null;

  const assetTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['货币资金占比', '重资产率', '议价能力指数'] },
    xAxis: { type: 'category', data: periods },
    yAxis: [{ type: 'value', name: '%', axisLabel: { formatter: '{value}%' } }, { type: 'value', name: '倍' }],
    series: [
      { name: '货币资金占比', type: 'line', smooth: true, yAxisIndex: 0, data: m.cash_ratio?.values || [], areaStyle: { opacity: 0.15 }, lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '重资产率', type: 'line', smooth: true, yAxisIndex: 0, data: m.heavy_asset_ratio?.values || [], areaStyle: { opacity: 0.1 }, lineStyle: { color: '#faad14' }, itemStyle: { color: '#faad14' } },
      { name: '议价能力指数', type: 'line', smooth: true, yAxisIndex: 1, data: m.bargaining_power?.values || [], lineStyle: { color: '#0f766e', width: 2.5 }, itemStyle: { color: '#0f766e' },
        markLine: { silent: true, data: [{ yAxis: 1, lineStyle: { color: '#94a3b8', type: 'dashed' }, label: { formatter: '强弱分界' } }] } },
    ],
  } : null;

  const scaleTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis', formatter: (params: any) => params.map((p: any) => `${p.marker} ${p.seriesName}: ${formatMoney(p.value)}`).join('<br/>') },
    legend: { data: ['总资产', '净资产', '货币资金'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatMoney(v) } },
    series: [
      { name: '总资产', type: 'line', smooth: true, data: m.total_assets?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '净资产', type: 'line', smooth: true, data: m.total_equity?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '货币资金', type: 'line', smooth: true, data: m.cash_and_equivalents?.values || [], lineStyle: { color: '#0f766e' }, itemStyle: { color: '#0f766e' } },
    ],
  } : null;

  const bp = asset.bargaining_power;

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}><Card title="资产结构水平堆叠图"><ReactECharts option={stackOption} style={{ height: 200 }} /></Card></Col>

      <Col xs={12} lg={4}><Card><Statistic title="流动比率" value={safety.current_ratio || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="速动比率" value={safety.quick_ratio || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="资产负债率" value={formatPercent(safety.debt_to_asset_ratio)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="净负债率" value={formatPercent(safety.net_debt_ratio)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="利息保障倍数" value={safety.interest_coverage?.toFixed(2) || '-'} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="重资产率" value={formatPercent(quality.heavy_asset_ratio)} /></Card></Col>

      {ratioTrendOption && (
        <Col span={24}><Card title="财务比率趋势"><ReactECharts option={ratioTrendOption} style={{ height: 320 }} /></Card></Col>
      )}
      {assetTrendOption && (
        <Col span={24}><Card title="资产质量与议价能力趋势"><ReactECharts option={assetTrendOption} style={{ height: 300 }} /></Card></Col>
      )}
      {scaleTrendOption && (
        <Col span={24}><Card title="资产规模趋势"><ReactECharts option={scaleTrendOption} style={{ height: 320 }} /></Card></Col>
      )}

      <Col span={24}><Card title="负债结构双饼图"><ReactECharts option={pieOption} style={{ height: 280 }} /></Card></Col>

      <Col xs={24} lg={12}>
        <Card title="上下游议价能力">
          <Descriptions column={1}>
            <Descriptions.Item label="经营类资产">{formatMoney(asset.operating_assets)}（应收+预付+存货+其他应收+合同资产）</Descriptions.Item>
            <Descriptions.Item label="经营类负债">{formatMoney(asset.operating_liabilities)}（应付+预收+其他应付）</Descriptions.Item>
            <Descriptions.Item label="议价能力指数">
              <Tag color={(bp ?? 0) > 1 ? 'green' : (bp ?? 0) > 0.5 ? 'orange' : 'red'}>
                {bp != null ? bp.toFixed(2) : '-'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="说明">(应付+预收)/(应收+预付)，&gt;1表示占用上下游资金，议价能力强</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>

      <Col xs={24} lg={12}>
        <Card title="资产质量">
          <Descriptions column={1}>
            <Descriptions.Item label="应收/营收">{formatPercent(quality.receivable_to_revenue)}</Descriptions.Item>
            <Descriptions.Item label="存货/营收">{formatPercent(quality.inventory_to_revenue)}</Descriptions.Item>
            <Descriptions.Item label="商誉/净资产">{formatPercent(quality.goodwill_to_equity)}</Descriptions.Item>
            <Descriptions.Item label="在建/固定">{formatPercent(quality.construction_to_fixed)}</Descriptions.Item>
            <Descriptions.Item label="重资产率">{formatPercent(quality.heavy_asset_ratio)}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );
};

export default BalanceSheetPage;
