import React, { useState, useEffect } from 'react';
import {
  FileText,
  User,
  Briefcase,
  Calendar,
  Mail,
  Phone,
  Building2,
  DollarSign,
  Shield,
  Clock,
  Sparkles,
  CheckCircle2,
  Download,
  AlertTriangle,
  RefreshCw,
  Eye,
  Info,
  Layers,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';
import { api } from '../services/api';

export default function WorkerConsolidationReview({
  workerProfile,
  onReset,
  onContractGenerated,
  onGoToMassive,
}) {
  const [profile, setProfile] = useState(workerProfile || null);
  const [fields, setFields] = useState(workerProfile?.fields || {});
  
  // Contract Parameters
  const [startDate, setStartDate] = useState(
    workerProfile?.contract_dates?.start_date ||
      new Date().toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric' })
  );
  const [durationMonths, setDurationMonths] = useState(
    workerProfile?.contract_dates?.duration_months || 3
  );
  const [calculatedEndDate, setCalculatedEndDate] = useState(
    workerProfile?.contract_dates?.end_date || ''
  );
  const [durationText, setDurationText] = useState(
    workerProfile?.contract_dates?.duration_text || '3 meses'
  );

  // Template and generation states
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Load templates on mount
  useEffect(() => {
    loadTemplates();
  }, []);

  // Update dates when startDate or durationMonths change
  useEffect(() => {
    if (startDate && durationMonths) {
      updateCalculatedDates(startDate, durationMonths);
    }
  }, [startDate, durationMonths]);

  const loadTemplates = async () => {
    try {
      const data = await api.getContractTemplates();
      if (data.templates && data.templates.length > 0) {
        setTemplates(data.templates);
        setSelectedTemplate(data.templates[0].name);
      }
    } catch (err) {
      console.error('Error loading templates:', err);
    }
  };

  const updateCalculatedDates = async (start, dur) => {
    try {
      const res = await api.calculateContractDates(start, dur);
      if (res.end_date) {
        setCalculatedEndDate(res.end_date);
        setDurationText(res.duration_text);
      }
    } catch (err) {
      console.error('Error calculating dates:', err);
    }
  };

  const handleFieldChange = (key, newValue) => {
    setFields((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        value: newValue,
        origin: 'Modificado por el Usuario',
        origin_type: 'USER',
      },
    }));
  };

  const handleRegenerateEmail = () => {
    const nombres = fields.first_names?.value || '';
    const paterno = fields.paternal_surname?.value || '';
    if (!nombres && !paterno) return;

    const fnClean = nombres.toLowerCase().split(' ')[0] || 'usuario';
    const snClean = paterno.toLowerCase().split(' ')[0] || 'trabajador';
    const emailProp = `${fnClean.replace(/[^a-z0-9]/g, '')}.${snClean.replace(/[^a-z0-9]/g, '')}@empresa.com.pe`;

    handleFieldChange('correo', emailProp);
  };

  const handleGenerateSampleContract = async () => {
    setIsGenerating(true);
    setErrorMsg(null);
    setGeneratedResult(null);

    try {
      const payload = {
        worker_data: {
          dni: profile?.dni || fields.dni?.value,
          full_name: profile?.full_name || fields.full_name?.value,
          fields: fields,
        },
        start_date: startDate,
        duration_months: Number(durationMonths),
        template_name: selectedTemplate || null,
        empresa_nombre: 'SERVICIOS INDUSTRIALES DEL PERÚ S.A.C.',
        empresa_ruc: '20601234567',
      };

      const res = await api.generateContract(payload);
      setGeneratedResult(res);

      if (onContractGenerated) {
        onContractGenerated(res);
      }
    } catch (err) {
      console.error('Error generating contract:', err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Error al generar el contrato');
    } finally {
      setIsGenerating(false);
    }
  };

  // Helper for origin badge styles
  const renderOriginBadge = (field) => {
    if (!field) return null;
    const type = field.origin_type || 'SYSTEM';

    let badgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
    let icon = <Info className="w-3 h-3 inline mr-1" />;

    if (type.includes('COMMENT') || field.is_hidden_or_note) {
      badgeClass = 'bg-purple-950/80 text-purple-300 border-purple-800/60';
      icon = <Sparkles className="w-3 h-3 inline mr-1 text-purple-400" />;
    } else if (type.includes('EXCEL')) {
      badgeClass = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60';
      icon = <Building2 className="w-3 h-3 inline mr-1 text-emerald-400" />;
    } else if (type === 'OCR') {
      badgeClass = 'bg-blue-950/80 text-blue-300 border-blue-800/60';
      icon = <Eye className="w-3 h-3 inline mr-1 text-blue-400" />;
    } else if (type === 'CALCULATED') {
      badgeClass = 'bg-amber-950/80 text-amber-300 border-amber-800/60';
      icon = <Clock className="w-3 h-3 inline mr-1 text-amber-400" />;
    } else if (type === 'USER') {
      badgeClass = 'bg-indigo-950/80 text-indigo-300 border-indigo-800/60';
      icon = <User className="w-3 h-3 inline mr-1 text-indigo-400" />;
    }

    return (
      <span
        title={field.origin}
        className={`inline-flex items-center text-[10px] px-2 py-0.5 rounded-md border font-mono truncate max-w-[280px] ${badgeClass}`}
      >
        {icon}
        <span className="truncate">{field.origin || type}</span>
      </span>
    );
  };

  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Top Header Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <span className="px-3 py-1 rounded-full bg-red-600/20 border border-red-500/30 text-red-400 text-xs font-mono font-bold">
                DNI: {profile?.dni || fields.dni?.value}
              </span>
              {profile?.excel_found ? (
                <span className="px-3 py-1 rounded-full bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center space-x-1">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  <span>Consolidado en Excel</span>
                </span>
              ) : (
                <span className="px-3 py-1 rounded-full bg-amber-600/20 border border-amber-500/30 text-amber-400 text-xs font-semibold flex items-center space-x-1">
                  <Info className="w-3.5 h-3.5 mr-1" />
                  <span>Nuevo / Extraído por OCR</span>
                </span>
              )}
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              {fields.full_name?.value || profile?.full_name || 'Trabajador'}
            </h2>

            <p className="text-xs text-slate-400 flex items-center space-x-2">
              <span>Hojas escaneadas:</span>
              <span className="font-mono text-slate-300">
                {profile?.excel_sheets_scanned?.length > 0
                  ? profile.excel_sheets_scanned.join(', ')
                  : 'Registros.xlsx'}
              </span>
            </p>
          </div>

          <div className="flex items-center space-x-3">
            {onReset && (
              <button
                type="button"
                onClick={onReset}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
              >
                Volver al Escaneo
              </button>
            )}
            {onGoToMassive && (
              <button
                type="button"
                onClick={onGoToMassive}
                className="px-4 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold border border-indigo-500/30 transition flex items-center space-x-1.5"
              >
                <Layers className="w-3.5 h-3.5" />
                <span>Ver Todos en Excel</span>
              </button>
            )}
          </div>

        </div>
      </div>

      {/* Main Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Data Review Form (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Section 1: Identification & Personal */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <User className="w-5 h-5 text-red-500" />
              <h3 className="text-base font-bold text-white">1. Datos de Identificación y Personales</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* DNI */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">DNI / Documento</label>
                  {renderOriginBadge(fields.dni)}
                </div>
                <input
                  type="text"
                  readOnly
                  value={fields.dni?.value || ''}
                  className="w-full bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:outline-none"
                />
              </div>

              {/* Fecha Nacimiento */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Fecha de Nacimiento</label>
                  {renderOriginBadge(fields.birth_date)}
                </div>
                <input
                  type="text"
                  value={fields.birth_date?.value || ''}
                  onChange={(e) => handleFieldChange('birth_date', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              {/* Apellido Paterno */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Apellido Paterno</label>
                  {renderOriginBadge(fields.paternal_surname)}
                </div>
                <input
                  type="text"
                  value={fields.paternal_surname?.value || ''}
                  onChange={(e) => handleFieldChange('paternal_surname', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              {/* Apellido Materno */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Apellido Materno</label>
                  {renderOriginBadge(fields.maternal_surname)}
                </div>
                <input
                  type="text"
                  value={fields.maternal_surname?.value || ''}
                  onChange={(e) => handleFieldChange('maternal_surname', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              {/* Nombres */}
              <div className="sm:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Nombres Completos</label>
                  {renderOriginBadge(fields.first_names)}
                </div>
                <input
                  type="text"
                  value={fields.first_names?.value || ''}
                  onChange={(e) => handleFieldChange('first_names', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              {/* Dirección */}
              <div className="sm:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Dirección Domiciliaria</label>
                  {renderOriginBadge(fields.address)}
                </div>
                <input
                  type="text"
                  value={fields.address?.value || ''}
                  onChange={(e) => handleFieldChange('address', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              {/* Distrito / Provincia / Dpto */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Distrito</label>
                  {renderOriginBadge(fields.district)}
                </div>
                <input
                  type="text"
                  value={fields.district?.value || 'LIMA'}
                  onChange={(e) => handleFieldChange('district', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Estado Civil</label>
                  {renderOriginBadge(fields.civil_status)}
                </div>
                <input
                  type="text"
                  value={fields.civil_status?.value || 'SOLTERO(A)'}
                  onChange={(e) => handleFieldChange('civil_status', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-red-500 focus:outline-none"
                />
              </div>

            </div>
          </div>

          {/* Section 2: Contact Info (Editable) */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Mail className="w-5 h-5 text-indigo-400" />
              <h3 className="text-base font-bold text-white">2. Contacto (Correo y Celular)</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Correo */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Correo Electrónico</label>
                  {renderOriginBadge(fields.correo)}
                </div>
                <div className="relative">
                  <input
                    type="email"
                    value={fields.correo?.value || ''}
                    onChange={(e) => handleFieldChange('correo', e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-3 pr-9 py-2 text-sm text-indigo-300 font-mono focus:border-indigo-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    title="Regenerar sugerencia corporativa"
                    onClick={handleRegenerateEmail}
                    className="absolute right-2 top-2.5 text-slate-500 hover:text-indigo-400 transition"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Propuesta automática basada en nombres y apellidos. Editable.
                </span>
              </div>

              {/* Celular */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Teléfono / Celular</label>
                  {renderOriginBadge(fields.celular)}
                </div>
                <input
                  type="text"
                  placeholder="Ej: 999 888 777"
                  value={fields.celular?.value || ''}
                  onChange={(e) => handleFieldChange('celular', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono focus:border-indigo-500 focus:outline-none"
                />
                <span className="text-[11px] text-slate-500 mt-1 block">
                  Si no está en Excel, puedes ingresarlo aquí sin modificar el archivo.
                </span>
              </div>

            </div>
          </div>

          {/* Section 3: Labor & Remuneration */}
          <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-6 shadow-lg space-y-5">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Briefcase className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">3. Datos Laborales y Remuneración</h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Cargo */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Cargo / Puesto</label>
                  {renderOriginBadge(fields.cargo)}
                </div>
                <input
                  type="text"
                  value={fields.cargo?.value || 'OPERARIO'}
                  onChange={(e) => handleFieldChange('cargo', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Área */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Área / Sección</label>
                  {renderOriginBadge(fields.area)}
                </div>
                <input
                  type="text"
                  value={fields.area?.value || 'OPERACIONES'}
                  onChange={(e) => handleFieldChange('area', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* AFP / Sistema Pensionario */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">AFP / Sistema Pensionario</label>
                  {renderOriginBadge(fields.afp)}
                </div>
                <input
                  type="text"
                  value={fields.afp?.value || 'AFP HABITAT'}
                  onChange={(e) => handleFieldChange('afp', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 font-semibold text-emerald-400 focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Remuneración Numérica */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Remuneración Mensual (S/)</label>
                  {renderOriginBadge(fields.remuneracion)}
                </div>
                <input
                  type="text"
                  value={fields.remuneracion?.value || '1500.00'}
                  onChange={(e) => handleFieldChange('remuneracion', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 font-mono font-bold focus:border-emerald-500 focus:outline-none"
                />
              </div>

              {/* Remuneración en Letras */}
              <div className="sm:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-slate-400">Monto en Letras (Para Contrato)</label>
                  {renderOriginBadge(fields.remuneracion_letras)}
                </div>
                <input
                  type="text"
                  value={fields.remuneracion_letras?.value || 'MIL QUINIENTOS Y 00/100 SOLES'}
                  onChange={(e) => handleFieldChange('remuneracion_letras', e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 font-mono focus:border-emerald-500 focus:outline-none"
                />
              </div>

            </div>
          </div>

        </div>

        {/* Right Column: Contract Setup & Generation Box (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          
          <div className="bg-gradient-to-br from-slate-900 via-slate-900 to-red-950/40 border border-red-500/20 rounded-2xl p-6 shadow-2xl space-y-6">
            
            <div className="flex items-center space-x-2.5 pb-4 border-b border-slate-800">
              <Calendar className="w-5 h-5 text-red-500" />
              <div>
                <h3 className="text-base font-bold text-white">4. Parámetros del Contrato</h3>
                <p className="text-xs text-slate-400">Cálculo exacto de vigencia laboral</p>
              </div>
            </div>

            {/* Fecha de Inicio (Manual) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span>Fecha de Inicio del Contrato:</span>
                <span className="text-[10px] text-amber-400 font-mono">Ingreso Manual Obligatorio</span>
              </label>
              <input
                type="text"
                placeholder="DD/MM/AAAA (Ej: 08/09/2026)"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full bg-slate-950 border border-red-500/40 focus:border-red-500 rounded-xl px-4 py-2.5 text-sm text-white font-mono font-bold focus:outline-none shadow-inner"
              />
            </div>

            {/* Duración del Contrato */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">
                Duración del Contrato:
              </label>
              <div className="grid grid-cols-4 gap-2">
                {[1, 2, 3, 6].map((months) => (
                  <button
                    key={months}
                    type="button"
                    onClick={() => setDurationMonths(months)}
                    className={`py-2 text-xs font-bold rounded-lg border transition ${
                      durationMonths === months
                        ? 'bg-red-600 text-white border-red-500 shadow-md shadow-red-600/30'
                        : 'bg-slate-950 hover:bg-slate-800 text-slate-300 border-slate-800'
                    }`}
                  >
                    {months} {months === 1 ? 'Mes' : 'Meses'}
                  </button>
                ))}
              </div>
              <div className="pt-1 flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setDurationMonths(12)}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg border transition ${
                    durationMonths === 12
                      ? 'bg-red-600 text-white border-red-500'
                      : 'bg-slate-950 hover:bg-slate-800 text-slate-300 border-slate-800'
                  }`}
                >
                  12 Meses (1 Año)
                </button>
              </div>
            </div>

            {/* Fecha de Fin (Calculada Automáticamente) */}
            <div className="bg-slate-950/90 border border-slate-800 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5 text-emerald-400 inline mr-1" />
                  <span>Fecha de Término (Calculada):</span>
                </span>
                <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/50">
                  Automático
                </span>
              </div>
              <div className="text-xl font-mono font-extrabold text-emerald-400">
                {calculatedEndDate || 'Calculando...'}
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Vigencia calculada: del <strong>{startDate}</strong> al <strong>{calculatedEndDate}</strong> ({durationText}).
              </p>
            </div>

            {/* Plantilla DOCX Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span>Plantilla de Contrato (.docx):</span>
                <span className="text-[10px] text-slate-400">100% Formato Preservado</span>
              </label>
              <select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-red-500"
              >
                {templates.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name} ({t.size_kb} KB)
                  </option>
                ))}
              </select>
            </div>

            {/* Error message */}
            {errorMsg && (
              <div className="p-3.5 rounded-xl bg-red-950/80 border border-red-800 text-red-300 text-xs flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Main Action: Generate Sample Contract */}
            <div className="pt-2">
              <button
                type="button"
                disabled={isGenerating}
                onClick={handleGenerateSampleContract}
                className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold text-sm shadow-lg shadow-red-600/30 flex items-center justify-center space-x-2 transition disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>Generando Contrato .docx...</span>
                  </>
                ) : (
                  <>
                    <FileText className="w-5 h-5" />
                    <span>Generar y Validar Contrato (Muestra)</span>
                  </>
                )}
              </button>
            </div>

            {/* Success Box after Generation */}
            {generatedResult && (
              <div className="p-4 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-200 space-y-3 animate-fade-in">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>¡Contrato generado con éxito!</span>
                </div>
                
                <div className="text-xs text-slate-300 space-y-1 font-mono bg-slate-950/60 p-2.5 rounded-lg border border-emerald-900/60">
                  <div className="truncate"><strong>Archivo:</strong> {generatedResult.file_details?.file_name}</div>
                  <div><strong>Variables reemplazadas:</strong> {generatedResult.file_details?.variables_replaced_count}</div>
                  <div><strong>Vigencia:</strong> {startDate} al {calculatedEndDate}</div>
                </div>

                <div className="flex items-center space-x-2 pt-1">
                  <a
                    href={api.getContractDownloadUrl(generatedResult.file_details?.file_name)}
                    download
                    className="flex-1 py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs text-center flex items-center justify-center space-x-1.5 transition"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Descargar .DOCX</span>
                  </a>

                  {onGoToMassive && (
                    <button
                      type="button"
                      onClick={onGoToMassive}
                      className="py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center space-x-1 border border-slate-700 transition"
                    >
                      <span>Ir a Masivo</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </div>
            )}

          </div>

        </div>

      </div>

    </div>
  );
}
