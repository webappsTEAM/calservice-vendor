import React, { useState, useEffect } from 'react';
import {
  X,
  Plus,
  Trash2,
  Camera,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Upload,
  Loader2,
  Wrench,
  Sparkles,
} from 'lucide-react';
import {
  apiSaveInspectionFindings,
  apiUploadInspectionPhoto,
  apiCompleteInspection,
} from '../../api/vendorEstimationService.js';

const DEFECT_TEMPLATES = [
  {
    type: 'Gas Leakage',
    title: 'Refrigerant Gas Leakage at Flare Nut',
    severity: 'HIGH',
    description: 'Oil traces and pressure drop detected at service valve connection.',
    recommended_action: 'Perform nitrogen leak test, braze flare joint, vacuum system, and top up gas.',
    quantity: 1,
    unit: 'refill',
  },
  {
    type: 'Coil Cleaning',
    title: 'Severe Cooling Coil Clogging & Slime',
    severity: 'MEDIUM',
    description: 'Indoor evaporator coil choked with grime, restricting airflow by >50%.',
    recommended_action: 'Deep chemical foam jet wash of indoor and outdoor condenser coil.',
    quantity: 1,
    unit: 'service',
  },
  {
    type: 'Capacitor',
    title: 'Compressor Run Capacitor Weak / Bulged',
    severity: 'HIGH',
    description: 'Dual capacitor measured 18uF against 45uF rated capacity.',
    recommended_action: 'Replace with genuine 45/5 uF heavy-duty capacitor.',
    quantity: 1,
    unit: 'piece',
  },
  {
    type: 'PCB fault',
    title: 'Indoor/Outdoor Inverter PCB Fault',
    severity: 'CRITICAL',
    description: 'Communication error code blinking on display; IPM circuit damaged.',
    recommended_action: 'Bench test and repair motherboard circuit / replace IPM module.',
    quantity: 1,
    unit: 'unit',
  },
  {
    type: 'Fan Motor',
    title: 'Condenser Fan Motor Bearing Jammed',
    severity: 'HIGH',
    description: 'Outdoor unit motor overheating and shutting down within 5 minutes.',
    recommended_action: 'Replace condenser fan motor and inspect blade alignment.',
    quantity: 1,
    unit: 'unit',
  },
  {
    type: 'Drainage',
    title: 'Condensate Drain Tray Overflow & Clog',
    severity: 'LOW',
    description: 'Water dripping from indoor unit front panel onto walls.',
    recommended_action: 'Flush drain pipe, re-pitch slope, and clean drain tray.',
    quantity: 1,
    unit: 'service',
  },
];

const SEVERITY_COLORS = {
  LOW: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  MEDIUM: 'bg-amber-50 text-amber-700 border-amber-200',
  HIGH: 'bg-orange-50 text-orange-700 border-orange-200',
  CRITICAL: 'bg-rose-50 text-rose-700 border-rose-200',
};

