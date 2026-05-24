import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertOutlined,
  ApartmentOutlined,
  AuditOutlined,
  BankOutlined,
  DashboardOutlined,
  DollarOutlined,
  RiseOutlined,
  FundOutlined,
  LineChartOutlined,
  MoneyCollectOutlined,
  ReadOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Segmented, Select, Spin, message } from 'antd';

import { analysisApi, companyApi } from './utils/api';
import { AnalysisResult, Company, TrendResult } from './types';
import { reportPeriodLabel } from './utils/format';

import UploadPage from './pages/Upload/UploadPage';
import OverviewPage from './pages/Overview/OverviewPage';
import GrowthPage from './pages/Growth/GrowthPage';
import SolvencyPage from './pages/Solvency/SolvencyPage';
import EfficiencyPage from './pages/Efficiency/EfficiencyPage';
import QualityScorePage from './pages/QualityScore/QualityScorePage';
import BalanceSheetPage from './pages/BalanceSheet/BalanceSheetPage';
import IncomeStatementPage from './pages/IncomeStatement/IncomeStatementPage';
import CashFlowPage from './pages/CashFlow/CashFlowPage';
import RiskAlertPage from './pages/RiskAlert/RiskAlertPage';
import TrendPage from './pages/Trend/TrendPage';
import ValuationPage from './pages/Valuation/ValuationPage';
import ComparePage from './pages/Compare/ComparePage';
import AIAnalysisPage from './pages/AIAnalysis/AIAnalysisPage';
import LogViewerPage from './pages/LogViewer/LogViewerPage';
import StatementsPage from './pages/Statements/StatementsPage';

const { Sider, Header, Content } = Layout;

