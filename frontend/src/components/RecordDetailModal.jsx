import React, { useState } from 'react';
import { X, Calendar, User, MapPin, CreditCard, ShieldCheck, FileSpreadsheet, Eye, Layers } from 'lucide-react';
import { api } from '../services/api';

export default function RecordDetailModal({ record, onClose }) {
  const [activeImageTab, setActiveImageTab] = useState('front_enhanced'); // 'front_orig' | 'front_enhanced' | 'back_orig' | 'back_enhanced'

  if (!record) return null;

  const isDni = record.doc_type === 'DNI';

  const getImageSrc = () => {
    switch (activeImageTab) {
      case 'front_orig':
        return api.getImageUrl(record.front_image_orig);
      case 'front_enhanced':
        return api.getImageUrl(record.front_image_enhanced);
      case 'back_orig':
        return api.getImageUrl(record.back_image_orig);
      case 'back_enhanced':
        return api.getImageUrl(record.back_image_enhanced);
      default:
        return '';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-4xl bg-white rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-[#080F72]">
          <div className="flex items-center space-x-3">
            <span className="p-2 rounded-xl bg-white/10 text-[#A8E63D] border border-white/20">
              {isDni ? <CreditCard className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </span>
            <div>
              <h3 className="text-base font-bold text-white">
                {record.paternal_surname} {record.maternal_surname} {record.first_names}
              </h3>
              <p className="text-xs text-slate-200">
                {record.doc_type}: <strong className="text-[#A8E63D] font-mono">{record.doc_number}</strong> • Escaneado el {record.scan_date ? new Date(record.scan_date).toLocaleString('es-PE') : 'N/A'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Images Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
                Fotografías del Documento
              </h4>
              <div className="flex items-center space-x-1.5 bg-[#F8FAFC] p-1 rounded-xl border border-[#E2E8F0] text-xs">
                <button
                  onClick={() => setActiveImageTab('front_enhanced')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    activeImageTab === 'front_enhanced' ? 'bg-[#101BCB] text-white shadow-sm' : 'text-[#64748B] hover:text-[#080F72]'
                  }`}
                >
                  Anverso Mejorado
                </button>
                <button
                  onClick={() => setActiveImageTab('front_orig')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    activeImageTab === 'front_orig' ? 'bg-[#101BCB] text-white shadow-sm' : 'text-[#64748B] hover:text-[#080F72]'
                  }`}
                >
                  Anverso Original
                </button>
                <button
                  onClick={() => setActiveImageTab('back_enhanced')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    activeImageTab === 'back_enhanced' ? 'bg-[#101BCB] text-white shadow-sm' : 'text-[#64748B] hover:text-[#080F72]'
                  }`}
                >
                  Reverso Mejorado
                </button>
                <button
                  onClick={() => setActiveImageTab('back_orig')}
                  className={`px-2.5 py-1 rounded-lg font-bold transition ${
                    activeImageTab === 'back_orig' ? 'bg-[#101BCB] text-white shadow-sm' : 'text-[#64748B] hover:text-[#080F72]'
                  }`}
                >
                  Reverso Original
                </button>
              </div>
            </div>

            <div className="relative rounded-xl overflow-hidden border border-[#CBD5E1] bg-slate-950 aspect-[1.586] max-h-[360px] flex items-center justify-center">
              {getImageSrc() ? (
                <img
                  src={getImageSrc()}
                  alt="Document preview"
                  className="w-full h-full object-contain"
                />
              ) : (
                <span className="text-xs text-slate-400">Imagen no disponible</span>
              )}
            </div>
          </div>

          {/* Key-Value Details Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
            
            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Número de Documento</span>
              <span className="text-sm font-bold text-[#080F72] font-mono">{record.doc_number || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Nacionalidad</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.nationality || 'PERUANA'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Sexo</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.sex || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Fecha de Nacimiento</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.birth_date || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Fecha de Emisión</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.issue_date || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Fecha de Vencimiento</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.expiry_date || '-'}</span>
            </div>

            <div className="sm:col-span-2 p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Dirección / Domicilio</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.address || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">
                {isDni ? 'Ubigeo' : 'Calidad Migratoria'}
              </span>
              <span className="text-sm font-semibold text-[#1E293B]">
                {isDni ? record.ubigeo || '-' : record.migratory_status || '-'}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Celular / Teléfono</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.phone || '999999999'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Correo Electrónico</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.email || 'sincorreo@gmail.com'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Estado Civil</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.civil_status || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Sistema Pensionario</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.pension_system || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">Comisión</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.pension_commission || '-'}</span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
              <span className="text-[11px] text-[#64748B] block font-medium">CUSPP</span>
              <span className="text-sm font-semibold text-[#1E293B]">{record.cuspp || '-'}</span>
            </div>

            {isDni && (
              <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[11px] text-[#64748B] block font-medium">Grupo Sanguíneo</span>
                <span className="text-sm font-semibold text-[#1E293B]">{record.blood_type || '-'}</span>
              </div>
            )}

            {record.observations && (
              <div className="sm:col-span-3 p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0]">
                <span className="text-[11px] text-[#64748B] block font-medium">Observaciones</span>
                <span className="text-xs text-[#1E293B]">{record.observations}</span>
              </div>
            )}

          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2.5 bg-[#101BCB] hover:bg-[#080F72] text-white text-xs font-bold rounded-xl transition shadow-sm"
          >
            Cerrar
          </button>
        </div>

      </div>
    </div>
  );
}
