export const formatMoney = (value?: number | null): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  const abs = Math.abs(value);
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(value / 1e4).toFixed(2)}万`;
  return value.toFixed(2);
};

export const formatPercent = (value?: number | null): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return `${value.toFixed(2)}%`;
};

export const formatNumber = (value?: number | null, decimals = 2): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return value.toFixed(decimals);
};

export const riskColor = (level?: string): string => {
  if (level === 'safe') return '#52c41a';
  if (level === 'warning') return '#faad14';
  if (level === 'danger') return '#ff4d4f';
  return '#8c8c8c';
};

export const scoreColor = (score?: number): string => {
  if (score === undefined || score === null) return '#8c8c8c';
  if (score >= 75) return '#52c41a';
  if (score >= 50) return '#faad14';
  return '#ff4d4f';
};

export const reportPeriodLabel = (year: number, quarter: number, view?: string): string => {
  if (view === 'single_quarter') {
    if (quarter === 0) return `${year}Q4单季`;
    return `${year}Q${quarter}单季`;
  }
  if (quarter === 0) return `${year}年报`;
  if (quarter === 1) return `${year}一季报`;
  if (quarter === 2) return `${year}半年报`;
  if (quarter === 3) return `${year}三季报`;
  return `${year}Q${quarter}`;
};
