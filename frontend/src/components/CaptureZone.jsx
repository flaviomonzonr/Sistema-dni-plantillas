import React, { useState, useRef } from 'react';
import {
  Upload,
  Camera,
  FileCheck,
  X,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CreditCard,
  RefreshCw,
  Eye,
  CheckCircle2,
  FileText,
  Scan,
  FileSearch,
} from 'lucide-react';
import CameraModal from './CameraModal';

export default function CaptureZone({
  docType,
  setDocType,
  frontFile,
  setFrontFile,
  frontPreview,
  setFrontPreview,
  backFile,
  setBackFile,
  backPreview,
  setBackPreview,
  onStartScan,
  isScanning,
  scanStep,
}) {
  const [activeCameraSide, setActiveCameraSide] = useState(null); // 'front' | 'back' | null
  const frontInputRef = useRef(null);
  const backInputRef = useRef(null);

  // Handle file select
  const handleFileChange = (e, side) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const previewUrl = URL.createObjectURL(file);
    if (side === 'front') {
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontFile(file);
      setFrontPreview(previewUrl);
    } else {
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackFile(file);
      setBackPreview(previewUrl);
    }
  };

  // Drag & drop handlers
  const handleDrop = (e, side) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    const previewUrl = URL.createObjectURL(file);
    if (side === 'front') {
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontFile(file);
      setFrontPreview(previewUrl);
    } else {
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackFile(file);
      setBackPreview(previewUrl);
    }
  };

  const handleCameraCapture = (file, previewUrl) => {
    if (activeCameraSide === 'front') {
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontFile(file);
      setFrontPreview(previewUrl);
    } else if (activeCameraSide === 'back') {
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackFile(file);
      setBackPreview(previewUrl);
    }
  };

  const removeImage = (side) => {
    if (side === 'front') {
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontFile(null);
      setFrontPreview(null);
      if (frontInputRef.current) frontInputRef.current.value = '';
    } else {
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackFile(null);
      setBackPreview(null);
      if (backInputRef.current) backInputRef.current.value = '';
    }
  };

  // Generator for synthetic testing sample cards (Casos A to L)
  const loadDemoScenario = (scenarioKey) => {
    let type = 'DNI';
    let docNum = '47895623';
    let patSur = 'RODRIGUEZ';
    let matSur = 'MENDOZA';
    let fNames = 'CARLOS EDUARDO';
    let birth = '18/09/1993';
    let sex = 'M';
    let isDnie = false;
    let applyShadow = false;
    let applyNoise = false;
    let applyAngle = false;

    if (scenarioKey === 'DNI_AZUL') {
      type = 'DNI';
      docNum = '42694271';
      patSur = 'QUISPE';
      matSur = 'MAMANI';
      fNames = 'JUAN CARLOS';
    } else if (scenarioKey === 'DNI_SHADOW') {
      type = 'DNI';
      docNum = '71829304';
      patSur = 'FLORES';
      matSur = 'GUTIERREZ';
      fNames = 'MARIA ELENA';
      applyShadow = true;
    } else if (scenarioKey === 'DNI_NOISY') {
      type = 'DNI';
      docNum = '10928374';
      patSur = 'VARGAS';
      matSur = 'TORRES';
      fNames = 'PEDRO LUIS';
      applyNoise = true;
    } else if (scenarioKey === 'DNIE_MRZ') {
      type = 'DNI';
      isDnie = true;
      docNum = '75849302';
      patSur = 'SANCHEZ';
      matSur = 'ALVAREZ';
      fNames = 'ANA LUCIA';
    } else if (scenarioKey === 'CARNET_EXT') {
      type = 'Carnet de Extranjería';
      docNum = '002345891';
      patSur = 'GONZALEZ';
      matSur = 'HERNANDEZ';
      fNames = 'GABRIEL ALEJANDRO';
      birth = '22/04/1990';
    } else if (scenarioKey === 'DNI_SKEWED') {
      type = 'DNI';
      docNum = '48392019';
      patSur = 'CHAVEZ';
      matSur = 'CASTILLO';
      fNames = 'LUIS ALBERTO';
      applyAngle = true;
    }

    setDocType(type);

    // Create front canvas sample
    const frontCanvas = document.createElement('canvas');
    frontCanvas.width = 1014;
    frontCanvas.height = 640;
    const fctx = frontCanvas.getContext('2d');

    if (applyAngle) {
      fctx.translate(507, 320);
      fctx.rotate((3.5 * Math.PI) / 180);
      fctx.translate(-507, -320);
    }

    // Card background
    fctx.fillStyle = isDnie ? '#e2e8f0' : '#85c1e9';
    fctx.fillRect(40, 30, 934, 580);

    // Header banner
    fctx.fillStyle = isDnie ? '#334155' : '#1b4f72';
    fctx.fillRect(40, 30, 934, 90);
    fctx.fillStyle = '#ffffff';
    fctx.font = 'bold 26px sans-serif';
    fctx.fillText('REPUBLICA DEL PERU', 180, 70);
    fctx.font = 'bold 20px sans-serif';
    fctx.fillText('REGISTRO NACIONAL DE IDENTIFICACION Y ESTADO CIVIL', 180, 100);

    // Photo rectangle
    fctx.fillStyle = '#cbd5e1';
    fctx.fillRect(80, 160, 240, 320);
    fctx.fillStyle = '#475569';
    fctx.font = 'bold 18px sans-serif';
    fctx.fillText('FOTO DNI', 150, 320);

    // Fields
    fctx.fillStyle = '#0f172a';
    fctx.font = 'bold 18px sans-serif';
    fctx.fillText('NUMERO DE DNI', 380, 175);
    fctx.font = 'bold 36px monospace';
    fctx.fillText(docNum, 380, 220);

    fctx.font = 'bold 16px sans-serif';
    fctx.fillText('PRIMER APELLIDO', 380, 265);
    fctx.font = 'bold 24px sans-serif';
    fctx.fillText(patSur, 380, 295);

    fctx.font = 'bold 16px sans-serif';
    fctx.fillText('SEGUNDO APELLIDO', 380, 335);
    fctx.font = 'bold 24px sans-serif';
    fctx.fillText(matSur, 380, 365);

    fctx.font = 'bold 16px sans-serif';
    fctx.fillText('PRENOMBRES', 380, 405);
    fctx.font = 'bold 24px sans-serif';
    fctx.fillText(fNames, 380, 435);

    fctx.font = 'bold 16px sans-serif';
    fctx.fillText('FECHA DE NACIMIENTO', 380, 475);
    fctx.font = 'bold 22px monospace';
    fctx.fillText(birth, 380, 505);

    fctx.font = 'bold 16px sans-serif';
    fctx.fillText('SEXO', 660, 475);
    fctx.font = 'bold 22px sans-serif';
    fctx.fillText(sex, 660, 505);

    // Simulate shadow if requested
    if (applyShadow) {
      const grad = fctx.createLinearGradient(0, 0, 1014, 640);
      grad.addColorStop(0, 'rgba(0,0,0,0.6)');
      grad.addColorStop(0.6, 'rgba(0,0,0,0.1)');
      grad.addColorStop(1, 'rgba(255,255,255,0)');
      fctx.fillStyle = grad;
      fctx.fillRect(0, 0, 1014, 640);
    }

    // Create back canvas sample
    const backCanvas = document.createElement('canvas');
    backCanvas.width = 1014;
    backCanvas.height = 640;
    const bctx = backCanvas.getContext('2d');

    bctx.fillStyle = isDnie ? '#e2e8f0' : '#85c1e9';
    bctx.fillRect(40, 30, 934, 580);

    bctx.fillStyle = '#0f172a';
    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('DOMICILIO / DIRECCION', 80, 90);
    bctx.font = 'bold 20px sans-serif';
    bctx.fillText('AV. TUPAC AMARU 2450 INT. 4B', 80, 120);

    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('UBIGEO (DPTO / PROV / DIST)', 80, 170);
    bctx.font = 'bold 20px sans-serif';
    bctx.fillText('LIMA / LIMA / INDEPENDENCIA (150112)', 80, 200);

    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('FECHA DE EMISION', 80, 250);
    bctx.font = 'bold 20px monospace';
    bctx.fillText('10/05/2021', 80, 280);

    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('FECHA DE VENCIMIENTO', 360, 250);
    bctx.font = 'bold 20px monospace';
    bctx.fillText('10/05/2029', 360, 280);

    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('ESTADO CIVIL', 640, 250);
    bctx.font = 'bold 20px sans-serif';
    bctx.fillText('SOLTERO', 640, 280);

    bctx.font = 'bold 16px sans-serif';
    bctx.fillText('GRUPO SANGUINEO', 80, 330);
    bctx.font = 'bold 20px sans-serif';
    bctx.fillText('O+', 80, 360);

    // MRZ Zone for DNIe
    bctx.fillStyle = '#f8fafc';
    bctx.fillRect(80, 420, 850, 160);
    bctx.fillStyle = '#0f172a';
    bctx.font = 'bold 26px monospace';
    bctx.fillText(`I<PER${docNum}<9<<<<<<<<<<<<<<<`, 100, 475);
    bctx.fillText(`9309185M2905101PER<<<<<<<<<<<6`, 100, 520);
    bctx.fillText(`${patSur}<<${fNames}<<<<<<<<`, 100, 565);

    // Convert canvases to Blob & File
    frontCanvas.toBlob((fBlob) => {
      const fFile = new File([fBlob], `demo_${scenarioKey.toLowerCase()}_front.jpg`, { type: 'image/jpeg' });
      setFrontFile(fFile);
      setFrontPreview(URL.createObjectURL(fBlob));
    }, 'image/jpeg', 0.95);

    backCanvas.toBlob((bBlob) => {
      const bFile = new File([bBlob], `demo_${scenarioKey.toLowerCase()}_back.jpg`, { type: 'image/jpeg' });
      setBackFile(bFile);
      setBackPreview(URL.createObjectURL(bBlob));
    }, 'image/jpeg', 0.95);
  };

  const canScan = Boolean(frontFile || backFile) && !isScanning;

  return (
    <div className="space-y-4 animate-fade-in">
      
      {/* ============================================================ */}
      {/* 1. HERO BANNER (Sleek, Modern & High-Tech Banner) */}
      {/* ============================================================ */}
      <div className="relative rounded-2xl px-5 py-3.5 sm:px-6 sm:py-4 overflow-hidden shadow-lg bg-gradient-to-r from-[#003B95] via-[#0D47A1] to-[#051C48] text-white">
        
        {/* Subtle decorative circles/watermark */}
        <div className="absolute -right-10 -bottom-10 w-64 h-64 rounded-full bg-cyan-400/10 blur-2xl pointer-events-none"></div>
        <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-10 pointer-events-none hidden lg:block">
          <CreditCard className="w-48 h-48 text-white" />
        </div>

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          
          {/* Left Title & Scanner Icon Box */}
          <div className="flex items-center space-x-4 flex-1">
            {/* Sleek Glowing Scanner Icon Box */}
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#1E60FF] to-[#0A3BB2] flex items-center justify-center text-white border-2 border-cyan-400 shadow-md shadow-cyan-500/20 flex-shrink-0">
              <Scan className="w-6 h-6 text-cyan-200" />
            </div>

            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-lg sm:text-xl font-black text-white tracking-tight">
                  Escaneo de DNI y Carnet de Extranjería
                </h2>
                <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#00A88F]/30 text-[#00E5BC] border border-[#00E5BC]/30">
                  Alta Precisión
                </span>
              </div>
              <p className="text-xs text-blue-100/90 mt-0.5 max-w-2xl leading-normal">
                Suba el anverso y reverso del DNI: <strong>detección automática de 4 bordes</strong>, corrección de perspectiva y extracción OCR directa para plantillas Excel.
              </p>
            </div>
          </div>

          {/* Right Floating Badge Card */}
          <div className="flex-shrink-0">
            <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-xl px-3.5 py-2 flex items-center space-x-3 shadow-md">
              <div className="w-7 h-7 rounded-lg bg-[#00A88F]/40 text-[#00E5BC] flex items-center justify-center border border-[#00E5BC]/30">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="text-xs font-extrabold text-white block">
                  Reconocimiento 100% Automático
                </span>
                <span className="text-[10px] text-cyan-200 font-medium block">
                  Con OpenCV y Lectura OCR
                </span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* ============================================================ */}
      {/* 2. TWO LARGE SIDE-BY-SIDE CARDS (ANVERSO & REVERSO) */}
      {/* ============================================================ */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Card 1: Anverso (Cara Frontal) */}
        <div className="rounded-2xl overflow-hidden shadow-lg border border-[#E2E8F0] bg-white flex flex-col justify-between">
          
          {/* Top Blue Header */}
          <div className="bg-[#101BCB] text-white px-6 py-4 flex items-center justify-between shadow-sm">
            <div className="flex items-center space-x-3">
              <span className="w-8 h-8 rounded-full bg-white text-[#101BCB] text-sm font-black flex items-center justify-center shadow-md">
                1
              </span>
              <h3 className="font-extrabold text-white text-base sm:text-lg">
                Anverso (Cara Frontal)
              </h3>
            </div>

            {frontPreview && (
              <button
                type="button"
                onClick={() => {}}
                className="flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-white/15 hover:bg-white/25 text-white text-xs font-bold transition border border-white/20"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Vista previa</span>
              </button>
            )}
          </div>

          {/* Card Body */}
          <div className="p-5 space-y-4 flex-1 flex flex-col justify-between">
            
            {/* Dropzone or Preview */}
            {!frontPreview ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleDrop(e, 'front')}
                className="relative border-2 border-dashed border-[#93C5FD] hover:border-[#101BCB] rounded-2xl p-6 text-center transition-all bg-[#F0F7FF] hover:bg-[#E0EFFF] group cursor-pointer"
                onClick={() => frontInputRef.current?.click()}
              >
                <input
                  ref={frontInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange(e, 'front')}
                  className="hidden"
                />
                
                {/* Upload Icon in Circle */}
                <div className="w-13 h-13 mx-auto rounded-full bg-blue-100 group-hover:bg-blue-200 flex items-center justify-center text-[#101BCB] transition mb-2 shadow-xs">
                  <Upload className="w-6 h-6" />
                </div>
                
                <p className="text-sm sm:text-base font-extrabold text-[#080F72]">
                  Arrastre la foto frontal o haga clic para subir
                </p>
                <p className="text-[11px] text-[#64748B] mt-0.5 font-medium">
                  PNG, JPG o WebP (Hasta 15MB)
                </p>

                <div className="mt-4 pt-3 border-t border-blue-200/60 flex items-center justify-center">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveCameraSide('front');
                    }}
                    className="flex items-center space-x-2 px-5 py-2 bg-[#101BCB] hover:bg-[#080F72] text-white text-xs font-bold rounded-xl transition shadow-md"
                  >
                    <Camera className="w-3.5 h-3.5 text-cyan-200" />
                    <span>Tomar Foto con Cámara</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="relative rounded-2xl overflow-hidden border border-[#CBD5E1] bg-slate-950 aspect-[1.586] flex items-center justify-center group shadow-inner">
                <img
                  src={frontPreview}
                  alt="Anverso preview"
                  className="w-full h-full object-contain"
                />
                <button
                  onClick={() => removeImage('front')}
                  className="absolute top-3 right-3 p-2.5 rounded-xl bg-black/75 hover:bg-[#DC2626] text-white transition shadow-lg backdrop-blur-sm"
                  title="Eliminar imagen"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Bottom 4 Blue Feature Checks */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-[11px] font-semibold text-[#101BCB]">
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
                <span>Detecta bordes</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
                <span>Corrige perspectiva</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
                <span>Elimina fondo</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#101BCB] flex-shrink-0" />
                <span>Optimiza imagen</span>
              </div>
            </div>

          </div>

        </div>

        {/* Card 2: Reverso (Cara Posterior - Opcional) */}
        <div className="rounded-2xl overflow-hidden shadow-md border border-[#E2E8F0] bg-white flex flex-col justify-between">
          
          {/* Top Teal Header */}
          <div className="bg-[#00A88F] text-white px-5 py-3.5 flex items-center justify-between shadow-xs">
            <div className="flex items-center space-x-2.5">
              <span className="w-7 h-7 rounded-full bg-white text-[#00A88F] text-xs font-black flex items-center justify-center shadow-xs">
                2
              </span>
              <h3 className="font-extrabold text-white text-sm sm:text-base">
                Reverso (Cara Posterior - Opcional)
              </h3>
            </div>

            {backPreview && (
              <button
                type="button"
                onClick={() => {}}
                className="flex items-center space-x-1.5 px-3 py-1 rounded-xl bg-white/15 hover:bg-white/25 text-white text-xs font-bold transition border border-white/20"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Vista previa</span>
              </button>
            )}
          </div>

          {/* Card Body */}
          <div className="p-5 space-y-4 flex-1 flex flex-col justify-between">
            
            {/* Dropzone or Preview */}
            {!backPreview ? (
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => handleDrop(e, 'back')}
                className="relative border-2 border-dashed border-[#6EE7B7] hover:border-[#00A88F] rounded-2xl p-6 text-center transition-all bg-[#F0FDF4] hover:bg-[#DCFCE7] group cursor-pointer"
                onClick={() => backInputRef.current?.click()}
              >
                <input
                  ref={backInputRef}
                  type="file"
                  accept="image/*"
                  onChange={(e) => handleFileChange(e, 'back')}
                  className="hidden"
                />
                
                {/* Upload Icon in Circle */}
                <div className="w-13 h-13 mx-auto rounded-full bg-emerald-100 group-hover:bg-emerald-200 flex items-center justify-center text-[#00A88F] transition mb-2 shadow-xs">
                  <Upload className="w-6 h-6" />
                </div>
                
                <p className="text-sm sm:text-base font-extrabold text-[#064E3B]">
                  Arrastre la foto posterior o haga clic para subir
                </p>
                <p className="text-[11px] text-[#64748B] mt-0.5 font-medium">
                  PNG, JPG o WebP (Lectura de MRZ, dirección y ubigeo)
                </p>

                <div className="mt-4 pt-3 border-t border-emerald-200/60 flex items-center justify-center">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveCameraSide('back');
                    }}
                    className="flex items-center space-x-2 px-5 py-2 bg-[#00A88F] hover:bg-[#008F7A] text-white text-xs font-bold rounded-xl transition shadow-md"
                  >
                    <Camera className="w-3.5 h-3.5 text-emerald-200" />
                    <span>Tomar Foto con Cámara</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="relative rounded-2xl overflow-hidden border border-[#CBD5E1] bg-slate-950 aspect-[1.586] flex items-center justify-center group shadow-inner">
                <img
                  src={backPreview}
                  alt="Reverso preview"
                  className="w-full h-full object-contain"
                />
                <button
                  onClick={() => removeImage('back')}
                  className="absolute top-3 right-3 p-2.5 rounded-xl bg-black/75 hover:bg-[#DC2626] text-white transition shadow-lg backdrop-blur-sm"
                  title="Eliminar imagen"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {/* Bottom 4 Green Feature Checks */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-slate-100 text-[11px] font-semibold text-[#00A88F]">
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#00A88F] flex-shrink-0" />
                <span>Lee MRZ</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#00A88F] flex-shrink-0" />
                <span>Extrae dirección</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#00A88F] flex-shrink-0" />
                <span>Detecta ubigeo</span>
              </div>
              <div className="flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-[#00A88F] flex-shrink-0" />
                <span>Procesa texto</span>
              </div>
            </div>

          </div>

        </div>

      </div>

      {/* ============================================================ */}
      {/* 3. BOTTOM ACTION BAR (Exact Match to Reference Screenshot) */}
      {/* ============================================================ */}
      <div className="bg-white rounded-2xl border border-[#E2E8F0] p-4 sm:p-5 shadow-sm flex flex-col lg:flex-row items-center justify-between gap-4">
        
        {/* Left: Quick Test Hint & Button */}
        <div className="flex flex-col sm:flex-row sm:items-center space-y-2 sm:space-y-0 sm:space-x-3.5 flex-1">
          
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 text-[#101BCB] flex items-center justify-center flex-shrink-0 shadow-xs">
              <FileSearch className="w-5 h-5" />
            </div>

            <div>
              <h4 className="text-xs sm:text-sm font-extrabold text-[#080F72]">
                ¿Quieres probar sin subir una foto?
              </h4>
              <p className="text-[11px] text-[#64748B]">
                Carga un documento de prueba para ver el recorte automático y extracción de datos.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => loadDemoScenario('DNI_AZUL')}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-[#EBF3FF] hover:bg-[#DBEAFE] text-[#101BCB] border border-blue-200 font-bold text-xs transition shadow-xs self-start sm:self-center"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Cargar Documento de Prueba</span>
          </button>

        </div>

        {/* Right: Primary Big Scan Action Button */}
        <button
          onClick={onStartScan}
          disabled={!canScan}
          className={`flex items-center space-x-2.5 px-6 py-3.5 rounded-xl font-extrabold text-xs sm:text-sm transition-all duration-300 shadow-md ${
            canScan
              ? 'bg-gradient-to-r from-[#00A88F] via-[#00BFA5] to-[#009688] hover:from-[#008F7A] hover:to-[#00796B] text-white shadow-[#00A88F]/25 transform hover:-translate-y-0.5 active:translate-y-0'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300'
          }`}
        >
          {isScanning ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin text-white" />
              <span>{scanStep || 'Procesando con OpenCV y OCR...'}</span>
            </>
          ) : (
            <>
              <Scan className="w-4 h-4" />
              <span>Escanear y Extraer Datos Automáticamente</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

      </div>

      {/* Camera Capture Modal */}
      <CameraModal
        isOpen={Boolean(activeCameraSide)}
        onClose={() => setActiveCameraSide(null)}
        onCapture={handleCameraCapture}
        sideTitle={activeCameraSide === 'front' ? 'Anverso (Cara Frontal)' : 'Reverso (Cara Posterior)'}
      />

    </div>
  );
}
