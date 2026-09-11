import React, { useState, useEffect } from 'react';
import {
  Cloud,
  Database,
  Key,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  X,
  Copy,
  Check,
  Server,
  HardDrive,
  ExternalLink,
  ShieldCheck,
  Save,
  HelpCircle,
} from 'lucide-react';
import { api } from '../services/api';

const SQL_SCHEMA_SCRIPT = `-- 1. Crear tabla para plantillas Excel / Documentos en Supabase
create table if not exists public.excel_templates (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    filename text not null,
    template_type text default 'EXCEL_CARGA_MASIVA',
    version text default '1.0',
    storage_path text not null,
    file_size_kb numeric default 0,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
    user_name text default 'Flavio Monzón',
    sheets_metadata jsonb default '[]'::jsonb,
    is_active boolean default true
);

-- 2. Asegurar que el bucket de almacenamiento exista
insert into storage.buckets (id, name, public)
values ('templates', 'templates', true)
on conflict (id) do nothing;

-- 3. Políticas de acceso (RLS) abiertas para la app
alter table public.excel_templates enable row level security;

create policy "Permitir todo a usuarios autenticados y anon"
on public.excel_templates for all
using (true)
with check (true);

create policy "Permitir acceso a bucket templates"
on storage.objects for all
using (bucket_id = 'templates')
with check (bucket_id = 'templates');`;

