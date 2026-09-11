import React, { useState } from 'react';
import { X, Cpu, Layers, CheckCircle2, AlertTriangle, FileText, Sparkles, Activity, ShieldCheck, Eye } from 'lucide-react';
import { api } from '../services/api';

export default function OCRDiagnosticModal({
  isOpen,
  onClose,
  scanResult,
}) {
  const [activeTab, setActiveTab] = useState('variants'); // 'variants' | 'passes' | 'classification'
  const [selectedVariantImg, setSelectedVariantImg] = useState(null);

  if (!isOpen) return null;

  const docSubtype = scanResult?.doc_subtype || 'DNI Azul Clásico';
  const sideFront = scanResult?.detected_side_front || 'ANVERSO';
  const sideBack = scanResult?.detected_side_back || 'REVERSO';
  const matchStatus = scanResult?.worker_match_status || 'NOT_FOUND';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-5xl bg-white border border-[#E2E8F0] rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-[#080F72]">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-white/10 text-[#A8E63D] border border-white/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Panel de Diagnóstico Técnico e Inspección Multi-Intento OCR</span>
              </h3>
              <p className="text-xs text-slate-200">
                Detalle del pipeline OpenCV, clasificación de documento y algoritmo de consenso.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Buttons */}
        <div className="flex items-center space-x-1 px-6 pt-3 border-b border-[#E2E8F0] bg-[#F8FAFC] text-xs font-semibold">
          <button
            onClick={() => setActiveTab('variants')}
            className={`px-4 py-2.5 rounded-t-xl border-b-2 flex items-center space-x-2 transition ${
              activeTab === 'variants'
                ? 'border-[#101BCB] text-[#101BCB] bg-white font-bold shadow-sm'
                : 'border-transparent text-[#64748B] hover:text-[#080F72]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Variantes OpenCV (6 Filtros)</span>
          </button>

          <button
            onClick={() => setActiveTab('passes')}
            className={`px-4 py-2.5 rounded-t-xl border-b-2 flex items-center space-x-2 transition ${
              activeTab === 'passes'
                ? 'border-[#101BCB] text-[#101BCB] bg-white font-bold shadow-sm'
                : 'border-transparent text-[#64748B] hover:text-[#080F72]'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Pasadas OCR y Consenso</span>
          </button>

          <button
            onClick={() => setActiveTab('classification')}
            className={`px-4 py-2.5 rounded-t-xl border-b-2 flex items-center space-x-2 transition ${
              activeTab === 'classification'
                ? 'border-[#101BCB] text-[#101BCB] bg-white font-bold shadow-sm'
                : 'border-transparent text-[#64748B] hover:text-[#080F72]'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Clasificador y Cruce con Base</span>
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-[#1E293B]">
          
          {/* TAB 1: VARIANTS */}
          {activeTab === 'variants' && (
            <div className="space-y-6">
              <div className="p-4 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-[#080F72]">Pipeline de Preprocesamiento Multi-Variante</h4>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    Cada variante aísla diferentes condiciones de captura: sombras, reflejos, desgaste físico y fondos con seguridad.
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-[#166534] font-bold bg-[#DCFCE7] px-2.5 py-1 rounded-full border border-[#86EFAC]">
                    Nitidez: {scanResult?.quality_front?.laplacian_var || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Grid of Variants */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                
                {/* 1. CLAHE */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">1. CLAHE + Nitidez</span>
                    <span className="text-[10px] bg-blue-50 text-[#101BCB] px-2 py-0.5 rounded-full font-bold">Principal</span>
                  </div>
                  <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-[#CBD5E1] aspect-[1.58/1]">
                    <img
                      src={api.getImageUrl(scanResult?.front_image_enhanced)}
                      alt="CLAHE Enhanced"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Realce de contraste adaptativo local para textos tenues y firmas.
                  </p>
                </div>

                {/* 2. Original Warped */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">2. Original Enderezada</span>
                    <span className="text-[10px] bg-slate-100 text-[#1E293B] px-2 py-0.5 rounded-full font-bold">Color BGR</span>
                  </div>
                  <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-[#CBD5E1] aspect-[1.58/1]">
                    <img
                      src={api.getImageUrl(scanResult?.front_image_orig)}
                      alt="Original Warped"
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Recorte de bordes y corrección de perspectiva homográfica.
                  </p>
                </div>

                {/* 3. Shadow Free */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">3. Aplanado de Sombras</span>
                    <span className="text-[10px] bg-emerald-50 text-[#166534] px-2 py-0.5 rounded-full font-bold">Móvil / Flash</span>
                  </div>
                  <div className="rounded-xl overflow-hidden bg-[#F8FAFC] border border-[#CBD5E1] aspect-[1.58/1] flex items-center justify-center p-4 text-center">
                    <span className="text-xs text-[#64748B] font-mono">División Morfológica 41x41</span>
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Elimina gradientes de iluminación en fotos tomadas con celular.
                  </p>
                </div>

                {/* 4. Adaptive Gaussian */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">4. Binarización Gaussian</span>
                    <span className="text-[10px] bg-amber-50 text-amber-700 px-2 py-0.5 rounded-full font-bold">Binarizado</span>
                  </div>
                  <div className="rounded-xl overflow-hidden bg-[#F8FAFC] border border-[#CBD5E1] aspect-[1.58/1] flex items-center justify-center p-4 text-center">
                    <span className="text-xs text-[#64748B] font-mono">Bloque Adaptativo 15, C=8</span>
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Aísla caracteres oscuros sobre fondos celestes y patrones de seguridad.
                  </p>
                </div>

                {/* 5. Otsu with Stroke Close */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">5. Otsu + Cierre</span>
                    <span className="text-[10px] bg-cyan-50 text-cyan-700 px-2 py-0.5 rounded-full font-bold">Trazos</span>
                  </div>
                  <div className="rounded-xl overflow-hidden bg-[#F8FAFC] border border-[#CBD5E1] aspect-[1.58/1] flex items-center justify-center p-4 text-center">
                    <span className="text-xs text-[#64748B] font-mono">Cierre de Trazos 2x2</span>
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Reconecta trazos de letras y números con desgaste o abrasión.
                  </p>
                </div>

                {/* 6. Dynamic Gamma */}
                <div className="bg-white border border-[#E2E8F0] rounded-2xl p-3 space-y-2 shadow-corporate-sm">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-[#080F72]">6. Corrección Gamma</span>
                    <span className="text-[10px] bg-purple-50 text-purple-700 px-2 py-0.5 rounded-full font-bold">Exposición</span>
                  </div>
                  <div className="rounded-xl overflow-hidden bg-[#F8FAFC] border border-[#CBD5E1] aspect-[1.58/1] flex items-center justify-center p-4 text-center">
                    <span className="text-xs text-[#64748B] font-mono">Curva Gamma γ=1.65 / γ=0.75</span>
                  </div>
                  <p className="text-[11px] text-[#64748B]">
                    Compensa fotos subexpuestas y reduce zonas de sobreexposición.
                  </p>
                </div>

              </div>
            </div>
          )}

          {/* TAB 2: PASSES & CONSENSUS */}
          {activeTab === 'passes' && (
            <div className="space-y-6">
              
              <div className="p-4 rounded-2xl bg-blue-50 border border-blue-200 flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-[#080F72]">Consenso Multi-Intento y Matriz de Confianza</h4>
                  <p className="text-xs text-[#64748B]">
                    Los resultados de múltiples intentos de OCR se alinean por candidato numérico y alfabético.
                  </p>
                </div>
                <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-[#DCFCE7] text-[#166534] text-xs font-bold border border-[#86EFAC]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Consenso Validado</span>
                </div>
              </div>

              {/* Extracted Fields Confidence Matrix Table */}
              <div className="border border-[#E2E8F0] rounded-2xl overflow-hidden shadow-corporate-sm">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#080F72] text-white font-bold border-b border-[#E2E8F0]">
                    <tr>
                      <th className="py-3 px-4">Campo Extraído</th>
                      <th className="py-3 px-4">Valor Resuelto</th>
                      <th className="py-3 px-4">Confianza</th>
                      <th className="py-3 px-4">Estado</th>
                      <th className="py-3 px-4">Procedencia</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E2E8F0] font-mono">
                    {Object.entries(scanResult?.fields || {}).map(([key, meta]) => {
                      const status = meta?.status || (meta?.confidence >= 80 ? 'CONFIRMADO' : 'REVISAR');
                      return (
                        <tr key={key} className="hover:bg-[#EEF2FF]">
                          <td className="py-2.5 px-4 font-sans font-semibold text-[#1E293B] capitalize">
                            {key.replace(/_/g, ' ')}
                          </td>
                          <td className="py-2.5 px-4 font-bold text-[#080F72]">
                            {meta?.value || '<No Detectado>'}
                          </td>
                          <td className="py-2.5 px-4">
                            <span className={`font-bold ${meta?.confidence >= 80 ? 'text-[#166534]' : 'text-[#92400E]'}`}>
                              {Math.round(meta?.confidence || 0)}%
                            </span>
                          </td>
                          <td className="py-2.5 px-4">
                            {status === 'CONFIRMADO' ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-[#DCFCE7] text-[#166534] text-[10px] font-bold border border-[#86EFAC]">
                                <span>✓ CONFIRMADO</span>
                              </span>
                            ) : status === 'REVISAR' ? (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-[#FEF3C7] text-[#92400E] text-[10px] font-bold border border-[#FDE68A]">
                                <span>⚠ REVISAR</span>
                              </span>
                            ) : (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full bg-slate-100 text-[#64748B] text-[10px] font-bold">
                                <span>✕ NO DETECTADO</span>
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 px-4 text-[#64748B] font-sans text-[11px]">
                            {meta?.origin_type || 'LEIDO_OCR'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

            </div>
          )}

          {/* TAB 3: CLASSIFICATION & WORKER MATCH */}
          {activeTab === 'classification' && (
            <div className="space-y-6">
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                {/* Card 1: Document Classification */}
                <div className="p-5 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
                  <div className="flex items-center space-x-2 text-xs font-bold text-[#101BCB] uppercase tracking-wider">
                    <Sparkles className="w-4 h-4" />
                    <span>Clasificación de Documento</span>
                  </div>
                  <div>
                    <h4 className="text-lg font-extrabold text-[#080F72]">{scanResult?.doc_type}</h4>
                    <p className="text-xs text-[#101BCB] font-semibold">{docSubtype}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-[#E2E8F0] text-xs">
                    <div>
                      <span className="text-[#64748B] block">Lado Anverso:</span>
                      <span className="font-bold text-[#166534]">{sideFront}</span>
                    </div>
                    <div>
                      <span className="text-[#64748B] block">Lado Reverso:</span>
                      <span className="font-bold text-[#166534]">{sideBack}</span>
                    </div>
                  </div>
                </div>

                {/* Card 2: Worker Matcher */}
                <div className="p-5 rounded-2xl bg-[#F8FAFC] border border-[#E2E8F0] space-y-3">
                  <div className="flex items-center space-x-2 text-xs font-bold text-[#080F72] uppercase tracking-wider">
                    <ShieldCheck className="w-4 h-4" />
                    <span>Identificación del Trabajador</span>
                  </div>
                  <div>
                    <h4 className="text-lg font-extrabold text-[#080F72]">
                      {matchStatus === 'EXACT_MATCH' ? 'Trabajador Identificado (Exacto)' : matchStatus === 'FUZZY_MATCH' ? 'Coincidencia Probable' : 'No Encontrado en Base'}
                    </h4>
                    <p className="text-xs text-[#64748B]">
                      {scanResult?.matched_worker_name || 'Nuevo trabajador para registrar'}
                    </p>
                  </div>
                  {scanResult?.duplicate_warning && (
                    <div className="p-2.5 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] text-[11px] text-[#92400E]">
                      {scanResult.duplicate_warning}
                    </div>
                  )}
                </div>

              </div>

            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#E2E8F0] bg-[#F8FAFC] flex items-center justify-between">
          <span className="text-xs text-[#64748B]">
            Motor de Extracción Tolerante a Variaciones • EscanDNI Chavín
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-[#101BCB] hover:bg-[#080F72] text-white text-xs font-semibold transition shadow-sm"
          >
            Cerrar Diagnóstico
          </button>
        </div>

      </div>
    </div>
  );
}
