import React, { useState, useEffect } from 'react';
import { X, UserCheck, Phone, Wrench, AlertCircle, Loader2 } from 'lucide-react';
import { apiAssignTechnician, apiGetVendorTechnicians } from '../../api/vendorEstimationService.js';

export default function TechnicianAssignModal({ estimation, isOpen, onClose, onSuccess }) {
  const [technicians, setTechnicians] = useState([]);
  const [loadingTechs, setLoadingTechs] = useState(false);
  const [selectedTechId, setSelectedTechId] = useState('');
  const [customName, setCustomName] = useState('');
  const [customPhone, setCustomPhone] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setCustomName(estimation?.technician?.name || '');
      setCustomPhone(estimation?.technician?.phone || '');
      fetchTechs();
    }
  }, [isOpen, estimation]);

  const fetchTechs = async () => {
    setLoadingTechs(true);
    try {
      const res = await apiGetVendorTechnicians();
      setTechnicians(res?.technicians || []);
    } catch (err) {
      console.warn('Could not fetch technicians list:', err);
    } finally {
      setLoadingTechs(false);
    }
  };

  const handleTechSelect = (e) => {
    const techId = e.target.value;
    setSelectedTechId(techId);
    if (techId) {
      const matched = technicians.find((t) => String(t.id) === String(techId));
      if (matched) {
        setCustomName(matched.name);
        setCustomPhone(matched.phone || '');
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!customName.trim()) {
      setError('Technician name is required.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const res = await apiAssignTechnician(estimation.id, {
        technician_id: selectedTechId || null,
        technician_name: customName.trim(),
        technician_phone: customPhone.trim(),
      });
      onSuccess?.(res?.data || res);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to assign technician.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-xs animate-in fade-in">
      <div className="relative w-full max-w-md bg-white rounded-xl shadow-2xl border border-zinc-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-100 bg-zinc-50/80">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-100">
              <Wrench className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-900">Assign Technician</h3>
              <p className="text-[11px] text-zinc-500">Lead #{estimation?.request_id || estimation?.id}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          {technicians.length > 0 && (
            <div>
              <label className="block text-xs font-semibold text-zinc-700 mb-1">
                Select from Available Team
              </label>
              <select
                value={selectedTechId}
                onChange={handleTechSelect}
                className="w-full text-xs px-3 py-2 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white"
              >
                <option value="">-- Choose team member or enter custom below --</option>
                {technicians.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.title || 'Technician'}) {t.phone ? `- ${t.phone}` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-zinc-700 mb-1">
              Technician Full Name <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="e.g. Suresh Kumar"
                required
                className="w-full text-xs px-3 py-2 pl-9 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
              <UserCheck className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-700 mb-1">
              Mobile Contact Number
            </label>
            <div className="relative">
              <input
                type="tel"
                value={customPhone}
                onChange={(e) => setCustomPhone(e.target.value)}
                placeholder="e.g. +91 98765 43210"
                className="w-full text-xs px-3 py-2 pl-9 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
              <Phone className="w-4 h-4 text-zinc-400 absolute left-3 top-2.5" />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-zinc-100">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-sm flex items-center gap-1.5 transition-colors"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <UserCheck className="w-3.5 h-3.5" />}
              <span>{saving ? 'Assigning...' : 'Confirm Assignment'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
