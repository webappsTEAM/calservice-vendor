import React, { useState, useEffect, useMemo } from 'react';
import {
  X,
  Plus,
  Trash2,
  FileSpreadsheet,
  Send,
  Save,
  CheckCircle2,
  AlertCircle,
  Percent,
  Receipt,
  Calendar,
  ShieldAlert,
  Loader2,
} from 'lucide-react';
import { apiSaveQuotation, apiSendQuotation } from '../../api/vendorEstimationService.js';

const QUICK_ITEM_TEMPLATES = [
  // HVAC & AC
  { title: 'R32 / R410A Refrigerant Gas Refill (Up to 1kg)', item_type: 'PART', unit_price: 1850, quantity: 1, unit: 'kg' },
  { title: 'Gas Leakage Repair & Nitrogen Pressure Brazing', item_type: 'LABOR', unit_price: 650, quantity: 1, unit: 'job' },
  { title: 'Inverter Dual Run Capacitor (45/5 uF)', item_type: 'PART', unit_price: 850, quantity: 1, unit: 'pc' },
  { title: 'Inverter PCB Motherboard Repair & Servicing', item_type: 'PART', unit_price: 2450, quantity: 1, unit: 'unit' },
  { title: 'Condenser Fan Motor Replacement', item_type: 'PART', unit_price: 1650, quantity: 1, unit: 'pc' },
  { title: 'Chemical Jet Foam Deep Coil Wash', item_type: 'LABOR', unit_price: 799, quantity: 1, unit: 'service' },
  // Plumbing
  { title: 'CPVC Concealed Pipe Line Repair & Joint Fitting', item_type: 'LABOR', unit_price: 650, quantity: 1, unit: 'point' },
  { title: 'Heavy-Duty Brass Ball Valve (1 Inch)', item_type: 'PART', unit_price: 450, quantity: 1, unit: 'pc' },
  { title: 'Drain Line Mechanical Snaking & Hydro Jetting', item_type: 'LABOR', unit_price: 950, quantity: 1, unit: 'service' },
  // Electrical
  { title: 'Distribution Board MCB Breaker (32A Double Pole)', item_type: 'PART', unit_price: 550, quantity: 1, unit: 'pc' },
  { title: 'Circuit Load Balancing & Diagnostic Rewiring', item_type: 'LABOR', unit_price: 850, quantity: 1, unit: 'job' },
  // Painting & Surface
  { title: 'Wall Crack Polymer Putty & Seepage Barrier (Per Sqft)', item_type: 'PART', unit_price: 35, quantity: 100, unit: 'sqft' },
  { title: 'Surface Waterproofing & Primer Application', item_type: 'LABOR', unit_price: 18, quantity: 100, unit: 'sqft' },
  // General Diagnostics
  { title: 'Senior Specialist On-Site Technical Diagnosis', item_type: 'LABOR', unit_price: 299, quantity: 1, unit: 'service' },
];

