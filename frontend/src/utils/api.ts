import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

export const companyApi = {
  list: () => api.get('/api/companies').then((r) => r.data),
  create: (data: { name: string; industry?: string; stock_code?: string }) => api.post('/api/companies', data).then((r) => r.data),
  update: (id: number, data: { name: string; industry?: string; stock_code?: string }) => api.put(`/api/companies/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/api/companies/${id}`).then((r) => r.data),
};

export const reportApi = {
  upload: (
    formData: FormData,
    companyId: number,
    year: number,
    quarter: number,
    onUploadProgress?: (progressEvent: any) => void,
  ) =>
    api.post('/api/upload', formData, {
      params: { company_id: companyId, year, quarter },
      timeout: 1200000,
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
    }).then((r) => r.data),
  uploadBatch: (formData: FormData, companyId: number) =>
    api.post('/api/upload/batch', formData, {
      params: { company_id: companyId },
      timeout: 3600000,
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data),
  downloadTemplate: () => api.get('/api/template', { responseType: 'blob' }).then((r) => r.data),
  getDetail: (id: number) => api.get(`/api/reports/${id}`).then((r) => r.data),
  update: (id: number, fields: Record<string, number>) => api.put(`/api/reports/${id}`, { fields }).then((r) => r.data),
  delete: (id: number) => api.delete(`/api/reports/${id}`).then((r) => r.data),
  deleteByYear: (companyId: number, year: number) =>
    api.delete(`/api/companies/${companyId}/reports`, { params: { year } }).then((r) => r.data),
};

export const analysisApi = {
  getSingle: (companyId: number, year?: number | null, quarter?: number | null, viewMode?: string) => {
    const params: any = {};
    if (year) params.year = year;
    if (quarter !== undefined && quarter !== null) params.quarter = quarter;
    if (viewMode) params.view = viewMode;
    return api.get(`/api/analysis/${companyId}`, { params }).then((r) => r.data);
  },
  getTrend: (companyId: number, viewMode?: string) => {
    const params: any = {};
    if (viewMode) params.view = viewMode;
    return api.get(`/api/trend/${companyId}`, { params }).then((r) => r.data);
  },
  compare: (ids: number[], year?: number | null) => {
    const params: any = { company_ids: ids.join(',') };
    if (year) params.year = year;
    return api.get('/api/compare', { params }).then((r) => r.data);
  },
};

export const valuationApi = {
  getDCF: (data: any) => api.post('/api/valuation/dcf', data).then((r) => r.data),
  getCompanyValuation: (companyId: number, year?: number | null, viewMode?: string) => {
    const params: any = {};
    if (year) params.year = year;
    if (viewMode) params.view = viewMode;
    return api.get(`/api/valuation/${companyId}`, { params }).then((r) => r.data);
  },
};

export const logApi = {
  list: () => api.get('/api/logs').then((r) => r.data),
  read: (filename: string, params?: { lines?: number; offset?: number; level?: string; search?: string }) =>
    api.get(`/api/logs/${filename}`, { params }).then((r) => r.data),
};

export const aiApi = {
  getSummary: (companyId: number, year?: number | null, quarter?: number | null, regenerate = false, viewMode?: string) => {
    const params: any = { regenerate };
    if (year) params.year = year;
    if (quarter !== undefined && quarter !== null) params.quarter = quarter;
    if (viewMode) params.view = viewMode;
    return api.get(`/api/ai-summary/${companyId}`, { params, timeout: 1200000 }).then((r) => r.data);
  },
};

export default api;

export const scrapeApi = {
  single: (companyId: number) => api.post(`/api/scrape/${companyId}`).then((r) => r.data),
  batch: (companyIds: number[]) => api.post("/api/scrape/batch", companyIds).then((r) => r.data),
};
