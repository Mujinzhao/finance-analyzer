import React from 'react';
import { Card, Col, Empty, Progress, Result, Row, Table, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { riskColor } from '../../utils/format';

const categoryLabel: Record<string, string> = {
  revenue: '收入端', expense: '费用端', cash_flow: '现金流端', safety: '安全性', other: '其他',
};

const severityColor: Record<string, string> = {
  high: 'red', medium: 'orange', critical: 'purple', low: 'green',
};

const RiskAlertPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const risk = data.risks;
  const columns = [
    { title: '类别', dataIndex: 'category', key: 'category', render: (v: string) => categoryLabel[v] || v },
    { title: '风险项', dataIndex: 'name', key: 'name' },
    { title: '严重程度', dataIndex: 'severity', key: 'severity', render: (v: string) => <Tag color={severityColor[v] || 'default'}>{v}</Tag> },
    { title: '详情', dataIndex: 'detail', key: 'detail' },
    { title: '阈值', dataIndex: 'threshold', key: 'threshold' },
  ];

  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const scoreTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['好企业评分'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}分' } },
    series: [{
      name: '好企业评分', type: 'line', smooth: true,
      data: m.score?.values || [],
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(15,118,110,0.2)' }, { offset: 1, color: 'rgba(15,118,110,0.02)' }] } },
      lineStyle: { color: '#0f766e', width: 2 },
      itemStyle: { color: '#0f766e' },
      markLine: { silent: true, data: [
        { yAxis: 75, lineStyle: { color: '#52c41a', type: 'dashed' }, label: { formatter: '优秀' } },
        { yAxis: 50, lineStyle: { color: '#faad14', type: 'dashed' }, label: { formatter: '警戒' } },
      ]},
    }],
  } : null;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}><Card title="综合风险评分"><Progress type="dashboard" percent={risk.score} strokeColor={riskColor(risk.level)} /></Card></Col>
      <Col xs={24} lg={16}>
        <Card title="风险分布">
          <Tag color="red">高风险 {risk.risk_count.high || 0}</Tag>
          <Tag color="orange">中风险 {risk.risk_count.medium || 0}</Tag>
          <Tag color="purple">严重 {risk.risk_count.critical || 0}</Tag>
        </Card>
      </Col>

      {scoreTrendOption && (
        <Col span={24}><Card title="好企业评历史趋势"><ReactECharts option={scoreTrendOption} style={{ height: 300 }} /></Card></Col>
      )}

      <Col span={24}>
        {risk.risks.length === 0 ? <Result status="success" title="未检测到明显风险信号" /> : <Table rowKey={(r) => `${r.name}-${r.detail}`} columns={columns} dataSource={risk.risks} />}
      </Col>
    </Row>
  );
};

export default RiskAlertPage;
