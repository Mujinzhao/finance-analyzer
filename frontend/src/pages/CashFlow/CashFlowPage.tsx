import React from 'react';
import { Card, Col, Descriptions, Empty, List, Row, Statistic, Tag } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { formatMoney, formatPercent } from '../../utils/format';

const qualityCheckLabels: Record<string, string> = {
  ocf_gt_net_profit: '经营现金流大于净利润',
  sales_cash_gte_revenue: '销售收现大于等于营业收入',
  investing_negative: '投资活动现金流为负（扩张特征）',
  cash_gte_interest_debt: '货币资金覆盖有息负债',
  dividend_reasonable: '分红率处于合理区间（20%-70%）',
};

const pieColors = ['#52c41a', '#ff4d4f', '#1677ff'];

const CashFlowPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const cf = data.analysis.cash_flow;
  const bars = [cf.net_cash_operations, cf.net_cash_investing, cf.net_cash_financing];

  const barOption = {
    xAxis: { type: 'category', data: ['经营活动', '投资活动', '筹资活动'] },
    yAxis: { type: 'value' },
    series: [{
      type: 'bar',
      data: bars.map((v) => ({ value: v, itemStyle: { color: v >= 0 ? '#52c41a' : '#ff4d4f' } })),
    }],
  };

  const totalAbs = bars.reduce((s, v) => s + Math.abs(v), 0) || 1;
  const pieOption = {
    tooltip: { trigger: 'item', formatter: (p: any) => `${p.name}: ${formatMoney(p.value)} (${p.percent}%)` },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '65%'],
      label: { formatter: '{b}\n{d}%' },
      data: [
        { name: '经营活动', value: Math.abs(cf.net_cash_operations), itemStyle: { color: pieColors[0] } },
        { name: '投资活动', value: Math.abs(cf.net_cash_investing), itemStyle: { color: pieColors[1] } },
        { name: '筹资活动', value: Math.abs(cf.net_cash_financing), itemStyle: { color: pieColors[2] } },
      ].filter((d) => d.value > 0),
    }],
  };

  const metrics = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];
  const fcfValues = metrics.free_cash_flow?.values || [];
  const ocfValues = metrics.net_cash_from_operations?.values || [];

  const fcfTrendOption = periods.length > 0 ? {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const items = params.map((p: any) => `${p.marker} ${p.seriesName}: ${formatMoney(p.value)}`).join('<br/>');
        return `${params[0].axisValue}<br/>${items}`;
      },
    },
    legend: { data: ['自由现金流', '经营现金流'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatMoney(v) } },
    series: [
      {
        name: '自由现金流', type: 'line', smooth: true,
        data: fcfValues,
        lineStyle: { color: '#0f766e' },
        itemStyle: { color: '#0f766e' },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(15,118,110,0.25)' }, { offset: 1, color: 'rgba(15,118,110,0.02)' }] } },
        markLine: {
          silent: true,
          data: [{ yAxis: 0, lineStyle: { color: '#94a3b8', type: 'dashed' } }],
          label: { formatter: '零线' },
        },
      },
      {
        name: '经营现金流', type: 'line', smooth: true,
        data: ocfValues,
        lineStyle: { color: '#1677ff', type: 'dashed' },
        itemStyle: { color: '#1677ff' },
      },
    ],
  } : null;

  const riskBg = cf.portrait.risk === 'low' ? '#f6ffed' : cf.portrait.risk === 'high' ? '#fff2f0' : '#fffbe6';

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={12}>
        <Card title="三大活动现金流"><ReactECharts option={barOption} style={{ height: 300 }} /></Card>
      </Col>

      <Col xs={24} lg={12}>
        <Card title="三大活动现金流占比"><ReactECharts option={pieOption} style={{ height: 300 }} /></Card>
      </Col>

      <Col xs={24} lg={8}>
        <Card title="企业画像" style={{ background: riskBg }}>
          <div style={{ fontSize: 64, textAlign: 'center' }}>{cf.portrait.emoji}</div>
          <h3 style={{ textAlign: 'center' }}>{cf.portrait.type}</h3>
          <p style={{ textAlign: 'center' }}>{cf.portrait.desc}</p>
          <Tag color={cf.portrait.risk === 'low' ? 'green' : cf.portrait.risk === 'high' ? 'red' : 'orange'} style={{ display: 'block', textAlign: 'center' }}>
            {cf.portrait.risk}
          </Tag>
        </Card>
      </Col>

      <Col xs={24} lg={16}>
        <Card title="现金流核心指标">
          <Row gutter={[16, 16]}>
            <Col span={8}><Statistic title="自由现金流" value={formatMoney(cf.free_cash_flow)} valueStyle={{ color: cf.free_cash_flow >= 0 ? '#52c41a' : '#ff4d4f' }} /></Col>
            <Col span={8}><Statistic title="经营现金流率" value={formatPercent(cf.ocf_margin)} /></Col>
            <Col span={8}><Statistic title="期末现金余额" value={formatMoney(cf.cash_at_end)} /></Col>
            <Col span={8}><Statistic title="经营现金流/净利润" value={cf.ocf_to_net_profit?.toFixed(2) || '-'} /></Col>
            <Col span={8}><Statistic title="销售收现/营收" value={cf.sales_cash_to_revenue?.toFixed(2) || '-'} /></Col>
            <Col span={8}><Statistic title="分红率" value={formatPercent(cf.dividend_payout_ratio)} /></Col>
            <Col span={8}><Statistic title="资本开支/经营现金流" value={cf.capex_to_ocf?.toFixed(2) || '-'} /></Col>
            <Col span={8}><Statistic title="资本开支/营收" value={cf.capex_to_revenue?.toFixed(2) || '-'} /></Col>
          </Row>
        </Card>
      </Col>

      {fcfTrendOption && (
        <Col span={24}>
          <Card title="自由现金流趋势">
            <ReactECharts option={fcfTrendOption} style={{ height: 320 }} />
          </Card>
        </Col>
      )}

      <Col span={24}>
        <Card title="5 项快速检验">
          <List
            dataSource={Object.entries(cf.quality_checks)}
            renderItem={([k, v]) => (
              <List.Item>
                {v ? <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} /> : <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />}
                {qualityCheckLabels[k] || k}
              </List.Item>
            )}
          />
        </Card>
      </Col>

      <Col span={24}>
        <Card title="现金流质量解读">
          <Descriptions column={2}>
            <Descriptions.Item label="经营现金流率">{cf.ocf_margin != null ? `${cf.ocf_margin}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="说明">经营现金流/营业收入，衡量收入"含金量"，越高越好</Descriptions.Item>
            <Descriptions.Item label="资本开支/经营现金流">{cf.capex_to_ocf != null ? cf.capex_to_ocf.toFixed(2) : '-'}</Descriptions.Item>
            <Descriptions.Item label="说明">维持性资本开支占经营现金流的比例，越低越轻松</Descriptions.Item>
            <Descriptions.Item label="分红率">{formatPercent(cf.dividend_payout_ratio)}</Descriptions.Item>
            <Descriptions.Item label="说明">分红/归母净利润，20%-70%为合理区间</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  );
};

export default CashFlowPage;
