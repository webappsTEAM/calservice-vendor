import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function Drawer({
  isOpen = false,
  onClose = () => {},
  title = '',
  subtitle = '',
  children,
  footer = null,
  width = 'max-w-md',
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      <div
        className="absolute inset-0 bg-zinc-950/40 backdrop-blur-xs transition-opacity animate-in fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-y-0 right-0 pl-10 max-w-full flex">
        <div
          className={`w-screen ${width} bg-white shadow-2xl border-l border-zinc-200/90 flex flex-col animate-in slide-in-from-right duration-200`}
        >
          {/* Header */}
          <div className="px-5 py-4 bg-zinc-50/90 border-b border-zinc-100 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 tracking-tight">{title}</h3>
              {subtitle && <p className="text-[11px] text-zinc-500 mt-0.5">{subtitle}</p>}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="px-5 py-3.5 bg-zinc-50/70 border-t border-zinc-100 flex items-center justify-end gap-2.5">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Drawer;

