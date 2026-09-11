import React, { useState, useRef } from 'react';
import {
  Upload,
  Files,
  Sparkles,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  ArrowRight,
  RefreshCw,
  FileSpreadsheet,
  Check,
  ShieldAlert,
  HelpCircle,
  Eye,
  FileCheck
} from 'lucide-react';
import { pairBatchFiles } from '../utils/batchFilePairer';
import { api } from '../services/api';

export default function BatchScanZone({ onNavigateToExcelGenerator }) {
  const [pairs, setPairs] = useState([]);
  const [isProcessingBatch, setIsProcessingBatch] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const [statusMessage, setStatusMessage] = useState('');
  const [batchCompleted, setBatchCompleted] = useState(false);
  const fileInputRef = useRef(null);

  // Handle file drop or selection
  const handleFilesAdded = (rawFiles) => {
    if (!rawFiles || rawFiles.length === 0) return;
    const newPairs = pairBatchFiles(rawFiles);
    setPairs(newPairs);
    setBatchCompleted(false);
    setCurrentIndex(-1);
    setStatusMessage('');
  };

  const handleInputChange = (e) => {
    handleFilesAdded(e.target.files);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleFilesAdded(e.dataTransfer.files);
  };

  const removePair = (pairId) => {
    if (isProcessingBatch) return;
    setPairs(prev => prev.filter(p => p.id !== pairId));
  };

  const clearAll = () => {
    if (isProcessingBatch) return;
    setPairs([]);
    setBatchCompleted(false);
    setCurrentIndex(-1);
    setStatusMessage('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // Helper to create a synthetic DNI image file
  const createSyntheticDNIImage = (docNum, patSur, matSur, fNames, birthDate, side = 'A') => {
    const canvas = document.createElement('canvas');
    canvas.width = 1014;
    canvas.height = 640;
    const ctx = canvas.getContext('2d');

    if (side === 'A') {
      // Anverso DNI Azul
      ctx.fillStyle = '#85c1e9';
      ctx.fillRect(40, 30, 934, 580);

      // Header
      ctx.fillStyle = '#1b4f72';
      ctx.fillRect(40, 30, 934, 90);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 26px sans-serif';
      ctx.fillText('REPUBLICA DEL PERU', 180, 70);
      ctx.font = 'bold 20px sans-serif';
      ctx.fillText('REGISTRO NACIONAL DE IDENTIFICACION Y ESTADO CIVIL', 180, 100);

      // Photo
      ctx.fillStyle = '#cbd5e1';
      ctx.fillRect(80, 160, 240, 320);
      ctx.fillStyle = '#475569';
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('FOTO DNI', 150, 320);

      // Fields
      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('NUMERO DE DNI', 380, 175);
      ctx.font = 'bold 36px monospace';
      ctx.fillText(docNum, 380, 220);

      ctx.font = 'bold 16px sans-serif';
      ctx.fillText('PRIMER APELLIDO', 380, 265);
      ctx.font = 'bold 24px sans-serif';
      ctx.fillText(patSur, 380, 295);

      ctx.font = 'bold 16px sans-serif';
      ctx.fillText('SEGUNDO APELLIDO', 380, 340);
      ctx.font = 'bold 24px sans-serif';
      ctx.fillText(matSur, 380, 370);

      ctx.font = 'bold 16px sans-serif';
      ctx.fillText('PRENOMBRES', 380, 415);
      ctx.font = 'bold 24px sans-serif';
      ctx.fillText(fNames, 380, 445);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('FECHA DE NACIMIENTO', 380, 490);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText(birthDate, 380, 515);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('SEXO', 620, 490);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('M', 620, 515);
    } else {
      // Reverso DNI Azul
      ctx.fillStyle = '#a9cce3';
      ctx.fillRect(40, 30, 934, 580);

      ctx.fillStyle = '#1b4f72';
      ctx.fillRect(40, 30, 934, 60);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 22px sans-serif';
      ctx.fillText('DIRECCION Y CONSTANCIAS DE SUFRAGIO', 180, 68);

      ctx.fillStyle = '#0f172a';
      ctx.font = 'bold 16px sans-serif';
      ctx.fillText('DOMICILIO / DIRECCION', 80, 140);
      ctx.font = 'bold 20px sans-serif';
      ctx.fillText('AV. LOS HEROES 450 DPTO 302', 80, 170);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('DEPARTAMENTO / PROVINCIA / DISTRITO', 80, 220);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('LIMA / LIMA / SANTIAGO DE SURCO', 80, 245);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('UBIGEO', 80, 290);
      ctx.font = 'bold 20px monospace';
      ctx.fillText('150140', 80, 315);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('ESTADO CIVIL', 350, 290);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('SOLTERO', 350, 315);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('FECHA DE EMISION', 600, 290);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('10/05/2021', 600, 315);

      ctx.font = 'bold 14px sans-serif';
      ctx.fillText('FECHA DE CADUCIDAD', 600, 355);
      ctx.font = 'bold 18px sans-serif';
      ctx.fillText('10/05/2029', 600, 380);
    }

    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        resolve(blob);
      }, 'image/jpeg', 0.95);
    });
  };

  // Load a 5-worker sample batch to demonstrate immediate functionality
  const loadDemoBatch = async () => {
    if (isProcessingBatch) return;

    const sampleWorkers = [
      { id: '1', doc: '42694271', pat: 'QUISPE', mat: 'MAMANI', names: 'JUAN CARLOS', birth: '15/04/1988' },
      { id: '2', doc: '71829304', pat: 'FLORES', mat: 'GUTIERREZ', names: 'MARIA ELENA', birth: '22/08/1995' },
      { id: '3', doc: '10928374', pat: 'VARGAS', mat: 'TORRES', names: 'PEDRO LUIS', birth: '03/11/1982' },
      { id: '4', doc: '47895623', pat: 'RODRIGUEZ', mat: 'MENDOZA', names: 'CARLOS EDUARDO', birth: '18/09/1993' },
      { id: '5', doc: '75849302', pat: 'SANCHEZ', mat: 'ALVAREZ', names: 'ANA LUCIA', birth: '30/01/1997' },
    ];

    const generatedFiles = [];

    for (const w of sampleWorkers) {
      const frontBlob = await createSyntheticDNIImage(w.doc, w.pat, w.mat, w.names, w.birth, 'A');
      const backBlob = await createSyntheticDNIImage(w.doc, w.pat, w.mat, w.names, w.birth, 'R');

      const frontFile = new File([frontBlob], `${w.id}.A.jpg`, { type: 'image/jpeg' });
      const backFile = new File([backBlob], `${w.id}.R.jpg`, { type: 'image/jpeg' });

      generatedFiles.push(frontFile, backFile);
    }

    handleFilesAdded(generatedFiles);
  };

  // Accelerated Concurrent Batch Scanning Process
  const startBatchProcessing = async () => {
    if (pairs.length === 0 || isProcessingBatch) return;

    setIsProcessingBatch(true);
    setBatchCompleted(false);

    const updatedPairs = [...pairs];

    // Process single pair helper
    const processPair = async (index) => {
      const currentPair = updatedPairs[index];
      setCurrentIndex(index);

      // Validate front file exists
      if (!currentPair.frontFile) {
        currentPair.status = 'error';
        currentPair.error = 'Falta archivo de Anverso (A)';
        setPairs([...updatedPairs]);
        return;
      }

      currentPair.status = 'processing';
      setStatusMessage(`Procesando DNI "${currentPair.label}" (OpenCV + RapidOCR)...`);
      setPairs([...updatedPairs]);

      try {
        const response = await api.scanAndSave(
          currentPair.frontFile,
          currentPair.backFile,
          'DNI'
        );

        if (response.success && response.record) {
          currentPair.status = 'done';
          currentPair.savedRecord = response.record;
          currentPair.extractedData = {
            doc_number: response.record.doc_number || response.scan_data?.doc_number,
            first_names: response.record.first_names || response.scan_data?.first_names,
            paternal_surname: response.record.paternal_surname || response.scan_data?.paternal_surname,
            maternal_surname: response.record.maternal_surname || response.scan_data?.maternal_surname,
            birth_date: response.record.birth_date,
            address: response.record.address,
            civil_status: response.record.civil_status,
            ubigeo: response.record.ubigeo,
          };
        } else {
          currentPair.status = 'error';
          currentPair.error = 'El servidor no pudo procesar el documento.';
        }
      } catch (err) {
        console.error(`Error procesando par ${currentPair.label}:`, err);
        currentPair.status = 'error';
        currentPair.error = err.response?.data?.detail || err.message || 'Error durante el escaneo';
      }

      setPairs([...updatedPairs]);
    };

    // Concurrency pool (2 parallel workers for fast processing without overwhelming CPU)
    const concurrency = Math.min(2, updatedPairs.length);
    let queueIndex = 0;

    const worker = async () => {
      while (queueIndex < updatedPairs.length) {
        const idx = queueIndex++;
        await processPair(idx);
      }
    };

    const workers = Array.from({ length: concurrency }, () => worker());
    await Promise.all(workers);

    setIsProcessingBatch(false);
    setCurrentIndex(-1);
    setBatchCompleted(true);
    setStatusMessage('¡Procesamiento por lote completado con éxito!');
  };

  // Stats
  const totalCount = pairs.length;
  const doneCount = pairs.filter(p => p.status === 'done').length;
  const errorCount = pairs.filter(p => p.status === 'error').length;
  const progressPercent = totalCount > 0 ? Math.round(((doneCount + errorCount) / totalCount) * 100) : 0;

  return (
    <div className="space-y-6 animate-fade-in">
      
      {/* 1. Top Upload & Configuration Card */}
      <div className="bg-white border border-[#E2E8F0] rounded-2xl p-6 shadow-corporate-md space-y-6">
        
        {/* Title and Badge */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="p-3 bg-blue-50 text-[#101BCB] border border-blue-100 rounded-xl shadow-sm">
              <Files className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-bold text-[#1E293B]">Carga y Escaneo por Lotes de DNI</h3>
                <span className="bg-emerald-50 text-[#00A88F] text-[11px] font-bold px-2.5 py-0.5 rounded-full border border-emerald-200">
                  Emparejamiento A / R Automático
                </span>
              </div>
              <p className="text-xs text-[#64748B] mt-0.5">
                Suba múltiples imágenes. El sistema empareja automáticamente Anverso y Reverso por nombre de archivo y registra cada DNI en la base de datos y Excel.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={loadDemoBatch}
              disabled={isProcessingBatch}
              className="py-2 px-3.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#080F72] text-xs font-bold border border-[#E2E8F0] transition flex items-center space-x-2 shadow-sm disabled:opacity-50"
              title="Genera un lote de 5 pares (1.A/1.R ... 5.A/5.R) para probar el flujo de inmediato"
            >
              <Sparkles className="w-4 h-4 text-[#101BCB]" />
              <span>Cargar Lote de Prueba (5 Pares)</span>
            </button>

            {pairs.length > 0 && (
              <button
                type="button"
                onClick={clearAll}
                disabled={isProcessingBatch}
                className="py-2 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-bold border border-rose-200 transition flex items-center space-x-1.5 shadow-sm disabled:opacity-50"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Limpiar</span>
              </button>
            )}
          </div>
        </div>

        {/* Multi-file Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={() => !isProcessingBatch && fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center transition cursor-pointer ${
            pairs.length > 0
              ? 'border-blue-300 bg-blue-50/20 hover:bg-blue-50/40'
              : 'border-slate-300 bg-slate-50 hover:bg-blue-50/30 hover:border-[#101BCB]'
          } ${isProcessingBatch ? 'opacity-60 cursor-not-allowed' : ''}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/png,image/jpeg,image/jpg,image/webp"
            onChange={handleInputChange}
            disabled={isProcessingBatch}
            className="hidden"
          />

          <div className="max-w-md mx-auto flex flex-col items-center space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-[#101BCB]/10 flex items-center justify-center text-[#101BCB]">
              <Upload className="w-7 h-7" />
            </div>
            <div>
              <p className="text-sm font-bold text-[#1E293B]">
                Arrastre aquí múltiples imágenes o haga clic para seleccionar
              </p>
              <p className="text-xs text-[#64748B] mt-1">
                Formatos compatibles: JPG, PNG, WEBP. Permite seleccionar cientos de fotos a la vez.
              </p>
            </div>

            <div className="bg-white px-4 py-2.5 rounded-xl border border-[#E2E8F0] shadow-sm text-left text-[11px] text-[#475569] space-y-1 w-full mt-2">
              <p className="font-bold text-[#080F72] flex items-center space-x-1">
                <HelpCircle className="w-3.5 h-3.5 text-[#101BCB]" />
                <span>Nomenclaturas soportadas para Anverso (A) y Reverso (R):</span>
              </p>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-slate-600 font-mono">
                <li>• 1.A.jpg / 1.R.jpg</li>
                <li>• DNI_44889922_A / DNI_44889922_R</li>
                <li>• 1_A.png / 1_R.png</li>
                <li>• DNI-A.jpg / DNI-R.jpg</li>
                <li>• 1A.jpg / 1R.jpg</li>
                <li>• Imágenes únicas (Anverso directo)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Action Controls & Stats */}
        {pairs.length > 0 && (
          <div className="pt-2 flex flex-col md:flex-row items-center justify-between gap-4 border-t border-[#E2E8F0]">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold text-[#475569]">Resumen del Lote:</span>
              <span className="bg-slate-100 text-[#1E293B] text-xs font-bold px-3 py-1 rounded-lg border border-slate-200">
                Total Pares: <span className="font-mono text-[#101BCB]">{totalCount}</span>
              </span>
              <span className="bg-emerald-50 text-[#00A88F] text-xs font-bold px-3 py-1 rounded-lg border border-emerald-200">
                Completados: <span className="font-mono">{doneCount}</span>
              </span>
              {errorCount > 0 && (
                <span className="bg-rose-50 text-rose-700 text-xs font-bold px-3 py-1 rounded-lg border border-rose-200">
                  Errores: <span className="font-mono">{errorCount}</span>
                </span>
              )}
            </div>

            <div className="flex items-center space-x-3 w-full md:w-auto">
              <button
                type="button"
                onClick={startBatchProcessing}
                disabled={isProcessingBatch || pairs.length === 0}
                className="flex-1 md:flex-initial py-2.5 px-6 rounded-xl bg-gradient-to-r from-[#00A88F] to-[#008f7a] hover:from-[#008f7a] hover:to-[#007664] text-white font-bold text-xs uppercase tracking-wider shadow-md shadow-emerald-700/20 flex items-center justify-center space-x-2 transition active:scale-95 disabled:opacity-50"
              >
                {isProcessingBatch ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Procesando Lote ({progressPercent}%)...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-current" />
                    <span>Iniciar Escaneo por Lote ({totalCount} Pares)</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Progress Bar */}
        {(isProcessingBatch || batchCompleted) && (
          <div className="space-y-2 bg-slate-50 p-4 rounded-xl border border-[#E2E8F0]">
            <div className="flex items-center justify-between text-xs font-bold text-[#1E293B]">
              <div className="flex items-center space-x-2">
                {isProcessingBatch ? (
                  <RefreshCw className="w-4 h-4 text-[#101BCB] animate-spin" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-[#00A88F]" />
                )}
                <span>{statusMessage}</span>
              </div>
              <span className="font-mono text-[#101BCB]">{progressPercent}%</span>
            </div>
            <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  batchCompleted ? 'bg-[#00A88F]' : 'bg-[#101BCB]'
                }`}
                style={{ width: `${progressPercent}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Batch Completed Success Callout */}
        {batchCompleted && doneCount > 0 && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-3.5">
              <div className="p-3 bg-emerald-600 text-white rounded-xl shadow-sm">
                <FileCheck className="w-6 h-6" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-emerald-950">
                  ¡{doneCount} DNIs escaneados y guardados con éxito!
                </h4>
                <p className="text-xs text-emerald-800 mt-0.5">
                  Los registros ya están almacenados con su fecha y hora en el sistema. Puede seleccionarlos en "Generar Excel por Lote" para completar sus plantillas.
                </p>
              </div>
            </div>

            {onNavigateToExcelGenerator && (
              <button
                type="button"
                onClick={onNavigateToExcelGenerator}
                className="py-2.5 px-5 rounded-xl bg-[#080F72] hover:bg-[#101BCB] text-white font-bold text-xs flex items-center space-x-2 transition shadow-md whitespace-nowrap"
              >
                <span>Generar Excel con estos registros</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

      </div>

      {/* 2. Structured Pairs Table */}
      {pairs.length > 0 && (
        <div className="bg-white border border-[#E2E8F0] rounded-2xl shadow-corporate-md overflow-hidden">
          
          <div className="px-6 py-4 border-b border-[#E2E8F0] bg-slate-50 flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <FileSpreadsheet className="w-5 h-5 text-[#101BCB]" />
              <h4 className="text-sm font-bold text-[#1E293B]">
                Listado de Pares Detectados ({pairs.length})
              </h4>
            </div>
            <span className="text-xs text-[#64748B]">
              Los datos se extraen con recorte automático OpenCV y RapidOCR AI
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E2E8F0] text-[11px] font-bold text-[#64748B] uppercase tracking-wider bg-white">
                  <th className="py-3 px-4 w-12 text-center">#</th>
                  <th className="py-3 px-4">Identificador / Par</th>
                  <th className="py-3 px-4">Anverso (A)</th>
                  <th className="py-3 px-4">Reverso (R)</th>
                  <th className="py-3 px-4">Estado</th>
                  <th className="py-3 px-4">Datos Extraídos</th>
                  <th className="py-3 px-4 text-center w-16">Acción</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E2E8F0] text-xs">
                {pairs.map((pair, idx) => {
                  const isCurrent = currentIndex === idx;
                  return (
                    <tr
                      key={pair.id}
                      className={`transition ${
                        isCurrent
                          ? 'bg-blue-50/60 font-semibold'
                          : pair.status === 'done'
                          ? 'bg-emerald-50/20 hover:bg-slate-50'
                          : pair.status === 'error'
                          ? 'bg-rose-50/30 hover:bg-slate-50'
                          : 'hover:bg-slate-50'
                      }`}
                    >
                      {/* Index */}
                      <td className="py-3 px-4 text-center font-mono font-bold text-[#64748B]">
                        {idx + 1}
                      </td>

                      {/* Label */}
                      <td className="py-3 px-4">
                        <span className="font-bold text-[#080F72] bg-blue-50 px-2.5 py-1 rounded-md border border-blue-100 font-mono">
                          {pair.label}
                        </span>
                      </td>

                      {/* Front File */}
                      <td className="py-3 px-4">
                        {pair.frontFile ? (
                          <div className="flex items-center space-x-1.5 text-slate-800">
                            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                            <span className="truncate max-w-[140px]" title={pair.frontName}>
                              {pair.frontName}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              ({(pair.frontFile.size / 1024).toFixed(0)} KB)
                            </span>
                          </div>
                        ) : (
                          <span className="text-rose-600 font-bold text-[11px] flex items-center space-x-1">
                            <AlertCircle className="w-3 h-3" />
                            <span>Falta Anverso</span>
                          </span>
                        )}
                      </td>

                      {/* Back File */}
                      <td className="py-3 px-4">
                        {pair.backFile ? (
                          <div className="flex items-center space-x-1.5 text-slate-800">
                            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                            <span className="truncate max-w-[140px]" title={pair.backName}>
                              {pair.backName}
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              ({(pair.backFile.size / 1024).toFixed(0)} KB)
                            </span>
                          </div>
                        ) : (
                          <span className="text-slate-400 italic text-[11px]">
                            Sin Reverso (Opcional)
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4">
                        {pair.status === 'pending' && (
                          <span className="inline-flex items-center space-x-1.5 bg-slate-100 text-slate-600 px-2.5 py-0.5 rounded-full text-[11px] font-bold">
                            <Clock className="w-3 h-3" />
                            <span>Pendiente</span>
                          </span>
                        )}
                        {pair.status === 'processing' && (
                          <span className="inline-flex items-center space-x-1.5 bg-blue-100 text-[#101BCB] px-2.5 py-0.5 rounded-full text-[11px] font-bold animate-pulse">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            <span>Escaneando...</span>
                          </span>
                        )}
                        {pair.status === 'done' && (
                          <span className="inline-flex items-center space-x-1.5 bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Completado</span>
                          </span>
                        )}
                        {pair.status === 'error' && (
                          <span className="inline-flex items-center space-x-1.5 bg-rose-100 text-rose-800 px-2.5 py-0.5 rounded-full text-[11px] font-bold" title={pair.error}>
                            <AlertCircle className="w-3 h-3 text-rose-600" />
                            <span>Error</span>
                          </span>
                        )}
                      </td>

                      {/* Extracted Data Preview */}
                      <td className="py-3 px-4">
                        {pair.extractedData ? (
                          <div className="space-y-0.5">
                            <div className="font-mono font-bold text-[#101BCB]">
                              DNI: {pair.extractedData.doc_number || '---'}
                            </div>
                            <div className="text-[11px] text-slate-700 truncate max-w-[220px]">
                              {pair.extractedData.first_names} {pair.extractedData.paternal_surname} {pair.extractedData.maternal_surname}
                            </div>
                          </div>
                        ) : pair.error ? (
                          <span className="text-rose-600 text-[11px] italic">
                            {pair.error}
                          </span>
                        ) : (
                          <span className="text-slate-400 text-[11px] italic">
                            En espera de escaneo...
                          </span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3 px-4 text-center">
                        <button
                          type="button"
                          onClick={() => removePair(pair.id)}
                          disabled={isProcessingBatch}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition disabled:opacity-30"
                          title="Eliminar este par"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

        </div>
      )}

    </div>
  );
}
