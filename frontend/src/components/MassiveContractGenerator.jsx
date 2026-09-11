import React, { useState, useEffect } from 'react';
import {
  Users,
  Search,
  CheckSquare,
  Square,
  FileText,
  Calendar,
  Clock,
  Download,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  FolderArchive,
  Layers,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';

export default function MassiveContractGenerator({ onSelectWorkerForReview }) {
  const [workers, setWorkers] = useState([]);
  const [filteredWorkers, setFilteredWorkers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDnis, setSelectedDnis] = useState(new Set());
  const [isLoading, setIsLoading] = useState(true);

  // Contract settings
  const [startDate, setStartDate] = useState(
    new Date().toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
  );
  const [durationMonths, setDurationMonths] = useState(3);
  const [calculatedEndDate, setCalculatedEndDate] = useState('');
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');

  // Generation status
  const [isGenerating, setIsGenerating] = useState(false);
  const [batchResult, setBatchResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (startDate && durationMonths) {
      api
        .calculateContractDates(startDate, durationMonths)
        .then((res) => {
          if (res.end_date) setCalculatedEndDate(res.end_date);
        })
        .catch(console.error);
    }
  }, [startDate, durationMonths]);

  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredWorkers(workers);
    } else {
      const q = searchTerm.toLowerCase().trim();
      const filtered = workers.filter(
        (w) =>
          w.dni?.toLowerCase().includes(q) ||
          w.full_name?.toLowerCase().includes(q) ||
          w.cargo?.toLowerCase().includes(q) ||
          w.area?.toLowerCase().includes(q)
      );
      setFilteredWorkers(filtered);
    }
  }, [searchTerm, workers]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [workersRes, templatesRes] = await Promise.all([
        api.getExcelWorkers(),
        api.getContractTemplates(),
      ]);

      if (workersRes.workers) {
        setWorkers(workersRes.workers);
        setFilteredWorkers(workersRes.workers);
        // By default select all
        setSelectedDnis(new Set(workersRes.workers.map((w) => w.dni)));
      }

      if (templatesRes.templates && templatesRes.templates.length > 0) {
        setTemplates(templatesRes.templates);
        setSelectedTemplate(templatesRes.templates[0].name);
      }
    } catch (err) {
      console.error('Error loading excel workers:', err);
      setErrorMsg('Error cargando trabajadores desde el archivo Excel.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleSelectDni = (dni) => {
    const next = new Set(selectedDnis);
    if (next.has(dni)) {
      next.delete(dni);
    } else {
      next.add(dni);
    }
    setSelectedDnis(next);
  };

  const handleSelectAll = () => {
    if (selectedDnis.size === filteredWorkers.length) {
      setSelectedDnis(new Set());
    } else {
      setSelectedDnis(new Set(filteredWorkers.map((w) => w.dni)));
    }
  };

  const handleGenerateBatch = async () => {
    const selectedList = workers.filter((w) => selectedDnis.has(w.dni));
    if (selectedList.length === 0) {
      alert('Por favor selecciona al menos un trabajador.');
      return;
    }

    setIsGenerating(true);
    setErrorMsg(null);
    setBatchResult(null);

    try {
      const payload = {
        workers: selectedList,
        start_date: startDate,
        duration_months: Number(durationMonths),
        template_name: selectedTemplate || null,
      };

      const res = await api.generateBatchContracts(payload);
      setBatchResult(res);
    } catch (err) {
      console.error('Error in batch generation:', err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Error en la generación masiva');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 text-xs font-bold flex items-center space-x-1">
              <Users className="w-3.5 h-3.5 mr-1" />
              <span>Módulo de Generación Masiva</span>
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Emisión de Contratos en Lote
          </h2>
          <p className="text-xs text-slate-400">
            Seleccione trabajadores identificados en el Excel para generar sus contratos `.docx` y descargarlos en paquete `.zip`.
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          disabled={isLoading}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Recargar Excel</span>
        </button>
      </div>

      {/* Control Bar: Global Contract Params */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950/40 border border-indigo-500/20 rounded-2xl p-6 shadow-xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
          
          {/* Fecha Inicio */}
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
              Fecha de Inicio Global:
            </label>
            <input
              type="text"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              placeholder="DD/MM/AAAA"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono focus:border-indigo-500 focus:outline-none"
            />
          </div>

          {/* Duración */}
          <div>
            <label className="text-xs font-semibold text-slate-300 mb-1.5 block">
              Duración:
            </label>
            <select
              value={durationMonths}
              onChange={(e) => setDurationMonths(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
            >
              <option value={1}>1 Mes</option>
              <option value={2}>2 Meses</option>
              <option value={3}>3 Meses</option>
              <option value={6}>6 Meses</option>
              <option value={12}>12 Meses (1 Año)</option>
            </select>
          </div>

          {/* Fecha Fin */}
          <div>
            <label className="text-xs font-semibold text-slate-400 mb-1.5 block">
              Fecha Fin (Calculada):
            </label>
            <div className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-emerald-400 font-mono font-bold">
              {calculatedEndDate || 'Calculando...'}
            </div>
          </div>

          {/* Generar Botón */}
          <div>
            <button
              type="button"
              disabled={isGenerating || selectedDnis.size === 0}
              onClick={handleGenerateBatch}
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/30 flex items-center justify-center space-x-2 transition disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Generando ({selectedDnis.size})...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generar ({selectedDnis.size}) Contratos</span>
                </>
              )}
            </button>
          </div>

        </div>
      </div>

      {/* Batch Result Success Card */}
      {batchResult && (
        <div className="p-6 rounded-2xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-200 shadow-2xl space-y-4 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-xl bg-emerald-600/30 border border-emerald-500/40 text-emerald-400">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  ¡Lote generado exitosamente! ({batchResult.total_generated} de {batchResult.total_requested})
                </h3>
                <p className="text-xs text-emerald-300 font-mono">
                  Vigencia: {startDate} al {calculatedEndDate}
                </p>
              </div>
            </div>

            {batchResult.zip_download_url && (
              <a
                href={batchResult.zip_download_url}
                download
                className="py-2.5 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-lg flex items-center justify-center space-x-2 transition"
              >
                <FolderArchive className="w-4 h-4" />
                <span>Descargar Paquete ZIP ({batchResult.total_generated} DOCX)</span>
              </a>
            )}
          </div>
        </div>
      )}

      {/* Search and Worker Selection Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        
        {/* Table Filter Header */}
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-slate-900/60">
          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={handleSelectAll}
              className="flex items-center space-x-2 text-xs font-semibold text-slate-300 hover:text-white transition"
            >
              {selectedDnis.size === filteredWorkers.length && filteredWorkers.length > 0 ? (
                <CheckSquare className="w-4 h-4 text-indigo-400" />
              ) : (
                <Square className="w-4 h-4 text-slate-500" />
              )}
              <span>
                Seleccionar Todos ({selectedDnis.size} / {filteredWorkers.length})
              </span>
            </button>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Buscar por DNI, nombre, cargo..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="p-3.5 w-10 text-center">Sel</th>
                <th className="p-3.5">DNI</th>
                <th className="p-3.5">Trabajador / Nombre Completo</th>
                <th className="p-3.5">Cargo</th>
                <th className="p-3.5">Área</th>
                <th className="p-3.5">Remuneración</th>
                <th className="p-3.5">Origen Excel</th>
                <th className="p-3.5 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Cargando trabajadores del Excel...</span>
                  </td>
                </tr>
              ) : filteredWorkers.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-slate-500">
                    No se encontraron trabajadores con el criterio de búsqueda.
                  </td>
                </tr>
              ) : (
                filteredWorkers.map((w) => {
                  const isSelected = selectedDnis.has(w.dni);
                  return (
                    <tr
                      key={w.dni}
                      className={`hover:bg-slate-800/40 transition ${
                        isSelected ? 'bg-indigo-950/10' : ''
                      }`}
                    >
                      <td className="p-3.5 text-center">
                        <button
                          type="button"
                          onClick={() => toggleSelectDni(w.dni)}
                          className="text-slate-400 hover:text-white"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-indigo-400" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-600" />
                          )}
                        </button>
                      </td>
                      <td className="p-3.5 font-mono font-bold text-white">
                        {w.dni}
                      </td>
                      <td className="p-3.5 font-semibold text-slate-100">
                        {w.full_name}
                      </td>
                      <td className="p-3.5 text-slate-300">
                        {w.cargo || '-'}
                      </td>
                      <td className="p-3.5 text-slate-400">
                        {w.area || '-'}
                      </td>
                      <td className="p-3.5 font-mono text-emerald-400">
                        S/ {w.remuneracion || '1,500.00'}
                      </td>
                      <td className="p-3.5 text-slate-400 text-[11px] font-mono">
                        Hoja '{w.sheet_origin}'
                      </td>
                      <td className="p-3.5 text-right">
                        {onSelectWorkerForReview && (
                          <button
                            type="button"
                            onClick={() => onSelectWorkerForReview(w.dni)}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-400 text-[11px] font-semibold border border-slate-700 transition"
                          >
                            Revisar Individual
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

      </div>

    </div>
  );
}
