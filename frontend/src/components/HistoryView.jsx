import React, { useState, useEffect } from 'react';
import {
  Search,
  Download,
  Filter,
  Trash2,
  Eye,
  Calendar,
  CreditCard,
  ShieldCheck,
  FileSpreadsheet,
  RefreshCw,
  Clock,
  Layers,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import RecordDetailModal from './RecordDetailModal';

export default function HistoryView({ reconnectTrigger }) {
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDocType, setSelectedDocType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Selected record for modal detail
  const [selectedRecord, setSelectedRecord] = useState(null);

  useEffect(() => {
    fetchRecords();
    fetchStats();
  }, [page, selectedDocType, startDate, endDate]);

  // Auto-reload on reconnectTrigger
  useEffect(() => {
    if (reconnectTrigger !== undefined && reconnectTrigger > 0) {
      fetchRecords();
      fetchStats();
    }
  }, [reconnectTrigger]);

  const fetchRecords = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await api.getRecords({
        page,
        page_size: pageSize,
        search: searchTerm,
        doc_type: selectedDocType,
        start_date: startDate,
        end_date: endDate,
      });
      setRecords(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Error fetching records:', err);
      setErrorMsg('No se pudo conectar con el servidor Backend (Python). Todos tus registros están 100% seguros y guardados en tu equipo. Inicia start_backend.bat o start_all.bat para visualizarlos.');
    } finally {
      setLoading(false);
    }
  };


  const fetchStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchRecords();
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setSelectedDocType('');
    setStartDate('');
    setEndDate('');
    setPage(1);
    setTimeout(() => {
      fetchRecords();
    }, 50);
  };

  const handleDelete = async (id, docNumber) => {
    if (!window.confirm(`¿Está seguro de eliminar el registro del documento ${docNumber}?`)) {
      return;
    }
    try {
      await api.deleteRecord(id);
      fetchRecords();
      fetchStats();
    } catch (err) {
      alert('Error al eliminar registro: ' + (err.response?.data?.detail || err.message));
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-4 animate-fade-in">
      
      {/* Top Stats Cards (Compact & High-Impact) */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        
        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-[#64748B] block">Total Escaneados</span>
            <span className="text-xl font-black text-[#080F72] mt-0.5 block">
              {stats?.total_records ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-blue-50 text-[#101BCB] border border-blue-100">
            <Layers className="w-4 h-4" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-[#64748B] block">DNI Peruanos</span>
            <span className="text-xl font-black text-[#080F72] mt-0.5 block">
              {stats?.dni_count ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-indigo-50 text-[#101BCB] border border-indigo-100">
            <CreditCard className="w-4 h-4" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-[#64748B] block">Carnet Extranjería</span>
            <span className="text-xl font-black text-[#080F72] mt-0.5 block">
              {stats?.ce_count ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600 border border-amber-100">
            <ShieldCheck className="w-4 h-4" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-[#E2E8F0] shadow-xs flex items-center justify-between">
          <div>
            <span className="text-[11px] font-semibold text-[#64748B] block">Escaneados Hoy</span>
            <span className="text-xl font-black text-[#166534] mt-0.5 block">
              {stats?.scanned_today ?? 0}
            </span>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 text-[#166534] border border-emerald-100">
            <Clock className="w-4 h-4" />
          </div>
        </div>

      </div>

      {/* Error Message Banner */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[#991B1B] text-xs sm:text-sm animate-fade-in shadow-xs">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-[#DC2626] flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => {
              fetchRecords();
              fetchStats();
            }}
            className="px-3.5 py-1.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold flex items-center space-x-1.5 transition shrink-0 shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reintentar Carga</span>
          </button>
        </div>
      )}

      {/* Search, Filters & Excel Download Bar (Compact & Sleek) */}
      <div className="bg-white p-4 sm:p-5 rounded-2xl border border-[#E2E8F0] shadow-xs space-y-3">
        
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          
          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center space-x-2">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748B]" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Buscar por DNI, Nombres, Apellidos o Dirección..."
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-[#101BCB] hover:bg-[#080F72] text-white font-bold text-xs rounded-xl shadow-xs transition"
            >
              Buscar
            </button>
          </form>

          {/* Direct Excel and Backup Actions */}
          <div className="flex items-center space-x-2 flex-shrink-0">
            <a
              href={api.getDownloadFullBackupZipUrl()}
              download
              className="flex items-center space-x-1.5 px-3.5 py-2 bg-blue-50 hover:bg-blue-100 text-[#101BCB] border border-blue-200 text-xs font-bold rounded-xl shadow-xs transition transform active:scale-95"
              title="Descargar copia de seguridad completa con SQLite y Excel"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Respaldo ZIP</span>
            </a>

            <a
              href={api.getExportExcelUrl({
                search: searchTerm,
                doc_type: selectedDocType,
                start_date: startDate,
                end_date: endDate,
              })}
              download
              className="flex items-center space-x-1.5 px-3.5 py-2 bg-[#16A34A] hover:bg-[#15803d] text-white text-xs font-bold rounded-xl shadow-xs transition transform active:scale-95"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Descargar Excel</span>
            </a>
          </div>

        </div>


        {/* Filters Row */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 pt-3 border-t border-[#E2E8F0]">
          
          <div>
            <label className="text-[11px] font-bold text-[#64748B] block mb-1">Tipo de Documento</label>
            <select
              value={selectedDocType}
              onChange={(e) => {
                setSelectedDocType(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB]"
            >
              <option value="">Todos los Tipos</option>
              <option value="DNI">DNI Peruano</option>
              <option value="Carnet de Extranjería">Carnet de Extranjería</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold text-[#64748B] block mb-1">Fecha Desde</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                setStartDate(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB]"
            />
          </div>

          <div>
            <label className="text-[11px] font-bold text-[#64748B] block mb-1">Fecha Hasta</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => {
                setEndDate(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB]"
            />
          </div>

          <div className="flex items-end">
            <button
              type="button"
              onClick={handleResetFilters}
              className="w-full py-2 px-3 text-xs font-semibold text-[#64748B] hover:text-[#1E293B] bg-slate-100 hover:bg-slate-200 rounded-xl border border-[#CBD5E1] transition"
            >
              Limpiar Filtros
            </button>
          </div>

        </div>

      </div>

      {/* Records Table */}
      <div className="bg-white rounded-2xl border border-[#E2E8F0] shadow-corporate-sm overflow-hidden">
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#E2E8F0] bg-[#080F72] text-[11px] font-bold uppercase tracking-wider text-white">
                <th className="py-3.5 px-4">Fecha Escaneo</th>
                <th className="py-3.5 px-4">Tipo</th>
                <th className="py-3.5 px-4">N° Documento</th>
                <th className="py-3.5 px-4">Apellidos y Nombres</th>
                <th className="py-3.5 px-4">Sexo</th>
                <th className="py-3.5 px-4">F. Nacimiento</th>
                <th className="py-3.5 px-4">Dirección</th>
                <th className="py-3.5 px-4 text-center">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E2E8F0] text-xs">
              {loading ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-[#64748B]">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-[#101BCB] mb-2" />
                    <span>Cargando registros...</span>
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan="8" className="py-12 text-center text-[#64748B]">
                    <CreditCard className="w-10 h-10 mx-auto text-slate-400 mb-2" />
                    <p className="font-bold text-[#1E293B]">No se encontraron registros</p>
                    <p className="text-[11px] text-[#64748B] mt-0.5">Escanee un nuevo documento para agregarlo al sistema.</p>
                  </td>
                </tr>
              ) : (
                records.map((r) => {
                  const isDni = r.doc_type === 'DNI';
                  return (
                    <tr key={r.id} className="hover:bg-[#EEF2FF] transition">
                      <td className="py-3 px-4 text-[#64748B] font-mono whitespace-nowrap">
                        {r.scan_date ? new Date(r.scan_date).toLocaleString('es-PE') : '-'}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          isDni
                            ? 'bg-blue-50 text-[#101BCB] border-blue-200'
                            : 'bg-amber-50 text-amber-700 border-amber-200'
                        }`}>
                          {r.doc_type}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-[#080F72] whitespace-nowrap">
                        {r.doc_number}
                      </td>
                      <td className="py-3 px-4 font-semibold text-[#1E293B]">
                        {r.paternal_surname} {r.maternal_surname} {r.first_names}
                      </td>
                      <td className="py-3 px-4 text-[#1E293B]">
                        {r.sex || '-'}
                      </td>
                      <td className="py-3 px-4 text-[#1E293B] font-mono whitespace-nowrap">
                        {r.birth_date || '-'}
                      </td>
                      <td className="py-3 px-4 text-[#64748B] max-w-[220px] truncate" title={r.address}>
                        {r.address || '-'}
                      </td>
                      <td className="py-3 px-4 text-center whitespace-nowrap">
                        <div className="flex items-center justify-center space-x-1.5">
                          <button
                            onClick={() => setSelectedRecord(r)}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-[#080F72] transition"
                            title="Ver detalles e imágenes"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(r.id, r.doc_number)}
                            className="p-1.5 rounded-lg bg-red-50 hover:bg-red-100 text-[#DC2626] transition"
                            title="Eliminar registro"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between text-xs text-[#64748B]">
          <div>
            Mostrando <strong>{records.length}</strong> de <strong>{total}</strong> registros
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] hover:bg-slate-50 text-[#1E293B] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Anterior
            </button>
            <span className="font-semibold text-[#1E293B] px-2">
              Página {page} de {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] hover:bg-slate-50 text-[#1E293B] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Siguiente
            </button>
          </div>
        </div>

      </div>

      {/* Record Detail Modal */}
      <RecordDetailModal
        record={selectedRecord}
        onClose={() => setSelectedRecord(null)}
      />

    </div>
  );
}
