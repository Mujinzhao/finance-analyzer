import React, { useMemo, useState } from 'react';
import {
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  message,
  Modal,
  Popconfirm,
  Statistic,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Upload,
  Card,
  Typography,
  Row,
  Col,
} from 'antd';
import { ArrowLeftOutlined, DeleteOutlined, DownloadOutlined, EditOutlined, EyeOutlined, PlusOutlined, SaveOutlined, UploadOutlined } from '@ant-design/icons';

import { Company, ReportDetail, ReportMeta } from '../../types';
import { companyApi, reportApi } from '../../utils/api';
import { formatMoney, reportPeriodLabel } from '../../utils/format';

interface Props {
  companies: Company[];
  onRefresh: () => Promise<void>;
}

interface UploadItem {
  file: File;
  year: number;
  quarter: number;
  parsed: boolean;  // whether year/quarter was auto-detected from filename
  status: 'pending' | 'uploading' | 'success' | 'error';
  message?: string;
}

function parseFilenamePeriod(filename: string): { year: number; quarter: number } | null {
  const m = filename.match(/(20\d{2})/);
  if (!m) return null;
  const year = parseInt(m[1], 10);
  const base = filename.toLowerCase();
  if (/一季|1季|q1|一季度/.test(base)) return { year, quarter: 1 };
  if (/半年|中报|二季|2季|q2|二季度|semi/.test(base)) return { year, quarter: 2 };
  if (/三季|3季|q3|三季度/.test(base)) return { year, quarter: 3 };
  if (/年报|年度|q4|annual/.test(base)) return { year, quarter: 0 };
  return null;
}

