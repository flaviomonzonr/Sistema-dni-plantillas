import React, { useRef, useState, useEffect } from 'react';
import { Camera, X, RefreshCw, Check, AlertCircle } from 'lucide-react';

export default function CameraModal({ isOpen, onClose, onCapture, sideTitle }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [facingMode, setFacingMode] = useState('environment'); // environment (back camera) or user (front camera)
  const [errorMsg, setErrorMsg] = useState(null);
  const [capturedPreview, setCapturedPreview] = useState(null);
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (isOpen) {
      startCamera();
    } else {
      stopCamera();
      setCapturedPreview(null);
      setErrorMsg(null);
    }
    return () => {
      stopCamera();
    };
  }, [isOpen, facingMode]);

  const startCamera = async () => {
    stopCamera();
    setErrorMsg(null);
    try {
      const constraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      };
      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      setStream(mediaStream);
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
      }
    } catch (err) {
      console.error('Error accessing camera:', err);
      setErrorMsg(
        'No se pudo acceder a la cámara. Verifique los permisos del navegador o intente subir una foto directamente.'
      );
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  };

  const toggleFacingMode = () => {
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'));
  };

  const takeSnapshot = () => {
    if (!videoRef.current || !canvasRef.current) return;

    setFlash(true);
    setTimeout(() => setFlash(false), 200);

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (blob) {
          const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
          const previewUrl = URL.createObjectURL(blob);
          setCapturedPreview({ file, previewUrl });
        }
      },
      'image/jpeg',
      0.95
    );
  };

  const handleConfirm = () => {
    if (capturedPreview) {
      onCapture(capturedPreview.file, capturedPreview.previewUrl);
      onClose();
    }
  };

  const handleRetake = () => {
    if (capturedPreview?.previewUrl) {
      URL.revokeObjectURL(capturedPreview.previewUrl);
    }
    setCapturedPreview(null);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl overflow-hidden border border-[#E2E8F0] shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0] bg-[#080F72]">
          <div className="flex items-center space-x-2.5">
            <Camera className="w-5 h-5 text-[#A8E63D]" />
            <h3 className="text-base font-bold text-white">
              Capturar {sideTitle || 'Documento'}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Viewport */}
        <div className="relative flex-1 bg-black min-h-[380px] max-h-[550px] flex items-center justify-center overflow-hidden">
          {errorMsg ? (
            <div className="p-8 text-center text-slate-300 max-w-md">
              <AlertCircle className="w-12 h-12 text-[#DC2626] mx-auto mb-3" />
              <p className="text-sm">{errorMsg}</p>
              <button
                onClick={startCamera}
                className="mt-4 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg"
              >
                Reintentar Acceso
              </button>
            </div>
          ) : capturedPreview ? (
            <img
              src={capturedPreview.previewUrl}
              alt="Preview captura"
              className="w-full h-full object-contain max-h-[500px]"
            />
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-contain max-h-[500px]"
              />

              {/* Flash effect */}
              {flash && <div className="absolute inset-0 bg-white transition-opacity duration-150"></div>}

              {/* Document ID Overlay Guide */}
              <div className="absolute inset-0 pointer-events-none flex items-center justify-center p-6">
                <div className="relative w-full max-w-[500px] aspect-[1.586] border-2 border-dashed border-[#A8E63D] rounded-2xl shadow-2xl flex flex-col justify-between p-4 bg-blue-950/20 backdrop-contrast-125">
                  {/* Corner accents */}
                  <div className="absolute -top-1 -left-1 w-6 h-6 border-t-4 border-l-4 border-[#A8E63D] rounded-tl-lg"></div>
                  <div className="absolute -top-1 -right-1 w-6 h-6 border-t-4 border-r-4 border-[#A8E63D] rounded-tr-lg"></div>
                  <div className="absolute -bottom-1 -left-1 w-6 h-6 border-b-4 border-l-4 border-[#A8E63D] rounded-bl-lg"></div>
                  <div className="absolute -bottom-1 -right-1 w-6 h-6 border-b-4 border-r-4 border-[#A8E63D] rounded-br-lg"></div>

                  <div className="text-center">
                    <span className="inline-block px-3 py-1 bg-black/70 backdrop-blur-sm rounded-full text-[11px] font-bold text-white border border-white/10">
                      Alinee los bordes del carnet aquí
                    </span>
                  </div>

                  <div className="text-center">
                    <span className="text-[11px] text-slate-200 bg-black/60 px-2.5 py-0.5 rounded">
                      Buena iluminación • Evite reflejos
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}

          <canvas ref={canvasRef} className="hidden" />
        </div>

        {/* Footer controls */}
        <div className="px-6 py-4 bg-[#F8FAFC] border-t border-[#E2E8F0] flex items-center justify-between">
          {!capturedPreview ? (
            <>
              <button
                onClick={toggleFacingMode}
                className="flex items-center space-x-1.5 px-3.5 py-2 text-xs font-bold text-[#080F72] bg-white hover:bg-slate-50 border border-[#CBD5E1] rounded-xl transition shadow-sm"
              >
                <RefreshCw className="w-3.5 h-3.5 text-[#101BCB]" />
                <span>Girar Cámara</span>
              </button>

              <button
                onClick={takeSnapshot}
                disabled={!stream}
                className="flex items-center space-x-2 px-6 py-2.5 bg-[#101BCB] hover:bg-[#080F72] text-white font-bold text-sm rounded-xl shadow-corporate-md disabled:opacity-50 transition transform active:scale-95"
              >
                <Camera className="w-4 h-4 text-[#A8E63D]" />
                <span>Tomar Foto</span>
              </button>

              <div className="w-24"></div>
            </>
          ) : (
            <>
              <button
                onClick={handleRetake}
                className="px-4 py-2 text-xs font-bold text-[#64748B] hover:text-[#1E293B] bg-white border border-[#CBD5E1] rounded-xl transition shadow-sm"
              >
                Volver a Tomar
              </button>

              <button
                onClick={handleConfirm}
                className="flex items-center space-x-2 px-6 py-2.5 bg-[#16A34A] hover:bg-[#15803d] text-white font-bold text-sm rounded-xl shadow-sm transition transform active:scale-95"
              >
                <Check className="w-4 h-4" />
                <span>Usar Esta Foto</span>
              </button>
            </>
          )}
        </div>

      </div>
    </div>
  );
}
