import React, { useState } from 'react';
import {
  Save,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Cpu,
  ArrowLeft,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { api } from '../services/api';
import OCRDiagnosticModal from './OCRDiagnosticModal';

export default function ReviewForm({
  scanResult,
  onReset,
  onRecordSaved,
}) {
  const [formData, setFormData] = useState({
    doc_type: scanResult?.doc_type || 'DNI',
    doc_number: scanResult?.doc_number || '',
    paternal_surname: scanResult?.paternal_surname || '',
    maternal_surname: scanResult?.maternal_surname || '',
    first_names: scanResult?.first_names || '',
    nationality: scanResult?.nationality || (scanResult?.doc_type === 'DNI' ? 'PERUANA' : ''),
    birth_date: scanResult?.birth_date || '',
    sex: scanResult?.sex || '',
    address: scanResult?.address || '',
    ubigeo: scanResult?.ubigeo || '',
    issue_date: scanResult?.issue_date || '',
    expiry_date: scanResult?.expiry_date || '',
    blood_type: scanResult?.blood_type || '',
    civil_status: scanResult?.civil_status || '',
    migratory_status: scanResult?.migratory_status || '',
    phone: scanResult?.phone || '999999999',
    email: scanResult?.email || 'sincorreo@gmail.com',
    pension_system: scanResult?.pension_system || '',
    pension_commission: scanResult?.pension_commission || '',
    cuspp: scanResult?.cuspp || '',
    observations: scanResult?.observations || '',
  });

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showDiagnostic, setShowDiagnostic] = useState(false);

  const fieldsMeta = scanResult?.fields || {};
  const isDni = formData.doc_type === 'DNI' || formData.doc_type === 'DNI Electrónico';

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Helper for 3-tier status and confidence badge (compact corporate badge)
  const renderConfidenceBadge = (fieldKey) => {
    const meta = fieldsMeta[fieldKey];
    if (!meta) return null;

    const conf = Math.round(meta.confidence || 0);
    const status = meta.status || (conf >= 80 ? 'CONFIRMADO' : conf >= 40 ? 'REVISAR' : 'NO_DETECTADO');

    let badgeColor = 'bg-[#DCFCE7] text-[#166534] border-[#86EFAC]';
    let iconText = '✓';

    if (status === 'NO_DETECTADO' || conf < 40) {
      badgeColor = 'bg-slate-100 text-[#64748B] border-[#CBD5E1]';
      iconText = '✕';
    } else if (status === 'REVISAR' || conf < 80) {
      badgeColor = 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]';
      iconText = '⚠';
    }

    return (
      <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-full border inline-flex items-center space-x-0.5 ${badgeColor}`}>
        <span>{iconText}</span>
        <span>{status === 'CONFIRMADO' ? `CONFIRMADO (${conf}%)` : `${status} (${conf}%)`}</span>
      </span>
    );
  };

  // Standard Save to DB & Master Excel
  const handleSave = async (e) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setErrorMsg(null);

    if (isDni && formData.doc_number.length !== 8) {
      setErrorMsg('El número de DNI debe contener exactamente 8 dígitos.');
      setIsSaving(false);
      return;
    }

    try {
      const payload = {
        ...formData,
        front_image_orig: scanResult?.front_image_orig || '',
        front_image_enhanced: scanResult?.front_image_enhanced || '',
        back_image_orig: scanResult?.back_image_orig || '',
        back_image_enhanced: scanResult?.back_image_enhanced || '',
        quality_score_front: scanResult?.quality_front?.laplacian_var || 0,
        quality_score_back: scanResult?.quality_back?.laplacian_var || 0,
        is_blurry_front: scanResult?.quality_front?.is_blurry || false,
        is_blurry_back: scanResult?.quality_back?.is_blurry || false,
        field_confidences: scanResult?.fields || {},
      };

      const saved = await api.saveRecord(payload);

      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#101BCB', '#A8E63D', '#080F72'],
      });

      setSaveSuccess(true);
      setTimeout(() => {
        if (onRecordSaved) onRecordSaved(saved);
      }, 800);
    } catch (err) {
      console.error('Error saving record:', err);
      setErrorMsg(
        err.response?.data?.detail || 'Error al guardar el registro en la base de datos o Excel.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white p-4 sm:p-5 rounded-xl border border-[#CBD5E1] shadow-sm space-y-4">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#E2E8F0]">
        <div className="flex items-center space-x-2.5">
          <button
            type="button"
            onClick={onReset}
            title="Retroceder a la pantalla de escaneo"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-100 hover:bg-slate-200 text-[#080F72] border border-[#CBD5E1] transition shadow-xs hover:border-[#101BCB]"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-[#101BCB]" />
            <span>← Atrás</span>
          </button>

          <div>
            <div className="flex items-center space-x-2">
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.2 rounded bg-blue-100 text-[#101BCB]">
                Paso 2
              </span>
              <h2 className="text-sm sm:text-base font-extrabold text-[#080F72]">
                Datos Extraídos del DNI
              </h2>
            </div>
            <p className="text-[11px] text-[#64748B] mt-0.5">
              Verifique o edite la información antes de guardar o generar Excel.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            type="button"
            onClick={() => setShowDiagnostic(true)}
            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-slate-50 hover:bg-slate-100 text-[#080F72] border border-[#CBD5E1] transition shadow-xs"
          >
            <Cpu className="w-3 h-3 text-[#101BCB]" />
            <span>Diagnóstico OCR</span>
          </button>

          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-[#DBEAFE] text-[#1E40AF] border border-blue-200">
            {formData.doc_type}
          </span>
        </div>
      </div>

      {/* OCR Warnings Banner (Compact) */}
      {scanResult?.warnings && scanResult.warnings.length > 0 && (
        <div className="p-2.5 rounded-lg bg-[#FEF3C7] border border-[#FDE68A] space-y-1">
          <div className="flex items-center space-x-1.5 text-[11px] font-bold text-[#92400E]">
            <AlertTriangle className="w-3.5 h-3.5 text-[#92400E]" />
            <span>Alertas de Extracción OCR:</span>
          </div>
          <ul className="text-[11px] text-[#92400E] list-disc list-inside space-y-0.2 pl-1">
            {scanResult.warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {errorMsg && (
        <div className="p-2.5 rounded-lg bg-[#FEE2E2] border border-[#FCA5A5] flex items-center space-x-2 text-[#991B1B] text-xs">
          <AlertCircle className="w-4 h-4 text-[#DC2626] flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Form Grid (High-Density & Cleanly Spaced) */}
      <form onSubmit={handleSave} className="space-y-3.5">
        
        {/* Row 1: Document Number & Sex & Nationality */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          {/* Doc Number */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">
                {isDni ? 'Número de DNI (8 dígitos)' : 'Número de Carnet CE'} *
              </label>
              {renderConfidenceBadge('doc_number')}
            </div>
            <input
              type="text"
              value={formData.doc_number}
              onChange={(e) => handleChange('doc_number', e.target.value)}
              required
              className={`w-full px-3 py-1.5 rounded-lg bg-white border text-[#1E293B] font-mono text-xs font-bold focus:outline-none transition ${
                isDni && formData.doc_number.length !== 8
                  ? 'border-[#DC2626] focus:border-[#DC2626] ring-1 ring-[#DC2626]'
                  : 'border-[#CBD5E1] focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]'
              }`}
              placeholder={isDni ? 'Ej. 72345678' : 'Ej. 001234567'}
            />
          </div>

          {/* Sex */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Sexo</label>
              {renderConfidenceBadge('sex')}
            </div>
            <select
              value={formData.sex}
              onChange={(e) => handleChange('sex', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
            >
              <option value="">Seleccione</option>
              <option value="M">M - Masculino</option>
              <option value="F">F - Femenino</option>
            </select>
          </div>

          {/* Nationality */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Nacionalidad</label>
              {renderConfidenceBadge('nationality')}
            </div>
            <input
              type="text"
              value={formData.nationality}
              onChange={(e) => handleChange('nationality', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. PERUANA"
            />
          </div>

        </div>

        {/* Row 2: Surnames & First Names */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Apellido Paterno</label>
              {renderConfidenceBadge('paternal_surname')}
            </div>
            <input
              type="text"
              value={formData.paternal_surname}
              onChange={(e) => handleChange('paternal_surname', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. MENDEZ"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Apellido Materno</label>
              {renderConfidenceBadge('maternal_surname')}
            </div>
            <input
              type="text"
              value={formData.maternal_surname}
              onChange={(e) => handleChange('maternal_surname', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. LOPEZ"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Nombres / Prenombres</label>
              {renderConfidenceBadge('first_names')}
            </div>
            <input
              type="text"
              value={formData.first_names}
              onChange={(e) => handleChange('first_names', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. BETY VALERIANA"
            />
          </div>

        </div>

        {/* Row 3: Dates (Birth, Issue, Expiry) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Fecha de Nacimiento</label>
              {renderConfidenceBadge('birth_date')}
            </div>
            <input
              type="text"
              value={formData.birth_date}
              onChange={(e) => handleChange('birth_date', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="DD/MM/AAAA (02/06/1997)"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Fecha de Emisión</label>
              {renderConfidenceBadge('issue_date')}
            </div>
            <input
              type="text"
              value={formData.issue_date}
              onChange={(e) => handleChange('issue_date', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="DD/MM/AAAA (20/09/2023)"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Fecha Caducidad / Vencimiento</label>
              {renderConfidenceBadge('expiry_date')}
            </div>
            <input
              type="text"
              value={formData.expiry_date}
              onChange={(e) => handleChange('expiry_date', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="DD/MM/AAAA o NO CADUCA"
            />
          </div>

        </div>

        {/* Row 4: Address & Ubigeo */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="sm:col-span-2 space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Dirección / Domicilio</label>
              {renderConfidenceBadge('address')}
            </div>
            <input
              type="text"
              value={formData.address}
              onChange={(e) => handleChange('address', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. CASERIO CORACOLLO SN"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Ubigeo (Dpto / Prov / Dist)</label>
              {renderConfidenceBadge('ubigeo')}
            </div>
            <input
              type="text"
              value={formData.ubigeo}
              onChange={(e) => handleChange('ubigeo', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. ANCASH / YUNGAY / QUILLO (021505)"
            />
          </div>

        </div>

        {/* Row 5: Contacto & Estado Civil (3 cols) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Celular / Teléfono</label>
              <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-blue-50 text-[#101BCB]">
                AUTO (Modificable)
              </span>
            </div>
            <input
              type="text"
              value={formData.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="999999999"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Correo Electrónico</label>
              <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-blue-50 text-[#101BCB]">
                AUTO (Modificable)
              </span>
            </div>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => handleChange('email', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="sincorreo@gmail.com"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Estado Civil</label>
              {renderConfidenceBadge('civil_status')}
            </div>
            <input
              type="text"
              value={formData.civil_status}
              onChange={(e) => handleChange('civil_status', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="SOLTERO / CASADO / etc."
            />
          </div>

        </div>

        {/* Row 6: Sistema Pensionario, Comisión y CUSPP (3 cols) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Sistema Pensionario</label>
              <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                Opcional
              </span>
            </div>
            <input
              type="text"
              value={formData.pension_system}
              onChange={(e) => handleChange('pension_system', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="ONP / HABITAT / INTEGRA / PRIMA / PROFUTURO"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Comisión</label>
              <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                Opcional
              </span>
            </div>
            <input
              type="text"
              value={formData.pension_commission}
              onChange={(e) => handleChange('pension_commission', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="FLUJO / MIXTA"
            />
          </div>

          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">CUSPP</label>
              <span className="text-[9px] font-semibold px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                Opcional
              </span>
            </div>
            <input
              type="text"
              value={formData.cuspp}
              onChange={(e) => handleChange('cuspp', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase font-mono"
              placeholder="Código CUSPP"
            />
          </div>

        </div>

        {/* Row 7: Blood Type & Observations (3 cols: 1 col + 2 cols) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold text-[#1E293B]">Grupo Sanguíneo</label>
              {renderConfidenceBadge('blood_type')}
            </div>
            <input
              type="text"
              value={formData.blood_type}
              onChange={(e) => handleChange('blood_type', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB] uppercase"
              placeholder="Ej. O+, A+, B+"
            />
          </div>

          <div className="sm:col-span-2 space-y-1">
            <label className="text-[11px] font-bold text-[#1E293B]">
              Observaciones
            </label>
            <input
              type="text"
              value={formData.observations}
              onChange={(e) => handleChange('observations', e.target.value)}
              className="w-full px-3 py-1.5 rounded-lg bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB] focus:ring-1 focus:ring-[#101BCB]"
              placeholder="Anotaciones internas"
            />
          </div>

        </div>

        {/* Actions Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-[#E2E8F0]">
          
          <button
            type="button"
            onClick={onReset}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg border border-[#CBD5E1] bg-slate-50 hover:bg-slate-100 text-[#080F72] text-xs font-bold transition shadow-2xs hover:border-[#101BCB]"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-[#101BCB]" />
            <span>← Retroceder / Volver a Escanear</span>
          </button>

          <button
            type="submit"
            disabled={isSaving || saveSuccess}
            className={`flex items-center space-x-1.5 px-4 py-2 rounded-lg font-bold text-xs shadow-sm transition ${
              saveSuccess
                ? 'bg-[#16A34A] text-white'
                : 'bg-[#16A34A] hover:bg-[#15803d] text-white'
            }`}
          >
            {saveSuccess ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                <span>¡Guardado en Base de Datos!</span>
              </>
            ) : isSaving ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                <span>Guardando...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5 text-white" />
                <span>Guardar en Base de Datos</span>
              </>
            )}
          </button>

        </div>

      </form>

      {/* Technical OCR Diagnostic Modal */}
      <OCRDiagnosticModal
        isOpen={showDiagnostic}
        onClose={() => setShowDiagnostic(false)}
        scanResult={scanResult}
      />

    </div>
  );
}
