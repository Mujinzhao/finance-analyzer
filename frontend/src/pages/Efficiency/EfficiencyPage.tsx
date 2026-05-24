import React from 'react';
import { Card, Col, Empty, Row, Statistic, Table } from 'antd';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, TrendResult } from '../../types';

const EfficiencyPage: React.FC<{ data: AnalysisResult | null; trendData: TrendResult | null; loading: boolean }> = ({ data, trendData }) => {
  if (!data) return <Empty />;

  const turnover = data.analysis.turnover;
  const m = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const daysOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['应收天数', '存货天数', '应付天数', '现金周期'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}天' } },
    series: [
      { name: '应收天数', type: 'line', smooth: true, data: m.receivable_days?.values || [], lineStyle: { color: '#ff4d4f' }, itemStyle: { color: '#ff4d4f' } },
      { name: '存货天数', type: 'line', smooth: true, data: m.inventory_days?.values || [], lineStyle: { color: '#faad14' }, itemStyle: { color: '#faad14' } },
      { name: '应付天数', type: 'line', smooth: true, data: m.payable_days?.values || [], lineStyle: { color: '#52c41a' }, itemStyle: { color: '#52c41a' } },
      { name: '现金周期', type: 'line', smooth: true, data: m.cash_conversion_cycle?.values || [], lineStyle: { color: '#0f766e', width: 2.5 }, itemStyle: { color: '#0f766e' } },
    ],
  };

  const turnoverOption = periods.length > 0 ? {
    tooltip: { trigger: 'axis' },
    legend: { data: ['总资产周转率', '存货周转率', '固定资产周转率'] },
    xAxis: { type: 'category', data: periods },
    yAxis: { type: 'value' },
    series: [
      { name: '总资产周转率', type: 'line', smooth: true, data: m.total_asset_turnover?.values || [], lineStyle: { color: '#1677ff' }, itemStyle: { color: '#1677ff' } },
      { name: '存货周转率', type: 'line', smooth: true, data: m.inventory_turnover?.values || [], lineStyle: { color: '#faad14' }, itemStyle: { color: '#faad14' } },
      { name: '固定资产周转率', type: 'line', smooth: true, data: m.fixed_asset_turnover?.values || [], lineStyle: { color: '#52c41a', type: 'dashed' }, itemStyle: { color: '#52c41a' } },
    ],
  } : null;

  const tableData = periods.map((p, idx) => ({
    key: p, period: p,
    tat: m.total_asset_turnover?.values?.[idx], tat_yoy: m.total_asset_turnover?.yoy?.[idx],
    rd: m.receivable_days?.values?.[idx], rd_yoy: m.receivable_days?.yoy?.[idx],
    id: m.inventory_days?.values?.[idx], id_yoy: m.inventory_days?.yoy?.[idx],
    ccc: m.cash_conversion_cycle?.values?.[idx], ccc_yoy: m.cash_conversion_cycle?.yoy?.[idx],
  }));

  const yoyColumns = [
    { title: '期间', dataIndex: 'period', key: 'period', fixed: 'left' as const },
    { title: '总资产周转率', dataIndex: 'tat', key: 'tat', render: (v: any) => v?.toFixed(4) ?? '-' },
    { title: '同比', dataIndex: 'tat_yoy', key: 'tat_yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '应收天数', dataIndex: 'rd', key: 'rd', render: (v: any) => v?.toFixed(1) ?? '-' },
    { title: '同比', dataIndex: 'rd_yoy', key: 'rd_yoy', render: (v: any) => v != null ? <span style={{ color: v <= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '存货天数', dataIndex: 'id', key: 'id', render: (v: any) => v?.toFixed(1) ?? '-' },
    { title: '同比', dataIndex: 'id_yoy', key: 'id_yoy', render: (v: any) => v != null ? <span style={{ color: v <= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
    { title: '现金周期', dataIndex: 'ccc', key: 'ccc', render: (v: any) => v?.toFixed(1) ?? '-' },
    { title: '同比', dataIndex: 'ccc_yoy', key: 'ccc_yoy', render: (v: any) => v != null ? <span style={{ color: v <= 0 ? '#52c41a' : '#ff4d4f' }}>{v.toFixed(2)}%</span> : '-' },
  ];

  return (
    <Row gutter={[16, 16]}>
      <Col xs={12} lg={4}><Card><Statistic title="应收周转率" value={turnover.receivable_turnover || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="应收天数" value={turnover.receivable_days || 0} precision={2} suffix="天" /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="存货周转率" value={turnover.inventory_turnover || 0} precision={2} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="存货天数" value={turnover.inventory_days || 0} precision={2} suffix="天" /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="总资产周转率" value={turnover.total_asset_turnover || 0} precision={4} /></Card></Col>
      <Col xs={12} lg={4}><Card><Statistic title="现金转换周期" value={turnover.cash_conversion_cycle || 0} precision={1} suffix="天" /></Card></Col>

      <Col span={24}><Card title="周转天数趋势"><ReactECharts option={daysOption} style={{ height: 320 }} /></Card></Col>

      {turnoverOption && (
        <Col span={24}><Card title="周转率趋势"><ReactECharts option={turnoverOption} style={{ height: 300 }} /></Card></Col>
      )}

      <Col xs={24} lg={12}>
        <Card title="管理层营运能力详解">
          <Row gutter={[12, 12]}>
            <Col span={12}><Statistic title="固定资产周转率" value={turnover.fixed_asset_turnover?.toFixed(4) || '-'} /></Col>
            <Col span={12}><Statistic title="应付周转天数" value={turnover.payable_days?.toFixed(2) || '-'} suffix="天" /></Col>
            <Col span={24}>
              <p style={{ color: '#64748b', marginTop: 8 }}>
                现金转换周期 = 应收天数 + 存货天数 - 应付天数。越短越好，表示现金周转效率高。负值意味着企业占用供应商资金的时间超过存货和应收款的周转时间，是强议价能力的表现。
              </p>
            </Col>
          </Row>
        </Card>
      </Col>

      {tableData.length > 0 && (
        <Col xs={24} lg={12}>
          <Card title="营运效率指标同比">
            <Table scroll={{ x: 'max-content' }} size="small" columns={yoyColumns} dataSource={tableData} pagination={false} />
          </Card>
        </Col>
      )}
    </Row>
  );
};

export default EfficiencyPage;
