import React, { useEffect, useMemo, useState } from 'react';
import { Button, Card, Empty, Space, Spin, Tag, Typography } from 'antd';
import { aiApi } from '../../utils/api';
import { AISummaryResult } from '../../types';

const titleEmoji: Record<string, string> = {
  企业概况总结: '🏢',
  盈利能力分析: '📈',
  资产质量评估: '🏦',
  现金流健康度: '💰',
  风险提示: '⚠️',
  投资建议: '💡',
};

const parseSimpleMarkdown = (text: string) => {
  return text.split('\n').map((line, idx) => {
    if (line.startsWith('- ')) return <div key={idx} style={{ paddingLeft: 16 }}>• {line.slice(2)}</div>;
    if (line.includes('**')) {
      const replaced = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return <div key={idx} dangerouslySetInnerHTML={{ __html: replaced }} />;
    }
    return <div key={idx}>{line}</div>;
  });
};

const AIAnalysisPage: React.FC<{ companyId: number | null; selectedYear: number | null; selectedQuarter: number | null; viewMode?: string }> = ({ companyId, selectedYear, selectedQuarter, viewMode }) => {
  const [data, setData] = useState<AISummaryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const load = async (regenerate = false) => {
    if (!companyId) return;
    setLoading(true);
    try {
      const res = await aiApi.getSummary(companyId, selectedYear ?? undefined, selectedQuarter ?? undefined, regenerate, viewMode);
      setData(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(false).catch(() => setData(null));
  }, [companyId, selectedYear, selectedQuarter, viewMode]);

  const sections = useMemo(() => {
    if (!data?.summary) return [];
    return data.summary.split('## ').filter(Boolean).map((segment) => {
      const lines = segment.split('\n');
      const title = lines[0].trim();
      const content = lines.slice(1).join('\n');
      return { title, content };
    });
  }, [data]);

  if (!companyId) return <Empty description="请选择公司" />;
  if (loading) return <Spin tip="DeepSeek 正在生成分析报告，首次约 10-20 秒..." />;

  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Tag>{data?.generated_at ? `生成时间: ${new Date(data.generated_at).toLocaleString()}` : '暂无时间'}</Tag>
        <Tag color={data?.cached ? 'blue' : 'green'}>{data?.cached ? 'DeepSeek 缓存结果' : 'DeepSeek 新生成'}</Tag>
        <Button
          loading={regenerating}
          onClick={async () => {
            setRegenerating(true);
            try {
              await load(true);
            } finally {
              setRegenerating(false);
            }
          }}
        >
          重新生成
        </Button>
      </Space>

      {sections.map((s) => (
        <Card key={s.title} style={{ marginBottom: 12 }} title={`${titleEmoji[s.title] || '📝'} ${s.title}`}>
          <Typography.Paragraph>{parseSimpleMarkdown(s.content)}</Typography.Paragraph>
        </Card>
      ))}
    </div>
  );
};

export default AIAnalysisPage;
