import React, { useState } from 'react';
import { Layers, Eye, Zap, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';

export default function ImageCompare({ scanResult }) {
  const [activeSide, setActiveSide] = useState('front'); // 'front' | 'back'
  const [viewMode, setViewMode] = useState('enhanced'); // 'enhanced' | 'original'

  if (!scanResult) return null;

  const quality = activeSide === 'front' ? scanResult.quality_front : scanResult.quality_back;
  const origImgUrl = activeSide === 'front' ? api.getImageUrl(scanResult.front_image_orig) : api.getImageUrl(scanResult.back_image_orig);
  const enhImgUrl = activeSide === 'front' ? api.getImageUrl(scanResult.front_image_enhanced) : api.getImageUrl(scanResult.back_image_enhanced);

  const isBlurry = quality?.is_blurry;
  const laplacianScore = quality?.laplacian_var || 0;

  return (
    <div className="bg-white p-3.5 sm:p-4 rounded-xl border border-[#CBD5E1] shadow-sm space-y-3 lg:sticky lg:top-4">
      
      {/* Header & Controls Toolbar */}
      <div className="flex items-center justify-between gap-2 pb-2.5 border-b border-[#E2E8F0]">
        <div className="flex items-center space-x-1.5">
          <Layers className="w-4 h-4 text-[#101BCB]" />
          <h3 className="font-bold text-[#080F72] text-xs uppercase tracking-wide">Inspección OpenCV</h3>
        </div>

        {/* Side switcher (Anverso / Reverso) */}
        <div className="flex items-center space-x-1 bg-slate-100 p-0.5 rounded-lg border border-[#E2E8F0]">
          <button
            type="button"
            onClick={() => setActiveSide('front')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition ${
              activeSide === 'front'
                ? 'bg-[#101BCB] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#080F72]'
            }`}
          >
            Anverso
          </button>
          <button
            type="button"
            onClick={() => setActiveSide('back')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-bold transition ${
              activeSide === 'back'
                ? 'bg-[#101BCB] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#080F72]'
            }`}
          >
            Reverso
          </button>
        </div>
      </div>

      {/* Quality Badge (Compact) */}
      {isBlurry ? (
        <div className="px-2.5 py-1.5 rounded-lg bg-[#FEE2E2] border border-[#FCA5A5] flex items-center space-x-2 text-[#991B1B] text-[11px]">
          <ShieldAlert className="w-3.5 h-3.5 text-[#DC2626] flex-shrink-0" />
          <span className="truncate">Imagen con posible baja nitidez (Var: {laplacianScore})</span>
        </div>
      ) : (
        <div className="px-2.5 py-1.5 rounded-lg bg-[#DCFCE7] border border-[#86EFAC] flex items-center justify-between text-[#166534] text-[11px] font-medium">
          <div className="flex items-center space-x-1.5">
            <CheckCircle className="w-3.5 h-3.5 text-[#16A34A]" />
            <span>Nitidez OCR Óptima (Varianza: <strong>{laplacianScore}</strong>)</span>
          </div>
          {quality?.perspective_corrected && (
            <span className="px-1.5 py-0.2 rounded bg-emerald-200 text-[#166534] text-[9px] font-bold">
              ID-1 OK
            </span>
          )}
        </div>
      )}

      {/* Image Display Canvas */}
      <div className="relative rounded-xl overflow-hidden border border-[#CBD5E1] bg-slate-950 aspect-[1.586] flex items-center justify-center group shadow-inner">
        <img
          src={viewMode === 'enhanced' ? enhImgUrl : origImgUrl}
          alt={`Vista ${viewMode} ${activeSide}`}
          className="w-full h-full object-contain"
        />

        {/* View Mode Toggle Pill inside bottom */}
        <div className="absolute bottom-2 inset-x-2 flex items-center justify-between">
          <div className="px-2 py-0.5 rounded-md bg-black/80 backdrop-blur-sm text-[10px] font-mono text-slate-200 border border-white/10">
            {viewMode === 'enhanced' ? '✨ OpenCV Enhanced' : '📷 Original'}
          </div>

          <div className="flex items-center space-x-1 bg-black/80 backdrop-blur-sm p-0.5 rounded-lg border border-white/10">
            <button
              type="button"
              onClick={() => setViewMode('enhanced')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition flex items-center space-x-1 ${
                viewMode === 'enhanced'
                  ? 'bg-[#101BCB] text-white shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Zap className="w-2.5 h-2.5 text-[#A8E63D]" />
              <span>Mejorada</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('original')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition flex items-center space-x-1 ${
                viewMode === 'original'
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Eye className="w-2.5 h-2.5 text-slate-300" />
              <span>Original</span>
            </button>
          </div>
        </div>
      </div>

    </div>
  );
}
