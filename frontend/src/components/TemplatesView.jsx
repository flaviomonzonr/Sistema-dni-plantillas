import React, { useState, useEffect, useRef } from 'react';
import {
  FileSpreadsheet,
  Plus,
  Download,
  Trash2,
  Edit3,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Table,
  Layers,
  ArrowRight,
  Eye,
  FileUp,
  Save,
  X,
  AlertTriangle,
  Sliders,
  Check,
  Cloud,
  HardDrive,
  Settings,
  Sparkles,
  Tag,
  User,
  Calendar,
  ShieldCheck,
  UploadCloud,
} from 'lucide-react';
import { api } from '../services/api';
import SupabaseConfigModal from './SupabaseConfigModal';

const AVAILABLE_DNI_FIELDS = [
  { key: 'none', label: '— Columna libre / No asignar —' },
  { key: 'doc_number', label: 'DNI / Nro Documento' },
  { key: 'paternal_surname', label: 'Primer Apellido (Paterno)' },
  { key: 'maternal_surname', label: 'Segundo Apellido (Materno)' },
  { key: 'first_names', label: 'Nombres / Prenombres' },
  { key: 'full_name', label: 'Apellidos y Nombres (Completo)' },
  { key: 'birth_date', label: 'Fecha de Nacimiento' },
  { key: 'sex', label: 'Sexo (M / F)' },
  { key: 'civil_status', label: 'Estado Civil' },
  { key: 'address', label: 'Dirección / Domicilio' },
  { key: 'department', label: 'Departamento' },
  { key: 'province', label: 'Provincia' },
  { key: 'district', label: 'Distrito' },
  { key: 'ubigeo', label: 'Ubigeo (Código o Dpto/Prov/Dist)' },
  { key: 'issue_date', label: 'Fecha de Emisión' },
  { key: 'expiry_date', label: 'Fecha de Caducidad' },
  { key: 'nationality', label: 'Nacionalidad' },
  { key: 'blood_type', label: 'Grupo Sanguíneo' },
  { key: 'phone', label: 'Celular / Teléfono' },
  { key: 'email', label: 'Correo Electrónico' },
  { key: 'pension_system', label: 'Sistema Pensionario (AFP / ONP)' },
  { key: 'pension_commission', label: 'Tipo de Comisión (Flujo / Mixta)' },
  { key: 'cuspp', label: 'Código CUSPP' },
];

