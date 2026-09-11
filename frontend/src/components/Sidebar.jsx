import React from 'react';
import {
  Scan,
  FileSpreadsheet,
  History,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Layers,
  X,
  LogOut,
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  healthInfo,
  collapsed,
  setCollapsed,
  mobileOpen,
  setMobileOpen,
}) {
  const mainNavItems = [
    {
      id: 'scan',
      label: 'Escanear DNI',
      icon: Scan,
      description: 'Captura y OCR Automático',
    },
    {
      id: 'batch_excel',
      label: 'Generar Excel por Lote',
      icon: FileSpreadsheet,
      description: 'Listado por fecha y hora',
    },
    {
      id: 'templates',
      label: 'Plantillas Excel',
      icon: FileSpreadsheet,
      description: 'Mapeo de celdas amarillas',
    },
    {
      id: 'scan_history',
      label: 'Historial de Registros',
      icon: History,
      description: 'Base de datos de escaneos',
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-slate-950/70 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* Main Vertical Sidebar */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 flex flex-col justify-between transition-all duration-300 ease-in-out select-none shadow-2xl ${
          // Reference image deep rich blue background
          'bg-[#060D27] border-r border-[#15234E]'
        } ${
          collapsed ? 'w-[80px]' : 'w-[290px]'
        } ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Top Section: Brand & Nav Items */}
        <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden">
          
          {/* Header Brand */}
          <div className="flex items-center justify-between p-4 border-b border-white/10 min-h-[88px]">
            <div className="flex items-center space-x-3 overflow-hidden">
              {/* Peruvian Logo Emblem */}
              <div className="relative flex-shrink-0 w-11 h-11 rounded-2xl bg-gradient-to-br from-[#101BCB] to-[#080F72] border-2 border-white/30 flex items-center justify-center shadow-lg">
                <div className="flex w-6 h-4 rounded-sm overflow-hidden shadow-inner">
                  <div className="w-1/3 bg-[#DC2626]"></div>
                  <div className="w-1/3 bg-white flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#101BCB]"></div>
                  </div>
                  <div className="w-1/3 bg-[#DC2626]"></div>
                </div>
              </div>

              {!collapsed && (
                <div className="min-w-0 flex-1">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-lg font-black text-white tracking-tight">
                      EscanDNI
                    </span>
                    <span className="text-lg font-black text-[#EF4444] tracking-tight">
                      Perú
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-300 font-medium leading-tight line-clamp-2 mt-0.5">
                    Reconoce OpenCV, OCR, Alta Precisión, Carga Automática en Plantillas Excel
                  </p>
                </div>
              )}
            </div>

            {/* Mobile Close Button */}
            <button
              onClick={() => setMobileOpen(false)}
              className="p-1.5 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 lg:hidden"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Desktop Collapse Toggle */}
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="hidden lg:flex p-1.5 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition"
              title={collapsed ? 'Expandir menú lateral' : 'Contraer menú lateral'}
            >
              {collapsed ? (
                <ChevronsRight className="w-5 h-5 text-[#00A88F]" />
              ) : (
                <ChevronsLeft className="w-5 h-5 text-slate-300" />
              )}
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3.5 space-y-2">
            
            {/* Main Navigation Items */}
            {mainNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileOpen(false);
                  }}
                  title={collapsed ? item.label : undefined}
                  className={`w-full flex items-center rounded-2xl transition-all duration-200 group relative text-left ${
                    collapsed
                      ? 'justify-center p-3.5'
                      : 'justify-between px-4 py-3.5'
                  } ${
                    isActive
                      ? 'bg-gradient-to-r from-[#00A88F] via-[#00BFA5] to-[#009688] text-white font-bold shadow-lg shadow-[#00A88F]/25 border border-white/20'
                      : 'bg-white/5 hover:bg-white/10 text-slate-200 hover:text-white border border-transparent'
                  }`}
                >
                  <div className="flex items-center space-x-3.5 min-w-0">
                    <div
                      className={`flex-shrink-0 p-1.5 rounded-xl ${
                        isActive
                          ? 'bg-black/15 text-white'
                          : 'text-slate-300 group-hover:text-white'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>

                    {!collapsed && (
                      <div className="min-w-0">
                        <span className="text-sm font-bold block leading-tight truncate">
                          {item.label}
                        </span>
                        <span
                          className={`text-[11px] block leading-tight truncate mt-0.5 ${
                            isActive ? 'text-white/90 font-medium' : 'text-slate-400 group-hover:text-slate-300'
                          }`}
                        >
                          {item.description}
                        </span>
                      </div>
                    )}
                  </div>

                  {!collapsed && (
                    <ChevronRight
                      className={`w-4 h-4 flex-shrink-0 transition ${
                        isActive ? 'text-white translate-x-0.5' : 'text-slate-500 group-hover:text-slate-300'
                      }`}
                    />
                  )}

                  {/* Floating Tooltip in Collapsed Mode */}
                  {collapsed && (
                    <div className="absolute left-full ml-3 px-3 py-2 rounded-xl bg-[#060D27] border border-[#15234E] text-white text-xs font-bold whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150 shadow-2xl z-50">
                      {item.label}
                    </div>
                  )}
                </button>
              );
            })}

          </nav>
        </div>

        {/* Bottom Section: System Status Cards & Collapse Action */}
        <div className="p-3.5 border-t border-white/10 space-y-2 bg-black/20">
          
          {/* Indicator 1: OCR / Backend Status */}
          {healthInfo && (healthInfo.status === 'healthy' || healthInfo.status === 'degraded') ? (
            <div
              className={`flex items-center rounded-2xl transition border border-white/10 bg-white/5 ${
                collapsed
                  ? 'justify-center p-3'
                  : 'px-3.5 py-2.5 justify-between'
              }`}
              title={`Motor de Lectura: ${healthInfo?.ocr_engine || 'RapidOCR AI'}`}
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="relative flex-shrink-0">
                  <span className="w-2.5 h-2.5 rounded-full block bg-[#00A88F] animate-pulse shadow-glow-green" />
                </div>
                {!collapsed && (
                  <div className="min-w-0">
                    <span className="text-[10px] text-slate-400 block font-medium">Motor de Lectura</span>
                    <span className="text-xs font-bold text-white truncate block">
                      {healthInfo?.ocr_engine || 'RapidOCR AI'}
                    </span>
                  </div>
                )}
              </div>

              {!collapsed && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#00A88F]/20 text-[#00A88F] border border-[#00A88F]/30">
                  Activo
                </span>
              )}
            </div>
          ) : (
            <div
              className={`flex items-center rounded-2xl transition border border-rose-500/30 bg-rose-950/30 ${
                collapsed
                  ? 'justify-center p-3'
                  : 'px-3.5 py-2.5 justify-between'
              }`}
              title="Backend Desconectado: Ejecute start_backend.bat para conectar"
            >
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="relative flex-shrink-0">
                  <span className="w-2.5 h-2.5 rounded-full block bg-rose-500 animate-ping" />
                </div>
                {!collapsed && (
                  <div className="min-w-0">
                    <span className="text-[10px] text-rose-300 block font-medium">Servidor Backend</span>
                    <span className="text-xs font-bold text-rose-200 truncate block">
                      Desconectado
                    </span>
                  </div>
                )}
              </div>

              {!collapsed && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  Offline
                </span>
              )}
            </div>
          )}

          {/* Indicator 2: Data Protection & Persistence Badge */}
          <div
            className={`flex items-center rounded-2xl transition border border-white/10 bg-white/5 ${
              collapsed
                ? 'justify-center p-3'
                : 'px-3.5 py-2.5 justify-between'
            }`}
            title="Persistencia de Datos: SQLite + Excel Master Activo"
          >
            <div className="flex items-center space-x-2.5 min-w-0">
              <div className="flex-shrink-0 text-[#00A88F]">
                <Layers className="w-4 h-4" />
              </div>
              {!collapsed && (
                <div className="min-w-0">
                  <span className="text-[10px] text-slate-400 block font-medium">Persistencia Datos</span>
                  <span className="text-xs font-bold text-[#00A88F] truncate block">
                    Protegida (Auto-Backup)
                  </span>
                </div>
              )}
            </div>

            {!collapsed && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#00A88F]/20 text-[#00A88F] border border-[#00A88F]/30">
                Segura
              </span>
            )}
          </div>

          {/* Collapse Button / Cerrar Menú */}
          {!collapsed && (
            <button
              onClick={() => setCollapsed(true)}
              className="w-full flex items-center space-x-2.5 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-white/10 transition mt-1"
            >
              <LogOut className="w-4 h-4 rotate-180" />
              <span>Cerrar menú</span>
            </button>
          )}

        </div>


      </aside>
    </>
  );
}
