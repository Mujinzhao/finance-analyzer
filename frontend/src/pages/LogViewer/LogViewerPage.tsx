import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Button, Card, Col, Empty, Input, Row, Select, Space, Switch, Tag, Typography } from 'antd';
import { ReloadOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons';
import { logApi } from '../../utils/api';

interface LogFile {
  name: string;
  size: number;
  size_display: string;
  modified: string;
}

const levelColors: Record<string, string> = {
  ERROR: '#dc2626',
  CRITICAL: '#dc2626',
  WARNING: '#f97316',
  WARN: '#f97316',
  INFO: '#2563eb',
  DEBUG: '#8c8c8c',
};

const lineLevel = (line: string): string | null => {
  const m = line.match(/\b(ERROR|CRITICAL|WARNING|WARN|INFO|DEBUG)\b/);
  return m ? m[1] : null;
};

const LogViewerPage: React.FC = () => {
  const [files, setFiles] = useState<LogFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [totalLines, setTotalLines] = useState(0);
  const [returnedLines, setReturnedLines] = useState(0);
  const [linesParam, setLinesParam] = useState(200);
  const [levelFilter, setLevelFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadFiles = useCallback(async () => {
    try {
      const data = await logApi.list();
      setFiles(data.files || []);
      if (!selectedFile && data.files?.length > 0) {
        setSelectedFile(data.files[0].name);
      }
    } catch {
      // ignore
    }
  }, [selectedFile]);

  const loadContent = useCallback(async () => {
    if (!selectedFile) return;
    setLoading(true);
    try {
      const data = await logApi.read(selectedFile, {
        lines: linesParam,
        level: levelFilter || undefined,
        search: searchText || undefined,
      });
      setLogLines(data.lines || []);
      setTotalLines(data.total_lines);
      setReturnedLines(data.returned_lines);
    } catch {
      setLogLines([]);
    } finally {
      setLoading(false);
    }
  }, [selectedFile, linesParam, levelFilter, searchText]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  useEffect(() => {
    loadContent();
  }, [loadContent]);

  useEffect(() => {
    if (autoRefresh) {
      timerRef.current = setInterval(loadContent, 10000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, loadContent]);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logLines]);

  const handleDownload = () => {
    if (!selectedFile) return;
    const blob = new Blob([logLines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClearSearch = () => {
    setSearchText('');
    setLevelFilter(undefined);
  };

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card size="small">
          <Space wrap>
            <Select
              style={{ minWidth: 200 }}
              value={selectedFile}
              onChange={(v) => {
                setSelectedFile(v);
                setLogLines([]);
              }}
              options={files.map((f) => ({
                label: `${f.name} (${f.size_display})`,
                value: f.name,
              }))}
            />
            <Select
              style={{ width: 120 }}
              value={linesParam}
              onChange={(v) => setLinesParam(v)}
              options={[50, 100, 200, 500, 1000, 2000].map((n) => ({ label: `最近${n}行`, value: n }))}
            />
            <Select
              allowClear
              style={{ width: 100 }}
              placeholder="级别"
              value={levelFilter}
              onChange={(v) => setLevelFilter(v)}
              options={['ERROR', 'WARNING', 'INFO', 'DEBUG'].map((l) => ({ label: l, value: l }))}
            />
            <Input
              allowClear
              style={{ width: 200 }}
              placeholder="搜索关键词..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onPressEnter={loadContent}
            />
            <Button icon={<ReloadOutlined />} loading={loading} onClick={loadContent}>刷新</Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownload} disabled={!selectedFile || logLines.length === 0}>
              下载
            </Button>
            <Switch
              checkedChildren="自动刷新"
              unCheckedChildren="手动"
              checked={autoRefresh}
              onChange={setAutoRefresh}
            />
          </Space>
          <div style={{ marginTop: 8, color: '#8c8c8c', fontSize: 12 }}>
            共 {totalLines.toLocaleString()} 行 | 显示 {returnedLines} 行
            {(levelFilter || searchText) && (
              <Tag closable onClose={handleClearSearch} style={{ marginLeft: 8 }}>
                {[levelFilter, searchText].filter(Boolean).join(' + ')}
              </Tag>
            )}
          </div>
        </Card>
      </Col>

      <Col span={24}>
        <Card size="small" bodyStyle={{ padding: 0 }}>
          {logLines.length === 0 ? (
            <Empty description={loading ? '加载中...' : '无日志内容'} style={{ padding: 40 }} />
          ) : (
            <div
              ref={containerRef}
              style={{
                height: 'calc(100vh - 320px)',
                minHeight: 400,
                overflow: 'auto',
                background: '#0d1117',
                color: '#c9d1d9',
                fontFamily: "'SF Mono', 'Fira Code', 'Consolas', monospace",
                fontSize: 12,
                lineHeight: '20px',
                padding: '12px 16px',
              }}
            >
              {logLines.map((line, i) => {
                const lvl = lineLevel(line);
                const color = lvl ? levelColors[lvl] : undefined;
                return (
                  <div
                    key={i}
                    style={{
                      whiteSpace: 'pre',
                      color,
                      backgroundColor: lvl === 'ERROR' || lvl === 'CRITICAL' ? 'rgba(220,38,38,0.08)' : lvl === 'WARNING' ? 'rgba(249,115,22,0.06)' : undefined,
                      padding: lvl === 'ERROR' || lvl === 'CRITICAL' ? '0 4px' : undefined,
                      borderRadius: lvl ? 2 : undefined,
                    }}
                  >
                    {line.trimEnd()}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default LogViewerPage;
