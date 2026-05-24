import React from 'react';
import { Card, Col, Empty, Progress, Row, Statistic } from 'antd';
import ReactECharts from 'echarts-for-react';

import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent } from '../../utils/format';

interface Props {
  data: AnalysisResult | null;
  trendData: TrendResult | null;
  loading: boolean;
}

const DashboardPage: React.FC<Props> = ({ data, trendData }) => {
  if (!data) return <Empty description="请选择公司并上传数据" />;

  const score = data.analysis.good_company_score.score;
  const items = data.analysis.good_company_score.items;
  const cf = data.analysis.cash_flow;

  const pieOption = {
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        data: [
          { name: '货币资金', value: data.analysis.asset_structure.cash_ratio || 0 },
          { name: '投资类', value: data.analysis.asset_structure.investment_assets_ratio || 0 },
          { name: '经营类', value: data.analysis.asset_structure.operating_assets_ratio || 0 },
          { name: '生产类', value: data.analysis.asset_structure.production_assets_ratio || 0 },
          { name: '其他', value: 100 },
        ],
      },
    ],
  };

  const hasTrend = Boolean(trendData?.trend?.metrics);
  const periods = trendData?.trend?.periods || [];
  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收', '净利润', '经营现金流'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value' },
    series: [
      { name: '营收', type: 'line', smooth: true, data: trendData?.trend?.metrics?.revenue?.values || [] },
      { name: '净利润', type: 'line', smooth: true, data: trendData?.trend?.metrics?.net_profit?.values || [] },
      { name: '经营现金流', type: 'line', smooth: true, data: trendData?.trend?.metrics?.net_cash_from_operations?.values || [] },
    ],
  };

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={12}>
        <Card className="panel-card" title="好企业评分卡">
          <Progress type="dashboard" percent={score} strokeColor="#0f766e" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {Object.entries(items).map(([k, v]) => (
              <div key={k}>{v.pass ? '✅' : '❌'} {k}</div>
            ))}
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card className="panel-card" title="企业现金流画像">
          <div style={{ fontSize: 64 }}>{cf.portrait.emoji}</div>
          <h3>{cf.portrait.type}</h3>
          <p>{cf.portrait.desc}</p>
        </Card>
      </Col>

      <Col xs={12} lg={4}><Card><Statistic title="ROE" value={formatPercent(data.analysis.profitability.roe as number)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="毛利率" value={formatPercent(data.analysis.profitability.gross_margin as number)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="净利率" value={formatPercent(data.analysis.profitability.net_margin as number)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="资产负债率" value={formatPercent(data.analysis.safety.debt_to_asset_ratio as number)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="自由现金流" value={formatMoney(cf.free_cash_flow)} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="经营/净利" value={cf.ocf_to_net_profit ?? '-'} precision={2} /></Card></Col>

      <Col xs={24} lg={12}>
        <Card title="资产结构环形图"><ReactECharts option={pieOption} style={{ height: 320 }} /></Card>
      </Col>
      <Col xs={24} lg={12}>
        <Card title="三年趋势折线图">{hasTrend ? <ReactECharts option={trendOption} style={{ height: 320 }} /> : <Empty />}</Card>
      </Col>
    </Row>
  );
};

export default DashboardPage;
