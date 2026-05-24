import React, { useEffect, useMemo, useState } from 'react';
import { Card, Col, Empty, Row, Spin, Statistic, Table, Typography } from 'antd';
import ReactECharts from 'echarts-for-react';
import { Company, ReportDetail, TrendResult } from '../../types';
import { reportApi } from '../../utils/api';
import { formatMoney } from '../../utils/format';

interface Props {
  company: Company | null;
  year: number | null;
  quarter: number | null;
  trendData: TrendResult | null;
}

const statementColors = {
  balance: { header: '#16a34a', border: '#86efac' },
  income: { header: '#2563eb', border: '#93c5fd' },
  cash: { header: '#ea580c', border: '#fdba74' },
};

const metricLabelMap: Record<string, string> = {
  revenue: '营业收入', net_profit: '净利润', net_profit_parent: '归母净利润',
  operating_profit: '营业利润', total_assets: '总资产', total_equity: '净资产',
  total_liabilities: '总负债', cash_and_equivalents: '货币资金',
  accounts_receivable: '应收账款', inventory: '存货',
  net_cash_from_operations: '经营现金流', net_cash_from_investing: '投资现金流',
  net_cash_from_financing: '筹资现金流', ebit: 'EBIT',
};

const StatementsPage: React.FC<Props> = ({ company, year, quarter, trendData }) => {
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedField, setSelectedField] = useState<string | null>(null);

  useEffect(() => {
    if (!company || year == null) {
      setDetail(null);
      return;
    }
    const reports = company.reports || [];
    const match = reports.find((r) => r.year === year && r.quarter === (quarter ?? 0));
    if (!match) {
      setDetail(null);
      return;
    }
    setLoading(true);
    reportApi.getDetail(match.id)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setLoading(false));
  }, [company, year, quarter]);

  const trendMetrics = trendData?.trend?.metrics || {};
  const periods = trendData?.trend?.periods || [];

  const allReportFields = useMemo(() => new Set([
    ...(detail?.balance_sheet || []).map((d) => d.field),
    ...(detail?.income_statement || []).map((d) => d.field),
    ...(detail?.cash_flow || []).map((d) => d.field),
  ]), [detail]);

  const fieldLabelMap = useMemo(() => {
    const map: Record<string, string> = {};
    for (const d of detail?.balance_sheet || []) map[d.field] = d.label;
    for (const d of detail?.income_statement || []) map[d.field] = d.label;
    for (const d of detail?.cash_flow || []) map[d.field] = d.label;
    return map;
  }, [detail]);

  const trendChartOption = useMemo(() => {
    if (!selectedField || !periods.length) return null;
    const fieldData = trendMetrics[selectedField];
    if (!fieldData) return null;

    const label = fieldLabelMap[selectedField] || metricLabelMap[selectedField] || selectedField;
    const isMoney = allReportFields.has(selectedField);

    return {
      tooltip: { trigger: 'axis' },
      legend: { data: [label, `${label}同比`, `${label}环比`] },
      xAxis: { type: 'category', data: periods },
      yAxis: [
        { type: 'value', name: isMoney ? '金额' : '值', axisLabel: isMoney ? { formatter: (v: number) => formatMoney(v) } : undefined },
        { type: 'value', name: '%', axisLabel: { formatter: '{value}%' } },
      ],
      series: [
        {
          name: label, type: 'line', smooth: true, yAxisIndex: 0,
          data: fieldData.values || [],
          lineStyle: { color: '#0f766e', width: 2.5 }, itemStyle: { color: '#0f766e' },
          areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(15,118,110,0.2)' }, { offset: 1, color: 'rgba(15,118,110,0.02)' }] } },
        },
        {
          name: `${label}同比`, type: 'bar', yAxisIndex: 1,
          data: fieldData.yoy || [],
          itemStyle: { color: '#1677ff', opacity: 0.6 }, barWidth: '35%',
        },
        {
          name: `${label}环比`, type: 'bar', yAxisIndex: 1,
          data: fieldData.qoq || [],
          itemStyle: { color: '#d97706', opacity: 0.6 }, barWidth: '35%',
        },
      ],
    };
  }, [selectedField, trendMetrics, periods, allReportFields, fieldLabelMap]);

  const yoyTableData = useMemo(() => {
    if (!selectedField || !periods.length) return [];
    const fieldData = trendMetrics[selectedField];
    if (!fieldData) return [];
    return periods.map((p, idx) => ({
      key: p, period: p,
      value: fieldData.values?.[idx],
      yoy: fieldData.yoy?.[idx],
      qoq: fieldData.qoq?.[idx],
    }));
  }, [selectedField, trendMetrics, periods]);

  const yoyColumns = [
    { title: '期间', dataIndex: 'period', key: 'period', fixed: 'left' as const },
    { title: '数值', dataIndex: 'value', key: 'value', render: (v: any) => v != null ? formatMoney(v) : '-' },
    { title: '同比', dataIndex: 'yoy', key: 'yoy', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }}>{v.toFixed(2)}%</span> : '-' },
    { title: '环比', dataIndex: 'qoq', key: 'qoq', render: (v: any) => v != null ? <span style={{ color: v >= 0 ? '#16a34a' : '#dc2626', fontWeight: 600 }}>{v.toFixed(2)}%</span> : '-' },
  ];

  if (!company || year == null) return <Empty description="请选择公司和年度" />;

  const q = quarter ?? 0;
  const periodLabel = `${year}年${q === 0 ? '年报' : `Q${q}`}`;

  const renderTable = (data: { field: string; label: string; value: number }[], color: typeof statementColors.balance) => (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <tbody>
        {data.map((item, idx) => (
          <tr
            key={item.field}
            onClick={() => setSelectedField(item.field)}
            style={{
              cursor: 'pointer', background: selectedField === item.field ? `${color.header}18` : idx % 2 === 0 ? '#fff' : '#f8fafc',
              transition: 'background 0.15s',
            }}
            onMouseEnter={(e) => { if (selectedField !== item.field) e.currentTarget.style.background = '#f1f5f9'; }}
            onMouseLeave={(e) => { if (selectedField !== item.field) e.currentTarget.style.background = idx % 2 === 0 ? '#fff' : '#f8fafc'; }}
          >
            <td style={{ padding: '6px 16px', color: '#475569', fontSize: 13, width: '55%' }}>{item.label}</td>
            <td style={{
              padding: '6px 16px', textAlign: 'right', fontFamily: 'monospace', fontSize: 14,
              color: item.value < 0 ? '#dc2626' : '#1e293b',
              fontWeight: selectedField === item.field ? 600 : 400,
            }}>
              {formatMoney(item.value)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  const totalAssets = detail?.balance_sheet?.reduce((s, d) => s + d.value, 0) ?? 0;
  const netProfit = detail?.income_statement?.find((d) => d.field === 'net_profit')?.value;
  const revenue = detail?.income_statement?.find((d) => d.field === 'revenue')?.value;
  const cashEnd = detail?.cash_flow?.find((d) => d.field === 'cash_at_end')?.value;

  const selectedLabel = selectedField ? (fieldLabelMap[selectedField] || metricLabelMap[selectedField] || selectedField) : null;

  return (
    <Spin spinning={loading}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card style={{ borderRadius: 14 }}>
            <Row gutter={16} align="middle">
              <Col flex="auto">
                <Typography.Title level={4} style={{ margin: 0 }}>{company.name} · {periodLabel} 财务报表</Typography.Title>
              </Col>
              <Col><Statistic title="总资产" value={formatMoney(totalAssets)} /></Col>
              <Col><Statistic title="营收" value={formatMoney(revenue)} /></Col>
              <Col><Statistic title="净利润" value={formatMoney(netProfit)} valueStyle={{ color: (netProfit ?? 0) >= 0 ? '#16a34a' : '#dc2626' }} /></Col>
              <Col><Statistic title="期末现金" value={formatMoney(cashEnd)} /></Col>
            </Row>
          </Card>
        </Col>

        {!detail ? (
          <Col span={24}><Empty description="未找到该报告期的报表数据" /></Col>
        ) : (
          <>
            <Col xs={24} lg={8}>
              <Card
                title={<span style={{ color: statementColors.balance.header, fontSize: 16 }}>资产负债表</span>}
                style={{ borderRadius: 14, borderTop: `3px solid ${statementColors.balance.border}` }}
                bodyStyle={{ padding: '8px 0', maxHeight: 580, overflowY: 'auto' }}
              >
                {renderTable(detail.balance_sheet, statementColors.balance)}
              </Card>
            </Col>

            <Col xs={24} lg={8}>
              <Card
                title={<span style={{ color: statementColors.income.header, fontSize: 16 }}>利润表</span>}
                style={{ borderRadius: 14, borderTop: `3px solid ${statementColors.income.border}` }}
                bodyStyle={{ padding: '8px 0', maxHeight: 580, overflowY: 'auto' }}
              >
                {renderTable(detail.income_statement, statementColors.income)}
              </Card>
            </Col>

            <Col xs={24} lg={8}>
              <Card
                title={<span style={{ color: statementColors.cash.header, fontSize: 16 }}>现金流量表</span>}
                style={{ borderRadius: 14, borderTop: `3px solid ${statementColors.cash.border}` }}
                bodyStyle={{ padding: '8px 0', maxHeight: 580, overflowY: 'auto' }}
              >
                {renderTable(detail.cash_flow, statementColors.cash)}
              </Card>
            </Col>
          </>
        )}

        {selectedField && trendChartOption && (
          <>
            <Col span={24}>
              <Card title={`${selectedLabel} — 趋势图`} style={{ borderRadius: 14 }}>
                <ReactECharts option={trendChartOption} style={{ height: 340 }} />
              </Card>
            </Col>
            <Col span={24}>
              <Card title={`${selectedLabel} — 同比环比`} style={{ borderRadius: 14 }}>
                <Table
                  scroll={{ x: 'max-content' }} size="small"
                  columns={yoyColumns} dataSource={yoyTableData} pagination={false}
                />
              </Card>
            </Col>
          </>
        )}

        {selectedField && !trendChartOption && periods.length > 0 && (
          <Col span={24}>
            <Card style={{ borderRadius: 14 }}>
              <Empty description={`"${selectedLabel}"暂无趋势数据`} />
            </Card>
          </Col>
        )}
      </Row>
    </Spin>
  );
};

export default StatementsPage;
