import React, { useEffect, useRef, useState } from 'react';
import JsBarcode from 'jsbarcode';
import { Copy, Check, Barcode as BarcodeIcon, AlertCircle } from 'lucide-react';

/**
 * Reusable Barcode Renderer Component
 * Renders scannable SVG barcode using JsBarcode with automatic format fallback
 */
export function BarcodeRenderer({
  value,
  format = 'CODE128',
  width = 1.6,
  height = 40,
  displayValue = true,
  fontSize = 11,
  background = '#ffffff',
  lineColor = '#0f172a',
  margin = 6,
  className = '',
  compact = false,
  showCopyButton = false,
  alt = '',
}) {
  const svgRef = useRef(null);
  const [renderError, setRenderError] = useState(false);
  const [copied, setCopied] = useState(false);

  const cleanValue = value ? String(value).trim() : '';

  useEffect(() => {
    if (!svgRef.current || !cleanValue) {
      setRenderError(false);
      return;
    }

    setRenderError(false);

    const tryRender = (fmt) => {
      try {
        JsBarcode(svgRef.current, cleanValue, {
          format: fmt,
          width: compact ? Math.max(1, width * 0.75) : width,
          height: compact ? Math.max(20, height * 0.6) : height,
          displayValue: compact ? false : displayValue,
          fontSize: compact ? 9 : fontSize,
          font: 'monospace',
          textMargin: 2,
          background: background,
          lineColor: lineColor,
          margin: compact ? 2 : margin,
          valid: (valid) => {
            if (!valid) throw new Error('Invalid barcode data');
          },
        });
        return true;
      } catch (err) {
        return false;
      }
    };

    // First attempt requested format
    let success = tryRender(format);

    // If failed and not already CODE128, try fallback to CODE128 (universal alphanumeric)
    if (!success && format !== 'CODE128') {
      success = tryRender('CODE128');
    }

    // If still failed, try CODE39
    if (!success && format !== 'CODE39') {
      success = tryRender('CODE39');
    }

    if (!success) {
      setRenderError(true);
    }
  }, [cleanValue, format, width, height, displayValue, fontSize, background, lineColor, margin, compact]);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (!cleanValue) return;
    navigator.clipboard.writeText(cleanValue);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!cleanValue) {
    return (
      <span className="text-slate-400 text-xs italic">No barcode</span>
    );
  }

  if (renderError) {
    return (
      <div className={`inline-flex items-center gap-1 px-2 py-1 bg-slate-100 border border-slate-200 rounded text-slate-700 font-mono text-[11px] ${className}`}>
        <BarcodeIcon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <span>{cleanValue}</span>
      </div>
    );
  }

  return (
    <div className={`inline-flex flex-col items-center group relative ${className}`}>
      <div className="bg-white rounded-lg p-1 border border-slate-200 shadow-2xs overflow-hidden flex items-center justify-center">
        <svg ref={svgRef} className="max-w-full h-auto" />
      </div>

      {showCopyButton && (
        <button
          type="button"
          onClick={handleCopy}
          className="mt-1 inline-flex items-center gap-1 text-[10px] font-mono text-slate-500 hover:text-slate-800 transition-colors"
          title="Copy barcode value"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-600" />
              <span className="text-emerald-700 font-semibold">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-slate-400" />
              <span>Copy</span>
            </>
          )}
        </button>
      )}
    </div>
  );
}
