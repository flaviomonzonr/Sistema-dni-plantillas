import axios from 'axios';

const getApiBaseUrl = () => {
  // 1. Variable de entorno explícita (VITE_API_URL en Render / Vercel)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }
  // 2. URL personalizada en localStorage si el usuario la configuró
  if (typeof window !== 'undefined' && window.localStorage) {
    const customUrl = window.localStorage.getItem('API_BASE_URL');
    if (customUrl) return customUrl.replace(/\/$/, '');
  }
  // 3. En entorno de producción web (Render, dominio propio), usar ruta relativa al mismo dominio
  if (typeof window !== 'undefined' && window.location) {
    const hostname = window.location.hostname;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return '';
    }
  }
  // 4. Desarrollo local por defecto
  return 'http://127.0.0.1:8000';
};

const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds to allow for initial AI model loading and high-res OCR
});

export const api = {
  // Check backend health & OCR status
  checkHealth: async () => {
    const res = await apiClient.get('/api/health');
    return res.data;
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

  // Save confirmed record to SQLite and Excel
  saveRecord: async (recordData) => {
    const res = await apiClient.post('/api/records', recordData);
    return res.data;
  },

  // List records with pagination and filters
  getRecords: async (params = {}) => {
    const res = await apiClient.get('/api/records', { params });
    return res.data;
  },

  // Get summary stats
  getStats: async () => {
    const res = await apiClient.get('/api/records/stats');
    return res.data;
  },

  // Get single record
  getRecord: async (recordId) => {
    const res = await apiClient.get(`/api/records/${recordId}`);
    return res.data;
  },

  // Delete record
  deleteRecord: async (recordId) => {
    const res = await apiClient.delete(`/api/records/${recordId}`);
    return res.data;
  },

  // Excel download URL helper
  getExportExcelUrl: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append('search', params.search);
    if (params.doc_type) query.append('doc_type', params.doc_type);
    if (params.start_date) query.append('start_date', params.start_date);
    if (params.end_date) query.append('end_date', params.end_date);
    return `${API_BASE_URL}/api/export-excel?${query.toString()}`;
  },

  // Absolute URL for uploads
  getImageUrl: (path) => {
    if (!path) return '';
    if (path.startsWith('http')) return path;
    return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`;
  },

  // ============================================================
  // Inteligencia de Excel, Consolidación y Generación de Contratos
  // ============================================================

  // Search worker in Excel and previous database records
  searchWorkerByDni: async (dni) => {
    const res = await apiClient.get(`/api/worker/search/${dni}`);
    return res.data;
  },

  // Consolidate OCR scan with Excel data
  consolidateWorker: async (payload) => {
    const res = await apiClient.post('/api/worker/consolidate', payload);
    return res.data;
  },

  // Calculate contract end date automatically
  calculateContractDates: async (startDate, durationMonths) => {
    const res = await apiClient.post('/api/contracts/calculate-dates', {
      start_date: startDate,
      duration_months: Number(durationMonths),
    });
    return res.data;
  },

  // Get contract templates
  getContractTemplates: async () => {
    const res = await apiClient.get('/api/contracts/templates');
    return res.data;
  },

  // Generate single contract (.docx)
  generateContract: async (payload) => {
    const res = await apiClient.post('/api/contracts/generate', payload);
    return res.data;
  },

  // Generate batch contracts (.docx / .zip)
  generateBatchContracts: async (payload) => {
    const res = await apiClient.post('/api/contracts/generate-batch', payload);
    return res.data;
  },

  // Get generated contracts history
  getContractsHistory: async (params = {}) => {
    const res = await apiClient.get('/api/contracts/history', { params });
    return res.data;
  },

  // Get contract download URL
  getContractDownloadUrl: (filename) => {
    return `${API_BASE_URL}/api/contracts/download/${filename}`;
  },

  // Get Excel diagnostic inspection
  getExcelDiagnostic: async () => {
    const res = await apiClient.get('/api/excel/diagnostic');
    return res.data;
  },

  // List all workers in Excel
  getExcelWorkers: async () => {
    const res = await apiClient.get('/api/excel/workers');
    return res.data;
  },

  // ============================================================
  // Plantillas Excel & Llenado Automático de DNI
  // ============================================================

  // List all registered Excel templates
  getExcelTemplates: async () => {
    const res = await apiClient.get('/api/excel-templates');
    return res.data;
  },

  // Upload a new Excel template (.xlsx)
  uploadExcelTemplate: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/excel-templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Fill DNI data into an Excel template (single)
  fillExcelTemplate: async (templateName, data, sheetName = null) => {
    const res = await apiClient.post('/api/excel-templates/fill', {
      template_name: templateName,
      data,
      sheet_name: sheetName,
    });
    return res.data;
  },

  // Generate batch Excel from selected workers adhering to yellow cells rule
  generateBatchExcel: async (templateName, recordIds, sheetName = null) => {
    const res = await apiClient.post('/api/excel-templates/generate-batch', {
      template_name: templateName,
      record_ids: recordIds,
      sheet_name: sheetName,
    });
    return res.data;
  },

  // Get list of available scanned dates
  getScannedDates: async () => {
    const res = await apiClient.get('/api/scanned-records/dates');
    return res.data;
  },

  // Filter scanned records by date and time range
  getRecordsByDateTime: async (params = {}) => {
    const res = await apiClient.get('/api/scanned-records/by-date-time', { params });
    return res.data;
  },

  // Delete an Excel template
  deleteExcelTemplate: async (filename) => {
    const res = await apiClient.delete(`/api/excel-templates/${encodeURIComponent(filename)}`);
    return res.data;
  },

  // Rename an Excel template
  renameExcelTemplate: async (filename, newName) => {
    const res = await apiClient.put(`/api/excel-templates/${encodeURIComponent(filename)}/rename`, {
      new_name: newName,
    });
    return res.data;
  },

  // Save custom column mappings
  saveExcelTemplateMapping: async (filename, sheetName, mappings) => {
    const res = await apiClient.post(`/api/excel-templates/${encodeURIComponent(filename)}/mapping`, {
      sheet_name: sheetName,
      mappings,
    });
    return res.data;
  },

  // Get original template download URL
  getTemplateDownloadUrl: (filename) => {
    return `${API_BASE_URL}/api/excel-templates/download/${encodeURIComponent(filename)}`;
  },

  // Get export file download URL
  getExportDownloadUrl: (filename) => {
    return `${API_BASE_URL}/api/exports/download/${encodeURIComponent(filename)}`;
  },

  // Get technical OCR diagnostic for multi-variant inspection
  getOcrDiagnostic: async (imageFile, docType = 'DNI') => {
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('doc_type', docType);
    const res = await apiClient.post('/api/ocr/diagnostic', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Get continuous learning stats
  getOcrLearningStats: async () => {
    const res = await apiClient.get('/api/ocr/learning-stats');
    return res.data;
  },

  // ============================================================
  // Copias de Seguridad y Persistencia de Datos
  // ============================================================
  getBackupStatus: async () => {
    const res = await apiClient.get('/api/backups/status');
    return res.data;
  },

  createBackup: async () => {
    const res = await apiClient.post('/api/backups/create');
    return res.data;
  },

  getDownloadFullBackupZipUrl: () => {
    return `${API_BASE_URL}/api/backups/download-zip`;
  },

  // ============================================================
  // Módulo Supabase: Gestión de Plantillas en la Nube
  // ============================================================
  supabase: {
    getConfig: async () => {
      const res = await apiClient.get('/api/supabase/config');
      return res.data;
    },

    saveConfig: async (payload) => {
      const res = await apiClient.post('/api/supabase/config', payload);
      return res.data;
    },

    testConnection: async () => {
      const res = await apiClient.post('/api/supabase/test-connection');
      return res.data;
    },

    getTemplates: async () => {
      const res = await apiClient.get('/api/supabase-templates');
      return res.data;
    },

    uploadTemplate: async (file, { name, templateType, version, userName } = {}) => {
      const formData = new FormData();
      formData.append('file', file);
      if (name) formData.append('name', name);
      if (templateType) formData.append('template_type', templateType);
      if (version) formData.append('version', version || '1.0');
      if (userName) formData.append('user_name', userName || 'Flavio Monzón');

      const res = await apiClient.post('/api/supabase-templates/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },

    replaceTemplate: async (templateId, file, userName = 'Flavio Monzón') => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_name', userName);

      const res = await apiClient.post(`/api/supabase-templates/${templateId}/replace`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },

    updateMetadata: async (templateId, data) => {
      const res = await apiClient.put(`/api/supabase-templates/${templateId}`, data);
      return res.data;
    },

    deleteTemplate: async (templateId) => {
      const res = await apiClient.delete(`/api/supabase-templates/${templateId}`);
      return res.data;
    },

    saveMapping: async (templateId, sheetName, mappings) => {
      const res = await apiClient.post(`/api/supabase-templates/${templateId}/mapping`, {
        sheet_name: sheetName,
        mappings,
      });
      return res.data;
    },

    generateBatchExcel: async (templateId, recordIds, sheetName = null) => {
      const res = await apiClient.post('/api/supabase-templates/generate-batch', {
        template_id: templateId,
        record_ids: recordIds,
        sheet_name: sheetName,
      });
      return res.data;
    },

    getDownloadUrl: (templateId) => {
      return `${API_BASE_URL}/api/supabase-templates/${templateId}/download`;
    },
  },
};



