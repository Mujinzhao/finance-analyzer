import React from 'react';
import { Card, Col, Descriptions, Empty, Progress, Row, Statistic, Tag, Typography } from 'antd';
import ReactECharts from 'echarts-for-react';

import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent, scoreColor } from '../../utils/format';

const scoreItemLabels: Record<string, string> = {
  roe_gt_15: 'ROE > 15%',
  gross_margin_gt_40: '毛利率 > 40%',
  net_margin_gt_15: '净利率 > 15%',
  ocf_gt_profit: '经营现金流 > 净利润',
};

const OverviewPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty description="请选择公司并上传数据" />;

  const metrics = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];
  const latestRevenue = metrics.revenue?.values?.[metrics.revenue?.values.length - 1] ?? null;
  const latestNetProfit = metrics.net_profit_parent?.values?.[metrics.net_profit_parent?.values.length - 1] ?? null;
  const latestOCF = metrics.net_cash_from_operations?.values?.[metrics.net_cash_from_operations?.values.length - 1] ?? null;

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['营收', '归母净利润', '经营现金流'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value' },
    series: [
      { name: '营收', type: 'line', smooth: true, data: metrics.revenue?.values || [] },
      { name: '归母净利润', type: 'line', smooth: true, data: metrics.net_profit_parent?.values || [] },
      { name: '经营现金流', type: 'line', smooth: true, data: metrics.net_cash_from_operations?.values || [] },
    ],
  };

  const qualitySections = Object.values(data.financial_quality.sections);
  const qualityBarOption = {
    grid: { left: 30, right: 20, top: 20, bottom: 20 },
    xAxis: { type: 'value', max: 100 },
    yAxis: { type: 'category', data: qualitySections.map((s) => s.label) },
    series: [{
      type: 'bar',
      data: qualitySections.map((s) => ({
        value: s.score,
        itemStyle: { color: s.score >= 70 ? '#16a34a' : s.score >= 50 ? '#d97706' : '#dc2626' },
      })),
      label: { show: true, position: 'right', formatter: '{c}分' },
    }],
  };

  const asset = data.analysis.asset_structure;
  const pieOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [{
      type: 'pie',
      radius: ['45%', '72%'],
      label: { formatter: '{b}\n{d}%' },
      data: [
        { name: '货币资金', value: asset.cash_ratio || 0 },
        { name: '投资类', value: asset.investment_assets_ratio || 0 },
        { name: '经营类', value: asset.operating_assets_ratio || 0 },
        { name: '生产类', value: asset.production_assets_ratio || 0 },
      ].filter((d) => (d.value || 0) > 0),
    }],
  };

  const cf = data.analysis.cash_flow;
  const score = data.analysis.good_company_score.score;
  const scoreItems = data.analysis.good_company_score.items;
  const p = data.analysis.profitability;
  const v = data.valuation;
  const dupont = data.analysis.dupont;

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card className="overview-hero-card">
          <div className="overview-hero-head">
            <div>
              <Typography.Title level={3} style={{ margin: 0 }}>{data.company.name}</Typography.Title>
              <Typography.Paragraph style={{ margin: '8px 0 0', color: '#475569' }}>
                当前分析报告期为 {data.period.year}{data.period.quarter ? `Q${data.period.quarter}` : '年报'}
                {data.view_mode === 'single_quarter' && '（单季数据）'}
              </Typography.Paragraph>
            </div>
            <Tag color={data.risks.level === 'safe' ? 'green' : data.risks.level === 'warning' ? 'orange' : 'red'}>
              风险等级: {data.risks.level}
            </Tag>
          </div>
          <Descriptions column={4} style={{ marginTop: 12 }}>
            <Descriptions.Item label="公司名称">{data.company.name}</Descriptions.Item>
            <Descriptions.Item label="行业">{data.company.industry || '-'}</Descriptions.Item>
            <Descriptions.Item label="股票代码">{data.company.stock_code || '-'}</Descriptions.Item>
            <Descriptions.Item label="报告期">{data.period.year}{data.period.quarter ? `Q${data.period.quarter}` : '年报'}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>

      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="营业收入" value={formatMoney(latestRevenue)} /></Card></Col>
      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="归母净利润" value={formatMoney(latestNetProfit)} /></Card></Col>
      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="经营现金流" value={formatMoney(latestOCF)} /></Card></Col>
      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="财务质量总分" value={data.financial_quality.total_score} suffix="分" valueStyle={{ color: scoreColor(data.financial_quality.total_score) }} /></Card></Col>
      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="经济商誉" value={formatMoney(v.economic_goodwill)} /></Card></Col>
      <Col xs={12} lg={4}><Card className="overview-kpi-card"><Statistic title="ROE" value={formatPercent(p.roe)} /></Card></Col>

      <Col xs={24} lg={8}>
        <Card title="好企业评分卡">
          <Progress type="dashboard" percent={score} strokeColor="#0f766e" />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 8 }}>
            {Object.entries(scoreItems).map(([k, v]) => (
              <div key={k}>{v.pass ? '✅' : '❌'} {scoreItemLabels[k] || k}</div>
            ))}
          </div>
        </Card>
      </Col>

      <Col xs={24} lg={8}>
        <Card title="企业现金流画像">
          <div style={{ fontSize: 64, textAlign: 'center' }}>{cf.portrait.emoji}</div>
          <h3 style={{ textAlign: 'center' }}>{cf.portrait.type}</h3>
          <p style={{ textAlign: 'center', color: '#64748b' }}>{cf.portrait.desc}</p>
          <Tag color={cf.portrait.risk === 'low' ? 'green' : cf.portrait.risk === 'high' ? 'red' : 'orange'} style={{ display: 'block', textAlign: 'center' }}>
            风险: {cf.portrait.risk}
          </Tag>
        </Card>
      </Col>

      <Col xs={24} lg={8}>
        <Card title="估值概览">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="EPS">{v.relative?.eps?.toFixed(4) || '-'}</Descriptions.Item>
            <Descriptions.Item label="BVPS">{v.relative?.bvps?.toFixed(4) || '-'}</Descriptions.Item>
            <Descriptions.Item label="SPS">{v.relative?.sps?.toFixed(4) || '-'}</Descriptions.Item>
            <Descriptions.Item label="自由现金流">{formatMoney(v.fcf)}</Descriptions.Item>
            <Descriptions.Item label="经济商誉">{formatMoney(v.economic_goodwill)}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>

      <Col xs={24} lg={14}><Card title="核心趋势"><ReactECharts option={trendOption} style={{ height: 320 }} /></Card></Col>
      <Col xs={24} lg={10}>
        <Card title="资产结构">
          <ReactECharts option={pieOption} style={{ height: 320 }} />
        </Card>
      </Col>

      <Col xs={24} lg={12}>
        <Card title="分项评分条形图"><ReactECharts option={qualityBarOption} style={{ height: 280 }} /></Card></Col>
      <Col xs={24} lg={12}>
        <Card title="杜邦分析 + 成长质量">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="ROE (杜邦)">{formatPercent(dupont.roe_dupont)}</Descriptions.Item>
            <Descriptions.Item label="  = 净利率 × 周转率 × 杠杆">
              {formatPercent(dupont.net_profit_rate)} × {dupont.asset_turnover} × {dupont.equity_multiplier}
            </Descriptions.Item>
            <Descriptions.Item label="营收增长率">{formatPercent(data.growth.revenue_growth)}</Descriptions.Item>
            <Descriptions.Item label="归母净利增长率">{formatPercent(data.growth.net_profit_parent_growth)}</Descriptions.Item>
            <Descriptions.Item label="经营现金流增长率">{formatPercent(data.growth.net_cash_from_operations_growth)}</Descriptions.Item>
            <Descriptions.Item label="增长质量判断">{data.growth.growth_quality}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>

      <Col span={24}>
        <Card title="重点提示">
          <div className="overview-highlight-grid">
            {data.financial_quality.highlights.map((item) => (
              <Tag key={item} className="overview-highlight-tag">{item}</Tag>
            ))}
          </div>
        </Card>
      </Col>
    </Row>
  );
};

export default OverviewPage;
