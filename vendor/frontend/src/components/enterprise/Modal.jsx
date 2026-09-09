import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export function Modal({
  isOpen = false,
  onClose = () => {},
  title = '',
  subtitle = '',
  icon: Icon = null,
  children,
  footer = null,
  maxWidth = 'max-w-lg',
  className = '',
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 overflow-y-auto">
      <div
        className="fixed inset-0 bg-zinc-950/40 backdrop-blur-xs transition-opacity animate-in fade-in"
        onClick={onClose}
      />
      <div
        className={`relative bg-white rounded-md border border-zinc-200/90 shadow-modal ${maxWidth} w-full my-6 sm:my-8 overflow-hidden z-10 animate-in zoom-in-95 duration-150 ${className}`}
      >
        {/* Header */}
        <div className="px-4 sm:px-5 py-3.5 bg-zinc-50/90 border-b border-zinc-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            {Icon && (
              <span className="p-1.5 rounded-lg bg-zinc-100 text-zinc-700 shrink-0">
                {typeof Icon === 'function' || typeof Icon === 'object' ? (
                  <Icon className="w-4 h-4" />
                ) : (
                  Icon
                )}
              </span>
            )}
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-zinc-900 tracking-tight">{title}</h3>
              {subtitle && <p className="text-[11px] text-zinc-500 mt-0.5">{subtitle}</p>}
            </div>
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
        <div className="p-4 sm:p-5 space-y-4 max-h-[calc(100vh-180px)] overflow-y-auto">{children}</div>

        {/* Footer */}
        {footer && (
          <div className="px-4 sm:px-5 py-3 bg-zinc-50/70 border-t border-zinc-100 flex items-center justify-end gap-2.5">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;

