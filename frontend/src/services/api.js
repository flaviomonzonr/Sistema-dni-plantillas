import axios from 'axios';

const CORRECT_RENDER_BACKEND = 'https://sistema-dni-plantillas.onrender.com';

export const getApiBaseUrl = () => {
  // 1. URL personalizada en localStorage si el usuario la configuró
  if (typeof window !== 'undefined' && window.localStorage) {
    const customUrl = window.localStorage.getItem('API_BASE_URL');
    if (customUrl) return customUrl.replace(/\/$/, '');
  }

  // 2. Variable de entorno explícita (corrigiendo automáticamente si apunta a backend viejo 503)
  if (import.meta.env.VITE_API_URL) {
    let envUrl = import.meta.env.VITE_API_URL.replace(/\/$/, '');
    if (envUrl.includes('sistema-dni-backend.onrender.com')) {
      return CORRECT_RENDER_BACKEND;
    }
    return envUrl;
  }

  // 3. En entorno de producción web (Render)
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    if (hostname.includes('onrender.com') || (hostname !== 'localhost' && hostname !== '127.0.0.1')) {
      return CORRECT_RENDER_BACKEND;
    }
  }

  // 4. Desarrollo local por defecto
  return 'http://127.0.0.1:8000';
};

export const setApiBaseUrl = (newUrl) => {
  if (typeof window !== 'undefined' && window.localStorage) {
    if (newUrl) {
      window.localStorage.setItem('API_BASE_URL', newUrl.trim().replace(/\/$/, ''));
    } else {
      window.localStorage.removeItem('API_BASE_URL');
    }
    window.location.reload();
  }
};

const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds to allow for initial AI model loading and high-res OCR
});

