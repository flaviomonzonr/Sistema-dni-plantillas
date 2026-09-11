import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Layers,
  EyeOff,
  MessageSquare,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Table,
  ShieldCheck,
} from 'lucide-react';
import { api } from '../services/api';

export default function ExcelDiagnosticView() {
  const [diagnostic, setDiagnostic] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDiagnostic();
  }, []);

  const loadDiagnostic = async () => {
    setIsLoading(true);
    try {
      const data = await api.getExcelDiagnostic();
      setDiagnostic(data);
    } catch (err) {
      console.error('Error loading excel diagnostic:', err);
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
            <span className="px-3 py-1 rounded-full bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center space-x-1">
              <FileSpreadsheet className="w-3.5 h-3.5 mr-1" />
              <span>Análisis Estructural de Excel</span>
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
            Diagnóstico de Hojas, Notas y Celdas Ocultas
          </h2>
          <p className="text-xs text-slate-400">
            Inspección profunda en modo solo lectura para garantizar que ninguna nota, comentario o dato auxiliar quede sin procesar.
          </p>
        </div>

        <button
          type="button"
          onClick={loadDiagnostic}
          className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition flex items-center space-x-1.5 self-start sm:self-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Re-analizar Excel</span>
        </button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-slate-500 bg-slate-900/60 rounded-2xl border border-slate-800">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-emerald-400" />
          <p className="text-sm font-semibold text-slate-300">Escaneando estructura completa del Excel...</p>
          <p className="text-xs text-slate-500 mt-1">Revisando celdas ocultas, comentarios, fórmulas y hojas.</p>
        </div>
      ) : !diagnostic || diagnostic.status === 'error' ? (
        <div className="p-6 rounded-2xl bg-amber-950/40 border border-amber-800/60 text-amber-200">
          <div className="flex items-center space-x-2 font-bold mb-1">
            <AlertCircle className="w-5 h-5 text-amber-400" />
            <span>Aviso del Diagnóstico</span>
          </div>
          <p className="text-xs text-amber-300/90">
            {diagnostic?.message || 'No se pudo cargar el archivo Excel fuente. Asegúrese de que exista en la carpeta `exports/Registros.xlsx` o `data/`.'}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          
          {/* Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
                <span>Hojas Totales</span>
                <Layers className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white font-mono">{diagnostic.total_sheets}</div>
              <p className="text-[11px] text-slate-500">Hojas activas, ocultas y auxiliares</p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
                <span>Notas y Comentarios</span>
                <MessageSquare className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-purple-300 font-mono">{diagnostic.total_comments}</div>
              <p className="text-[11px] text-slate-500">Anotaciones de celdas recuperables</p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
                <span>Filas Ocultas</span>
                <EyeOff className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-bold text-amber-300 font-mono">{diagnostic.total_hidden_rows}</div>
              <p className="text-[11px] text-slate-500">Filas ocultas analizadas por DNI</p>
            </div>

            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-semibold">
                <span>Columnas Ocultas</span>
                <EyeOff className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-blue-300 font-mono">{diagnostic.total_hidden_cols}</div>
              <p className="text-[11px] text-slate-500">Columnas ocultas incluidas</p>
            </div>

          </div>

          {/* Sheets List Breakdown */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-4 border-b border-slate-800 bg-slate-900/60 font-semibold text-xs text-slate-200 flex items-center space-x-2">
              <Table className="w-4 h-4 text-emerald-400" />
              <span>Desglose por Hoja del Libro Excel</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950 text-slate-400 font-semibold uppercase text-[11px]">
                  <tr>
                    <th className="p-3.5">Nombre de Hoja</th>
                    <th className="p-3.5">Estado</th>
                    <th className="p-3.5">Dimensiones (Filas x Cols)</th>
                    <th className="p-3.5">Filas / Cols Ocultas</th>
                    <th className="p-3.5">Comentarios</th>
                    <th className="p-3.5">Encabezados Detectados</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {diagnostic.sheets?.map((s) => (
                    <tr key={s.sheet_name} className="hover:bg-slate-800/40 transition">
                      <td className="p-3.5 font-bold text-white font-mono">
                        {s.sheet_name}
                      </td>
                      <td className="p-3.5">
                        {s.is_hidden ? (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-amber-950/80 text-amber-400 border border-amber-800/50 font-semibold">
                            Oculta ({s.sheet_state})
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950/80 text-emerald-400 border border-emerald-800/50 font-semibold">
                            Visible
                          </span>
                        )}
                      </td>
                      <td className="p-3.5 font-mono text-slate-300">
                        {s.max_rows} filas × {s.max_cols} columnas
                      </td>
                      <td className="p-3.5 font-mono text-slate-400">
                        {s.hidden_rows} filas | {s.hidden_cols} cols
                      </td>
                      <td className="p-3.5 font-mono text-purple-300">
                        {s.comments_count} notas
                      </td>
                      <td className="p-3.5 text-slate-400 text-[11px] truncate max-w-xs">
                        {s.sample_headers?.slice(0, 5).join(', ')}
                        {s.sample_headers?.length > 5 ? '...' : ''}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Sample Comments / Notes Found */}
          {diagnostic.comments_sample && diagnostic.comments_sample.length > 0 && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
              <div className="flex items-center space-x-2 text-xs font-bold text-purple-300 border-b border-slate-800 pb-3">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span>Muestra de Comentarios y Notas Detectados en Celdas</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {diagnostic.comments_sample.map((c, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-purple-900/40 text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                      <span className="text-purple-400 font-bold">Hoja '{c.sheet}' [{c.coordinate}]</span>
                      <span>Autor: {c.author || 'Sistema'}</span>
                    </div>
                    <p className="text-slate-200 font-medium bg-purple-950/30 p-2 rounded border border-purple-800/30">
                      "{c.text}"
                    </p>
                    <div className="text-[10px] text-slate-500 truncate">
                      Valor visible en celda: <span className="text-slate-400">{c.cell_value || '(Vacío)'}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
