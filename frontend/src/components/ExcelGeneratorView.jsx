import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Calendar,
  Clock,
  Search,
  CheckSquare,
  Square,
  Download,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Users,
  Layers,
  ArrowRight,
  Filter,
  Check,
  FileDown,
  Info,
  Cloud,
  HardDrive,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { api } from '../services/api';

export default function ExcelGeneratorView({ onNavigateToScan, onNavigateToTemplates, reconnectTrigger }) {
  // Available dates from backend
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('all'); // 'all' or 'YYYY-MM-DD'
  const [customDate, setCustomDate] = useState('');

  // Time range filter
  const [timePreset, setTimePreset] = useState('all'); // 'morning' | 'afternoon' | 'all' | 'custom'
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');

  // Search filter
  const [searchTerm, setSearchTerm] = useState('');

  // Records list & selection
  const [records, setRecords] = useState([]);
  const [loadingRecords, setLoadingRecords] = useState(true);
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Combined Templates (Supabase + Local)
  const [combinedTemplates, setCombinedTemplates] = useState([]);
  const [selectedTemplateKey, setSelectedTemplateKey] = useState('');
  const [loadingTemplates, setLoadingTemplates] = useState(true);

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateSuccess, setGenerateSuccess] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadDates();
    loadAllTemplates();
  }, []);

  useEffect(() => {
    loadRecords();
  }, [selectedDate, customDate, startTime, endTime, searchTerm]);

  // Auto-reload when connection recovers or reconnectTrigger changes
  useEffect(() => {
    if (reconnectTrigger !== undefined && reconnectTrigger > 0) {
      loadDates();
      loadAllTemplates();
      loadRecords();
    }
  }, [reconnectTrigger]);

  // Load available dates
  const loadDates = async () => {
    try {
      const data = await api.getScannedDates();
      const list = data.dates || [];
      setAvailableDates(list);
      if (list.length > 0 && selectedDate === 'all') {
        setSelectedDate(list[0].date);
      }
    } catch (err) {
      console.error('Error loading scan dates:', err);
    }
  };

  // Load all templates: Supabase Cloud + Local Filesystem
  const loadAllTemplates = async () => {
    setLoadingTemplates(true);
    try {
      const combined = [];

      // 1. Fetch Supabase templates
      try {
        const supaData = await api.supabase.getTemplates();
        if (supaData && supaData.templates) {
          supaData.templates.forEach((t) => {
            combined.push({
              key: `supabase:${t.id}`,
              source: 'supabase',
              id: t.id,
              name: t.name || t.filename,
              filename: t.filename,
              version: t.version || '1.0',
              file_size_kb: t.file_size_kb || 0,
              template_type: t.template_type || 'EXCEL_CARGA_MASIVA',
              sheets: t.sheets_metadata || [],
              yellow_columns_count: t.sheets_metadata?.[0]?.yellow_columns_count || 0,
            });
          });
        }
      } catch (e) {
        console.warn('Could not fetch Supabase templates:', e);
      }

      // 2. Fetch Local templates
      try {
        const localData = await api.getExcelTemplates();
        if (localData && localData.templates) {
          localData.templates.forEach((t) => {
            combined.push({
              key: `local:${t.filename}`,
              source: 'local',
              id: t.filename,
              name: t.filename,
              filename: t.filename,
              version: 'Local',
              file_size_kb: t.file_size_kb || 0,
              template_type: 'EXCEL_CARGA_MASIVA',
              sheets: t.sheets || [],
              yellow_columns_count: t.sheets?.[0]?.yellow_columns_count || 0,
            });
          });
        }
      } catch (e) {
        console.warn('Could not fetch local templates:', e);
      }

      setCombinedTemplates(combined);

      // Auto-select first template if none selected or invalid
      if (combined.length > 0) {
        setSelectedTemplateKey((prev) => {
          if (prev && combined.some((t) => t.key === prev)) return prev;
          return combined[0].key;
        });
      }
    } catch (err) {
      console.error('Error loading combined templates:', err);
    } finally {
      setLoadingTemplates(false);
    }
  };

  // Load records filtered by date and time
  const loadRecords = async () => {
    setLoadingRecords(true);
    setErrorMsg(null);
    try {
      const actualDate = selectedDate === 'custom' ? customDate : selectedDate;
      const params = {
        date: actualDate === 'all' ? '' : actualDate,
        start_time: startTime,
        end_time: endTime,
        search: searchTerm,
      };
      const res = await api.getRecordsByDateTime(params);
      const items = res.items || [];
      setRecords(items);

      // Auto-select all filtered records by default
      const allIds = new Set(items.map((r) => r.id));
      setSelectedIds(allIds);
    } catch (err) {
      console.error('Error loading filtered records:', err);
      setErrorMsg('No se pudo conectar con el servidor Backend (Python). Tus escaneos están 100% seguros y guardados en el equipo.');
    } finally {
      setLoadingRecords(false);
    }
  };

  // Quick Time Preset Handlers
  const handleTimePreset = (preset) => {
    setTimePreset(preset);
    if (preset === 'morning') {
      setStartTime('08:00');
      setEndTime('12:00');
    } else if (preset === 'afternoon') {
      setStartTime('12:00');
      setEndTime('17:00');
    } else if (preset === 'all') {
      setStartTime('');
      setEndTime('');
    }
  };

  // Toggle single item selection
  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Select all or deselect all
  const toggleSelectAll = () => {
    if (selectedIds.size === records.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(records.map((r) => r.id)));
    }
  };

  // Selected Template Object
  const selectedTemplateObj = combinedTemplates.find((t) => t.key === selectedTemplateKey);

  // Batch Excel Generation
  const handleGenerateExcel = async () => {
    if (!selectedTemplateObj) {
      alert('Por favor seleccione una plantilla Excel.');
      return;
    }

    if (selectedIds.size === 0) {
      alert('Por favor seleccione al menos un trabajador escaneado.');
      return;
    }

    setIsGenerating(true);
    setErrorMsg(null);
    setGenerateSuccess(null);

    try {
      const orderedRecordIds = records
        .filter((r) => selectedIds.has(r.id))
        .map((r) => r.id);

      let res;
      if (selectedTemplateObj.source === 'supabase') {
        res = await api.supabase.generateBatchExcel(selectedTemplateObj.id, orderedRecordIds);
      } else {
        res = await api.generateBatchExcel(selectedTemplateObj.filename, orderedRecordIds);
      }

      setGenerateSuccess(res);

      // Confetti celebration
      confetti({
        particleCount: 100,
        spread: 80,
        origin: { y: 0.6 },
        colors: ['#101BCB', '#A8E63D', '#080F72', '#ffffff'],
      });

      // Automatic file download in browser
      if (res.filename) {
        const downloadUrl = api.getExportDownloadUrl(res.filename);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.setAttribute('download', res.filename);
        document.body.appendChild(link);
        link.click();
        link.remove();
      }
    } catch (err) {
      console.error('Error generating batch excel:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al generar el archivo Excel.');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in">

      {/* Success Notification Banner */}
      {generateSuccess && (
        <div className="p-5 rounded-2xl bg-[#DCFCE7] border border-[#86EFAC] shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-scale-in">
          <div className="flex items-start space-x-3.5">
            <div className="p-2.5 rounded-xl bg-emerald-100 border border-[#86EFAC] text-[#166534] flex-shrink-0">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-[#166534]">¡Excel Generado y Descargado con Éxito!</h4>
              <p className="text-xs text-[#166534] mt-0.5">
                Archivo: <span className="font-mono font-bold text-[#080F72]">{generateSuccess.filename}</span> ({generateSuccess.total_workers} trabajadores)
              </p>
              <p className="text-[11px] text-[#64748B] mt-1">
                Se respetaron todas las fórmulas y textos fijos; solo se completaron las columnas amarillas correspondientes.
              </p>
            </div>
          </div>

          <a
            href={api.getExportDownloadUrl(generateSuccess.filename)}
            download={generateSuccess.filename}
            className="px-5 py-2.5 rounded-xl bg-[#16A34A] hover:bg-[#15803d] text-white text-xs font-bold shadow-md flex items-center space-x-2 transition transform active:scale-95"
          >
            <FileDown className="w-4 h-4" />
            <span>Volver a Descargar</span>
          </a>
        </div>
      )}

      {/* Error Message Banner */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[#991B1B] text-xs sm:text-sm animate-fade-in shadow-xs">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-[#DC2626] flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => {
              loadDates();
              loadAllTemplates();
              loadRecords();
            }}
            className="px-3.5 py-1.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold flex items-center space-x-1.5 transition shrink-0 shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reintentar Carga</span>
          </button>
        </div>
      )}

      {/* Unified Ultra-Compact Control Bar */}
      <div className="bg-white p-3 sm:p-3.5 rounded-2xl border border-[#CBD5E1] shadow-xs space-y-2.5">
        
        {/* Row 1: Template Selector & Main Action Button */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            <span className="text-xs font-bold text-[#080F72] flex items-center space-x-1.5 flex-shrink-0">
              <FileSpreadsheet className="w-4 h-4 text-[#101BCB]" />
              <span>Plantilla Destino:</span>
            </span>

            {loadingTemplates ? (
              <span className="text-xs text-[#64748B]">Cargando plantillas...</span>
            ) : combinedTemplates.length === 0 ? (
              <span className="text-xs text-amber-600 font-bold">No hay plantillas registradas.</span>
            ) : (
              <select
                value={selectedTemplateKey}
                onChange={(e) => setSelectedTemplateKey(e.target.value)}
                className="flex-1 max-w-lg px-2.5 py-1.5 rounded-xl bg-slate-50 border border-[#CBD5E1] text-[#1E293B] text-xs font-bold focus:outline-none focus:border-[#101BCB] focus:bg-white truncate transition"
              >
                {combinedTemplates.map((tpl) => (
                  <option key={tpl.key} value={tpl.key}>
                    {tpl.source === 'supabase' ? '☁️ [Nube Supabase] ' : '📁 [Local] '}
                    {tpl.name} {tpl.version ? `(v${tpl.version})` : ''} — {tpl.file_size_kb} KB
                  </option>
                ))}
              </select>
            )}

            {selectedTemplateObj && (
              <span className="hidden lg:inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-lg text-[11px] font-semibold text-[#101BCB] bg-blue-50 border border-blue-200 flex-shrink-0">
                <span>🟡 {selectedTemplateObj.yellow_columns_count} cols</span>
                <span>•</span>
                <span>{selectedTemplateObj.source === 'supabase' ? '☁️ Supabase Cloud' : '📁 Local'}</span>
              </span>
            )}
          </div>

          {/* Action Button: Generate Excel */}
          <button
            onClick={handleGenerateExcel}
            disabled={isGenerating || selectedIds.size === 0 || !selectedTemplateObj}
            className={`px-5 py-2 sm:py-2.5 rounded-xl text-xs sm:text-sm font-extrabold text-white shadow-md flex items-center justify-center space-x-2 transition transform active:scale-95 flex-shrink-0 ${
              isGenerating || selectedIds.size === 0 || !selectedTemplateObj
                ? 'bg-slate-200 text-slate-400 border border-slate-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-[#00A88F] via-[#00BFA5] to-[#009688] hover:from-[#008F7A] hover:to-[#00796B] shadow-[#00A88F]/20'
            }`}
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Generando...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Generar Excel ({selectedIds.size} Trabajadores) ➔</span>
              </>
            )}
          </button>
        </div>

        {/* Row 2: Filters & Refresh in 1 compact row */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
          
          {/* 1. Date Selector */}
          <div className="flex items-center space-x-1.5 min-w-[170px]">
            <Calendar className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
            <select
              value={selectedDate}
              onChange={(e) => {
                setSelectedDate(e.target.value);
                if (e.target.value !== 'custom') setCustomDate('');
              }}
              className="w-full px-2.5 py-1 rounded-lg bg-slate-50 border border-[#CBD5E1] text-[#1E293B] text-xs font-bold focus:outline-none focus:border-[#101BCB] focus:bg-white transition"
            >
              <option value="all">📅 Todas las fechas</option>
              {availableDates.map((d) => (
                <option key={d.date} value={d.date}>
                  📅 {d.formatted} ({d.count})
                </option>
              ))}
              <option value="custom">📅 Personalizada...</option>
            </select>
          </div>

          {selectedDate === 'custom' && (
            <input
              type="date"
              value={customDate}
              onChange={(e) => setCustomDate(e.target.value)}
              className="px-2 py-1 rounded-lg bg-white border border-[#101BCB] text-[#1E293B] text-xs font-bold focus:outline-none"
            />
          )}

          {/* 2. Time Range Selector */}
          <div className="flex items-center space-x-1.5 min-w-[155px]">
            <Clock className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
            <select
              value={timePreset}
              onChange={(e) => handleTimePreset(e.target.value)}
              className="w-full px-2.5 py-1 rounded-lg bg-slate-50 border border-[#CBD5E1] text-[#1E293B] text-xs font-bold focus:outline-none focus:border-[#101BCB] focus:bg-white transition"
            >
              <option value="all">⏰ Todo el día</option>
              <option value="morning">⏰ 08:00 - 12:00</option>
              <option value="afternoon">⏰ 12:00 - 17:00</option>
              <option value="custom">⏰ Personalizado...</option>
            </select>
          </div>

          {timePreset === 'custom' && (
            <div className="flex items-center space-x-1 bg-slate-50 p-0.5 rounded-lg border border-[#CBD5E1]">
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="px-1.5 py-0.5 rounded bg-white text-xs text-[#1E293B] border border-slate-200"
              />
              <span className="text-[10px] text-slate-400">a</span>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="px-1.5 py-0.5 rounded bg-white text-xs text-[#1E293B] border border-slate-200"
              />
            </div>
          )}

          {/* 3. Search Filter */}
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#64748B]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Buscar por DNI, Nombres, Apellidos..."
              className="w-full pl-8 pr-2.5 py-1 rounded-lg bg-slate-50 border border-[#CBD5E1] text-[#1E293B] text-xs font-medium focus:outline-none focus:bg-white focus:border-[#101BCB] transition"
            />
          </div>

          {/* 4. Actualizar Button */}
          <button
            onClick={() => {
              loadDates();
              loadAllTemplates();
              loadRecords();
            }}
            className="py-1 px-3 rounded-lg border border-[#CBD5E1] bg-slate-50 hover:bg-slate-100 text-[#080F72] text-xs font-bold transition flex items-center space-x-1.5 shadow-xs flex-shrink-0"
            title="Refrescar lista de escaneos y plantillas"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-[#101BCB] ${loadingRecords ? 'animate-spin' : ''}`} />
            <span>Actualizar</span>
          </button>

        </div>

      </div>

      {/* Workers Selection List */}
      <div className="bg-white rounded-2xl border border-[#CBD5E1] overflow-hidden shadow-2xs space-y-0">
        
        {/* Table Top Bar */}
        <div className="py-2.5 px-4 bg-[#080F72] text-white flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          
          <div className="flex items-center space-x-3">
            <button
              onClick={toggleSelectAll}
              disabled={records.length === 0}
              className="flex items-center space-x-2 text-xs font-bold text-white hover:text-[#A8E63D] transition"
            >
              {selectedIds.size > 0 && selectedIds.size === records.length ? (
                <CheckSquare className="w-4 h-4 text-[#A8E63D]" />
              ) : selectedIds.size > 0 ? (
                <div className="w-4 h-4 rounded border border-[#A8E63D] bg-white/20 flex items-center justify-center text-[#A8E63D] text-[10px] font-bold">
                  -
                </div>
              ) : (
                <Square className="w-4 h-4 text-slate-300" />
              )}
              <span>
                {selectedIds.size === records.length ? 'Deseleccionar Todos' : 'Seleccionar Todos'}
              </span>
            </button>

            <span className="text-xs text-white/40">•</span>

            <span className="text-xs font-bold text-[#A8E63D]">
              {selectedIds.size} de {records.length} trabajadores seleccionados
            </span>
          </div>

          <div className="flex items-center space-x-2 text-[11px] text-slate-200">
            <span>Se insertarán en el orden de la lista</span>
          </div>

        </div>

        {/* List Content */}
        {loadingRecords ? (
          <div className="p-12 text-center text-[#64748B] text-xs space-y-2">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#101BCB]" />
            <p>Cargando escaneos de DNI...</p>
          </div>
        ) : records.length === 0 ? (
          <div className="p-12 text-center text-[#64748B] text-xs space-y-3">
            <Users className="w-10 h-10 mx-auto text-slate-400" />
            <p className="text-sm font-bold text-[#1E293B]">
              No se encontraron escaneos de DNI con los filtros aplicados.
            </p>
            <p className="text-xs text-[#64748B] max-w-md mx-auto">
              Prueba cambiando la fecha o el rango de horas, o escanea nuevos DNI desde la pestaña "Escanear DNI".
            </p>
          </div>
        ) : (
          <div className="divide-y divide-[#E2E8F0] max-h-[calc(100vh-270px)] min-h-[400px] overflow-y-auto">
            {records.map((rec, index) => {
              const isSelected = selectedIds.has(rec.id);
              const fullName = `${rec.paternal_surname || ''} ${rec.maternal_surname || ''} ${rec.first_names || ''}`.trim() || 'Sin Nombre';

              return (
                <div
                  key={rec.id}
                  onClick={() => toggleSelect(rec.id)}
                  className={`py-2.5 px-4 flex items-center justify-between gap-3 cursor-pointer transition ${
                    isSelected
                      ? 'bg-[#EEF2FF] hover:bg-[#E0E7FF]'
                      : 'bg-white hover:bg-[#F8FAFC]'
                  }`}
                >
                  <div className="flex items-center space-x-3 min-w-0 flex-1">
                    
                    {/* Checkbox */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelect(rec.id);
                      }}
                      className="text-slate-400 hover:text-[#101BCB] flex-shrink-0"
                    >
                      {isSelected ? (
                        <CheckSquare className="w-4 h-4 text-[#101BCB]" />
                      ) : (
                        <Square className="w-4 h-4 text-slate-400" />
                      )}
                    </button>

                    {/* Order Index */}
                    <span className="w-5 h-5 rounded bg-slate-100 text-[#080F72] font-mono text-[10px] flex items-center justify-center font-bold flex-shrink-0">
                      {index + 1}
                    </span>

                    {/* Worker Info */}
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <h4 className="text-xs sm:text-sm font-bold text-[#1E293B] truncate">{fullName}</h4>
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-mono font-bold bg-blue-50 border border-blue-200 text-[#101BCB]">
                          DNI: {rec.doc_number || 'N/A'}
                        </span>
                        {rec.sex && (
                          <span className="text-[10px] px-1 py-0.2 rounded bg-slate-100 text-[#1E293B] font-bold">
                            {rec.sex}
                          </span>
                        )}
                        {rec.civil_status && (
                          <span className="text-[10px] px-1 py-0.2 rounded bg-slate-100 text-[#64748B]">
                            {rec.civil_status}
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[11px] text-[#64748B] mt-0.5">
                        {rec.address && (
                          <span className="truncate max-w-sm" title={rec.address}>
                            📍 {rec.address}
                          </span>
                        )}
                        {rec.ubigeo && (
                          <span>Ubigeo: {rec.ubigeo}</span>
                        )}
                        {rec.birth_date && (
                          <span>F.Nac: {rec.birth_date}</span>
                        )}
                      </div>
                    </div>

                  </div>

                  {/* Scan Date & Time Badge */}
                  <div className="text-right flex-shrink-0">
                    <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg bg-slate-100 border border-[#CBD5E1] text-[11px] font-mono text-[#080F72] font-bold">
                      <Clock className="w-3 h-3 text-[#101BCB]" />
                      <span>{rec.formatted_time || '—'}</span>
                    </div>
                    <div className="text-[10px] text-[#64748B]">
                      {rec.formatted_date || ''}
                    </div>
                  </div>

                </div>
              );
            })}
          </div>
        )}

      </div>

    </div>
  );
}