const UploadPage: React.FC<Props> = ({ companies, onRefresh }) => {
  const [companyModal, setCompanyModal] = useState(false);
  const [uploadModal, setUploadModal] = useState(false);
  const [editDrawer, setEditDrawer] = useState(false);
  const [detailCompanyId, setDetailCompanyId] = useState<number | null>(null);
  const [editingReport, setEditingReport] = useState<ReportDetail | null>(null);
  const [uploadCompanyId, setUploadCompanyId] = useState<number | null>(null);
  const [uploadFiles, setUploadFiles] = useState<UploadItem[]>([]);
  const [changedFields, setChangedFields] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [form] = Form.useForm();
  const detailCompany = useMemo(() => companies.find((item) => item.id === detailCompanyId) || null, [companies, detailCompanyId]);
  const yearGroups = useMemo(() => {
    if (!detailCompany?.reports) return [];
    const years = Array.from(new Set(detailCompany.reports.map((report) => report.year))).sort((a, b) => b - a);
    return years.map((groupYear) => ({
      year: groupYear,
      reports: detailCompany.reports?.filter((report) => report.year === groupYear).sort((a, b) => a.quarter - b.quarter) || [],
    }));
  }, [detailCompany]);
  const reportCount = detailCompany?.reports?.length || 0;
  const yearCount = yearGroups.length;
  const latestReport = detailCompany?.reports?.slice().sort((a, b) => (b.year - a.year) || (b.quarter - a.quarter))[0];

  const openUploadModal = (companyId?: number | null) => {
    setUploadCompanyId(companyId ?? null);
    setUploadFiles([]);
    setUploadModal(true);
  };

  const openEdit = async (report: ReportMeta) => {
    const detail = await reportApi.getDetail(report.id);
    setEditingReport(detail);
    setChangedFields({});
    setEditDrawer(true);
  };

  const submitCompany = async () => {
    const values = await form.validateFields();
    await companyApi.create(values);
    message.success('公司已创建');
    setCompanyModal(false);
    form.resetFields();
    await onRefresh();
  };

  const doBatchUpload = async () => {
    if (!uploadCompanyId || uploadFiles.length === 0) {
      message.warning('请选择至少一个文件');
      return;
    }

    const invalid = uploadFiles.find((item) => !item.year || item.quarter === undefined);
    if (invalid) {
      message.warning(`无法识别文件 "${invalid.file.name}" 的报告期间，请手动填写年份/季度`);
      return;
    }

    setUploading(true);
    const updated = [...uploadFiles];

    for (let i = 0; i < updated.length; i++) {
      updated[i] = { ...updated[i], status: 'uploading' as const };
      setUploadFiles([...updated]);

      const fd = new FormData();
      fd.append('file', updated[i].file);
      try {
        await reportApi.upload(fd, uploadCompanyId, updated[i].year, updated[i].quarter);
        updated[i] = { ...updated[i], status: 'success' as const };
      } catch (e: any) {
        updated[i] = {
          ...updated[i],
          status: 'error' as const,
          message: e?.response?.data?.detail || e?.message || '上传失败',
        };
      }
      setUploadFiles([...updated]);
    }

    setUploading(false);
    const ok = updated.filter((item) => item.status === 'success').length;
    const fail = updated.filter((item) => item.status === 'error').length;
    if (fail === 0) {
      message.success(`全部 ${ok} 份报表上传成功`);
      setUploadModal(false);
    } else {
      message.warning(`上传完成: ${ok} 成功, ${fail} 失败`);
    }
    await onRefresh();
  };

  const removeCompany = async (id: number) => {
    await companyApi.delete(id);
    message.success('公司已删除');
    if (detailCompanyId === id) {
      setDetailCompanyId(null);
    }
    await onRefresh();
  };

  const removeReport = (report: ReportMeta) => {
    Modal.confirm({
      title: '删除当前报表？',
      content: `将删除 ${reportPeriodLabel(report.year, report.quarter)}，此操作不可恢复。`,
      okButtonProps: { danger: true },
      onOk: async () => {
        await reportApi.delete(report.id);
        message.success('报表已删除');
        await onRefresh();
      },
    });
  };

  const removeYearReports = (companyId: number, year: number) => {
    Modal.confirm({
      title: `删除 ${year} 年全部报表？`,
      content: '将删除该公司该年度所有季度/年报，且不可恢复。',
      okButtonProps: { danger: true },
      onOk: async () => {
        const resp = await reportApi.deleteByYear(companyId, year);
        message.success(`已删除 ${resp.deleted_count ?? 0} 份报表`);
        await onRefresh();
      },
    });
  };

  const updateField = (field: string, value: number | null | undefined) => {
    if (!editingReport) return;
    const num = Number(value || 0);
    setChangedFields((prev) => ({ ...prev, [field]: num }));

    const patch = (list: any[]) => list.map((row) => (row.field === field ? { ...row, value: num } : row));
    setEditingReport({
      ...editingReport,
      balance_sheet: patch(editingReport.balance_sheet),
      income_statement: patch(editingReport.income_statement),
      cash_flow: patch(editingReport.cash_flow),
    });
  };

  const saveChanges = async () => {
    if (!editingReport || Object.keys(changedFields).length === 0) return;
    setSaving(true);
    try {
      await reportApi.update(editingReport.id, changedFields);
      message.success('保存成功');
      setChangedFields({});
      await onRefresh();
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    { title: '公司名称', dataIndex: 'name', key: 'name' },
    { title: '股票代码', dataIndex: 'stock_code', key: 'stock_code' },
    { title: '所属行业', dataIndex: 'industry', key: 'industry' },
    {
      title: '报表概览',
      key: 'reports',
      render: (_: any, row: Company) => (
        <Space wrap>
          <Tag color="cyan">{row.reports?.length || 0} 份报表</Tag>
          {Array.from(new Set((row.reports || []).map((r) => r.year))).sort((a, b) => b - a).map((y) => (
            <Tag key={y}>{y}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, row: Company) => (
        <Space>
          <Button icon={<EyeOutlined />} onClick={() => setDetailCompanyId(row.id)}>详情</Button>
          <Button type="primary" icon={<UploadOutlined />} onClick={() => openUploadModal(row.id)}>上传</Button>
          <Button danger onClick={() => removeCompany(row.id)}>删除</Button>
        </Space>
      ),
    },
  ];

  const detailColumns = [
    { title: '科目', dataIndex: 'label', key: 'label', width: '50%' },
    {
      title: '金额',
      key: 'value',
      render: (_: any, row: any) => (
        <InputNumber
          style={{ width: '100%' }}
          value={row.value}
          onChange={(v) => updateField(row.field, v)}
          formatter={(v) => String(v)}
        />
      ),
    },
    {
      title: '预览',
      key: 'preview',
      render: (_: any, row: any) => <span style={{ color: changedFields[row.field] !== undefined ? '#1677ff' : undefined }}>{formatMoney(row.value)}</span>,
    },
  ];

  const renderListView = () => (
    <div className="company-workspace">
      <div className="company-workspace__hero">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>公司数据管理</Typography.Title>
          <Typography.Paragraph style={{ margin: '8px 0 0', color: '#475569' }}>
            先选公司，再进入详情页集中维护报表。新增、编辑、删除都放在单公司视角里，操作范围更清楚。
          </Typography.Paragraph>
        </div>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCompanyModal(true)}>新建公司</Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={async () => {
              const blob = await reportApi.downloadTemplate();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = '财报上传模板.xlsx';
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            下载 Excel 模板
          </Button>
        </Space>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="公司数量" value={companies.length} /></Card></Col>
        <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="报表总数" value={companies.reduce((sum, company) => sum + (company.reports?.length || 0), 0)} /></Card></Col>
        <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="有数据公司" value={companies.filter((company) => (company.reports?.length || 0) > 0).length} /></Card></Col>
      </Row>

      <Card className="company-table-card">
        <Table rowKey="id" columns={columns} dataSource={companies} pagination={{ pageSize: 8 }} />
      </Card>
    </div>
  );

  const renderDetailView = () => {
    if (!detailCompany) {
      return <Empty description="未找到公司详情" />;
    }

    return (
      <div className="company-detail-page">
        <div className="company-detail-page__hero">
          <div>
            <Button icon={<ArrowLeftOutlined />} type="link" style={{ paddingLeft: 0 }} onClick={() => setDetailCompanyId(null)}>
              返回公司列表
            </Button>
            <Typography.Title level={3} style={{ margin: '8px 0 4px' }}>{detailCompany.name}</Typography.Title>
            <Space wrap>
              {detailCompany.stock_code ? <Tag color="geekblue">{detailCompany.stock_code}</Tag> : null}
              {detailCompany.industry ? <Tag color="green">{detailCompany.industry}</Tag> : null}
              <Tag color="cyan">{reportCount} 份报表</Tag>
              <Tag color="gold">{yearCount} 个年度</Tag>
            </Space>
          </div>
          <Space wrap>
            <Button type="primary" icon={<UploadOutlined />} onClick={() => openUploadModal(detailCompany.id)}>新增报表</Button>
            <Popconfirm title="删除当前公司？" description="会一并删除该公司全部报表。" okText="删除" cancelText="取消" onConfirm={() => removeCompany(detailCompany.id)}>
              <Button danger icon={<DeleteOutlined />}>删除公司</Button>
            </Popconfirm>
          </Space>
        </div>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="报表数量" value={reportCount} /></Card></Col>
          <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="覆盖年度" value={yearCount} /></Card></Col>
          <Col xs={24} md={8}><Card className="company-stat-card"><Statistic title="最新报表" value={latestReport ? reportPeriodLabel(latestReport.year, latestReport.quarter) : '暂无'} /></Card></Col>
        </Row>

        {yearGroups.length === 0 ? (
          <Card className="company-empty-card">
            <Empty description="该公司还没有上传任何报表">
              <Button type="primary" icon={<UploadOutlined />} onClick={() => openUploadModal(detailCompany.id)}>上传第一份报表</Button>
            </Empty>
          </Card>
        ) : (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {yearGroups.map((group) => (
              <Card
                key={group.year}
                className="company-year-card"
                title={<Space><Tag color="blue">{group.year}</Tag><span>年度报表</span></Space>}
                extra={<Button size="small" danger onClick={() => removeYearReports(detailCompany.id, group.year)}>删除该年全部</Button>}
              >
                <List
                  dataSource={group.reports}
                  renderItem={(report) => (
                    <List.Item
                      actions={[
                        <Button key="edit" type="link" icon={<EditOutlined />} onClick={() => openEdit(report)}>编辑</Button>,
                        <Button key="delete" type="link" danger onClick={() => removeReport(report)}>删除</Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={<Space><Tag color={report.quarter === 0 ? 'purple' : 'magenta'}>{reportPeriodLabel(report.year, report.quarter)}</Tag><span>{report.report_type === 'annual' ? '年度报告' : '季度报告'}</span></Space>}
                        description={`报表 ID: ${report.id}`}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            ))}
          </Space>
        )}
      </div>
    );
  };

  return (
    <div>
      {detailCompanyId ? renderDetailView() : renderListView()}

      <Modal title="新建公司" open={companyModal} onCancel={() => setCompanyModal(false)} onOk={submitCompany}>
        <Form layout="vertical" form={form}>
          <Form.Item label="公司名称" name="name" rules={[{ required: true, message: '请输入公司名称' }]}><Input /></Form.Item>
          <Form.Item label="行业" name="industry"><Input /></Form.Item>
          <Form.Item label="股票代码" name="stock_code"><Input /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title="批量上传报表"
        open={uploadModal}
        width={720}
        onCancel={() => {
          if (uploading) return;
          setUploadModal(false);
        }}
        footer={[
          <Button key="cancel" disabled={uploading} onClick={() => setUploadModal(false)}>取消</Button>,
          <Button key="upload" type="primary" loading={uploading} disabled={uploadFiles.length === 0} onClick={doBatchUpload}>
            上传全部（{uploadFiles.length} 份）
          </Button>,
        ]}
        maskClosable={!uploading}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Select
            disabled={uploading}
            value={uploadCompanyId ?? undefined}
            onChange={(v) => setUploadCompanyId(v)}
            options={companies.map((c) => ({ label: c.name, value: c.id }))}
            placeholder="选择公司"
          />
          <Upload
            disabled={uploading}
            multiple
            accept=".xlsx,.xls,.pdf"
            showUploadList={false}
            beforeUpload={(f) => {
              const parsed = parseFilenamePeriod(f.name);
              const item: UploadItem = {
                file: f,
                year: parsed?.year ?? new Date().getFullYear(),
                quarter: parsed?.quarter ?? 0,
                parsed: parsed !== null,
                status: 'pending',
              };
              setUploadFiles((prev) => [...prev, item]);
              return false;
            }}
          >
            <Button icon={<UploadOutlined />} disabled={uploading}>选择文件（可多选）</Button>
          </Upload>

          {uploadFiles.length > 0 && (
            <Table<UploadItem>
              rowKey={(r) => r.file.name + r.file.size}
              dataSource={uploadFiles}
              pagination={false}
              size="small"
              columns={[
                {
                  title: '文件名',
                  dataIndex: 'file',
                  render: (f: File) => (
                    <span style={{ fontSize: 13 }}>
                      {f.name}
                      {f.name.toLowerCase().endsWith('.pdf') ? <Tag color="purple" style={{ marginLeft: 6, fontSize: 11 }}>PDF</Tag> : <Tag color="green" style={{ marginLeft: 6, fontSize: 11 }}>Excel</Tag>}
                    </span>
                  ),
                },
                {
                  title: '年份', width: 90,
                  render: (_: any, record: UploadItem) => (
                    <InputNumber
                      size="small"
                      style={{ width: 70 }}
                      disabled={uploading}
                      value={record.year}
                      onChange={(v) => {
                        const next = [...uploadFiles];
                        const idx = next.indexOf(record);
                        if (idx >= 0) next[idx] = { ...next[idx], year: Number(v || new Date().getFullYear()) };
                        setUploadFiles(next);
                      }}
                    />
                  ),
                },
                {
                  title: '报告期', width: 110,
                  render: (_: any, record: UploadItem) => (
                    <Select
                      size="small"
                      style={{ width: 100 }}
                      disabled={uploading}
                      value={record.quarter}
                      onChange={(v) => {
                        const next = [...uploadFiles];
                        const idx = next.indexOf(record);
                        if (idx >= 0) next[idx] = { ...next[idx], quarter: v };
                        setUploadFiles(next);
                      }}
                      options={[
                        { label: '一季报', value: 1 },
                        { label: '半年报', value: 2 },
                        { label: '三季报', value: 3 },
                        { label: '年报', value: 0 },
                      ]}
                    />
                  ),
                },
                {
                  title: '识别', width: 70,
                  render: (_: any, record: UploadItem) =>
                    record.parsed ? <Tag color="blue" style={{ fontSize: 11 }}>自动</Tag> : <Tag color="default" style={{ fontSize: 11 }}>手动</Tag>,
                },
                {
                  title: '状态', width: 90,
                  render: (_: any, record: UploadItem) => {
                    if (record.status === 'uploading') return <Tag color="processing">上传中</Tag>;
                    if (record.status === 'success') return <Tag color="success">成功</Tag>;
                    if (record.status === 'error') return <Tooltip title={record.message}><Tag color="error">失败</Tag></Tooltip>;
                    return <Tag>等待</Tag>;
                  },
                },
                {
                  title: '', width: 40,
                  render: (_: any, record: UploadItem) => (
                    <Button
                      type="link" size="small" danger
                      disabled={uploading}
                      onClick={() => setUploadFiles((prev) => prev.filter((item) => item !== record))}
                    >移除</Button>
                  ),
                },
              ]}
            />
          )}
        </Space>
      </Modal>

      <Drawer
        title="报表编辑"
        width={720}
        open={editDrawer}
        onClose={() => {
          if (Object.keys(changedFields).length > 0) {
            Modal.confirm({
              title: '有未保存修改，确认关闭？',
              onOk: () => setEditDrawer(false),
            });
          } else {
            setEditDrawer(false);
          }
        }}
        extra={
          <Space>
            <span>修改项 {Object.keys(changedFields).length}</span>
            <Button type="primary" loading={saving} icon={<SaveOutlined />} onClick={saveChanges}>保存</Button>
          </Space>
        }
      >
        {editingReport && (
          <Tabs
            items={[
              { key: 'b', label: '资产负债表', children: <Table rowKey="field" columns={detailColumns} dataSource={editingReport.balance_sheet} pagination={false} /> },
              { key: 'i', label: '利润表', children: <Table rowKey="field" columns={detailColumns} dataSource={editingReport.income_statement} pagination={false} /> },
              { key: 'c', label: '现金流量表', children: <Table rowKey="field" columns={detailColumns} dataSource={editingReport.cash_flow} pagination={false} /> },
            ]}
          />
        )}
      </Drawer>
    </div>
  );
};

export default UploadPage;
