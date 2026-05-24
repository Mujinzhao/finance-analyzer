import React from 'react';
import { Card, Col, Empty, List, Progress, Row, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';
import { scoreColor } from '../../utils/format';

const QualityScorePage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const sections = Object.values(data.financial_quality.sections);
  const radarOption = {
    radar: {
      indicator: sections.map((section) => ({ name: section.label, max: 100 })),
    },
    series: [{
      type: 'radar',
      data: [{ value: sections.map((section) => section.score), name: '当前评分' }],
    }],
  };

  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const scoreTrendOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}分' } },
    series: [{
      type: 'line', smooth: true,
      data: m.score?.values || [],
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(15,118,110,0.25)' }, { offset: 1, color: 'rgba(15,118,110,0.02)' }] } },
      lineStyle: { color: '#0f766e', width: 3 },
      itemStyle: { color: '#0f766e' },
      markLine: {
        silent: true,
        data: [
          { yAxis: 75, lineStyle: { color: '#52c41a', type: 'dashed' }, label: { formatter: '优秀(75)' } },
          { yAxis: 50, lineStyle: { color: '#faad14', type: 'dashed' }, label: { formatter: '一般(50)' } },
        ],
      },
    }],
  } : null;

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} lg={8}>
        <Card title="总评分">
          <Progress type="dashboard" percent={Math.round(data.financial_quality.total_score)} strokeColor={scoreColor(data.financial_quality.total_score)} />
        </Card>
      </Col>
      <Col xs={24} lg={16}><Card title="评分雷达图"><ReactECharts option={radarOption} style={{ height: 320 }} /></Card></Col>

      {scoreTrendOption && (
        <Col span={24}><Card title="评分趋势"><ReactECharts option={scoreTrendOption} style={{ height: 300 }} /></Card></Col>
      )}

      <Col span={24}>
        <Card title="分项评分">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
            {sections.map((section) => (
              <Tag key={section.label} color={section.score >= 70 ? 'green' : section.score >= 50 ? 'orange' : 'red'}>
                {section.label} {section.score}分
              </Tag>
            ))}
          </div>
        </Card>
      </Col>
      <Col span={24}>
        <Card title="系统提示">
          <List dataSource={data.financial_quality.highlights} renderItem={(item) => <List.Item>{item}</List.Item>} />
        </Card>
      </Col>
    </Row>
  );
};

export default QualityScorePage;