export default function VendorQuotationBuilder({
  estimation,
  isOpen,
  onClose,
  onQuotationSent,
}) {
  const [items, setItems] = useState([]);
  const [applyGst, setApplyGst] = useState(true);
  const [taxRatePercent, setTaxRatePercent] = useState(18);
  const [discountAmount, setDiscountAmount] = useState(0);
  const [validUntil, setValidUntil] = useState('');
  const [notes, setNotes] = useState('Includes 90-day CalServices warranty on all replacement parts and labor.');
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [createdQuote, setCreatedQuote] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setError(null);
      setShowConfirmModal(false);

      // Default valid until: 7 days from today
      const d = new Date();
      d.setDate(d.getDate() + 7);
      setValidUntil(d.toISOString().split('T')[0]);

      // Check if existing quote exists to preload
      const latest = estimation?.latest_quotation || (estimation?.quotations && estimation.quotations[0]);
      if (latest && latest.items && latest.items.length > 0) {
        setItems(latest.items.map((it) => ({
          title: it.service_name || it.title,
          item_type: it.item_type || 'LABOR',
          quantity: Number(it.quantity) || 1,
          unit: it.unit || 'unit',
          unit_price: Number(it.unit_price) || 0,
        })));
        setTaxRatePercent(latest.tax_amount > 0 ? 18 : 0);
        setApplyGst(latest.tax_amount > 0);
        setDiscountAmount(Number(latest.discount_amount) || 0);
        setNotes(latest.notes || notes);
        setCreatedQuote(latest);
      } else {
        // Preload based on inspection findings if available
        if (estimation?.findings && estimation.findings.length > 0) {
          const generatedItems = estimation.findings.map((f) => {
            let p = 650;
            let itType = 'LABOR';
            if (f.finding_type?.toLowerCase().includes('gas')) {
              p = 1850;
              itType = 'GAS';
            } else if (f.finding_type?.toLowerCase().includes('pcb') || f.finding_type?.toLowerCase().includes('motor')) {
              p = 1950;
              itType = 'PART';
            } else if (f.finding_type?.toLowerCase().includes('coil')) {
              p = 799;
              itType = 'LABOR';
            }
            return {
              title: f.recommended_action || f.title,
              item_type: itType,
              quantity: Number(f.quantity) || 1,
              unit: f.unit || 'unit',
              unit_price: p,
            };
          });
          setItems(generatedItems);
        } else {
          // Default starting line item
          setItems([
            {
              title: 'AC Diagnosis & Remedial Service',
              item_type: 'LABOR',
              quantity: 1,
              unit: 'job',
              unit_price: 650,
            },
          ]);
        }
      }
    }
  }, [isOpen, estimation]);

  // Real-time calculations
  const subtotal = useMemo(() => {
    return items.reduce((sum, it) => sum + (Number(it.quantity) || 0) * (Number(it.unit_price) || 0), 0);
  }, [items]);

  const taxAmount = useMemo(() => {
    if (!applyGst) return 0;
    return Math.round(subtotal * (Number(taxRatePercent) / 100) * 100) / 100;
  }, [subtotal, applyGst, taxRatePercent]);

  const grandTotal = useMemo(() => {
    const tot = subtotal + taxAmount - (Number(discountAmount) || 0);
    return Math.max(0, Math.round(tot * 100) / 100);
  }, [subtotal, taxAmount, discountAmount]);

  if (!isOpen) return null;

  const handleAddItem = (type = 'LABOR') => {
    setItems([
      ...items,
      {
        title: type === 'GAS' ? 'Refrigerant Gas' : type === 'PART' ? 'Spare Component' : 'Labor Service',
        item_type: type,
        quantity: 1,
        unit: 'unit',
        unit_price: 500,
      },
    ]);
  };

  const handleQuickAdd = (tpl) => {
    setItems([...items, { ...tpl }]);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, idx) => idx !== index));
  };

  const handleItemChange = (index, field, val) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: val };
    setItems(updated);
  };

  const handleSaveDraft = async () => {
    if (items.length === 0) {
      setError('Please add at least one line item.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const payload = {
        valid_until: validUntil,
        tax_rate_percent: applyGst ? taxRatePercent : 0,
        discount_amount: Number(discountAmount) || 0,
        notes: notes,
        items: items.map((it) => ({
          title: it.title,
          item_type: it.item_type,
          quantity: Number(it.quantity) || 1,
          unit: it.unit,
          unit_price: Number(it.unit_price) || 0,
        })),
      };

      const res = await apiSaveQuotation(estimation.id, payload);
      const latestQ = res?.data?.latest_quotation || (res?.data?.quotations && res.data.quotations[0]);
      setCreatedQuote(latestQ);
      return latestQ;
    } catch (err) {
      setError(err.message || 'Failed to save quotation draft.');
      return null;
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmSend = async () => {
    setSending(true);
    setError(null);
    try {
      // 1. Save / Update draft first to ensure latest edits are saved
      const quote = await handleSaveDraft();
      const quoteId = quote?.id || createdQuote?.id;

      if (!quoteId) {
        throw new Error('Unable to resolve quotation ID for dispatch.');
      }

      // 2. Publish to customer
      const res = await apiSendQuotation(estimation.id, quoteId);
      setShowConfirmModal(false);
      onQuotationSent?.(res?.data || res);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to send quotation to customer.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-zinc-950/70 backdrop-blur-xs animate-in fade-in overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-white rounded-2xl shadow-2xl border border-zinc-200 overflow-hidden my-auto max-h-[94vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-zinc-100 bg-zinc-50 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm sm:text-base font-bold text-zinc-900">
                Official Commercial Quotation Builder
              </h2>
              <p className="text-xs text-zinc-500">
                Job #{estimation?.request_id} • Customer: {estimation?.customer_name}
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

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-red-700 font-medium">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
              <span>{error}</span>
            </div>
          )}

          {/* Quick-Add Presets */}
          <div>
            <span className="font-bold text-zinc-900 uppercase tracking-wider text-[11px] block mb-2">
              Common AC Repair Line Item Catalog Presets
            </span>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_ITEM_TEMPLATES.map((tpl, tIdx) => (
                <button
                  key={tIdx}
                  type="button"
                  onClick={() => handleQuickAdd(tpl)}
                  className="px-2.5 py-1 text-[11px] font-medium bg-zinc-100 hover:bg-zinc-200 text-zinc-700 rounded-lg flex items-center gap-1 transition-colors"
                >
                  <Plus className="w-3 h-3 text-zinc-400" />
                  <span>{tpl.title}</span>
                  <strong className="text-zinc-900 font-mono">₹{tpl.unit_price}</strong>
                </button>
              ))}
            </div>
          </div>

          {/* Line Items Table */}
          <div className="border border-zinc-200 rounded-xl overflow-hidden shadow-xs">
            <div className="bg-zinc-50 px-4 py-2.5 border-b border-zinc-200 flex items-center justify-between">
              <span className="font-bold text-zinc-800 text-[11px] uppercase tracking-wider">
                Quotation Line Items ({items.length})
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleAddItem('LABOR')}
                  className="px-2.5 py-1 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 font-bold rounded-lg flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Labor
                </button>
                <button
                  type="button"
                  onClick={() => handleAddItem('PART')}
                  className="px-2.5 py-1 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 font-bold rounded-lg flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Part
                </button>
                <button
                  type="button"
                  onClick={() => handleAddItem('GAS')}
                  className="px-2.5 py-1 bg-white border border-zinc-300 hover:bg-zinc-100 text-zinc-700 font-bold rounded-lg flex items-center gap-1"
                >
                  <Plus className="w-3 h-3" /> Add Gas
                </button>
              </div>
            </div>

            <div className="divide-y divide-zinc-100">
              {items.map((item, idx) => {
                const lineTotal = (Number(item.quantity) || 0) * (Number(item.unit_price) || 0);
                return (
                  <div key={idx} className="p-3 bg-white hover:bg-zinc-50/50 flex flex-col sm:flex-row sm:items-center gap-2.5">
                    {/* Item Type Badge */}
                    <select
                      value={item.item_type}
                      onChange={(e) => handleItemChange(idx, 'item_type', e.target.value)}
                      className="w-24 text-[10px] font-bold uppercase px-2 py-1 bg-zinc-100 border border-zinc-200 rounded-md"
                    >
                      <option value="LABOR">LABOR</option>
                      <option value="PART">PART</option>
                      <option value="GAS">GAS</option>
                      <option value="OTHER">OTHER</option>
                    </select>

                    {/* Title Description */}
                    <input
                      type="text"
                      value={item.title}
                      onChange={(e) => handleItemChange(idx, 'title', e.target.value)}
                      placeholder="Service / Component title"
                      className="flex-1 px-2.5 py-1 border border-zinc-200 rounded-md text-xs font-medium"
                    />

                    {/* Quantity & Unit */}
                    <div className="flex items-center gap-1.5 w-28">
                      <input
                        type="number"
                        min="1"
                        step="0.5"
                        value={item.quantity}
                        onChange={(e) => handleItemChange(idx, 'quantity', e.target.value)}
                        className="w-14 px-2 py-1 border border-zinc-200 rounded-md text-xs text-center font-mono"
                      />
                      <input
                        type="text"
                        value={item.unit}
                        onChange={(e) => handleItemChange(idx, 'unit', e.target.value)}
                        placeholder="unit"
                        className="w-12 px-1.5 py-1 border border-zinc-200 rounded-md text-[11px] text-zinc-500 text-center"
                      />
                    </div>

                    {/* Unit Price */}
                    <div className="flex items-center gap-1 w-28">
                      <span className="text-zinc-400 font-mono">₹</span>
                      <input
                        type="number"
                        min="0"
                        step="10"
                        value={item.unit_price}
                        onChange={(e) => handleItemChange(idx, 'unit_price', e.target.value)}
                        className="w-full px-2 py-1 border border-zinc-200 rounded-md text-xs font-mono font-bold"
                      />
                    </div>

                    {/* Line Total */}
                    <div className="w-24 text-right font-mono font-bold text-zinc-900 pr-1">
                      ₹{lineTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>

                    {/* Remove */}
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(idx)}
                      className="p-1 rounded text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pricing Summary & Taxes */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-zinc-50/80 p-4 rounded-xl border border-zinc-200">
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  Quotation Validity
                </label>
                <div className="relative">
                  <input
                    type="date"
                    value={validUntil}
                    onChange={(e) => setValidUntil(e.target.value)}
                    className="w-full px-3 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-zinc-700 mb-1">
                  Customer Guarantee & Warranty Terms
                </label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full p-2.5 bg-white border border-zinc-200 rounded-lg text-xs"
                />
              </div>
            </div>

            {/* Calculations Panel */}
            <div className="space-y-2.5 self-center bg-white p-4 rounded-xl border border-zinc-200 shadow-xs">
              <div className="flex justify-between items-center text-zinc-600">
                <span>Subtotal (Base Services & Parts)</span>
                <span className="font-mono font-semibold text-zinc-900">
                  ₹{subtotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>

              <div className="flex justify-between items-center py-1 border-y border-zinc-100">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="gstToggle"
                    checked={applyGst}
                    onChange={(e) => setApplyGst(e.target.checked)}
                    className="rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <label htmlFor="gstToggle" className="text-xs font-medium text-zinc-700 cursor-pointer">
                    Apply 18% GST ({applyGst ? 'CGST 9% + SGST 9%' : 'Exempt'})
                  </label>
                </div>
                <span className="font-mono font-semibold text-zinc-900">
                  ₹{taxAmount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>

              <div className="flex justify-between items-center text-zinc-600">
                <span>Special Goodwill Discount</span>
                <div className="flex items-center gap-1 w-24">
                  <span className="text-zinc-400 font-mono">₹</span>
                  <input
                    type="number"
                    min="0"
                    value={discountAmount}
                    onChange={(e) => setDiscountAmount(e.target.value)}
                    className="w-full text-right px-1.5 py-0.5 border border-zinc-200 rounded text-xs font-mono"
                  />
                </div>
              </div>

              <div className="pt-2 border-t-2 border-zinc-900 flex justify-between items-center">
                <div>
                  <span className="text-xs font-bold text-zinc-900 block">Grand Total</span>
                  <span className="text-[10px] text-zinc-500">Including applicable taxes</span>
                </div>
                <span className="text-base font-black font-mono text-emerald-600">
                  ₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
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
          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={saving}
              onClick={handleSaveDraft}
              className="px-4 py-2 text-xs font-semibold text-zinc-700 bg-white border border-zinc-300 hover:bg-zinc-100 disabled:opacity-50 rounded-xl shadow-xs flex items-center gap-1.5 transition-colors"
            >
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
              <span>Save Draft</span>
            </button>
            <button
              type="button"
              onClick={() => setShowConfirmModal(true)}
              className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-sm flex items-center gap-2 transition-colors"
            >
              <Send className="w-4 h-4" />
              <span>Review & Send to Customer</span>
            </button>
          </div>
        </div>

        {/* Send Confirmation Modal */}
        {showConfirmModal && (
          <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/60 backdrop-blur-xs animate-in fade-in">
            <div className="bg-white rounded-xl max-w-sm w-full p-5 space-y-4 shadow-2xl border border-zinc-200 text-center">
              <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                <Send className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-zinc-900">
                  Send Quotation to Customer?
                </h3>
                <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                  Quotation total of <strong className="text-zinc-900 font-mono">₹{grandTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong> will be dispatched to {estimation?.customer_name}. The customer will be able to Approve or Reject online.
                </p>
              </div>
              <div className="flex items-center justify-center gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setShowConfirmModal(false)}
                  className="px-3.5 py-1.5 text-xs font-semibold text-zinc-600 hover:bg-zinc-100 rounded-lg"
                >
                  Back to Editing
                </button>
                <button
                  type="button"
                  disabled={sending}
                  onClick={handleConfirmSend}
                  className="px-4 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 rounded-lg flex items-center gap-1.5"
                >
                  {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  <span>{sending ? 'Sending...' : 'Confirm & Send'}</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
