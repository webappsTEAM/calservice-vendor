import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode';
import {
  Camera,
  X,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  UploadCloud,
  Keyboard,
  Volume2,
  VolumeX,
  RotateCcw,
  Sparkles,
  Barcode as BarcodeIcon,
} from 'lucide-react';

/**
 * Play a high-pitch success beep using Web Audio API
 */
function playSuccessBeep() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime); // A5 note
    osc.frequency.exponentialRampToValueAtTime(1760, ctx.currentTime + 0.12); // A6 note

    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.12);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.13);
  } catch (e) {
    // AudioContext may be blocked before user gesture
  }
}

export function BarcodeScannerModal({
  isOpen,
  onClose,
  onScan,
  title = 'Scan Product Barcode',
  description = 'Point your camera at any 1D/2D product barcode (EAN-13, UPC, Code 128, QR Code)',
}) {
  const [activeMode, setActiveMode] = useState('camera'); // 'camera' | 'file' | 'manual'
  const [cameras, setCameras] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState('');
  const [scanning, setScanning] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [lastScannedResult, setLastScannedResult] = useState('');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [manualInput, setManualInput] = useState('');
  const [fileScanning, setFileScanning] = useState(false);

  const scannerRef = useRef(null);
  const containerId = 'sevo-barcode-reader-region';

  // Handle successful scan
  const handleScanSuccess = useCallback(
    (decodedText) => {
      if (!decodedText || decodedText === lastScannedResult) return;
      setLastScannedResult(decodedText);

      if (soundEnabled) {
        playSuccessBeep();
      }

      if (navigator.vibrate) {
        try {
          navigator.vibrate(120);
        } catch (ignored) {}
      }

      // Automatically invoke callback and close
      onScan(decodedText.trim());
      onClose();
    },
    [lastScannedResult, soundEnabled, onScan, onClose]
  );

  // Initialize camera scanner
  const startCameraScanner = useCallback(async (cameraId = null) => {
    setErrorMsg('');
    setScanning(true);

    try {
      // 1. Get available cameras if not yet retrieved
      let availableCameras = cameras;
      if (availableCameras.length === 0) {
        availableCameras = await Html5Qrcode.getCameras();
        setCameras(availableCameras || []);
      }

      if (!availableCameras || availableCameras.length === 0) {
        throw new Error('No camera detected on this device. You can use the File Upload or Manual test input below.');
      }

      // 2. Select back camera by default if available
      let targetCamera = cameraId;
      if (!targetCamera) {
        const backCam = availableCameras.find(
          (c) =>
            c.label.toLowerCase().includes('back') ||
            c.label.toLowerCase().includes('rear') ||
            c.label.toLowerCase().includes('environment')
        );
        targetCamera = backCam ? backCam.id : availableCameras[0].id;
        setSelectedCameraId(targetCamera);
      }

      // 3. Stop existing scanner instance if running
      if (scannerRef.current) {
        try {
          if (scannerRef.current.isScanning) {
            await scannerRef.current.stop();
          }
          await scannerRef.current.clear();
        } catch (e) {
          console.warn('Error clearing previous scanner instance', e);
        }
      }

      // 4. Create new scanner instance
      const formatsToSupport = [
        Html5QrcodeSupportedFormats.EAN_13,
        Html5QrcodeSupportedFormats.EAN_8,
        Html5QrcodeSupportedFormats.CODE_128,
        Html5QrcodeSupportedFormats.CODE_39,
        Html5QrcodeSupportedFormats.UPC_A,
        Html5QrcodeSupportedFormats.UPC_E,
        Html5QrcodeSupportedFormats.QR_CODE,
        Html5QrcodeSupportedFormats.ITF,
      ];

      const html5QrCode = new Html5Qrcode(containerId, {
        formatsToSupport,
        verbose: false,
      });
      scannerRef.current = html5QrCode;

      const qrConfig = {
        fps: 15,
        qrbox: (viewfinderWidth, viewfinderHeight) => {
          const minEdge = Math.min(viewfinderWidth, viewfinderHeight);
          const qrboxSize = Math.floor(minEdge * 0.75);
          return {
            width: Math.min(viewfinderWidth - 20, Math.max(220, qrboxSize + 40)),
            height: Math.min(viewfinderHeight - 20, Math.max(140, Math.floor(qrboxSize * 0.65))),
          };
        },
        aspectRatio: 1.333334,
      };

      await html5QrCode.start(
        targetCamera,
        qrConfig,
        (decodedText) => {
          handleScanSuccess(decodedText);
        },
        (errorMessage) => {
          // Ignored per frame noise
        }
      );
    } catch (err) {
      console.error('Camera Scanner Error:', err);
      let friendlyMsg = err?.message || 'Failed to start camera.';
      if (friendlyMsg.includes('Permission') || friendlyMsg.includes('NotAllowedError')) {
        friendlyMsg = 'Camera permission was denied. Please allow camera access in your browser settings.';
      } else if (friendlyMsg.includes('NotFoundError') || friendlyMsg.includes('No camera')) {
        friendlyMsg = 'No camera found on this device. You can test using the Manual Simulator input or Image Upload tabs below.';
      }
      setErrorMsg(friendlyMsg);
      setScanning(false);
    }
  }, [cameras, handleScanSuccess]);

  // Clean stop scanner helper
  const stopCameraScanner = useCallback(async () => {
    if (scannerRef.current) {
      try {
        if (scannerRef.current.isScanning) {
          await scannerRef.current.stop();
        }
        await scannerRef.current.clear();
      } catch (e) {
        console.warn('Error stopping scanner', e);
      }
      scannerRef.current = null;
    }
    setScanning(false);
  }, []);

  // Lifecycle when modal opens/closes or changes mode
  useEffect(() => {
    if (isOpen) {
      setLastScannedResult('');
      setErrorMsg('');
      if (activeMode === 'camera') {
        // Small delay to ensure DOM element with id is rendered
        const timer = setTimeout(() => {
          startCameraScanner(selectedCameraId);
        }, 150);
        return () => clearTimeout(timer);
      }
    } else {
      stopCameraScanner();
    }
    return () => {
      stopCameraScanner();
    };
  }, [isOpen, activeMode, startCameraScanner, stopCameraScanner, selectedCameraId]);

  // Handle camera device switch
  const handleCameraChange = async (e) => {
    const newCamId = e.target.value;
    setSelectedCameraId(newCamId);
    await stopCameraScanner();
    startCameraScanner(newCamId);
  };

  // Handle file-based barcode scanning
  const handleImageFileScan = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileScanning(true);
    setErrorMsg('');

    try {
      const html5QrCode = new Html5Qrcode('sevo-barcode-file-region', {
        formatsToSupport: [
          Html5QrcodeSupportedFormats.EAN_13,
          Html5QrcodeSupportedFormats.EAN_8,
          Html5QrcodeSupportedFormats.CODE_128,
          Html5QrcodeSupportedFormats.CODE_39,
          Html5QrcodeSupportedFormats.UPC_A,
          Html5QrcodeSupportedFormats.UPC_E,
          Html5QrcodeSupportedFormats.QR_CODE,
          Html5QrcodeSupportedFormats.ITF,
        ],
      });

      const decodedText = await html5QrCode.scanFile(file, true);
      if (decodedText) {
        handleScanSuccess(decodedText);
      } else {
        throw new Error('No readable barcode found in this image.');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Could not detect barcode from image file. Try a clearer photo.');
    } finally {
      setFileScanning(false);
    }
  };

  // Handle manual / test simulated submit
  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualInput.trim()) return;
    handleScanSuccess(manualInput.trim());
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/70 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto animate-in fade-in duration-150">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-600 text-white rounded-2xl shadow-xs">
              <BarcodeIcon className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm tracking-tight">{title}</h3>
              <p className="text-[11px] text-slate-500 line-clamp-1">{description}</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`p-2 rounded-xl border transition-colors ${
                soundEnabled
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-slate-100 text-slate-400 border-slate-200'
              }`}
              title={soundEnabled ? 'Beep sound enabled' : 'Muted'}
            >
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            <button
              type="button"
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Scanner Mode Tabs */}
        <div className="flex items-center border-b border-slate-100 bg-slate-50/40 px-6 pt-2 gap-2">
          <button
            type="button"
            onClick={() => {
              setActiveMode('camera');
            }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 flex items-center gap-1.5 transition-all ${
              activeMode === 'camera'
                ? 'border-emerald-600 text-emerald-800'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Live Camera</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveMode('file');
              stopCameraScanner();
            }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 flex items-center gap-1.5 transition-all ${
              activeMode === 'file'
                ? 'border-emerald-600 text-emerald-800'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Image File</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveMode('manual');
              stopCameraScanner();
            }}
            className={`pb-2.5 px-3 text-xs font-bold border-b-2 flex items-center gap-1.5 transition-all ${
              activeMode === 'manual'
                ? 'border-emerald-600 text-emerald-800'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Keyboard className="w-3.5 h-3.5" />
            <span>Simulate / Test</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 flex-1 flex flex-col space-y-4">
          {/* CAMERA MODE */}
          {activeMode === 'camera' && (
            <div className="space-y-3">
              {/* Camera view container */}
              <div className="relative w-full aspect-4/3 bg-slate-950 rounded-2xl overflow-hidden border-2 border-slate-800 flex items-center justify-center shadow-inner">
                {/* Scanner container for html5-qrcode */}
                <div id={containerId} className="w-full h-full object-cover" />

                {/* Animated Targeting Reticle Overlay */}
                {scanning && !errorMsg && (
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    {/* Reticle guide box */}
                    <div className="relative w-64 h-36 border-2 border-emerald-400/80 rounded-2xl shadow-[0_0_0_9999px_rgba(15,23,42,0.45)]">
                      {/* Corner Accents */}
                      <span className="absolute -top-1 -left-1 w-4 h-4 border-t-4 border-l-4 border-emerald-400 rounded-tl-lg" />
                      <span className="absolute -top-1 -right-1 w-4 h-4 border-t-4 border-r-4 border-emerald-400 rounded-tr-lg" />
                      <span className="absolute -bottom-1 -left-1 w-4 h-4 border-b-4 border-l-4 border-emerald-400 rounded-bl-lg" />
                      <span className="absolute -bottom-1 -right-1 w-4 h-4 border-b-4 border-r-4 border-emerald-400 rounded-br-lg" />

                      {/* Moving laser scanline */}
                      <div className="absolute left-0 right-0 h-0.5 bg-emerald-400 shadow-[0_0_12px_#34d399] animate-[bounce_2s_infinite]" />
                    </div>

                    <p className="mt-3 text-[11px] font-semibold text-white/90 bg-slate-900/80 px-3 py-1 rounded-full backdrop-blur-xs">
                      Align barcode within frame
                    </p>
                  </div>
                )}

                {/* Error Banner inside camera */}
                {errorMsg && (
                  <div className="absolute inset-0 bg-slate-900/95 p-6 flex flex-col items-center justify-center text-center text-white space-y-3">
                    <div className="p-3 bg-rose-500/20 text-rose-400 rounded-2xl border border-rose-500/30">
                      <AlertCircle className="w-8 h-8" />
                    </div>
                    <p className="text-xs font-semibold max-w-xs">{errorMsg}</p>
                    <div className="flex items-center gap-2 pt-2">
                      <button
                        type="button"
                        onClick={() => startCameraScanner(selectedCameraId)}
                        className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        <span>Retry Camera</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => setActiveMode('manual')}
                        className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold transition-colors"
                      >
                        Try Manual Test
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Camera selection dropdown if multiple cameras available */}
              {cameras.length > 1 && (
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-slate-500 font-medium shrink-0">Switch Camera:</span>
                  <select
                    value={selectedCameraId}
                    onChange={handleCameraChange}
                    className="flex-1 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 outline-none"
                  >
                    {cameras.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.label || `Camera ${c.id.substring(0, 8)}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* FILE UPLOAD MODE */}
          {activeMode === 'file' && (
            <div className="space-y-4">
              <div id="sevo-barcode-file-region" className="hidden" />
              <div className="p-8 border-2 border-dashed border-slate-200 hover:border-emerald-500 rounded-2xl text-center bg-slate-50/50 flex flex-col items-center justify-center space-y-3">
                <div className="p-3.5 bg-emerald-50 text-emerald-600 rounded-2xl">
                  <UploadCloud className="w-8 h-8" />
                </div>
                <div>
                  <h4 className="text-xs font-bold text-slate-800">Select an image containing a barcode</h4>
                  <p className="text-[11px] text-slate-400 mt-0.5">Supports PNG, JPG, WebP from photo library or scans</p>
                </div>

                <label className="cursor-pointer px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors inline-flex items-center gap-1.5">
                  <UploadCloud className="w-4 h-4" />
                  <span>{fileScanning ? 'Decoding image...' : 'Browse Image File'}</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageFileScan}
                    disabled={fileScanning}
                    className="hidden"
                  />
                </label>
              </div>

              {errorMsg && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                  <span>{errorMsg}</span>
                </div>
              )}
            </div>
          )}

          {/* MANUAL SIMULATOR / TEST MODE */}
          {activeMode === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-2xl text-xs text-emerald-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-emerald-800">
                  <Sparkles className="w-4 h-4 text-emerald-600" />
                  <span>Scanner Simulator / USB Wedge Mode</span>
                </div>
                <p className="text-[11px] text-emerald-700 leading-relaxed">
                  Enter or paste any barcode digit string (or use sample barcodes below) to test the exact workflow as if scanned by a physical scanner.
                </p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Barcode Value</label>
                <div className="relative">
                  <input
                    type="text"
                    value={manualInput}
                    onChange={(e) => setManualInput(e.target.value)}
                    placeholder="e.g. 8901030773952"
                    autoFocus
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 focus:bg-white focus:border-emerald-500 rounded-xl text-xs font-mono text-slate-800 outline-none shadow-2xs"
                  />
                  {manualInput && (
                    <button
                      type="button"
                      onClick={() => setManualInput('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Quick Sample Presets */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Quick Test Samples:</span>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { label: 'Fortune Oil (EAN-13)', val: '8906007281452' },
                    { label: 'Tata Salt 1kg (EAN-13)', val: '8901058852332' },
                    { label: 'Aashirvaad Atta (EAN-13)', val: '8901725181223' },
                    { label: 'Warehouse SKU (Code 128)', val: 'SEVO-GROC-8921' },
                  ].map((preset) => (
                    <button
                      key={preset.val}
                      type="button"
                      onClick={() => setManualInput(preset.val)}
                      className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-mono border border-slate-200 transition-colors"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={!manualInput.trim()}
                  className={`w-full py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                    manualInput.trim()
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                      : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Simulate Barcode Scan</span>
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between text-[11px] text-slate-500">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Auto-detects EAN-13, UPC, Code 128, QR</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 font-semibold text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