export default function SupabaseConfigModal({ isOpen, onClose, onConfigSaved }) {
  const [url, setUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [bucketName, setBucketName] = useState('templates');

  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [copiedSql, setCopiedSql] = useState(false);
  const [showSqlGuide, setShowSqlGuide] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadCurrentConfig();
    }
  }, [isOpen]);

  const loadCurrentConfig = async () => {
    setLoading(true);
    setTestResult(null);
    setSaveSuccessMsg(null);
    try {
      const data = await api.supabase.getConfig();
      if (data) {
        setUrl(data.url || '');
        setApiKey(data.key || '');
        setBucketName(data.bucket_name || 'templates');
      }
    } catch (err) {
      console.error('Error fetching Supabase config:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTestConnection = async () => {
    if (!url.trim() || !apiKey.trim()) {
      setTestResult({
        success: false,
        message: 'Por favor ingrese la URL del proyecto y el API Key de Supabase.',
      });
      return;
    }

    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await api.supabase.testConnection({
        url: url.trim(),
        key: apiKey.trim(),
        bucket_name: bucketName.trim() || 'templates',
      });
      setTestResult(res);
    } catch (err) {
      console.error('Error testing Supabase connection:', err);
      setTestResult({
        success: false,
        message: err.response?.data?.detail || 'No se pudo conectar con Supabase. Verifique las credenciales.',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    setIsSaving(true);
    setSaveSuccessMsg(null);
    try {
      const res = await api.supabase.saveConfig({
        url: url.trim(),
        key: apiKey.trim(),
        bucket_name: bucketName.trim() || 'templates',
      });
      setSaveSuccessMsg('¡Configuración de Supabase guardada correctamente!');
      if (onConfigSaved) onConfigSaved();
      setTimeout(() => {
        setSaveSuccessMsg(null);
        onClose();
      }, 1500);
    } catch (err) {
      console.error('Error saving Supabase config:', err);
      alert(err.response?.data?.detail || 'Error al guardar la configuración.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopySql = () => {
    navigator.clipboard.writeText(SQL_SCHEMA_SCRIPT);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 3000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white border border-[#CBD5E1] rounded-2xl max-w-2xl w-full p-6 space-y-5 shadow-2xl animate-scale-in max-h-[92vh] overflow-y-auto">
        
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-[#E2E8F0]">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-blue-50 border border-blue-200 text-[#101BCB]">
              <Cloud className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-[#080F72] flex items-center space-x-2">
                <span>Configuración de Supabase Cloud</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-[#00A88F] border border-emerald-200 font-extrabold uppercase">
                  Gestión de Plantillas
                </span>
              </h3>
              <p className="text-xs text-[#64748B] mt-0.5">
                Conecta tu proyecto Supabase para guardar plantillas en la nube y acceder a ellas desde cualquier equipo o navegador.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-[#64748B] hover:text-[#1E293B] p-1.5 rounded-lg hover:bg-slate-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Success Alert */}
        {saveSuccessMsg && (
          <div className="p-3.5 rounded-xl bg-[#DCFCE7] border border-[#86EFAC] text-[#166534] text-xs font-bold flex items-center space-x-2 animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0" />
            <span>{saveSuccessMsg}</span>
          </div>
        )}

        {/* Test Result Alert */}
        {testResult && (
          <div
            className={`p-4 rounded-xl border text-xs leading-relaxed animate-fade-in ${
              testResult.success
                ? 'bg-[#DCFCE7] border-[#86EFAC] text-[#166534]'
                : 'bg-[#FEF2F2] border-[#FCA5A5] text-[#991B1B]'
            }`}
          >
            <div className="flex items-center space-x-2 font-bold mb-1">
              {testResult.success ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-[#16A34A]" />
                  <span>Conexión Exitosa con Supabase</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-4 h-4 text-[#DC2626]" />
                  <span>Fallo de Conexión</span>
                </>
              )}
            </div>
            <p className="mt-0.5">{testResult.message}</p>
            {testResult.total_templates !== undefined && (
              <p className="text-[11px] text-emerald-800 mt-1 font-semibold">
                📊 Plantillas encontradas en Supabase: {testResult.total_templates}
              </p>
            )}
          </div>
        )}

        {/* Form Inputs */}
        <form onSubmit={handleSave} className="space-y-4 text-xs">
          
          {/* Supabase URL */}
          <div className="space-y-1">
            <label className="font-bold text-[#1E293B] flex items-center space-x-1.5">
              <Server className="w-3.5 h-3.5 text-[#101BCB]" />
              <span>URL del Proyecto Supabase</span>
            </label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://xyzabcdefghijklm.supabase.co"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-[#CBD5E1] text-[#1E293B] font-mono focus:outline-none focus:border-[#101BCB] focus:bg-white text-xs transition"
              required
            />
            <span className="text-[11px] text-[#64748B]">
              Se encuentra en: Supabase Dashboard &gt; Project Settings &gt; API &gt; Project URL.
            </span>
          </div>

          {/* Supabase API Key */}
          <div className="space-y-1">
            <label className="font-bold text-[#1E293B] flex items-center space-x-1.5">
              <Key className="w-3.5 h-3.5 text-[#101BCB]" />
              <span>API Key (anon / service_role)</span>
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
              className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-[#CBD5E1] text-[#1E293B] font-mono focus:outline-none focus:border-[#101BCB] focus:bg-white text-xs transition"
              required
            />
            <span className="text-[11px] text-[#64748B]">
              Se encuentra en: Supabase Dashboard &gt; Project Settings &gt; API &gt; Project API keys (anon public o service_role).
            </span>
          </div>

          {/* Storage Bucket */}
          <div className="space-y-1">
            <label className="font-bold text-[#1E293B] flex items-center space-x-1.5">
              <HardDrive className="w-3.5 h-3.5 text-[#101BCB]" />
              <span>Nombre del Bucket de Storage</span>
            </label>
            <input
              type="text"
              value={bucketName}
              onChange={(e) => setBucketName(e.target.value)}
              placeholder="templates"
              className="w-full px-3.5 py-2 rounded-xl bg-slate-50 border border-[#CBD5E1] text-[#1E293B] font-mono focus:outline-none focus:border-[#101BCB] focus:bg-white text-xs transition"
              required
            />
            <span className="text-[11px] text-[#64748B]">
              Bucket en Supabase Storage donde se guardarán los archivos binarios (.xlsx / .docx). Por defecto: <code className="text-[#080F72] font-bold">templates</code>.
            </span>
          </div>

          {/* SQL Setup Helper Accordion */}
          <div className="border border-[#CBD5E1] rounded-xl overflow-hidden bg-slate-50">
            <button
              type="button"
              onClick={() => setShowSqlGuide(!showSqlGuide)}
              className="w-full p-3 flex items-center justify-between text-left text-xs font-bold text-[#080F72] hover:bg-slate-100 transition"
            >
              <div className="flex items-center space-x-2">
                <HelpCircle className="w-4 h-4 text-[#101BCB]" />
                <span>¿Primera vez configurando Supabase? Ver Script SQL para crear la tabla y bucket</span>
              </div>
              <span className="text-[11px] text-[#101BCB]">{showSqlGuide ? 'Ocultar ▲' : 'Ver Script ▼'}</span>
            </button>

            {showSqlGuide && (
              <div className="p-3.5 border-t border-[#CBD5E1] bg-slate-900 text-slate-100 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-slate-300 font-mono">SQL Editor en Supabase Dashboard:</span>
                  <button
                    type="button"
                    onClick={handleCopySql}
                    className="px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] flex items-center space-x-1.5 transition"
                  >
                    {copiedSql ? <Check className="w-3 h-3 text-white" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedSql ? '¡Copiado!' : 'Copiar SQL'}</span>
                  </button>
                </div>
                <pre className="text-[10px] font-mono text-emerald-400 bg-slate-950 p-2.5 rounded-lg overflow-x-auto max-h-48 border border-slate-800">
                  {SQL_SCHEMA_SCRIPT}
                </pre>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2.5 pt-3 border-t border-[#E2E8F0]">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={isTesting || !url.trim() || !apiKey.trim()}
              className="w-full sm:w-auto px-4 py-2 rounded-xl text-xs font-bold text-[#080F72] bg-blue-50 hover:bg-blue-100 border border-blue-200 transition flex items-center justify-center space-x-1.5"
            >
              {isTesting ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#101BCB]" />
              ) : (
                <ShieldCheck className="w-3.5 h-3.5 text-[#101BCB]" />
              )}
              <span>Probar Conexión</span>
            </button>

            <div className="flex items-center space-x-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-bold text-[#64748B] hover:text-[#1E293B] bg-slate-100 hover:bg-slate-200 transition"
              >
                Cerrar
              </button>
              <button
                type="submit"
                disabled={isSaving || !url.trim() || !apiKey.trim()}
                className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#101BCB] hover:bg-[#080F72] shadow-sm transition flex items-center justify-center space-x-1.5"
              >
                {isSaving ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Save className="w-3.5 h-3.5" />
                )}
                <span>Guardar Configuración</span>
              </button>
            </div>
          </div>

        </form>

      </div>
    </div>
  );
}