const App: React.FC = () => {
  const [currentPage, setCurrentPage] = useState('upload');
  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedQuarter, setSelectedQuarter] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'cumulative' | 'single_quarter'>('cumulative');
  const [analysisData, setAnalysisData] = useState<AnalysisResult | null>(null);
  const [trendData, setTrendData] = useState<TrendResult | null>(null);
  const [loading, setLoading] = useState(false);

  const selectedCompany = useMemo(() => companies.find((c) => c.id === selectedCompanyId), [companies, selectedCompanyId]);

  const loadCompanies = async () => {
    const data = await companyApi.list();
    setCompanies(data);
    if (!selectedCompanyId && data.length > 0) {
      setSelectedCompanyId(data[0].id);
    }
  };

  const loadAnalysis = async (companyId: number, year?: number | null, quarter?: number | null) => {
    setLoading(true);
    try {
      const [single, trend] = await Promise.all([
        analysisApi.getSingle(companyId, year ?? undefined, quarter ?? undefined, viewMode),
        analysisApi.getTrend(companyId, viewMode),
      ]);
      setAnalysisData(single);
      setTrendData(trend);
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '加载分析失败');
      setAnalysisData(null);
      setTrendData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies().catch(() => message.error('加载公司失败'));
  }, []);

  useEffect(() => {
    if (!selectedCompanyId) return;
    loadAnalysis(selectedCompanyId, selectedYear, selectedQuarter).catch(() => undefined);
  }, [selectedCompanyId, selectedYear, selectedQuarter, viewMode]);

  const menuItems = [
    { key: 'upload', icon: <UploadOutlined />, label: '数据上传' },
    { key: 'dashboard', icon: <DashboardOutlined />, label: '公司概览' },
    { key: 'growth', icon: <RiseOutlined />, label: '成长分析' },
    { key: 'solvency', icon: <SafetyCertificateOutlined />, label: '偿债能力' },
    { key: 'efficiency', icon: <ThunderboltOutlined />, label: '营运效率' },
    { key: 'quality', icon: <AuditOutlined />, label: '财务质量评分' },
    { key: 'balance', icon: <BankOutlined />, label: '资产负债表' },
    { key: 'income', icon: <FundOutlined />, label: '利润表' },
    { key: 'cashflow', icon: <MoneyCollectOutlined />, label: '现金流量表' },
    { key: 'statements', icon: <ReadOutlined />, label: '财务报表' },
    { key: 'risk', icon: <AlertOutlined />, label: '风险预警' },
    { key: 'trend', icon: <LineChartOutlined />, label: '趋势分析' },
    { key: 'valuation', icon: <DollarOutlined />, label: '估值分析' },
    { key: 'compare', icon: <ApartmentOutlined />, label: '多公司对比' },
    { key: 'ai-analysis', icon: <RobotOutlined />, label: 'AI 分析' },
    { key: 'logs', icon: <FileTextOutlined />, label: '系统日志' },
  ];

  const yearOptions = Array.from(new Set((selectedCompany?.reports || []).map((r) => r.year)))
    .sort((a, b) => b - a)
    .map((year) => ({ label: `${year}`, value: year }));

  const quarterOptions = (selectedCompany?.reports || [])
    .filter((r) => (selectedYear ? r.year === selectedYear : true))
    .map((r) => r.quarter)
    .filter((q, idx, arr) => arr.indexOf(q) === idx)
    .sort((a, b) => {
      const order = { 1: 1, 2: 2, 3: 3, 0: 4 } as Record<number, number>;
      return (order[a] ?? 99) - (order[b] ?? 99);
    })
    .map((q) => ({ label: selectedYear ? reportPeriodLabel(selectedYear, q) : `Q${q}`, value: q }));

  const renderPage = () => {
    switch (currentPage) {
      case 'upload':
        return <UploadPage companies={companies} onRefresh={loadCompanies} />;
      case 'dashboard':
        return <OverviewPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'growth':
        return <GrowthPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'solvency':
        return <SolvencyPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'efficiency':
        return <EfficiencyPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'quality':
        return <QualityScorePage data={analysisData} trendData={trendData} loading={loading} />;
      case 'balance':
        return <BalanceSheetPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'income':
        return <IncomeStatementPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'cashflow':
        return <CashFlowPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'statements':
        return <StatementsPage company={selectedCompany ?? null} year={selectedYear} quarter={selectedQuarter} trendData={trendData} />;
      case 'risk':
        return <RiskAlertPage data={analysisData} trendData={trendData} loading={loading} />;
      case 'trend':
        return <TrendPage trendData={trendData} loading={loading} />;
      case 'valuation':
        return <ValuationPage data={analysisData} companyId={selectedCompanyId} loading={loading} />;
      case 'compare':
        return <ComparePage companies={companies} />;
      case 'ai-analysis':
        return <AIAnalysisPage companyId={selectedCompanyId} selectedYear={selectedYear} selectedQuarter={selectedQuarter} viewMode={viewMode} />;
      case 'logs':
        return <LogViewerPage />;
      default:
        return null;
    }
  };

  return (
    <Layout className="layout-root">
      <Sider width={220} className="app-sider" breakpoint="lg" collapsedWidth="0">
        <div className="app-logo">财报全景分析</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[currentPage]}
          onClick={(e) => setCurrentPage(e.key)}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Select
            placeholder="选择公司"
            style={{ minWidth: 220 }}
            value={selectedCompanyId ?? undefined}
            options={companies.map((c) => ({ label: `${c.name}${c.stock_code ? `(${c.stock_code})` : ''}`, value: c.id }))}
            onChange={(v) => {
              setSelectedCompanyId(v);
              setSelectedYear(null);
              setSelectedQuarter(null);
            }}
          />
          <Select
            placeholder="选择年度"
            allowClear
            style={{ minWidth: 160 }}
            value={selectedYear ?? undefined}
            options={yearOptions}
            onChange={(v) => {
              setSelectedYear(v ?? null);
              setSelectedQuarter(null);
            }}
          />
          <Select
            placeholder="选择报告期"
            allowClear
            style={{ minWidth: 180 }}
            value={selectedQuarter ?? undefined}
            options={quarterOptions}
            onChange={(v) => setSelectedQuarter(v ?? null)}
            disabled={!selectedYear}
          />
          <Segmented
            options={[
              { label: '累计', value: 'cumulative' },
              { label: '单季', value: 'single_quarter' },
            ]}
            value={viewMode}
            onChange={(v) => setViewMode(v as 'cumulative' | 'single_quarter')}
          />
        </Header>
        <Content className="app-content">{loading && currentPage !== 'upload' ? <Spin /> : renderPage()}</Content>
      </Layout>
    </Layout>
  );
};

export default App;
