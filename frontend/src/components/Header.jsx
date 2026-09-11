import React, { useState } from 'react';
import {
  Menu,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  User,
  ShieldCheck,
  Download,
} from 'lucide-react';
import { api } from '../services/api';

export default function Header({
  activeTab,
  setMobileOpen,
  healthInfo,
  onRetryConnection,
}) {
  const [downloadingBackup, setDownloadingBackup] = useState(false);
  const isOnline = healthInfo && (healthInfo.status === 'healthy' || healthInfo.status === 'degraded');

  const handleDownloadBackup = () => {
    try {
      setDownloadingBackup(true);
      const url = api.getDownloadFullBackupZipUrl();
      window.open(url, '_blank');
    } catch (e) {
      console.error('Error downloading backup:', e);
    } finally {
      setTimeout(() => setDownloadingBackup(false), 2000);
    }
  };

  return (
    <header className="sticky top-0 z-30 w-full bg-white border-b border-[#E2E8F0] shadow-xs">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          
          {/* Left: Mobile Menu Trigger & Context Title */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 rounded-xl text-slate-600 hover:text-[#080F72] hover:bg-slate-100 lg:hidden transition"
              title="Abrir menú"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="hidden lg:flex items-center space-x-2 text-xs font-bold text-[#080F72]">
              <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-[#00A88F]' : 'bg-rose-500 animate-ping'}`} />
              <span>Agroindustrias Chavín • Escaneo & Carga Automática de Datos</span>
            </div>
          </div>

          {/* Right: User Profile, Quick Backup & Real System Status */}
          <div className="flex items-center space-x-2.5 sm:space-x-3">
            
            {/* Quick Backup Download Button */}
            <button
              onClick={handleDownloadBackup}
              disabled={downloadingBackup}
              className="hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-blue-50 hover:bg-blue-100 border border-blue-200 text-[11px] font-bold text-[#101BCB] transition shadow-xs"
              title="Descargar copia de seguridad completa (.ZIP con base de datos y plantillas)"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-[#101BCB]" />
              <span>{downloadingBackup ? 'Descargando...' : 'Copia de Seguridad (.ZIP)'}</span>
            </button>

            {/* User Profile Pill */}
            <div className="flex items-center space-x-2 px-3 py-1 rounded-full bg-slate-50 hover:bg-slate-100 border border-[#E2E8F0] transition cursor-pointer">
              <div className="w-6 h-6 rounded-full bg-[#101BCB] flex items-center justify-center text-white shadow-xs">
                <User className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-bold text-[#1E293B]">Flavio Monzón</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </div>

            {/* Dynamic System Status Pill */}
            {isOnline ? (
              <div
                className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#DCFCE7] border border-[#86EFAC] text-[11px] font-bold text-[#166534] shadow-xs"
                title="El servidor Backend está conectado y funcionando correctamente."
              >
                <CheckCircle2 className="w-3.5 h-3.5 text-[#16A34A]" />
                <span>Backend Conectado</span>
              </div>
            ) : (
              <button
                onClick={onRetryConnection}
                className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-rose-50 hover:bg-rose-100 border border-rose-300 text-[11px] font-bold text-rose-700 shadow-xs transition animate-pulse"
                title="El servidor backend no está respondiendo. Haz clic para reintentar la conexión o inicia start_backend.bat"
              >
                <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
                <span>Backend Desconectado (Reintentar)</span>
                <RefreshCw className="w-3 h-3 text-rose-600 ml-1" />
              </button>
            )}

          </div>

        </div>
      </div>
    </header>
  );
}

