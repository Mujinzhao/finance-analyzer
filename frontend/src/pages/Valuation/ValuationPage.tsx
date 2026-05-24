import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Empty, Form, InputNumber, Row, Statistic, Tag, Tooltip } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { AnalysisResult, DCFResult } from '../../types';
import { valuationApi } from '../../utils/api';
import { formatMoney } from '../../utils/format';

const ValuationPage: React.FC<{ data: AnalysisResult | null; companyId: number | null; loading: boolean }> = ({ data }) => {
  const [dcfResult, setDcfResult] = useState<DCFResult | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    if (!data) return;
    form.setFieldsValue({
      free_cash_flow_year3: data.analysis.cash_flow.free_cash_flow,
      discount_rate: 0.09,
      perpetual_growth: 0.03,
      forecast_growth: 0.05,
      forecast_years: 5,
      total_shares: data.valuation?.total_shares || undefined,
    });
  }, [data]);

  if (!data) return <Empty />;

  const doDcf = async () => {
    const values = await form.validateFields();
    const res = await valuationApi.getDCF(values);
    setDcfResult(res);
  };

  const hasPerShare = dcfResult?.fair_price_per_share != null && dcfResult?.buy_price_per_share != null && dcfResult?.sell_price_per_share != null;
  const hasAdvice = Boolean(dcfResult?.advice);

  const adviceColor = hasAdvice
    ? (dcfResult!.advice === '严重低估' || dcfResult!.advice === '低估区间' ? 'green'
      : dcfResult!.advice === '高估' ? 'red' : 'blue')
    : 'blue';

  const tempOption = dcfResult?.temperature != null ? {
    tooltip: { formatter: `估值温度: ${dcfResult.temperature.toFixed(1)}°` },
    grid: { left: 60, right: 30, top: 10, bottom: 20 },
    xAxis: { type: 'value', min: 0, max: 100, axisLabel: { formatter: '{value}' } },
    yAxis: { type: 'category', data: [''] },
    series: [
      {
        type: 'bar', data: [100], barWidth: 24,
        itemStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#16a34a' },
              { offset: 0.3, color: '#52c41a' },
              { offset: 0.5, color: '#faad14' },
              { offset: 0.7, color: '#f97316' },
              { offset: 1, color: '#dc2626' },
            ],
          },
        },
        label: { show: true, position: 'inside', formatter: '低估 ← 合理 → 高估', color: '#fff' },
      },
      {
        type: 'scatter', data: [[dcfResult.temperature, 0]],
        symbol: 'triangle', symbolSize: 28, symbolRotate: 180,
        itemStyle: { color: '#000' },
        label: { show: true, position: 'top', formatter: `${dcfResult.temperature.toFixed(1)}°`, fontSize: 14, fontWeight: 'bold' },
      },
    ],
  } : null;

  const v = data.valuation;
  const needParamsHint = !dcfResult || (!hasPerShare && !hasAdvice);

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title="估值概览" extra={data.view_mode === 'single_quarter' ? <Tag>基于单季利润（未年化）</Tag> : null}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic
                title={<Tooltip title="每股收益 = 归母净利润 ÷ 总股本。衡量每持有一股对应的净利润，是市盈率(PE)的分母。">EPS <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} /></Tooltip>}
                value={v.relative?.eps?.toFixed(4) || '-'}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={<Tooltip title="每股净资产 = 归母净资产 ÷ 总股本。衡量每持有一股对应的账面净资产，是市净率(PB)的分母。">BVPS <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} /></Tooltip>}
                value={v.relative?.bvps?.toFixed(4) || '-'}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={<Tooltip title="每股营收 = 营业收入 ÷ 总股本。衡量每持有一股对应的收入规模，是市销率(PS)的分母。">SPS <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} /></Tooltip>}
                value={v.relative?.sps?.toFixed(4) || '-'}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title={<Tooltip title="经济商誉 = (ROE ÷ 市场平均回报率 - 1) × 归母净资产。巴菲特概念：企业持续产生超额回报（ROE > 市场回报）的部分折现价值。负值或接近零说明企业缺乏护城河。">经济商誉 <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} /></Tooltip>}
                value={formatMoney(v.economic_goodwill)}
              />
            </Col>
          </Row>
        </Card>
      </Col>

      <Col xs={24} lg={10}>
        <Card title="DCF 估值参数">
          <Form layout="vertical" form={form}>
            <Form.Item name="free_cash_flow_year3" label="基期自由现金流" rules={[{ required: true, message: '必填' }]}>
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="discount_rate" label="折现率">
              <InputNumber min={0.01} max={0.5} step={0.01} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="forecast_growth" label="预测期增速">
              <InputNumber min={0} max={0.5} step={0.01} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="forecast_years" label="预测年数">
              <InputNumber min={1} max={10} step={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="perpetual_growth" label="永续增长率">
              <InputNumber min={0} max={0.1} step={0.005} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="total_shares" label="总股本(万股)" extra="填写后可计算每股公允价值、买点、卖点">
              <InputNumber style={{ width: '100%' }} placeholder="从报表自动获取" />
            </Form.Item>
            <Form.Item name="current_price" label="当前股价(元)" extra="填写后可输出估值温度和建议">
              <InputNumber style={{ width: '100%' }} placeholder="输入当前股价" />
            </Form.Item>
            <Button type="primary" onClick={doDcf}>计算估值</Button>
          </Form>
        </Card>
      </Col>

      <Col xs={24} lg={14}>
        <Card title="DCF 估值结果">
          {dcfResult ? (
            <Row gutter={[16, 16]}>
              <Col span={8}><Statistic title="企业价值" value={formatMoney(dcfResult.enterprise_value)} /></Col>
              <Col span={8}><Statistic title="预测期现值" value={formatMoney(dcfResult.pv_forecast_period)} /></Col>
              <Col span={8}><Statistic title="终值现值" value={formatMoney(dcfResult.pv_terminal_value)} /></Col>
              <Col span={8}><Statistic title="快速估值" value={formatMoney(dcfResult.quick_fair_value)} /></Col>
              {hasPerShare && (
                <>
                  <Col span={8}><Statistic title="每股公允价值" value={dcfResult.fair_price_per_share!.toFixed(2)} prefix="¥" /></Col>
                  <Col span={8}>
                    <Statistic
                      title={
                        <Tooltip title="安全边际买入价 = 每股公允价值 × 50%。巴菲特/格雷厄姆式价值投资：当股价低于内在价值的一半时买入，留足容错空间。">
                          每股买点 <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
                        </Tooltip>
                      }
                      value={dcfResult.buy_price_per_share!.toFixed(2)} prefix="¥"
                      valueStyle={{ color: '#16a34a' }}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic
                      title={
                        <Tooltip title="高估卖出价 = 每股公允价值 × 150%。当股价超过内在价值的1.5倍时，市场可能过热，考虑卖出。">
                          每股卖点 <InfoCircleOutlined style={{ fontSize: 12, color: '#8c8c8c' }} />
                        </Tooltip>
                      }
                      value={dcfResult.sell_price_per_share!.toFixed(2)} prefix="¥"
                      valueStyle={{ color: '#dc2626' }}
                    />
                  </Col>
                </>
              )}
              {hasAdvice && (
                <Col span={24}>
                  <Tag color={adviceColor} style={{ fontSize: 16, padding: '4px 16px' }}>{dcfResult!.advice}</Tag>
                  {dcfResult!.current_price != null && (
                    <span style={{ marginLeft: 12, color: '#64748b' }}>当前股价: {dcfResult!.current_price} 元</span>
                  )}
                </Col>
              )}
              {needParamsHint && (
                <Col span={24}>
                  <Alert type="info" showIcon message="需要总股本(万股)和当前股价才能计算每股估值和温度计" style={{ marginTop: 8 }} />
                </Col>
              )}
              <Col span={24}>
                <Descriptions size="small" column={4}>
                  <Descriptions.Item label="折现率">{(dcfResult.discount_rate * 100).toFixed(0)}%</Descriptions.Item>
                  <Descriptions.Item label="预测增速">{(dcfResult.forecast_growth * 100).toFixed(0)}%</Descriptions.Item>
                  <Descriptions.Item label="永续增长">{(dcfResult.perpetual_growth * 100).toFixed(1)}%</Descriptions.Item>
                  <Descriptions.Item label="预测年数">{dcfResult.forecast_years}年</Descriptions.Item>
                </Descriptions>
              </Col>
            </Row>
          ) : (
            <Empty description="请填写参数后点击计算估值" />
          )}
        </Card>
      </Col>

      {dcfResult?.temperature != null && (
        <Col span={24}>
          <Card title="估值温度计">
            <ReactECharts option={tempOption!} style={{ height: 140 }} />
          </Card>
        </Col>
      )}
    </Row>
  );
};

export default ValuationPage;