// Auto-failover interceptor: si falla o da 503, redirige automáticamente a sistema-dni-plantillas.onrender.com
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (
      (error.message === 'Network Error' || error.response?.status === 503 || error.response?.status === 404) &&
      apiClient.defaults.baseURL !== CORRECT_RENDER_BACKEND &&
      typeof window !== 'undefined' &&
      window.location.hostname.includes('onrender.com')
    ) {
      console.warn('Conexión fallida. Cambiando automáticamente al backend saludable:', CORRECT_RENDER_BACKEND);
      apiClient.defaults.baseURL = CORRECT_RENDER_BACKEND;
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem('API_BASE_URL', CORRECT_RENDER_BACKEND);
      }
      const newConfig = { ...error.config, baseURL: CORRECT_RENDER_BACKEND };
      return axios(newConfig);
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Check backend health & OCR status
  checkHealth: async () => {
    try {
      const res = await apiClient.get('/api/health');
      return res.data;
    } catch (err) {
      // Fallback directo a sistema-dni-plantillas si estamos en Render
      if (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com')) {
        try {
          const directRes = await axios.get(`${CORRECT_RENDER_BACKEND}/api/health`, { timeout: 15000 });
          apiClient.defaults.baseURL = CORRECT_RENDER_BACKEND;
          window.localStorage.setItem('API_BASE_URL', CORRECT_RENDER_BACKEND);
          return directRes.data;
        } catch (e2) {
          throw err;
        }
      }
      throw err;
    }
  },

  // Scan front and back of document
  scanDocument: async (frontFile, backFile, docType) => {
    const formData = new FormData();
    if (frontFile) {
      formData.append('front_image', frontFile);
    }
    if (backFile) {
      formData.append('back_image', backFile);
    }
    formData.append('doc_type', docType || 'DNI');

    const res = await apiClient.post('/api/scan', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // Scan and directly save to database & Excel in one step (for batch scanning)
  scanAndSave: async (frontFile, backFile, docType) => {
    const formData = new FormData();
    if (frontFile) {
      formData.append('front_image', frontFile);
    }
    if (backFile) {
      formData.append('back_image', backFile);
    }
    formData.append('doc_type', docType || 'DNI');

    const res = await apiClient.post('/api/scan-and-save', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // Direct fast DNI scanning (OCR Engine V1)
  scanDniDirect: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/v1/scan-dni', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // Save confirmed record to SQLite and Excel
  saveRecord: async (recordData) => {
    const res = await apiClient.post('/api/records', recordData);
    return res.data;
  },

  // List scanned records with pagination & filters
  getRecords: async (params = {}) => {
    const res = await apiClient.get('/api/records', { params });
    return res.data;
  },

  // Get single record details
  getRecord: async (id) => {
    const res = await apiClient.get(`/api/records/${id}`);
    return res.data;
  },

  // Delete a record
  deleteRecord: async (id) => {
    const res = await apiClient.delete(`/api/records/${id}`);
    return res.data;
  },

  // Get summary dashboard statistics
  getStats: async () => {
    const res = await apiClient.get('/api/records/stats');
    return res.data;
  },

  // Export filtered records to Excel (triggers browser download)
  getExportUrl: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}/api/export-excel${query ? `?${query}` : ''}`;
  },

  // Get full image URL from relative path returned by backend
  getImageUrl: (path) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}${path.startsWith('/') ? '' : '/'}${path}`;
  },

  // Technical diagnostic endpoint for testing variants & OCR
  getOCRDiagnostic: async (file, docType = 'DNI') => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('doc_type', docType);

    const res = await apiClient.post('/api/ocr/diagnostic', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data;
  },

  // Continuous learning stats
  getLearningStats: async () => {
    const res = await apiClient.get('/api/ocr/learning-stats');
    return res.data;
  },

  // Search worker profile by DNI in Excel & Database
  searchWorkerProfile: async (dni) => {
    const res = await apiClient.get(`/api/worker/search/${dni}`);
    return res.data;
  },

  // Consolidate worker data from OCR scan
  consolidateWorker: async (payload) => {
    const res = await apiClient.post('/api/worker/consolidate', payload);
    return res.data;
  },

  // Calculate legal contract dates
  calculateContractDates: async (startDate, durationMonths) => {
    const res = await apiClient.post('/api/contracts/calculate-dates', {
      start_date: startDate,
      duration_months: durationMonths,
    });
    return res.data;
  },

  // List available contract templates (.docx)
  listContractTemplates: async () => {
    const res = await apiClient.get('/api/contracts/templates');
    return res.data;
  },

  // Generate single contract .docx
  generateContract: async (payload) => {
    const res = await apiClient.post('/api/contracts/generate', payload);
    return res.data;
  },

  // Generate batch contracts .docx (.zip)
  generateBatchContracts: async (payload) => {
    const res = await apiClient.post('/api/contracts/generate-batch', payload);
    return res.data;
  },

  // Get contract generation history
  getContractsHistory: async (params = {}) => {
    const res = await apiClient.get('/api/contracts/history', { params });
    return res.data;
  },

  // Download contract or ZIP file URL
  getContractDownloadUrl: (filename) => {
    if (!filename) return '';
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}/api/contracts/download/${filename}`;
  },

  // Excel deep diagnostic
  getExcelDiagnostic: async () => {
    const res = await apiClient.get('/api/excel/diagnostic');
    return res.data;
  },

  // List all Excel workers
  listExcelWorkers: async () => {
    const res = await apiClient.get('/api/excel/workers');
    return res.data;
  },

  // ==========================================
  // Excel Templates Management
  // ==========================================

  listExcelTemplates: async () => {
    const res = await apiClient.get('/api/excel-templates');
    return res.data;
  },

  uploadExcelTemplate: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/excel-templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  fillExcelTemplate: async (templateName, data, sheetName = null) => {
    const res = await apiClient.post('/api/excel-templates/fill', {
      template_name: templateName,
      data,
      sheet_name: sheetName,
    });
    return res.data;
  },

  generateBatchExcel: async (templateName, recordIds = [], records = null, sheetName = null) => {
    const res = await apiClient.post('/api/excel-templates/generate-batch', {
      template_name: templateName,
      record_ids: recordIds,
      records: records,
      sheet_name: sheetName,
    });
    return res.data;
  },

  getScannedDates: async () => {
    const res = await apiClient.get('/api/scanned-records/dates');
    return res.data;
  },

  getScannedRecordsByDateTime: async (params = {}) => {
    const res = await apiClient.get('/api/scanned-records/by-date-time', { params });
    return res.data;
  },

  deleteExcelTemplate: async (filename) => {
    const res = await apiClient.delete(`/api/excel-templates/${encodeURIComponent(filename)}`);
    return res.data;
  },

  renameExcelTemplate: async (filename, newName) => {
    const res = await apiClient.put(`/api/excel-templates/${encodeURIComponent(filename)}/rename`, {
      new_name: newName,
    });
    return res.data;
  },

  saveTemplateMapping: async (filename, sheetName, mappings) => {
    const res = await apiClient.post(`/api/excel-templates/${encodeURIComponent(filename)}/mapping`, {
      sheet_name: sheetName,
      mappings,
    });
    return res.data;
  },

  getTemplateDownloadUrl: (filename) => {
    if (!filename) return '';
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}/api/excel-templates/download/${encodeURIComponent(filename)}`;
  },

  getExportDownloadUrl: (filename) => {
    if (!filename) return '';
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}/api/exports/download/${encodeURIComponent(filename)}`;
  },

  // ==========================================
  // Supabase Cloud Templates Management
  // ==========================================

  getSupabaseConfig: async () => {
    const res = await apiClient.get('/api/supabase/config');
    return res.data;
  },

  saveSupabaseConfig: async (supabaseUrl, supabaseKey, bucketName = 'templates') => {
    const res = await apiClient.post('/api/supabase/config', {
      supabase_url: supabaseUrl,
      supabase_key: supabaseKey,
      bucket_name: bucketName,
    });
    return res.data;
  },

  testSupabaseConnection: async () => {
    const res = await apiClient.post('/api/supabase/test-connection');
    return res.data;
  },

  listSupabaseTemplates: async () => {
    const res = await apiClient.get('/api/supabase-templates');
    return res.data;
  },

  uploadSupabaseTemplate: async (file, name, templateType = 'EXCEL_CARGA_MASIVA', version = '1.0', userName = 'Flavio Monzón') => {
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    formData.append('template_type', templateType);
    formData.append('version', version);
    formData.append('user_name', userName);

    const res = await apiClient.post('/api/supabase-templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  replaceSupabaseTemplateFile: async (templateId, file, userName = 'Flavio Monzón') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_name', userName);

    const res = await apiClient.post(`/api/supabase-templates/${templateId}/replace`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  updateSupabaseTemplateMetadata: async (templateId, payload) => {
    const res = await apiClient.put(`/api/supabase-templates/${templateId}`, payload);
    return res.data;
  },

  deleteSupabaseTemplate: async (templateId) => {
    const res = await apiClient.delete(`/api/supabase-templates/${templateId}`);
    return res.data;
  },

  saveSupabaseTemplateMapping: async (templateId, sheetName, mappings) => {
    const res = await apiClient.post(`/api/supabase-templates/${templateId}/mapping`, {
      sheet_name: sheetName,
      mappings,
    });
    return res.data;
  },

  generateBatchExcelSupabase: async (templateId, recordIds = [], records = null, sheetName = null) => {
    const res = await apiClient.post('/api/supabase-templates/generate-batch', {
      template_id: templateId,
      record_ids: recordIds,
      records: records,
      sheet_name: sheetName,
    });
    return res.data;
  },

  getSupabaseTemplateDownloadUrl: (templateId) => {
    if (!templateId) return '';
    const base = apiClient.defaults.baseURL || API_BASE_URL;
    return `${base}/api/supabase-templates/${templateId}/download`;
  },
};
