import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Download,
  Calendar,
  Clock,
  CheckCircle2,
  RefreshCw,
  FolderOpen,
} from 'lucide-react';
import { api } from '../services/api';

export default function ContractHistoryView() {
  const [contracts, setContracts] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, [page, searchTerm]);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      const data = await api.getContractsHistory({
        page,
        page_size: pageSize,
        search: searchTerm || undefined,
      });
      setContracts(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Error loading contracts history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 rounded-full bg-red-600/20 border border-red-500/30 text-red-400 text-xs font-bold flex items-center space-x-1">
              <FolderOpen className="w-3.5 h-3.5 mr-1" />
              <span>Registro de Contratos Emitidos</span>
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Historial de Contratos Laborales
          </h2>
          <p className="text-xs text-slate-400">
            Control de todos los contratos generados en formato `.docx` con sus respectivas fechas de vigencia.
          </p>
        </div>

        <button
          type="button"
          onClick={loadHistory}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Actualizar</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-lg">
        <div className="relative w-full sm:w-96">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Buscar por DNI, nombre o archivo..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-red-500"
          />
        </div>

        <div className="text-xs text-slate-400 font-mono">
          Total de contratos registrados: <strong className="text-white">{total}</strong>
        </div>
      </div>

      {/* Contracts Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/80 text-slate-400 font-semibold border-b border-slate-800 uppercase tracking-wider text-[11px]">
              <tr>
                <th className="p-3.5">DNI</th>
                <th className="p-3.5">Trabajador</th>
                <th className="p-3.5">Tipo Contrato</th>
                <th className="p-3.5">Fecha Inicio</th>
                <th className="p-3.5">Fecha Fin</th>
                <th className="p-3.5">Plazo</th>
                <th className="p-3.5">Estado</th>
                <th className="p-3.5">Emisión</th>
                <th className="p-3.5 text-right">Descarga</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-500">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-red-500" />
                    <span>Cargando historial de contratos...</span>
                  </td>
                </tr>
              ) : contracts.length === 0 ? (
                <tr>
                  <td colSpan={9} className="p-8 text-center text-slate-500">
                    No se han registrado contratos generados todavía.
                  </td>
                </tr>
              ) : (
                contracts.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/40 transition">
                    <td className="p-3.5 font-mono font-bold text-white">
                      {c.dni}
                    </td>
                    <td className="p-3.5 font-semibold text-slate-100">
                      {c.worker_name}
                    </td>
                    <td className="p-3.5 text-slate-300">
                      {c.contract_type}
                    </td>
                    <td className="p-3.5 font-mono text-slate-200">
                      {c.start_date}
                    </td>
                    <td className="p-3.5 font-mono text-emerald-400 font-semibold">
                      {c.end_date}
                    </td>
                    <td className="p-3.5 text-slate-300 font-mono">
                      {c.duration}
                    </td>
                    <td className="p-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        {c.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-slate-400 font-mono text-[11px]">
                      {c.created_at}
                    </td>
                    <td className="p-3.5 text-right">
                      <a
                        href={api.getContractDownloadUrl(c.file_name)}
                        download
                        className="inline-flex items-center space-x-1 px-3 py-1 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-semibold shadow transition"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>.DOCX</span>
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
