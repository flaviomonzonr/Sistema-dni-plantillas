import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import CaptureZone from './components/CaptureZone';
import BatchScanZone from './components/BatchScanZone';
import ImageCompare from './components/ImageCompare';
import ReviewForm from './components/ReviewForm';
import TemplatesView from './components/TemplatesView';
import HistoryView from './components/HistoryView';
import ExcelGeneratorView from './components/ExcelGeneratorView';
import { api } from './services/api';
import { Sparkles, FileSpreadsheet, ArrowRight, ArrowLeft, CreditCard, Files } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('scan'); // 'scan' | 'batch_excel' | 'templates' | 'scan_history'
  const [scanMode, setScanMode] = useState('single'); // 'single' | 'batch'
  const [healthInfo, setHealthInfo] = useState(null);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  // Scan state (100% Automático)
  const [docType, setDocType] = useState('AUTO');
  const [frontFile, setFrontFile] = useState(null);
  const [frontPreview, setFrontPreview] = useState(null);
  const [backFile, setBackFile] = useState(null);
  const [backPreview, setBackPreview] = useState(null);

  const [isScanning, setIsScanning] = useState(false);
  const [scanStepText, setScanStepText] = useState('');
  const [scanResult, setScanResult] = useState(null);

  useEffect(() => {
    checkHealth();
    // Heartbeat cada 4 segundos para detectar conexión en tiempo real
    const interval = setInterval(() => {
      checkHealth();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await api.checkHealth();
      setHealthInfo((prev) => {
        if (!prev || prev.status === 'offline') {
          // Si acaba de volver a estar en línea, incrementar trigger de recarga
          setReconnectTrigger((t) => t + 1);
        }
        return data;
      });
    } catch (err) {
      setHealthInfo({ status: 'offline', ocr_engine: 'Sin conexión' });
    }
  };

  const handleManualRetry = () => {
    checkHealth();
    setReconnectTrigger((t) => t + 1);
  };


  const handleStartScan = async () => {
    if (!frontFile || !backFile) return;

    setIsScanning(true);
    setScanStepText('Detectando bordes con OpenCV y corrigiendo perspectiva...');

    try {
      setTimeout(() => setScanStepText('Recortando DNI y eliminando márgenes...'), 500);
      setTimeout(() => setScanStepText('Ejecutando OCR sobre DNI recortado...'), 1200);

      const result = await api.scanDocument(frontFile, backFile, docType);
      setScanResult(result);
    } catch (err) {
      console.error('Scan error:', err);
      let errorText = err.response?.data?.detail || err.message || 'Error desconocido';
      if (err.message === 'Network Error' || !err.response) {
        errorText = 'No se pudo conectar con el servidor backend (http://localhost:8000). Asegúrese de haber iniciado el servidor con start_backend.bat.';
      }
      alert('Error durante el escaneo: ' + errorText);
    } finally {
      setIsScanning(false);
      setScanStepText('');
    }
  };

  const handleResetScan = () => {
    setScanResult(null);
    if (frontPreview) URL.revokeObjectURL(frontPreview);
    if (backPreview) URL.revokeObjectURL(backPreview);
    setFrontFile(null);
    setFrontPreview(null);
    setBackFile(null);
    setBackPreview(null);
  };

  const handleRecordSaved = () => {
    handleResetScan();
    setActiveTab('scan');
  };

  return (
    <div className="min-h-screen bg-[#F4F7FB] text-[#1E293B] flex selection:bg-[#101BCB] selection:text-white">
      
      {/* 1. Left Vertical Sidebar (Chavín Corporate Azul Profundo #080F72) */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthInfo={healthInfo}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        mobileOpen={mobileOpen}
        setMobileOpen={setMobileOpen}
      />

      {/* 2. Main Content Wrapper */}
      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ease-in-out ${
          collapsed ? 'lg:pl-[80px]' : 'lg:pl-[290px]'
        }`}
      >
        {/* Top Header */}
        <Header
          activeTab={activeTab}
          setMobileOpen={setMobileOpen}
          healthInfo={healthInfo}
          onRetryConnection={handleManualRetry}
        />

        {/* Main Workspace Body */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 pt-3 pb-6">
          
          {/* TAB 1: ESCANEO DNI */}
          {activeTab === 'scan' && (
            !scanResult ? (
              <div className="space-y-4">
                
                {/* Mode Selector Tabs (Individual vs Por Lotes) */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-2.5 rounded-2xl border border-[#E2E8F0] shadow-sm">
                  <div className="flex items-center space-x-2 bg-slate-100 p-1 rounded-xl border border-slate-200 w-full sm:w-auto">
                    <button
                      type="button"
                      onClick={() => setScanMode('single')}
                      className={`flex-1 sm:flex-initial py-2 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 ${
                        scanMode === 'single'
                          ? 'bg-white text-[#080F72] shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <CreditCard className="w-4 h-4 text-[#101BCB]" />
                      <span>Escaneo Individual / Cámara</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setScanMode('batch')}
                      className={`flex-1 sm:flex-initial py-2 px-4 rounded-lg text-xs font-bold transition flex items-center justify-center space-x-2 ${
                        scanMode === 'batch'
                          ? 'bg-[#101BCB] text-white shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <Files className="w-4 h-4" />
                      <span>Subir por Lotes</span>
                      <span className="bg-[#00A88F] text-white text-[10px] px-1.5 py-0.2 rounded-full font-extrabold">
                        A/R Auto
                      </span>
                    </button>
                  </div>

                  <div className="text-xs text-[#64748B] hidden md:flex items-center space-x-2 pr-2">
                    <span className="w-2 h-2 rounded-full bg-[#00A88F]"></span>
                    <span>Modo: {scanMode === 'single' ? 'Un DNI con revisión en vivo' : 'Múltiples DNI con emparejamiento automático'}</span>
                  </div>
                </div>

                {/* Render Selected Scan Mode */}
                {scanMode === 'single' ? (
                  <CaptureZone
                    docType={docType}
                    setDocType={setDocType}
                    frontFile={frontFile}
                    setFrontFile={setFrontFile}
                    frontPreview={frontPreview}
                    setFrontPreview={setFrontPreview}
                    backFile={backFile}
                    setBackFile={setBackFile}
                    backPreview={backPreview}
                    setBackPreview={setBackPreview}
                    onStartScan={handleStartScan}
                    isScanning={isScanning}
                    scanStep={scanStepText}
                  />
                ) : (
                  <BatchScanZone
                    onNavigateToExcelGenerator={() => setActiveTab('batch_excel')}
                  />
                )}

              </div>
            ) : (
              <div className="space-y-4 animate-fade-in">
                
                {/* Compact Status Banner with Back Navigation */}
                <div className="bg-white border border-[#CBD5E1] rounded-xl px-4 py-2.5 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-xs">
                  <div className="flex items-center space-x-3">
                    <button
                      type="button"
                      onClick={handleResetScan}
                      title="Volver a la pantalla de escaneo"
                      className="py-1.5 px-3 rounded-lg bg-slate-100 hover:bg-slate-200 text-[#080F72] font-bold text-xs border border-[#CBD5E1] flex items-center space-x-1.5 transition shadow-2xs shrink-0 hover:border-[#101BCB]"
                    >
                      <ArrowLeft className="w-3.5 h-3.5 text-[#101BCB]" />
                      <span>← Retroceder / Atrás</span>
                    </button>
                    <div className="h-6 w-px bg-slate-200 hidden sm:block"></div>
                    <div>
                      <h4 className="text-xs font-bold text-[#1E293B]">
                        DNI Escaneado: <span className="font-mono text-[#101BCB] font-extrabold">{scanResult.doc_number || 'Detectado'}</span> • {scanResult.first_names} {scanResult.paternal_surname} {scanResult.maternal_surname}
                      </h4>
                      <p className="text-[11px] text-[#64748B]">
                        Verifique los datos extraídos o guarde el registro en la base de datos.
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setActiveTab('templates')}
                    className="py-1.5 px-3 rounded-lg bg-slate-50 hover:bg-slate-100 text-[#080F72] font-bold text-xs border border-[#CBD5E1] flex items-center space-x-1.5 transition shadow-2xs shrink-0"
                  >
                    <span>Ver Plantillas Registradas</span>
                    <ArrowRight className="w-3.5 h-3.5 text-[#101BCB]" />
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                  {/* Left Column: OpenCV Image Inspection (4 cols) */}
                  <div className="lg:col-span-4">
                    <ImageCompare scanResult={scanResult} />
                  </div>

                  {/* Right Column: Editable Review Form & Template Filler (8 cols) */}
                  <div className="lg:col-span-8">
                    <ReviewForm
                      scanResult={scanResult}
                      onReset={handleResetScan}
                      onRecordSaved={handleRecordSaved}
                    />
                  </div>
                </div>

              </div>
            )
          )}

          {/* TAB 2: GENERAR EXCEL POR LOTE */}
          {activeTab === 'batch_excel' && (
            <ExcelGeneratorView
              onNavigateToScan={() => setActiveTab('scan')}
              onNavigateToTemplates={() => setActiveTab('templates')}
              reconnectTrigger={reconnectTrigger}
            />
          )}

          {/* TAB 3: PLANTILLAS EXCEL */}
          {activeTab === 'templates' && (
            <TemplatesView
              reconnectTrigger={reconnectTrigger}
            />
          )}

          {/* TAB 4: HISTORIAL DE REGISTROS */}
          {activeTab === 'scan_history' && (
            <HistoryView
              reconnectTrigger={reconnectTrigger}
            />
          )}

        </main>


        {/* Corporate Footer */}
        <footer className="border-t border-[#E2E8F0] bg-white py-4 text-center text-xs text-[#64748B] mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#00A88F]"></span>
              <span className="font-semibold text-[#1E293B]">Sistema de Escaneo de DNI y Plantillas Excel</span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-600 font-medium">Desarrollado por Flavio</span>
            </div>
            <span className="text-slate-500 font-medium">
              OpenCV, RapidOCR AI & openpyxl
            </span>
          </div>
        </footer>

      </div>

    </div>
  );
}
