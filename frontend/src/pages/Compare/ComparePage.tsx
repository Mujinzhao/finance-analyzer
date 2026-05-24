import React, { useMemo, useState } from 'react';
import { Button, Card, Col, Empty, Row, Select, Table, Tag, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import { Company } from '../../types';
import { analysisApi } from '../../utils/api';
import { formatMoney, formatPercent } from '../../utils/format';

const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6664'];

const fmt = (v: any) => v != null ? `${(v as number).toFixed(2)}%` : '-';
const fmtRatio = (v: any) => v != null ? (v as number).toFixed(2) : '-';
const fmtDays = (v: any) => v != null ? (v as number).toFixed(1) : '-';

const ComparePage: React.FC<{ companies: Company[] }> = ({ companies }) => {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [year, setYear] = useState<number | undefined>();
  const [compareData, setCompareData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const availableYears = useMemo(() => {
    const years = new Set<number>();
    companies.forEach((c) => c.reports?.forEach((r) => years.add(r.year)));
    return Array.from(years).sort((a, b) => b - a);
  }, [companies]);

  const yearOptions = useMemo(() => {
    if (selectedIds.length === 0) return availableYears.map((y) => ({ label: String(y), value: y }));
    const selectedCompanies = companies.filter((c) => selectedIds.includes(c.id));
    const commonYears = new Set<number>();
    selectedCompanies.forEach((c) => {
      const companyYears = new Set((c.reports || []).map((r) => r.year));
      if (commonYears.size === 0) {
        companyYears.forEach((y) => commonYears.add(y));
      } else {
        Array.from(commonYears).forEach((y) => {
          if (!companyYears.has(y)) commonYears.delete(y);
        });
      }
    });
    return Array.from(commonYears).sort((a, b) => b - a).map((y) => ({ label: String(y), value: y }));
  }, [companies, selectedIds]);

  const load = async () => {
    if (selectedIds.length < 2 || selectedIds.length > 4) {
      message.warning('请选择2-4家公司');
      return;
    }
    setLoading(true);
    try {
      const res = await analysisApi.compare(selectedIds, year);
      setCompareData(res.results || []);
    } finally {
      setLoading(false);
    }
  };

  const maxOcfRatio = Math.max(3, ...compareData.map((r) => r.metrics.ocf_to_net_profit || 0));
  const maxTurnover = Math.max(1.5, ...compareData.map((r) => r.metrics.total_asset_turnover || 0));

  const radarOption = {
    legend: { data: compareData.map((r) => r.company.name) },
    radar: {
      indicator: [
        { name: '毛利率', max: 100 },
        { name: '净利率', max: 100 },
        { name: 'ROE', max: 50 },
        { name: 'ROA', max: 30 },
        { name: '风险安全分', max: 100 },
        { name: '流动比率', max: 5 },
        { name: 'OCF/净利', max: maxOcfRatio },
        { name: '总资产周转率', max: maxTurnover },
      ],
    },
    series: [{
      type: 'radar',
      data: compareData.map((r, idx) => ({
        value: [
          r.metrics.gross_margin || 0,
          r.metrics.net_margin || 0,
          r.metrics.roe || 0,
          r.metrics.roa || 0,
          r.metrics.risk_score || 0,
          r.metrics.current_ratio || 0,
          r.metrics.ocf_to_net_profit || 0,
          r.metrics.total_asset_turnover || 0,
        ],
        name: r.company.name,
        areaStyle: { opacity: 0.12 },
        lineStyle: { color: colors[idx] },
      })),
    }],
  };

  const cashFlowOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['经营活动', '投资活动', '筹资活动'] },
    xAxis: { type: 'category', data: compareData.map((r) => r.company.name) },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => formatMoney(v) } },
    series: [
      { name: '经营活动', type: 'bar', data: compareData.map((r) => r.metrics.net_cash_operations || 0), itemStyle: { color: '#52c41a' } },
      { name: '投资活动', type: 'bar', data: compareData.map((r) => r.metrics.net_cash_investing || 0), itemStyle: { color: '#ff4d4f' } },
      { name: '筹资活动', type: 'bar', data: compareData.map((r) => r.metrics.net_cash_financing || 0), itemStyle: { color: '#faad14' } },
    ],
  };

  const assetStructureOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['货币资金', '经营资产', '生产资产', '投资资产'] },
    xAxis: { type: 'category', data: compareData.map((r) => r.company.name) },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '货币资金', type: 'bar', stack: 'total', data: compareData.map((r) => r.metrics.cash_ratio || 0), itemStyle: { color: '#52c41a' } },
      { name: '经营资产', type: 'bar', stack: 'total', data: compareData.map((r) => r.metrics.operating_assets_ratio || 0), itemStyle: { color: '#1677ff' } },
      { name: '生产资产', type: 'bar', stack: 'total', data: compareData.map((r) => r.metrics.production_assets_ratio || 0), itemStyle: { color: '#faad14' } },
      { name: '投资资产', type: 'bar', stack: 'total', data: compareData.map((r) => r.metrics.investment_assets_ratio || 0), itemStyle: { color: '#722ed1' } },
    ],
  };

  const expenseOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['销售费用率', '管理费用率', '研发费用率', '财务费用率'] },
    xAxis: { type: 'category', data: compareData.map((r) => r.company.name) },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      { name: '销售费用率', type: 'bar', data: compareData.map((r) => r.metrics.selling_expense_ratio || 0), itemStyle: { color: '#5470c6' } },
      { name: '管理费用率', type: 'bar', data: compareData.map((r) => r.metrics.admin_expense_ratio || 0), itemStyle: { color: '#91cc75' } },
      { name: '研发费用率', type: 'bar', data: compareData.map((r) => r.metrics.rd_expense_ratio || 0), itemStyle: { color: '#fac858' } },
      { name: '财务费用率', type: 'bar', data: compareData.map((r) => r.metrics.finance_expense_ratio || 0), itemStyle: { color: '#ee6664' } },
    ],
  };

  const turnoverOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['应收周转天数', '存货周转天数', '应付周转天数', '现金转换周期'] },
    xAxis: { type: 'value', name: '天数' },
    yAxis: { type: 'category', data: compareData.map((r) => r.company.name) },
    series: [
      { name: '应收周转天数', type: 'bar', data: compareData.map((r) => r.metrics.receivable_days || 0), itemStyle: { color: '#5470c6' } },
      { name: '存货周转天数', type: 'bar', data: compareData.map((r) => r.metrics.inventory_days || 0), itemStyle: { color: '#91cc75' } },
      { name: '应付周转天数', type: 'bar', data: compareData.map((r) => r.metrics.payable_days || 0), itemStyle: { color: '#fac858' } },
      { name: '现金转换周期', type: 'bar', data: compareData.map((r) => r.metrics.cash_conversion_cycle || 0), itemStyle: { color: '#ee6664' } },
    ],
  };

  const tableColumns = [
    { title: '公司', dataIndex: ['company', 'name'], key: 'name', fixed: 'left' as const, width: 120 },
    {
      title: '盈利能力',
      children: [
        { title: '毛利率', dataIndex: ['metrics', 'gross_margin'], key: 'gm', render: fmt, width: 80 },
        { title: '净利率', dataIndex: ['metrics', 'net_margin'], key: 'nm', render: fmt, width: 80 },
        { title: '营业利润率', dataIndex: ['metrics', 'operating_margin'], key: 'om', render: fmt, width: 90 },
        { title: 'ROE', dataIndex: ['metrics', 'roe'], key: 'roe', render: fmt, width: 70 },
        { title: 'ROA', dataIndex: ['metrics', 'roa'], key: 'roa', render: fmt, width: 70 },
        { title: 'ROIC', dataIndex: ['metrics', 'roic'], key: 'roic', render: fmt, width: 70 },
      ],
    },
    {
      title: '安全性',
      children: [
        { title: '资产负债率', dataIndex: ['metrics', 'debt_to_asset_ratio'], key: 'dta', render: fmt, width: 90 },
        { title: '权益比率', dataIndex: ['metrics', 'equity_ratio'], key: 'er', render: fmt, width: 80 },
        { title: '流动比率', dataIndex: ['metrics', 'current_ratio'], key: 'cr', render: fmtRatio, width: 80 },
        { title: '速动比率', dataIndex: ['metrics', 'quick_ratio'], key: 'qr', render: fmtRatio, width: 80 },
        { title: '利息保障倍数', dataIndex: ['metrics', 'interest_coverage'], key: 'ic', render: fmtRatio, width: 100 },
        { title: '现金短债比', dataIndex: ['metrics', 'cash_short_debt_ratio'], key: 'csd', render: fmtRatio, width: 90 },
      ],
    },
    {
      title: '现金流',
      children: [
        { title: '自由现金流', dataIndex: ['metrics', 'free_cash_flow'], key: 'fcf', render: (v: any) => formatMoney(v), width: 100 },
        { title: 'OCF/净利', dataIndex: ['metrics', 'ocf_to_net_profit'], key: 'ocfnp', render: fmtRatio, width: 80 },
        { title: '销售收现率', dataIndex: ['metrics', 'sales_cash_to_revenue'], key: 'scr', render: fmtRatio, width: 90 },
        { title: 'OCF利润率', dataIndex: ['metrics', 'ocf_margin'], key: 'ocfm', render: fmt, width: 80 },
        { title: '现金流画像', dataIndex: ['metrics', 'cash_portrait_type'], key: 'portrait', width: 100,
          render: (v: any, record: any) => `${record.metrics.cash_portrait_emoji ?? ''} ${v ?? '-'}` },
      ],
    },
    {
      title: '营运效率',
      children: [
        { title: '总资产周转率', dataIndex: ['metrics', 'total_asset_turnover'], key: 'tat', render: fmtRatio, width: 100 },
        { title: '应收周转天数', dataIndex: ['metrics', 'receivable_days'], key: 'rd', render: fmtDays, width: 100 },
        { title: '存货周转天数', dataIndex: ['metrics', 'inventory_days'], key: 'id', render: fmtDays, width: 100 },
        { title: '应付周转天数', dataIndex: ['metrics', 'payable_days'], key: 'pd', render: fmtDays, width: 100 },
        { title: '现金转换周期', dataIndex: ['metrics', 'cash_conversion_cycle'], key: 'ccc', render: fmtDays, width: 100 },
      ],
    },
    {
      title: '费用结构',
      children: [
        { title: '销售费用率', dataIndex: ['metrics', 'selling_expense_ratio'], key: 'ser', render: fmt, width: 90 },
        { title: '管理费用率', dataIndex: ['metrics', 'admin_expense_ratio'], key: 'aer', render: fmt, width: 90 },
        { title: '研发费用率', dataIndex: ['metrics', 'rd_expense_ratio'], key: 'rder', render: fmt, width: 90 },
        { title: '财务费用率', dataIndex: ['metrics', 'finance_expense_ratio'], key: 'fer', render: fmt, width: 90 },
        { title: '费用率合计', dataIndex: ['metrics', 'total_expense_ratio'], key: 'ter', render: fmt, width: 90 },
      ],
    },
    {
      title: '综合评价',
      children: [
        { title: '好企业评分', dataIndex: ['metrics', 'score'], key: 'score', width: 90,
          render: (v: any) => v != null ? <span style={{ fontWeight: 600, color: v >= 75 ? '#16a34a' : v >= 50 ? '#d97706' : '#dc2626' }}>{v}</span> : '-' },
        { title: '风险安全分', dataIndex: ['metrics', 'risk_score'], key: 'rs', width: 90,
          render: (v: any) => v != null ? <span style={{ fontWeight: 600, color: v >= 75 ? '#16a34a' : v >= 50 ? '#d97706' : '#dc2626' }}>{v}</span> : '-' },
        { title: '风险等级', dataIndex: ['metrics', 'risk_level'], key: 'rl', width: 80,
          render: (v: any) => v ? <Tag color={v === 'safe' ? 'green' : v === 'warning' ? 'orange' : 'red'}>{v}</Tag> : '-' },
        { title: '高风险项', dataIndex: ['metrics', 'risk_count_high'], key: 'rch', width: 80,
          render: (v: any) => v != null ? <span style={{ color: v > 0 ? '#ff4d4f' : '#52c41a' }}>{v}</span> : '-' },
        { title: '中风险项', dataIndex: ['metrics', 'risk_count_medium'], key: 'rcm', width: 80,
          render: (v: any) => v != null ? <span style={{ color: v > 0 ? '#faad14' : '#52c41a' }}>{v}</span> : '-' },
        { title: '严重风险项', dataIndex: ['metrics', 'risk_count_critical'], key: 'rcc', width: 90,
          render: (v: any) => v != null ? <span style={{ color: v > 0 ? '#dc2626' : '#52c41a' }}>{v}</span> : '-' },
      ],
    },
  ];

  const hasData = compareData.length > 0;

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title="公司选择">
          <Row gutter={12}>
            <Col xs={24} lg={14}>
              <Select
                mode="multiple"
                maxCount={4}
                style={{ width: '100%' }}
                placeholder="选择2-4家公司"
                value={selectedIds}
                onChange={(v) => setSelectedIds(v)}
                options={companies.map((c) => ({ label: c.name, value: c.id }))}
              />
            </Col>
            <Col xs={24} lg={6}><Select allowClear style={{ width: '100%' }} placeholder="年份" value={year} onChange={(v) => setYear(v)} options={yearOptions} /></Col>
            <Col xs={24} lg={4}><Button type="primary" loading={loading} onClick={load}>开始对比</Button></Col>
          </Row>
        </Card>
      </Col>

      {!hasData && <Col span={24}><Empty description="请选择公司和年份后开始对比" /></Col>}

      {hasData && (
        <>
          <Col span={24}>
            <Card title="综合雷达图">
              <ReactECharts option={radarOption} style={{ height: 420 }} />
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="现金流对比"><ReactECharts option={cashFlowOption} style={{ height: 320 }} /></Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="资产结构对比"><ReactECharts option={assetStructureOption} style={{ height: 320 }} /></Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="费用率对比"><ReactECharts option={expenseOption} style={{ height: 320 }} /></Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card title="营运效率对比"><ReactECharts option={turnoverOption} style={{ height: 320 }} /></Card>
          </Col>

          <Col span={24}>
            <Card title="详细指标对比表">
              <Table
                rowKey={(r) => String(r.company.id)}
                dataSource={compareData}
                columns={tableColumns}
                pagination={false}
                bordered
                scroll={{ x: 'max-content' }}
                size="small"
              />
            </Card>
          </Col>
        </>
      )}
    </Row>
  );
};

export default ComparePage;
