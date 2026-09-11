import React from 'react';
import {
  Scan,
  FileSpreadsheet,
  History,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, healthInfo }) {
  const navItems = [
    { id: 'scan', label: 'Escanear DNI', icon: Scan },
    { id: 'batch_excel', label: 'Generar Excel por Lote', icon: Sparkles },
    { id: 'templates', label: 'Plantillas Excel', icon: FileSpreadsheet },
    { id: 'scan_history', label: 'Historial de Registros', icon: History },
  ];

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          
          {/* Brand & Logo */}
          <div className="flex items-center space-x-3.5">
            <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-br from-red-600 via-red-700 to-slate-900 border border-red-500/30 shadow-glow">
              <div className="flex w-6 h-4 rounded overflow-hidden shadow-sm border border-white/20">
                <div className="w-1/3 bg-red-600"></div>
                <div className="w-1/3 bg-white flex items-center justify-center">
                  <div className="w-1 h-1 rounded-full bg-amber-500"></div>
                </div>
                <div className="w-1/3 bg-red-600"></div>
              </div>
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg sm:text-xl font-bold bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">
                  EscanDNI <span className="text-red-500 font-extrabold">Perú</span>
                </h1>
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  OCR + Plantillas Excel
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Recorte OpenCV, OCR Alta Precisión y Carga Automática en Plantillas Excel
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center space-x-1 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-bold transition-all duration-200 relative ${
                    isActive
                      ? 'bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-md shadow-emerald-950/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* System Status Pills */}
          <div className="hidden xl:flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
              <span
                className={`w-2 h-2 rounded-full ${
                  healthInfo?.status === 'healthy' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              ></span>
              <span>
                OCR: <strong className="text-white font-medium">{healthInfo?.ocr_engine || 'Tesseract'}</strong>
              </span>
            </div>

            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-medium">Plantillas Activas</span>
            </div>
          </div>

        </div>

        {/* Mobile Navigation Scroll */}
        <div className="flex md:hidden overflow-x-auto py-2 space-x-2 border-t border-slate-800/60">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap font-medium transition ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-900 text-slate-300 border border-slate-800'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

      </div>
    </header>
  );
}