const TEMPLATE_TYPES = [
  { key: 'EXCEL_CARGA_MASIVA', label: 'Carga Masiva Excel', badgeColor: 'bg-blue-100 text-blue-800 border-blue-200' },
  { key: 'EXCEL_CONTRATOS', label: 'Plantilla de Contratos', badgeColor: 'bg-purple-100 text-purple-800 border-purple-200' },
  { key: 'EXCEL_ASISTENCIA', label: 'Registro de Asistencia', badgeColor: 'bg-emerald-100 text-emerald-800 border-emerald-200' },
  { key: 'DOCUMENTO_WORD', label: 'Documento Word (.docx)', badgeColor: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
  { key: 'OTRO', label: 'Otro Formato', badgeColor: 'bg-slate-100 text-slate-700 border-slate-200' },
];

export default function TemplatesView({ reconnectTrigger }) {
  // Mode: 'supabase' (Cloud) | 'local' (Disk)
  const [activeMode, setActiveMode] = useState('supabase');

  // Supabase State
  const [supabaseTemplates, setSupabaseTemplates] = useState([]);
  const [supabaseConnected, setSupabaseConnected] = useState(false);
  const [supabaseLoading, setSupabaseLoading] = useState(true);
  const [selectedSupabaseTemplate, setSelectedSupabaseTemplate] = useState(null);

  // Local State
  const [localTemplates, setLocalTemplates] = useState([]);
  const [localLoading, setLocalLoading] = useState(true);
  const [selectedLocalTemplate, setSelectedLocalTemplate] = useState(null);

  // General Inspector State
  const [selectedSheetIndex, setSelectedSheetIndex] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Modals State
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [templateToDelete, setTemplateToDelete] = useState(null);

  // Supabase Upload Form State
  const [uploadForm, setUploadForm] = useState({
    name: '',
    template_type: 'EXCEL_CARGA_MASIVA',
    version: '1.0',
    user_name: 'Flavio Monzón',
    file: null,
  });

  // Rename / Edit Metadata State
  const [editMetaForm, setEditMetaForm] = useState({
    name: '',
    template_type: 'EXCEL_CARGA_MASIVA',
    version: '1.0',
    user_name: '',
  });
  const [isEditingMeta, setIsEditingMeta] = useState(false);

  // Interactive column mapping state (colIndex -> fieldKey)
  const [editedMappings, setEditedMappings] = useState({});
  const [hasUnsavedMappings, setHasUnsavedMappings] = useState(false);
  const [isSavingMapping, setIsSavingMapping] = useState(false);

  // Refs
  const localFileInputRef = useRef(null);
  const replaceFileInputRef = useRef(null);
  const uploadFileInputRef = useRef(null);

  useEffect(() => {
    loadAllData();
  }, []);

  // Auto-reload on reconnectTrigger
  useEffect(() => {
    if (reconnectTrigger !== undefined && reconnectTrigger > 0) {
      loadAllData();
    }
  }, [reconnectTrigger]);

  const loadAllData = async () => {
    await Promise.all([loadSupabaseTemplates(), loadLocalTemplates()]);
  };

  const loadSupabaseTemplates = async (selectId = null) => {
    setSupabaseLoading(true);
    try {
      const data = await api.supabase.getTemplates();
      setSupabaseConnected(data.is_connected !== false);
      const list = data.templates || [];
      setSupabaseTemplates(list);

      if (list.length > 0) {
        if (selectId) {
          const found = list.find((t) => t.id === selectId) || list[0];
          setSelectedSupabaseTemplate(found);
        } else if (!selectedSupabaseTemplate || !list.some((t) => t.id === selectedSupabaseTemplate.id)) {
          setSelectedSupabaseTemplate(list[0]);
          setSelectedSheetIndex(0);
        } else {
          const updated = list.find((t) => t.id === selectedSupabaseTemplate.id) || list[0];
          setSelectedSupabaseTemplate(updated);
        }
      } else {
        setSelectedSupabaseTemplate(null);
      }
    } catch (err) {
      console.error('Error loading Supabase templates:', err);
      setSupabaseConnected(false);
    } finally {
      setSupabaseLoading(false);
    }
  };

  const loadLocalTemplates = async (selectFilename = null) => {
    setLocalLoading(true);
    try {
      const data = await api.getExcelTemplates();
      const list = data.templates || [];
      setLocalTemplates(list);

      if (list.length > 0) {
        if (selectFilename) {
          const found = list.find((t) => t.filename === selectFilename) || list[0];
          setSelectedLocalTemplate(found);
        } else if (!selectedLocalTemplate || !list.some((t) => t.filename === selectedLocalTemplate.filename)) {
          setSelectedLocalTemplate(list[0]);
          setSelectedSheetIndex(0);
        } else {
          const updated = list.find((t) => t.filename === selectedLocalTemplate.filename) || list[0];
          setSelectedLocalTemplate(updated);
        }
      } else {
        setSelectedLocalTemplate(null);
      }
    } catch (err) {
      console.error('Error loading local templates:', err);
    } finally {
      setLocalLoading(false);
    }
  };

  // Active Template & Sheet depending on activeMode
  const activeTemplate = activeMode === 'supabase' ? selectedSupabaseTemplate : selectedLocalTemplate;
  const activeSheetsList = activeMode === 'supabase' 
    ? (selectedSupabaseTemplate?.sheets_metadata || [])
    : (selectedLocalTemplate?.sheets || []);
  const activeSheet = activeSheetsList[selectedSheetIndex] || activeSheetsList[0];

  // Initialize edited mappings when active sheet or template changes
  useEffect(() => {
    if (!activeSheet) {
      setEditedMappings({});
      setHasUnsavedMappings(false);
      return;
    }

    const currentMap = {};
    // Seed from activeSheet.mapped_fields
    Object.entries(activeSheet.mapped_fields || {}).forEach(([fieldKey, info]) => {
      currentMap[info.column_index] = fieldKey;
    });

    // Also check custom_mappings
    if (activeSheet.custom_mappings) {
      Object.entries(activeSheet.custom_mappings).forEach(([colKey, fieldKey]) => {
        const colNum = parseInt(colKey, 10);
        if (!isNaN(colNum)) {
          currentMap[colNum] = fieldKey;
        }
      });
    }

    setEditedMappings(currentMap);
    setHasUnsavedMappings(false);
  }, [selectedSupabaseTemplate?.id, selectedLocalTemplate?.filename, selectedSheetIndex, activeMode]);

  // Handle Supabase Upload
  const handleUploadSupabase = async (e) => {
    if (e) e.preventDefault();
    if (!uploadForm.file) {
      alert('Por favor seleccione un archivo Excel (.xlsx)');
      return;
    }

    setIsUploading(true);
    setErrorMsg(null);
    try {
      const res = await api.supabase.uploadTemplate(
        uploadForm.file,
        uploadForm.name.trim() || uploadForm.file.name,
        uploadForm.template_type,
        uploadForm.version || '1.0',
        uploadForm.user_name || 'Flavio Monzón'
      );

      setUploadSuccess(`¡Plantilla "${res.template?.name || uploadForm.file.name}" guardada en Supabase Cloud!`);
      setTimeout(() => setUploadSuccess(null), 4000);
      setShowUploadModal(false);
      setUploadForm({
        name: '',
        template_type: 'EXCEL_CARGA_MASIVA',
        version: '1.0',
        user_name: 'Flavio Monzón',
        file: null,
      });
      await loadSupabaseTemplates(res.template?.id);
    } catch (err) {
      console.error('Error uploading to Supabase:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al subir la plantilla a Supabase.');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Replace File in Supabase or Local
  const handleReplaceFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !activeTemplate) return;

    if (!file.name.toLowerCase().endsWith('.xlsx')) {
      alert('Por favor seleccione un archivo Excel válido con extensión .xlsx');
      return;
    }

    setIsUploading(true);
    setErrorMsg(null);
    try {
      if (activeMode === 'supabase') {
        const res = await api.supabase.replaceTemplate(activeTemplate.id, file);
        setUploadSuccess(`¡Archivo reemplazado en Supabase! Nueva versión: ${res.template?.version || 'actualizada'}`);
        setTimeout(() => setUploadSuccess(null), 4000);
        await loadSupabaseTemplates(activeTemplate.id);
      } else {
        await api.uploadExcelTemplate(file);
        setUploadSuccess(`¡Archivo local actualizado: "${file.name}"!`);
        setTimeout(() => setUploadSuccess(null), 4000);
        await loadLocalTemplates(file.name);
      }
    } catch (err) {
      console.error('Error replacing template:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al reemplazar el archivo.');
    } finally {
      setIsUploading(false);
      if (replaceFileInputRef.current) replaceFileInputRef.current.value = '';
    }
  };

  // Handle Edit Metadata / Rename
  const handleSaveMetadata = async (e) => {
    if (e) e.preventDefault();
    if (!activeTemplate) return;

    setIsEditingMeta(true);
    setErrorMsg(null);
    try {
      if (activeMode === 'supabase') {
        await api.supabase.updateMetadata(activeTemplate.id, editMetaForm);
        setUploadSuccess('Metadatos de la plantilla actualizados.');
        setShowRenameModal(false);
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadSupabaseTemplates(activeTemplate.id);
      } else {
        let targetName = editMetaForm.name.trim();
        if (!targetName.toLowerCase().endsWith('.xlsx')) targetName += '.xlsx';
        await api.renameExcelTemplate(activeTemplate.filename, targetName);
        setUploadSuccess(`Plantilla renombrada a "${targetName}".`);
        setShowRenameModal(false);
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadLocalTemplates(targetName);
      }
    } catch (err) {
      console.error('Error updating metadata:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al actualizar metadatos.');
    } finally {
      setIsEditingMeta(false);
    }
  };

  // Handle Delete Template
  const handleDeleteTemplate = async () => {
    if (!templateToDelete) return;
    setIsUploading(true);
    setErrorMsg(null);
    try {
      if (activeMode === 'supabase') {
        await api.supabase.deleteTemplate(templateToDelete.id);
        setUploadSuccess(`Plantilla "${templateToDelete.name}" eliminada de Supabase.`);
        setShowDeleteModal(false);
        setTemplateToDelete(null);
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadSupabaseTemplates();
      } else {
        await api.deleteExcelTemplate(templateToDelete.filename);
        setUploadSuccess(`Plantilla local "${templateToDelete.filename}" eliminada.`);
        setShowDeleteModal(false);
        setTemplateToDelete(null);
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadLocalTemplates();
      }
    } catch (err) {
      console.error('Error deleting template:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al eliminar la plantilla.');
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Save Mappings
  const handleSaveMappings = async () => {
    if (!activeTemplate || !activeSheet) return;
    setIsSavingMapping(true);
    setErrorMsg(null);
    try {
      if (activeMode === 'supabase') {
        await api.supabase.saveMapping(
          activeTemplate.id,
          activeSheet.sheet_name,
          editedMappings
        );
        setHasUnsavedMappings(false);
        setUploadSuccess('¡Mapeo de columnas guardado en Supabase Cloud!');
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadSupabaseTemplates(activeTemplate.id);
      } else {
        await api.saveExcelTemplateMapping(
          activeTemplate.filename,
          activeSheet.sheet_name,
          editedMappings
        );
        setHasUnsavedMappings(false);
        setUploadSuccess('¡Mapeo de columnas local guardado!');
        setTimeout(() => setUploadSuccess(null), 3000);
        await loadLocalTemplates(activeTemplate.filename);
      }
    } catch (err) {
      console.error('Error saving mapping:', err);
      setErrorMsg(err.response?.data?.detail || 'Error al guardar el mapeo.');
    } finally {
      setIsSavingMapping(false);
    }
  };

  // Handle Mapping Field Change
  const handleMappingChange = (colIndex, fieldKey) => {
    setEditedMappings((prev) => ({
      ...prev,
      [colIndex]: fieldKey,
    }));
    setHasUnsavedMappings(true);
  };

  // Upload Local Template into Supabase with 1-click
  const handlePromoteLocalToSupabase = async (localTpl) => {
    setIsUploading(true);
    setErrorMsg(null);
    try {
      // In local mode, we can download or read from server
      alert(`Para subir "${localTpl.filename}" a Supabase Cloud, haz clic en "Agregar Plantilla en Supabase" y selecciona el archivo.`);
      setActiveMode('supabase');
      setShowUploadModal(true);
      setUploadForm((prev) => ({
        ...prev,
        name: localTpl.filename.replace('.xlsx', ''),
      }));
    } catch (err) {
      console.error('Error promoting template:', err);
    } finally {
      setIsUploading(false);
    }
  };

  const getBadgeForType = (typeKey) => {
    const found = TEMPLATE_TYPES.find((t) => t.key === typeKey);
    return found ? found.badgeColor : 'bg-slate-100 text-slate-700 border-slate-200';
  };

  const getLabelForType = (typeKey) => {
    const found = TEMPLATE_TYPES.find((t) => t.key === typeKey);
    return found ? found.label : typeKey || 'Plantilla';
  };

  return (
    <div className="space-y-4 animate-fade-in">
      
      {/* Hidden inputs */}
      <input
        type="file"
        ref={replaceFileInputRef}
        onChange={handleReplaceFile}
        accept=".xlsx"
        className="hidden"
      />

      {/* Header Banner */}
      <div className="bg-white px-5 py-4 rounded-2xl border border-[#CBD5E1] shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3.5">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-[#101BCB] text-[11px] font-bold shadow-2xs">
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Gestión de Plantillas</span>
            </span>

            {/* Supabase Status Indicator */}
            {supabaseConnected ? (
              <button
                onClick={() => setShowConfigModal(true)}
                className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 border border-emerald-200 text-[#00A88F] text-[11px] font-bold hover:bg-emerald-100 transition"
                title="Configuración de Supabase Cloud activa"
              >
                <Cloud className="w-3 h-3" />
                <span>Supabase Cloud Conectado</span>
                <Settings className="w-2.5 h-2.5 text-[#00A88F]" />
              </button>
            ) : (
              <button
                onClick={() => setShowConfigModal(true)}
                className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-300 text-amber-800 text-[11px] font-bold hover:bg-amber-100 transition animate-pulse"
                title="Haga clic para conectar su cuenta de Supabase"
              >
                <Settings className="w-3 h-3 text-amber-700" />
                <span>⚙️ Configurar Supabase Cloud</span>
              </button>
            )}
          </div>

          <h2 className="text-lg sm:text-xl font-black text-[#080F72] mt-1.5">
            Gestor de Plantillas Excel y Contratos
          </h2>
          <p className="text-xs text-[#64748B] mt-0.5 max-w-2xl">
            Almacena tus plantillas en <strong>Supabase Storage</strong> y base de datos permanente para que nunca se pierdan al cambiar de PC o navegador.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 w-full md:w-auto flex-shrink-0">
          
          <button
            onClick={() => setShowConfigModal(true)}
            className="px-3 py-2 rounded-xl text-xs font-bold text-[#080F72] bg-slate-50 hover:bg-slate-100 border border-[#CBD5E1] transition flex items-center space-x-1.5 shadow-2xs"
            title="Ajustes de conexión Supabase"
          >
            <Settings className="w-3.5 h-3.5 text-[#101BCB]" />
            <span className="hidden sm:inline">Configuración Supabase</span>
          </button>

          {activeMode === 'supabase' ? (
            <button
              onClick={() => {
                if (!supabaseConnected) {
                  setShowConfigModal(true);
                } else {
                  setShowUploadModal(true);
                }
              }}
              disabled={isUploading}
              className="flex-1 md:flex-none flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl font-extrabold text-xs bg-[#101BCB] hover:bg-[#080F72] text-white shadow-sm transition transform active:scale-95"
            >
              <UploadCloud className="w-4 h-4" />
              <span>+ Subir a Supabase Cloud</span>
            </button>
          ) : (
            <>
              <input
                type="file"
                ref={localFileInputRef}
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setIsUploading(true);
                  try {
                    await api.uploadExcelTemplate(file);
                    setUploadSuccess(`Plantilla local "${file.name}" agregada.`);
                    setTimeout(() => setUploadSuccess(null), 3000);
                    await loadLocalTemplates(file.name);
                  } catch (err) {
                    setErrorMsg('Error al subir archivo local.');
                  } finally {
                    setIsUploading(false);
                    if (localFileInputRef.current) localFileInputRef.current.value = '';
                  }
                }}
                accept=".xlsx"
                className="hidden"
              />
              <button
                onClick={() => localFileInputRef.current?.click()}
                disabled={isUploading}
                className="flex-1 md:flex-none flex items-center justify-center space-x-1.5 px-4 py-2.5 rounded-xl font-extrabold text-xs bg-[#A8E63D] hover:bg-[#97d82e] text-[#080F72] shadow-sm transition transform active:scale-95"
              >
                <Plus className="w-4 h-4" />
                <span>+ Agregar Plantilla Local</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Notifications */}
      {uploadSuccess && (
        <div className="p-4 rounded-xl bg-[#DCFCE7] border border-[#86EFAC] flex items-center space-x-3 text-[#166534] text-xs sm:text-sm animate-fade-in shadow-2xs">
          <CheckCircle2 className="w-5 h-5 text-[#16A34A] flex-shrink-0" />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 rounded-xl bg-[#FEF2F2] border border-[#FCA5A5] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-[#991B1B] text-xs sm:text-sm animate-fade-in shadow-xs">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-[#DC2626] flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={loadAllData}
            className="px-3.5 py-1.5 rounded-lg bg-[#DC2626] hover:bg-[#B91C1C] text-white text-xs font-bold flex items-center space-x-1.5 transition shrink-0"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reintentar</span>
          </button>
        </div>
      )}

      {/* Mode Switcher Tabs: Supabase Cloud vs Local */}
      <div className="flex items-center justify-between bg-white p-1.5 rounded-2xl border border-[#CBD5E1] shadow-2xs">
        <div className="flex items-center space-x-1 w-full sm:w-auto">
          <button
            onClick={() => {
              setActiveMode('supabase');
              setSelectedSheetIndex(0);
            }}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-2 ${
              activeMode === 'supabase'
                ? 'bg-[#101BCB] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#080F72] hover:bg-slate-50'
            }`}
          >
            <Cloud className="w-4 h-4" />
            <span>☁️ Plantillas Supabase Cloud</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${activeMode === 'supabase' ? 'bg-white/20 text-white' : 'bg-blue-50 text-[#101BCB]'}`}>
              {supabaseTemplates.length}
            </span>
          </button>

          <button
            onClick={() => {
              setActiveMode('local');
              setSelectedSheetIndex(0);
            }}
            className={`flex-1 sm:flex-initial px-4 py-2 rounded-xl text-xs font-bold transition flex items-center justify-center space-x-2 ${
              activeMode === 'local'
                ? 'bg-[#080F72] text-white shadow-sm'
                : 'text-[#64748B] hover:text-[#080F72] hover:bg-slate-50'
            }`}
          >
            <HardDrive className="w-4 h-4" />
            <span>📁 Almacenamiento Local</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${activeMode === 'local' ? 'bg-white/20 text-white' : 'bg-slate-100 text-[#64748B]'}`}>
              {localTemplates.length}
            </span>
          </button>
        </div>

        <div className="hidden lg:flex items-center space-x-2 text-xs text-[#64748B] pr-3">
          {activeMode === 'supabase' ? (
            <span className="flex items-center space-x-1 text-[#00A88F] font-bold">
              <ShieldCheck className="w-4 h-4" />
              <span>Plantillas seguras en Supabase Database & Storage</span>
            </span>
          ) : (
            <span className="text-[#64748B]">
              Plantillas guardadas en la carpeta local <code className="text-[#080F72]">templates/</code>
            </span>
          )}
        </div>
      </div>

      {/* Main Grid: Template List & Detailed Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Template Cards List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-1">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#64748B]">
              {activeMode === 'supabase' ? 'Plantillas en la Nube' : 'Plantillas Locales'} (
              {activeMode === 'supabase' ? supabaseTemplates.length : localTemplates.length})
            </h3>
            <button
              onClick={activeMode === 'supabase' ? loadSupabaseTemplates : loadLocalTemplates}
              className="text-xs text-[#101BCB] hover:text-[#080F72] flex items-center space-x-1 font-semibold"
            >
              <RefreshCw className={`w-3 h-3 ${(activeMode === 'supabase' ? supabaseLoading : localLoading) ? 'animate-spin' : ''}`} />
              <span>Actualizar</span>
            </button>
          </div>

          {/* Loading or Empty State */}
          {(activeMode === 'supabase' ? supabaseLoading : localLoading) ? (
            <div className="bg-white p-8 rounded-2xl border border-[#CBD5E1] text-center text-[#64748B] text-xs shadow-xs">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#101BCB]" />
              Cargando plantillas...
            </div>
          ) : (activeMode === 'supabase' ? supabaseTemplates : localTemplates).length === 0 ? (
            <div className="bg-white p-8 rounded-2xl border border-[#CBD5E1] text-center text-[#64748B] text-xs space-y-3 shadow-xs">
              <Cloud className="w-10 h-10 mx-auto text-slate-300" />
              <p className="font-bold text-[#1E293B]">
                {activeMode === 'supabase'
                  ? 'No hay plantillas en Supabase Cloud.'
                  : 'No hay plantillas locales registradas.'}
              </p>
              <p className="text-[11px] text-[#64748B]">
                {activeMode === 'supabase'
                  ? 'Sube tus plantillas para sincronizarlas permanentemente en cualquier equipo.'
                  : 'Sube un archivo .xlsx al disco local.'}
              </p>
              <button
                onClick={() => {
                  if (activeMode === 'supabase') {
                    if (!supabaseConnected) setShowConfigModal(true);
                    else setShowUploadModal(true);
                  } else {
                    localFileInputRef.current?.click();
                  }
                }}
                className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-[#101BCB] hover:bg-[#080F72] shadow-sm transition"
              >
                + Subir primera plantilla
              </button>
            </div>
          ) : (
            // Template Cards
            (activeMode === 'supabase' ? supabaseTemplates : localTemplates).map((tpl) => {
              const isSelected = activeMode === 'supabase'
                ? selectedSupabaseTemplate?.id === tpl.id
                : selectedLocalTemplate?.filename === tpl.filename;

              const title = activeMode === 'supabase' ? (tpl.name || tpl.filename) : tpl.filename;
              const subtext = activeMode === 'supabase' ? tpl.filename : `${tpl.file_size_kb} KB`;
              const version = activeMode === 'supabase' ? (tpl.version || '1.0') : 'v1.0';
              const type = activeMode === 'supabase' ? tpl.template_type : 'EXCEL_CARGA_MASIVA';

              return (
                <div
                  key={activeMode === 'supabase' ? tpl.id : tpl.filename}
                  onClick={() => {
                    if (activeMode === 'supabase') setSelectedSupabaseTemplate(tpl);
                    else setSelectedLocalTemplate(tpl);
                    setSelectedSheetIndex(0);
                  }}
                  className={`p-4 rounded-xl border transition-all cursor-pointer group relative ${
                    isSelected
                      ? 'bg-[#EEF2FF] border-[#101BCB] shadow-sm ring-1 ring-[#101BCB]/40'
                      : 'bg-white border-[#CBD5E1] hover:bg-slate-50 shadow-2xs'
                  }`}
                >
                  <div className="flex items-start justify-between space-x-2">
                    <div className="flex items-start space-x-3 min-w-0 flex-1">
                      <div className="p-2.5 rounded-lg bg-blue-50 border border-blue-200 text-[#101BCB] flex-shrink-0">
                        <FileSpreadsheet className="w-5 h-5" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-1.5">
                          <h4 className="text-xs sm:text-sm font-bold text-[#1E293B] truncate" title={title}>
                            {title}
                          </h4>
                        </div>

                        <p className="text-[11px] text-[#64748B] truncate mt-0.5" title={subtext}>
                          {subtext}
                        </p>

                        <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[10px]">
                          <span className="px-1.5 py-0.2 rounded font-mono font-extrabold bg-blue-100 text-[#101BCB] border border-blue-200">
                            v{version}
                          </span>
                          <span className={`px-1.5 py-0.2 rounded font-bold border ${getBadgeForType(type)}`}>
                            {getLabelForType(type)}
                          </span>
                          {activeMode === 'supabase' && tpl.user_name && (
                            <span className="text-slate-500 font-medium">
                              👤 {tpl.user_name}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Quick Card Delete Button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setTemplateToDelete(tpl);
                        setShowDeleteModal(true);
                      }}
                      className="opacity-70 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-50 text-slate-400 hover:text-[#DC2626] transition"
                      title="Eliminar plantilla"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Template Inspector & Column Mapper */}
        <div className="lg:col-span-2">
          {activeTemplate ? (
            <div className="bg-white p-4 sm:p-5 rounded-2xl border border-[#CBD5E1] shadow-xs space-y-4">
              
              {/* Template Top Header & Action Toolbar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#E2E8F0]">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[10px] font-bold text-[#101BCB] uppercase tracking-wider block">
                      {activeMode === 'supabase' ? 'Plantilla Supabase Cloud' : 'Plantilla Local'}
                    </span>
                    <span className="text-[10px] text-slate-400">•</span>
                    <span className="text-[10px] text-[#64748B] font-mono">
                      {activeTemplate.file_size_kb || 0} KB
                    </span>
                    {activeMode === 'supabase' && (
                      <>
                        <span className="text-[10px] text-slate-400">•</span>
                        <span className="text-[10px] px-1.5 py-0.2 rounded font-bold bg-blue-100 text-[#101BCB]">
                          Versión: {activeTemplate.version || '1.0'}
                        </span>
                      </>
                    )}
                  </div>

                  {/* Title & Selector */}
                  <h3 className="text-base font-black text-[#080F72] mt-1 truncate">
                    {activeMode === 'supabase' ? (activeTemplate.name || activeTemplate.filename) : activeTemplate.filename}
                  </h3>
                  <p className="text-[11px] text-[#64748B] font-mono mt-0.5">
                    Archivo: {activeTemplate.filename}
                  </p>
                </div>

                {/* Toolbar: Download, Replace, Edit Metadata, Delete */}
                <div className="flex flex-wrap items-center gap-1.5 flex-shrink-0">
                  
                  {/* Download Original File */}
                  <a
                    href={
                      activeMode === 'supabase'
                        ? api.supabase.getDownloadUrl(activeTemplate.id)
                        : api.getTemplateDownloadUrl(activeTemplate.filename)
                    }
                    download={activeTemplate.filename}
                    className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-[#080F72] border border-[#CBD5E1] text-xs font-bold flex items-center space-x-1.5 transition shadow-2xs"
                    title="Descargar archivo Excel original"
                  >
                    <Download className="w-3.5 h-3.5 text-[#101BCB]" />
                    <span className="hidden sm:inline">Descargar</span>
                  </a>

                  {/* Replace / Upload New Version */}
                  <button
                    onClick={() => replaceFileInputRef.current?.click()}
                    disabled={isUploading}
                    className="p-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-[#166534] border border-emerald-200 text-xs font-bold flex items-center space-x-1.5 transition shadow-2xs"
                    title="Reemplazar archivo Excel (incrementará la versión)"
                  >
                    <FileUp className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Reemplazar</span>
                  </button>

                  {/* Edit Metadata / Rename */}
                  <button
                    onClick={() => {
                      if (activeMode === 'supabase') {
                        setEditMetaForm({
                          name: activeTemplate.name || '',
                          template_type: activeTemplate.template_type || 'EXCEL_CARGA_MASIVA',
                          version: activeTemplate.version || '1.0',
                          user_name: activeTemplate.user_name || '',
                        });
                      } else {
                        setEditMetaForm({
                          name: activeTemplate.filename,
                          template_type: 'EXCEL_CARGA_MASIVA',
                          version: '1.0',
                          user_name: '',
                        });
                      }
                      setShowRenameModal(true);
                    }}
                    className="p-2 rounded-xl bg-blue-50 hover:bg-blue-100 text-[#2563EB] border border-blue-200 text-xs font-bold flex items-center space-x-1.5 transition shadow-2xs"
                    title="Editar metadatos y nombre"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Editar</span>
                  </button>

                  {/* Delete Template */}
                  <button
                    onClick={() => {
                      setTemplateToDelete(activeTemplate);
                      setShowDeleteModal(true);
                    }}
                    className="p-2 rounded-xl bg-red-50 hover:bg-red-100 text-[#DC2626] border border-red-200 text-xs font-bold flex items-center space-x-1.5 transition shadow-2xs"
                    title="Eliminar plantilla"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Eliminar</span>
                  </button>

                </div>
              </div>

              {/* Sheet Selector Tabs */}
              {activeSheetsList.length > 1 && (
                <div className="flex items-center space-x-1 bg-[#F8FAFC] p-1.5 rounded-xl border border-[#CBD5E1] overflow-x-auto">
                  {activeSheetsList.map((s, idx) => (
                    <button
                      key={s.sheet_name || idx}
                      onClick={() => setSelectedSheetIndex(idx)}
                      className={`px-3.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition ${
                        selectedSheetIndex === idx
                          ? 'bg-[#101BCB] text-white shadow-sm'
                          : 'text-[#64748B] hover:text-[#080F72]'
                      }`}
                    >
                      📄 Hoja: {s.sheet_name}
                    </button>
                  ))}
                </div>
              )}

              {/* Sheet Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#CBD5E1]">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Hoja Activa</span>
                  <span className="text-xs font-bold text-[#080F72] truncate block">
                    {activeSheet?.sheet_name || 'N/A'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#CBD5E1]">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Columnas</span>
                  <span className="text-xs font-bold text-[#101BCB] block">
                    {activeSheet?.total_columns || activeSheet?.headers?.length || 0}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#CBD5E1]">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Cols. Amarillas</span>
                  <span className="text-xs font-bold text-amber-600 block">
                    🟡 {activeSheet?.yellow_columns_count || 0} detectadas
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#CBD5E1]">
                  <span className="text-[10px] text-[#64748B] uppercase font-bold block">Campos Asignados</span>
                  <span className="text-xs font-bold text-[#166534] block">
                    {Object.values(editedMappings).filter((v) => v && v !== 'none').length} campos
                  </span>
                </div>
              </div>

              {/* Column Mapping Section */}
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h4 className="text-xs font-bold text-[#080F72] uppercase tracking-wider flex items-center space-x-1.5">
                      <Sliders className="w-3.5 h-3.5 text-[#101BCB]" />
                      <span>Editor de Mapeo de Columnas ({activeMode === 'supabase' ? 'Supabase Database' : 'Local'})</span>
                    </h4>
                    <p className="text-[11px] text-[#64748B]">
                      Asigna qué dato del DNI se insertará en cada columna del Excel al procesar un lote.
                    </p>
                  </div>

                  {hasUnsavedMappings && (
                    <button
                      onClick={handleSaveMappings}
                      disabled={isSavingMapping}
                      className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-[#16A34A] hover:bg-[#15803d] text-white shadow-md transition active:scale-95"
                    >
                      {isSavingMapping ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      <span>Guardar Mapeo</span>
                    </button>
                  )}
                </div>

                <div className="max-h-[380px] overflow-y-auto rounded-xl border border-[#CBD5E1] bg-white divide-y divide-[#E2E8F0]">
                  {activeSheet?.headers && activeSheet.headers.length > 0 ? (
                    activeSheet.headers.map((h, i) => {
                      const colIndex = i + 1;
                      const selectedField = editedMappings[colIndex] || 'none';
                      const isAssigned = selectedField && selectedField !== 'none';
                      const isYellow = activeSheet.yellow_columns?.includes(colIndex);

                      return (
                        <div
                          key={i}
                          className={`p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs transition ${
                            isAssigned ? 'bg-blue-50/30 hover:bg-blue-50/60' : 'hover:bg-[#F8FAFC]'
                          }`}
                        >
                          <div className="flex items-center space-x-3 min-w-[200px]">
                            <span className="w-6 h-6 rounded-md bg-slate-100 text-[#080F72] font-mono text-[10px] flex items-center justify-center font-bold flex-shrink-0">
                              {colIndex}
                            </span>
                            <div className="min-w-0">
                              <span className="font-semibold text-[#1E293B] block truncate">{h}</span>
                              {isYellow && (
                                <span className="text-[10px] text-amber-700 font-bold flex items-center space-x-1">
                                  <span>🟡 Columna con celda amarilla detectada</span>
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center space-x-2 w-full sm:w-auto">
                            <select
                              value={selectedField}
                              onChange={(e) => handleMappingChange(colIndex, e.target.value)}
                              className={`w-full sm:w-64 px-3 py-1.5 rounded-lg text-xs font-medium border focus:outline-none transition ${
                                isAssigned
                                  ? 'bg-[#DCFCE7] border-[#86EFAC] text-[#166534] font-bold focus:border-[#16A34A]'
                                  : 'bg-white border-[#CBD5E1] text-[#64748B] focus:border-[#101BCB]'
                              }`}
                            >
                              {AVAILABLE_DNI_FIELDS.map((f) => (
                                <option key={f.key} value={f.key}>
                                  {f.label}
                                </option>
                              ))}
                            </select>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-6 text-center text-xs text-[#64748B]">
                      No se encontraron encabezados legibles en esta hoja.
                    </div>
                  )}
                </div>

                {hasUnsavedMappings && (
                  <div className="flex items-center justify-between p-3 rounded-xl bg-[#FEF3C7] border border-[#FDE68A] text-[#92400E] text-xs">
                    <span>Tienes cambios de mapeo sin guardar.</span>
                    <button
                      onClick={handleSaveMappings}
                      disabled={isSavingMapping}
                      className="px-3 py-1 rounded-lg bg-[#16A34A] hover:bg-[#15803d] text-white font-bold text-xs transition"
                    >
                      {isSavingMapping ? 'Guardando...' : 'Guardar Cambios'}
                    </button>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="bg-white p-12 rounded-2xl border border-[#CBD5E1] text-center text-[#64748B] shadow-2xs">
              Seleccione una plantilla para ver o editar su estructura y columnas.
            </div>
          )}
        </div>

      </div>

      {/* ============================================================ */}
      {/* MODAL: SUBIR PLANTILLA A SUPABASE */}
      {/* ============================================================ */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#CBD5E1] rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
              <div className="flex items-center space-x-2 text-[#080F72] font-bold text-sm">
                <UploadCloud className="w-5 h-5 text-[#101BCB]" />
                <span>Subir Plantilla a Supabase Cloud</span>
              </div>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-[#64748B] hover:text-[#1E293B] p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleUploadSupabase} className="space-y-3.5 text-xs">
              {/* Name */}
              <div className="space-y-1">
                <label className="font-bold text-[#1E293B] block">Nombre Descriptivo de la Plantilla</label>
                <input
                  type="text"
                  value={uploadForm.name}
                  onChange={(e) => setUploadForm({ ...uploadForm, name: e.target.value })}
                  placeholder="Ej. Carga Masiva T-Registro 2026"
                  className="w-full px-3.5 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                  required
                />
              </div>

              {/* Type */}
              <div className="space-y-1">
                <label className="font-bold text-[#1E293B] block">Tipo de Plantilla</label>
                <select
                  value={uploadForm.template_type}
                  onChange={(e) => setUploadForm({ ...uploadForm, template_type: e.target.value })}
                  className="w-full px-3.5 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                >
                  {TEMPLATE_TYPES.map((t) => (
                    <option key={t.key} value={t.key}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Version & User in 2 cols */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-bold text-[#1E293B] block">Versión Inicial</label>
                  <input
                    type="text"
                    value={uploadForm.version}
                    onChange={(e) => setUploadForm({ ...uploadForm, version: e.target.value })}
                    placeholder="1.0"
                    className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-[#1E293B] block">Usuario Responsable</label>
                  <input
                    type="text"
                    value={uploadForm.user_name}
                    onChange={(e) => setUploadForm({ ...uploadForm, user_name: e.target.value })}
                    placeholder="Flavio Monzón"
                    className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                  />
                </div>
              </div>

              {/* File Input */}
              <div className="space-y-1 pt-1">
                <label className="font-bold text-[#1E293B] block">Archivo Excel (.xlsx)</label>
                <input
                  type="file"
                  ref={uploadFileInputRef}
                  onChange={(e) => setUploadForm({ ...uploadForm, file: e.target.files?.[0] || null })}
                  accept=".xlsx"
                  className="w-full px-3 py-2 rounded-xl bg-slate-50 border border-[#CBD5E1] text-[#1E293B] text-xs file:mr-2 file:py-1 file:px-2.5 file:rounded-lg file:border-0 file:text-xs file:font-bold file:bg-blue-50 file:text-[#101BCB] hover:file:bg-blue-100"
                  required
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-[#E2E8F0]">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[#64748B] hover:text-[#1E293B] bg-slate-100 hover:bg-slate-200 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadForm.file}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#101BCB] hover:bg-[#080F72] shadow-sm transition flex items-center space-x-1.5"
                >
                  {isUploading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span>Subir y Guardar en Supabase</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL: EDITAR METADATOS / RENOMBRAR */}
      {/* ============================================================ */}
      {showRenameModal && activeTemplate && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#CBD5E1] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
              <div className="flex items-center space-x-2 text-[#080F72] font-bold text-sm">
                <Edit3 className="w-4 h-4 text-[#101BCB]" />
                <span>{activeMode === 'supabase' ? 'Editar Metadatos de la Plantilla' : 'Renombrar Plantilla'}</span>
              </div>
              <button
                onClick={() => setShowRenameModal(false)}
                className="text-[#64748B] hover:text-[#1E293B] p-1 rounded-lg hover:bg-slate-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveMetadata} className="space-y-3.5 text-xs">
              <div className="space-y-1">
                <label className="font-bold text-[#1E293B] block">
                  {activeMode === 'supabase' ? 'Nombre Descriptivo' : 'Nombre de archivo (.xlsx)'}
                </label>
                <input
                  type="text"
                  value={editMetaForm.name}
                  onChange={(e) => setEditMetaForm({ ...editMetaForm, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs focus:outline-none focus:border-[#101BCB] font-bold"
                  required
                />
              </div>

              {activeMode === 'supabase' && (
                <>
                  <div className="space-y-1">
                    <label className="font-bold text-[#1E293B] block">Tipo de Plantilla</label>
                    <select
                      value={editMetaForm.template_type}
                      onChange={(e) => setEditMetaForm({ ...editMetaForm, template_type: e.target.value })}
                      className="w-full px-3.5 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                    >
                      {TEMPLATE_TYPES.map((t) => (
                        <option key={t.key} value={t.key}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="font-bold text-[#1E293B] block">Versión</label>
                      <input
                        type="text"
                        value={editMetaForm.version}
                        onChange={(e) => setEditMetaForm({ ...editMetaForm, version: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="font-bold text-[#1E293B] block">Usuario</label>
                      <input
                        type="text"
                        value={editMetaForm.user_name}
                        onChange={(e) => setEditMetaForm({ ...editMetaForm, user_name: e.target.value })}
                        className="w-full px-3 py-2 rounded-xl bg-white border border-[#CBD5E1] text-[#1E293B] text-xs font-semibold focus:outline-none focus:border-[#101BCB]"
                      />
                    </div>
                  </div>
                </>
              )}

              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-[#E2E8F0]">
                <button
                  type="button"
                  onClick={() => setShowRenameModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-[#64748B] hover:text-[#1E293B] bg-slate-100 hover:bg-slate-200 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isEditingMeta || !editMetaForm.name.trim()}
                  className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#101BCB] hover:bg-[#080F72] shadow-sm transition flex items-center space-x-1.5"
                >
                  {isEditingMeta ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span>Guardar Cambios</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* MODAL: ELIMINAR PLANTILLA */}
      {/* ============================================================ */}
      {showDeleteModal && templateToDelete && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white border border-[#FCA5A5] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-scale-in">
            <div className="flex items-center space-x-3 text-[#DC2626] pb-2 border-b border-[#E2E8F0]">
              <div className="p-2 rounded-xl bg-red-50 border border-red-200">
                <AlertTriangle className="w-5 h-5 text-[#DC2626]" />
              </div>
              <h3 className="text-sm font-bold text-[#1E293B]">¿Eliminar esta plantilla?</h3>
            </div>

            <p className="text-xs text-[#64748B] leading-relaxed">
              ¿Está seguro de que desea eliminar la plantilla{' '}
              <strong className="text-[#1E293B] font-mono">
                {templateToDelete.name || templateToDelete.filename}
              </strong>
              {activeMode === 'supabase'
                ? ' de Supabase Storage y Base de Datos?'
                : ' del disco local?'}
            </p>

            <div className="flex items-center justify-end space-x-2 pt-3">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setTemplateToDelete(null);
                }}
                disabled={isUploading}
                className="px-4 py-2 rounded-xl text-xs font-bold text-[#64748B] hover:text-[#1E293B] bg-slate-100 hover:bg-slate-200 transition"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleDeleteTemplate}
                disabled={isUploading}
                className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#DC2626] hover:bg-red-700 shadow-sm transition flex items-center space-x-1.5"
              >
                {isUploading ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                <span>Eliminar Definitivamente</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Supabase Configuration Modal Component */}
      <SupabaseConfigModal
        isOpen={showConfigModal}
        onClose={() => setShowConfigModal(false)}
        onConfigSaved={() => {
          loadAllData();
        }}
      />

    </div>
  );
}