export default function TechnicianInspectionSheet({
  estimation,
  isOpen,
  onClose,
  onComplete,
}) {
  const [findings, setFindings] = useState([]);
  const [diagnosis, setDiagnosis] = useState('');
  const [notes, setNotes] = useState('');
  const [photos, setPhotos] = useState([]);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      // Populate existing findings if any
      const existingFindings = estimation?.findings || [];
      if (existingFindings.length > 0) {
        setFindings(existingFindings);
      } else {
        // Pre-select 1 default template as starting point
        setFindings([DEFECT_TEMPLATES[0]]);
      }

      setDiagnosis(
        estimation?.inspection?.diagnosis ||
          `Thorough inspection completed for ${estimation?.ac_details?.ac_brand || ''} ${
            estimation?.ac_details?.ac_type || 'AC'
          }. Root cause identified.`
      );
      setNotes(estimation?.inspection?.notes || '');
      setPhotos(estimation?.photos || []);
    }
  }, [isOpen, estimation]);

  if (!isOpen) return null;

  const handleAddTemplate = (tpl) => {
    if (!findings.some((f) => f.title === tpl.title)) {
      setFindings([...findings, { ...tpl }]);
    }
  };

  const handleRemoveFinding = (index) => {
    setFindings(findings.filter((_, idx) => idx !== index));
  };

  const handleUpdateFinding = (index, field, value) => {
    const updated = [...findings];
    updated[index] = { ...updated[index], [field]: value };
    setFindings(updated);
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingPhoto(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('photo', file);
      formData.append('caption', `Defect photo - ${file.name}`);

      const res = await apiUploadInspectionPhoto(estimation.id, formData);
      if (res?.photo) {
        setPhotos((prev) => [...prev, res.photo]);
      }
    } catch (err) {
      setError(err.message || 'Failed to upload photo.');
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleSubmit = async () => {
    if (findings.length === 0) {
      setError('Please record at least one inspection defect finding.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      // 1. Save structured findings
      await apiSaveInspectionFindings(estimation.id, findings);

      // 2. Mark inspection complete with diagnosis
      const completeRes = await apiCompleteInspection(estimation.id, {
        diagnosis_summary: diagnosis,
        notes: notes,
      });

      onComplete?.(completeRes?.data || completeRes);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to complete inspection.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-zinc-950/70 backdrop-blur-xs animate-in fade-in overflow-y-auto">
      <div className="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl border border-zinc-200 overflow-hidden my-auto max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-100 bg-zinc-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-xs">
              <Wrench className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-zinc-900">
                Technician Inspection & Diagnosis Sheet
              </h2>
              <p className="text-xs text-zinc-500">
                Job #{estimation?.request_id} • {estimation?.ac_details?.ac_brand} {estimation?.ac_details?.ac_type} ({estimation?.ac_details?.ac_capacity})
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-700 font-medium">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          {/* Quick-Select Defect Checklist */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-zinc-900 uppercase tracking-wider text-[11px]">
                Quick-Select Common Defect Checklist
              </span>
              <span className="text-zinc-400 text-[11px]">Click to add to inspection findings</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {DEFECT_TEMPLATES.map((tpl) => {
                const isSelected = findings.some((f) => f.title === tpl.title);
                return (
                  <button
                    key={tpl.type}
                    type="button"
                    onClick={() => handleAddTemplate(tpl)}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      isSelected
                        ? 'bg-blue-50 border-blue-300 text-blue-700 shadow-xs'
                        : 'bg-white border-zinc-200 text-zinc-700 hover:border-zinc-300 hover:bg-zinc-50'
                    }`}
                  >
                    <Plus className="w-3 h-3" />
                    <span>{tpl.type}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Structured Findings List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-bold text-zinc-900 uppercase tracking-wider text-[11px]">
                Recorded Findings ({findings.length})
              </span>
              <button
                type="button"
                onClick={() =>
                  setFindings([
                    ...findings,
                    {
                      finding_type: 'Other',
                      title: 'Custom AC Finding',
                      severity: 'MEDIUM',
                      description: '',
                      recommended_action: '',
                      quantity: 1,
                      unit: 'unit',
                    },
                  ])
                }
                className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Custom Finding</span>
              </button>
            </div>

            {findings.length === 0 ? (
              <div className="p-6 text-center border-2 border-dashed border-zinc-200 rounded-xl text-zinc-400">
                No defects added yet. Click above to add findings.
              </div>
            ) : (
              findings.map((finding, idx) => (
                <div
                  key={idx}
                  className="p-4 border border-zinc-200 rounded-xl bg-zinc-50/50 space-y-3 relative group"
                >
                  <button
                    type="button"
                    onClick={() => handleRemoveFinding(idx)}
                    className="absolute top-3 right-3 p-1 rounded-md text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    title="Remove finding"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pr-8">
                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-600 mb-1">
                        Defect Type
                      </label>
                      <input
                        type="text"
                        value={finding.finding_type || ''}
                        onChange={(e) => handleUpdateFinding(idx, 'finding_type', e.target.value)}
                        className="w-full px-2.5 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-600 mb-1">
                        Finding Title
                      </label>
                      <input
                        type="text"
                        value={finding.title || ''}
                        onChange={(e) => handleUpdateFinding(idx, 'title', e.target.value)}
                        className="w-full px-2.5 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs font-medium"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-600 mb-1">
                        Severity Level
                      </label>
                      <select
                        value={finding.severity || 'MEDIUM'}
                        onChange={(e) => handleUpdateFinding(idx, 'severity', e.target.value)}
                        className={`w-full px-2.5 py-1.5 border rounded-lg text-xs font-bold ${
                          SEVERITY_COLORS[finding.severity || 'MEDIUM']
                        }`}
                      >
                        <option value="LOW">LOW (Minor cosmetic / routine)</option>
                        <option value="MEDIUM">MEDIUM (Requires attention)</option>
                        <option value="HIGH">HIGH (Affects cooling efficiency)</option>
                        <option value="CRITICAL">CRITICAL (System inoperable / risk)</option>
                      </select>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-600 mb-1">
                        Technical Observations / Diagnosis
                      </label>
                      <textarea
                        rows={2}
                        value={finding.description || ''}
                        onChange={(e) => handleUpdateFinding(idx, 'description', e.target.value)}
                        placeholder="Detailed inspection observations..."
                        className="w-full px-2.5 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-zinc-600 mb-1">
                        Recommended Remedial Action
                      </label>
                      <textarea
                        rows={2}
                        value={finding.recommended_action || ''}
                        onChange={(e) => handleUpdateFinding(idx, 'recommended_action', e.target.value)}
                        placeholder="Action recommended for quotation builder..."
                        className="w-full px-2.5 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs"
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Photo Upload Section */}
          <div className="space-y-3">
            <span className="font-bold text-zinc-900 uppercase tracking-wider text-[11px]">
              Defect Evidence Photos ({photos.length})
            </span>
            <div className="flex flex-wrap items-center gap-3">
              {photos.map((p, pIdx) => (
                <div
                  key={pIdx}
                  className="w-24 h-24 rounded-xl border border-zinc-200 overflow-hidden relative group bg-zinc-100 shadow-xs"
                >
                  <img
                    src={p.photo}
                    alt={p.caption || 'Evidence'}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-zinc-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-1">
                    <span className="text-[10px] text-white truncate">{p.caption || 'Photo'}</span>
                  </div>
                </div>
              ))}

              <label className="w-24 h-24 rounded-xl border-2 border-dashed border-zinc-300 hover:border-blue-500 hover:bg-blue-50/50 flex flex-col items-center justify-center gap-1.5 text-zinc-500 hover:text-blue-600 cursor-pointer transition-colors">
                <Camera className="w-5 h-5" />
                <span className="text-[10px] font-bold">
                  {uploadingPhoto ? 'Uploading...' : 'Add Photo'}
                </span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                  disabled={uploadingPhoto}
                  className="hidden"
                />
              </label>
            </div>
          </div>

          {/* Summary Diagnosis & Notes */}
          <div className="space-y-3 pt-3 border-t border-zinc-100">
            <div>
              <label className="block text-xs font-bold text-zinc-900 mb-1">
                Overall Diagnosis Summary
              </label>
              <textarea
                rows={2}
                value={diagnosis}
                onChange={(e) => setDiagnosis(e.target.value)}
                placeholder="Comprehensive diagnosis summary visible to customer..."
                className="w-full p-2.5 bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-zinc-900 mb-1">
                Internal Technician Notes (Optional)
              </label>
              <textarea
                rows={2}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Private notes for vendor management..."
                className="w-full p-2.5 bg-white border border-zinc-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-xs"
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-zinc-100 bg-zinc-50 flex items-center justify-between shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={handleSubmit}
            className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-xl shadow-sm flex items-center gap-2 transition-colors"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            <span>Submit Inspection & Proceed to Quotation</span>
          </button>
        </div>
      </div>
    </div>
  );
}
