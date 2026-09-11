import React, { useState, useEffect } from 'react';
import { ArrowUp, ArrowDown } from 'lucide-react';

export default function ScrollNavigator({ collapsed }) {
  const [showScroll, setShowScroll] = useState(true);

  useEffect(() => {
    const handleScroll = () => {
      // Keep always available or dynamically visible
      setShowScroll(true);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    });
  };

  const scrollToBottom = () => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: 'smooth',
    });
  };

  if (!showScroll) return null;

  return (
    <aside
      className={`fixed bottom-6 z-40 transition-all duration-300 ease-in-out flex flex-col items-center space-y-2 select-none ${
        collapsed ? 'left-[92px]' : 'left-[302px]'
      }`}
      aria-label="Navegación de desplazamiento rápido"
    >
      {/* Scroll Up Button */}
      <button
        type="button"
        onClick={scrollToTop}
        className="w-11 h-11 rounded-2xl bg-white/95 hover:bg-[#101BCB] text-[#080F72] hover:text-white border-2 border-[#CBD5E1] hover:border-[#101BCB] shadow-xl backdrop-blur-md flex flex-col items-center justify-center transition-all duration-200 transform hover:-translate-y-1 active:translate-y-0 group cursor-pointer"
        title="Subir al inicio de la página"
      >
        <ArrowUp className="w-5 h-5 text-[#101BCB] group-hover:text-white transition stroke-[2.5]" />
        <span className="sr-only">Subir</span>
      </button>

      {/* Scroll Down Button */}
      <button
        type="button"
        onClick={scrollToBottom}
        className="w-11 h-11 rounded-2xl bg-white/95 hover:bg-[#00A88F] text-[#080F72] hover:text-white border-2 border-[#CBD5E1] hover:border-[#00A88F] shadow-xl backdrop-blur-md flex flex-col items-center justify-center transition-all duration-200 transform hover:translate-y-1 active:translate-y-0 group cursor-pointer"
        title="Bajar al final de la página"
      >
        <ArrowDown className="w-5 h-5 text-[#00A88F] group-hover:text-white transition stroke-[2.5]" />
        <span className="sr-only">Bajar</span>
      </button>
    </aside>
  );
}
