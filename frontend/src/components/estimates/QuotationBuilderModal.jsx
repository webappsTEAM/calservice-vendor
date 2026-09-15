import React, { useState, useEffect } from 'react';
import {
  X,
  Plus,
  Trash2,
  Save,
  Send,
  Calculator,
  Ruler,
  Layers,
  FileText,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  ShieldCheck,
  ChevronRight,
  ChevronLeft,
} from 'lucide-react';
import PaintingInspectionForm from './PaintingInspectionForm.jsx';
import MasonInspectionForm from './MasonInspectionForm.jsx';
import {
  apiGetRateCards,
  apiGetQuoteDetail,
  apiCreateQuote,
  apiUpdateQuoteDraft,
  apiBulkSaveQuoteItems,
  apiBulkSaveQuoteMeasurements,
  apiSaveQuoteInspection,
  apiSendQuoteToCustomer,
} from '../../api/workforceService.js';

export default function QuotationBuilderModal({
  job,
  quoteId = null,
  isOpen,
  onClose,
  onQuoteSaved,
}) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const [activeQuoteId, setActiveQuoteId] = useState(quoteId);
  const [quoteNumber, setQuoteNumber] = useState('');
  const [quoteVersion, setQuoteVersion] = useState(1);
  const [quoteStatus, setQuoteStatus] = useState('DRAFT');

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [inspectionFeeAdjusted, setInspectionFeeAdjusted] = useState(0);

  const [inspectionData, setInspectionData] = useState({});
  const [measurements, setMeasurements] = useState([]);
  const [items, setItems] = useState([]);
  const [rateCards, setRateCards] = useState([]);

  const isPainting =
    job?.service_category?.toLowerCase().includes('painting') ||
    job?.issue_title?.toLowerCase().includes('painting');

  const isMason =
    job?.service_category?.toLowerCase().includes('mason') ||
    job?.issue_title?.toLowerCase().includes('mason') ||
    job?.issue_title?.toLowerCase().includes('brick') ||
    job?.issue_title?.toLowerCase().includes('plaster');

  // Load existing quote or initialize from job
  useEffect(() => {
    if (!isOpen) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Load rate cards
        const categoryParam = isPainting ? 'painting' : isMason ? 'mason' : '';
        const rCards = await apiGetRateCards(categoryParam);
        setRateCards(rCards || []);

        if (activeQuoteId) {
          const detail = await apiGetQuoteDetail(activeQuoteId);
          setQuoteNumber(detail.quote_number || '');
          setQuoteVersion(detail.quote_version || 1);
          setQuoteStatus(detail.status || 'DRAFT');
          setTitle(detail.title || '');
          setDescription(detail.description || '');
          setInspectionFeeAdjusted(detail.inspection_fee_adjusted || 0);
          setItems(detail.items || []);
          setMeasurements(detail.measurements || []);

          if (detail.painting_details) {
            setInspectionData(detail.painting_details);
          } else if (detail.mason_details) {
            setInspectionData(detail.mason_details);
          }
        } else if (job) {
          setTitle(`Quotation for ${job.issue_title || job.service_category}`);
          setDescription(`Site inspection and estimation for ${job.customer_name || 'Customer'}.`);

          // Pre-populate initial item suggestions from rate cards if empty
          if (rCards && rCards.length > 0) {
            const defaults = rCards.slice(0, 3).map((rc, idx) => ({
              id: `temp_${idx}`,
              section: rc.section,
              name: rc.item_name,
              description: rc.description || '',
              quantity: 1,
              unit: rc.unit,
              unit_price: parseFloat(rc.default_rate) || 0,
              tax_rate: parseFloat(rc.tax_rate) || 18,
              discount_amount: 0,
              material_source: 'CALTRACK',
            }));
            setItems(defaults);
          }
        }
      } catch (err) {
        console.error('Failed to load quotation builder data:', err);
        setError(err.message || 'Failed to initialize quotation data.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [isOpen, activeQuoteId, job]);

  // Live total calculations
  const calculateTotals = () => {
    let subtotal = 0;
    let totalDiscount = 0;
    let totalTax = 0;
    let materialsCost = 0;
    let laborCost = 0;

    items.forEach((item) => {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.unit_price) || 0;
      const disc = parseFloat(item.discount_amount) || 0;
      const taxRate = parseFloat(item.tax_rate) || 18;

      const gross = qty * price;
      const net = Math.max(0, gross - disc);
      const tax = net * (taxRate / 100);

      subtotal += net;
      totalDiscount += disc;
      totalTax += tax;

      if (item.section === 'MATERIAL') {
        materialsCost += net;
      } else if (item.section === 'LABOUR') {
        laborCost += net;
      }
    });

    const grandTotal = subtotal + totalTax;
    const netPayable = Math.max(0, grandTotal - (parseFloat(inspectionFeeAdjusted) || 0));

    return {
      subtotal: Math.round(subtotal * 100) / 100,
      totalDiscount: Math.round(totalDiscount * 100) / 100,
      totalTax: Math.round(totalTax * 100) / 100,
      grandTotal: Math.round(grandTotal * 100) / 100,
      netPayable: Math.round(netPayable * 100) / 100,
      materialsCost: Math.round(materialsCost * 100) / 100,
      laborCost: Math.round(laborCost * 100) / 100,
    };
  };

  const totals = calculateTotals();

  // Add line item
  const handleAddItem = (section = 'MATERIAL') => {
    setItems([
      ...items,
      {
        id: `temp_${Date.now()}`,
        section,
        name: '',
        description: '',
        quantity: 1,
        unit: isPainting ? 'sqft' : 'sqft',
        unit_price: 0,
        tax_rate: 18,
        discount_amount: 0,
        material_source: 'CALTRACK',
      },
    ]);
  };

  // Add line item from Rate Card select
  const handleSelectRateCardItem = (rcId) => {
    const rc = rateCards.find((r) => r.id === parseInt(rcId));
    if (!rc) return;
    setItems([
      ...items,
      {
        id: `temp_${Date.now()}`,
        section: rc.section,
        name: rc.item_name,
        description: rc.description || '',
        quantity: 1,
        unit: rc.unit,
        unit_price: parseFloat(rc.default_rate) || 0,
        tax_rate: parseFloat(rc.tax_rate) || 18,
        discount_amount: 0,
        material_source: 'CALTRACK',
      },
    ]);
  };

  const handleUpdateItem = (index, field, value) => {
    const updated = [...items];
    updated[index] = { ...updated[index], [field]: value };
    setItems(updated);
  };

  const handleRemoveItem = (index) => {
    setItems(items.filter((_, idx) => idx !== index));
  };

  // Measurement management
  const handleAddMeasurement = () => {
    setMeasurements([
      ...measurements,
      {
        name: `Area #${measurements.length + 1}`,
        measurement_type: 'area',
        length: 10,
        width: 10,
        height: 10,
        area: 100,
        unit: 'sqft',
        notes: '',
      },
    ]);
  };

  const handleUpdateMeasurement = (index, field, value) => {
    const updated = [...measurements];
    const item = { ...updated[index], [field]: value };

    // Auto compute area if length & height or width changed
    if (field === 'length' || field === 'height' || field === 'width') {
      const len = parseFloat(field === 'length' ? value : item.length) || 0;
      const hgt = parseFloat(field === 'height' ? value : item.height) || 0;
      const wid = parseFloat(field === 'width' ? value : item.width) || 0;
      if (len > 0 && hgt > 0) {
        item.area = Math.round(len * hgt * 100) / 100;
      } else if (len > 0 && wid > 0) {
        item.area = Math.round(len * wid * 100) / 100;
      }
    }

    updated[index] = item;
    setMeasurements(updated);
  };

  const handleRemoveMeasurement = (index) => {
    setMeasurements(measurements.filter((_, idx) => idx !== index));
  };

  // Save Draft to Backend
  const handleSaveDraft = async () => {
    setSaving(true);
    setError(null);
    setSuccessMsg(null);

    try {
      let currentId = activeQuoteId;

      if (!currentId) {
        // Create initial draft quote
        const created = await apiCreateQuote({
          job_id: job.id,
          title: title || `Quotation for ${job.issue_title}`,
          description,
          service_category: job.service_category,
          service_name: job.issue_title,
          inspection_fee: job.total_amount || 0,
          painting_details: isPainting ? inspectionData : undefined,
          mason_details: isMason ? inspectionData : undefined,
        });
        currentId = created.id;
        setActiveQuoteId(created.id);
        setQuoteNumber(created.quote_number);
      } else {
        await apiUpdateQuoteDraft(currentId, {
          title,
          description,
          inspection_fee_adjusted: inspectionFeeAdjusted,
          structural_impact: inspectionData.structural_impact || 'NONE',
        });
      }

      // Save Line Items in bulk
      if (items.length > 0) {
        await apiBulkSaveQuoteItems(currentId, items);
      }

      // Save Measurements
      if (measurements.length > 0) {
        await apiBulkSaveQuoteMeasurements(currentId, measurements);
      }

      // Save Inspection details
      if (Object.keys(inspectionData).length > 0) {
        await apiSaveQuoteInspection(currentId, {
          painting_details: isPainting ? inspectionData : undefined,
          mason_details: isMason ? inspectionData : undefined,
        });
      }

      setSuccessMsg('Draft quotation saved successfully!');
      if (onQuoteSaved) onQuoteSaved(currentId);
      setTimeout(() => setSuccessMsg(null), 3000);
      return currentId;
    } catch (err) {
      console.error('Failed to save draft quote:', err);
      setError(err.message || 'Failed to save quotation draft.');
      return null;
    } finally {
      setSaving(false);
    }
  };

  // Send Quote to Customer
  const handleSendQuote = async () => {
    setSending(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const currentId = await handleSaveDraft();
      if (!currentId) {
        throw new Error('Please save quotation before sending.');
      }

      const res = await apiSendQuoteToCustomer(currentId);
      setSuccessMsg(res.message || 'Quotation successfully sent to customer!');
      setQuoteStatus('SENT_TO_CUSTOMER');

      if (onQuoteSaved) onQuoteSaved(currentId);
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      console.error('Failed to send quote:', err);
      setError(err.message || 'Failed to send quotation to customer.');
    } finally {
      setSending(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6">
      <div className="bg-white dark:bg-gray-900 w-full max-w-4xl rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between bg-gray-50/80 dark:bg-gray-800/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-gray-900 dark:text-gray-100">
                  {quoteNumber ? `${quoteNumber} (v${quoteVersion})` : 'New Quotation Builder'}
                </h3>
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                    quoteStatus === 'SENT_TO_CUSTOMER'
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                      : quoteStatus === 'CUSTOMER_ACCEPTED'
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                      : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                  }`}
                >
                  {quoteStatus.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                {job?.issue_title || 'Site Inspection'} • {job?.customer_name || 'Customer'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden sm:flex flex-col items-end px-3 py-1 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
              <span className="text-[10px] uppercase font-bold text-gray-400">Estimated Total</span>
              <span className="text-sm font-extrabold text-blue-600 dark:text-blue-400">
                ₹{totals.netPayable.toLocaleString()}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Stepper Tabs */}
        <div className="px-6 py-2.5 bg-gray-100/70 dark:bg-gray-800/40 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between text-xs font-medium overflow-x-auto">
          {[
            { num: 1, label: '1. Site Inspection', icon: Layers },
            { num: 2, label: '2. Measurements', icon: Ruler },
            { num: 3, label: '3. Line Items & Pricing', icon: Calculator },
            { num: 4, label: '4. Review & Finalize', icon: FileText },
          ].map((s) => {
            const Icon = s.icon;
            const isActive = step === s.num;
            return (
              <button
                key={s.num}
                onClick={() => setStep(s.num)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${
                  isActive
                    ? 'bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400 font-semibold shadow-sm border border-gray-200 dark:border-gray-700'
                    : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{s.label}</span>
              </button>
            );
          })}
        </div>

        {/* Messages */}
        {error && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 flex items-center gap-2.5 text-xs text-red-800 dark:text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mx-6 mt-4 p-3 rounded-xl bg-green-50 dark:bg-green-950/40 border border-green-200 dark:border-green-800/60 flex items-center gap-2.5 text-xs text-green-800 dark:text-green-300">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-green-600" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {loading ? (
            <div className="py-16 text-center text-gray-500 text-sm">
              <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              Loading quotation parameters & rate cards...
            </div>
          ) : (
            <>
              {/* STEP 1: Inspection Form */}
              {step === 1 && (
                <div className="space-y-4">
                  {isPainting ? (
                    <PaintingInspectionForm data={inspectionData} onChange={setInspectionData} />
                  ) : isMason ? (
                    <MasonInspectionForm data={inspectionData} onChange={setInspectionData} />
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                          Quotation Title
                        </label>
                        <input
                          type="text"
                          value={title}
                          onChange={(e) => setTitle(e.target.value)}
                          className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2.5"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                          Scope & Findings
                        </label>
                        <textarea
                          rows={3}
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2.5"
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* STEP 2: Measurements */}
              {step === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                        Dimensional Site Measurements
                      </h4>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Log wall, room, or structural dimensions measured with laser/measuring tape.
                      </p>
                    </div>
                    <button
                      onClick={handleAddMeasurement}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800 hover:bg-blue-100"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Measurement
                    </button>
                  </div>

                  {measurements.length === 0 ? (
                    <div className="text-center py-10 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                      <Ruler className="w-8 h-8 text-gray-400 mx-auto mb-2 opacity-60" />
                      <p className="text-xs text-gray-500 font-medium">No site measurements recorded yet.</p>
                      <button
                        onClick={handleAddMeasurement}
                        className="mt-3 text-xs font-semibold text-blue-600 hover:underline"
                      >
                        + Add first room/wall measurement
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {measurements.map((m, idx) => (
                        <div
                          key={idx}
                          className="p-3.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/40 grid grid-cols-1 sm:grid-cols-12 gap-3 items-center"
                        >
                          <div className="sm:col-span-4">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Area / Location
                            </label>
                            <input
                              type="text"
                              value={m.name}
                              onChange={(e) => handleUpdateMeasurement(idx, 'name', e.target.value)}
                              placeholder="e.g. Master Bedroom Wall"
                              className="w-full text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <div className="sm:col-span-2">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Length (Ft)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={m.length || ''}
                              onChange={(e) => handleUpdateMeasurement(idx, 'length', e.target.value)}
                              className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-2">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Height (Ft)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={m.height || ''}
                              onChange={(e) => handleUpdateMeasurement(idx, 'height', e.target.value)}
                              className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-3">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Area (Sq.Ft.)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={m.area || ''}
                              onChange={(e) => handleUpdateMeasurement(idx, 'area', parseFloat(e.target.value) || 0)}
                              className="w-full text-xs font-bold rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 text-blue-600 dark:text-blue-400"
                            />
                          </div>

                          <div className="sm:col-span-1 flex justify-end pt-4">
                            <button
                              onClick={() => handleRemoveMeasurement(idx)}
                              className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* STEP 3: Line Items & Rate Cards */}
              {step === 3 && (
                <div className="space-y-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-blue-50/50 dark:bg-blue-950/20 p-3.5 rounded-xl border border-blue-100 dark:border-blue-900/40">
                    <div>
                      <h4 className="text-xs font-bold text-blue-900 dark:text-blue-200">
                        Add from Approved Rate Card Catalog
                      </h4>
                      <p className="text-[11px] text-blue-700 dark:text-blue-300">
                        Select pre-approved standard rates for material, labour, and logistics.
                      </p>
                    </div>

                    <select
                      onChange={(e) => {
                        if (e.target.value) {
                          handleSelectRateCardItem(e.target.value);
                          e.target.value = '';
                        }
                      }}
                      defaultValue=""
                      className="text-xs rounded-lg border border-blue-300 dark:border-blue-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                    >
                      <option value="" disabled>
                        + Choose approved item...
                      </option>
                      {rateCards.map((rc) => (
                        <option key={rc.id} value={rc.id}>
                          [{rc.section}] {rc.item_name} — ₹{rc.default_rate}/{rc.unit}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Items List */}
                  <div className="space-y-3">
                    {items.map((item, idx) => (
                      <div
                        key={item.id || idx}
                        className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/80 shadow-sm space-y-3"
                      >
                        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
                          <div className="sm:col-span-3">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Section
                            </label>
                            <select
                              value={item.section || 'MATERIAL'}
                              onChange={(e) => handleUpdateItem(idx, 'section', e.target.value)}
                              className="w-full text-xs font-semibold rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 p-2"
                            >
                              <option value="MATERIAL">Material</option>
                              <option value="LABOUR">Labour</option>
                              <option value="SURFACE_PREP">Surface Prep</option>
                              <option value="EQUIPMENT">Equipment & Scaffolding</option>
                              <option value="TRANSPORT">Transport & Logistics</option>
                              <option value="OTHER">Other</option>
                            </select>
                          </div>

                          <div className="sm:col-span-5">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Item Name / Scope
                            </label>
                            <input
                              type="text"
                              value={item.name}
                              onChange={(e) => handleUpdateItem(idx, 'name', e.target.value)}
                              placeholder="e.g. Premium Acrylic Emulsion"
                              className="w-full text-xs font-semibold rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2 focus:ring-1 focus:ring-blue-500"
                            />
                          </div>

                          <div className="sm:col-span-2">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Quantity
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={item.quantity || ''}
                              onChange={(e) =>
                                handleUpdateItem(idx, 'quantity', parseFloat(e.target.value) || 0)
                              }
                              className="w-full text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-2">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Unit
                            </label>
                            <input
                              type="text"
                              value={item.unit || 'sqft'}
                              onChange={(e) => handleUpdateItem(idx, 'unit', e.target.value)}
                              className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center pt-1 border-t border-gray-100 dark:border-gray-700/60">
                          <div className="sm:col-span-3">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Rate (₹)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={item.unit_price || ''}
                              onChange={(e) =>
                                handleUpdateItem(idx, 'unit_price', parseFloat(e.target.value) || 0)
                              }
                              className="w-full text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-3">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Discount (₹)
                            </label>
                            <input
                              type="number"
                              step="0.1"
                              value={item.discount_amount || ''}
                              onChange={(e) =>
                                handleUpdateItem(idx, 'discount_amount', parseFloat(e.target.value) || 0)
                              }
                              className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-3">
                            <label className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Tax (GST %)
                            </label>
                            <input
                              type="number"
                              value={item.tax_rate ?? 18}
                              onChange={(e) =>
                                handleUpdateItem(idx, 'tax_rate', parseFloat(e.target.value) || 0)
                              }
                              className="w-full text-xs rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-2"
                            />
                          </div>

                          <div className="sm:col-span-2 text-right">
                            <span className="block text-[10px] font-bold text-gray-400 uppercase mb-1">
                              Net Total
                            </span>
                            <span className="text-xs font-extrabold text-gray-900 dark:text-gray-100">
                              ₹
                              {(
                                Math.max(0, (item.quantity || 1) * (item.unit_price || 0) - (item.discount_amount || 0))
                              ).toLocaleString()}
                            </span>
                          </div>

                          <div className="sm:col-span-1 flex justify-end">
                            <button
                              onClick={() => handleRemoveItem(idx)}
                              className="p-1.5 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/40"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => handleAddItem('MATERIAL')}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    + Add Custom Line Item
                  </button>
                </div>
              )}

              {/* STEP 4: Review & Finalize */}
              {step === 4 && (
                <div className="space-y-6">
                  <div className="p-5 rounded-2xl border border-gray-200 dark:border-gray-700 bg-gray-50/70 dark:bg-gray-800/40 space-y-4">
                    <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-3">
                      <div>
                        <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                          {title || `Quotation for ${job?.issue_title}`}
                        </h4>
                        <p className="text-xs text-gray-500 mt-0.5">{job?.address}</p>
                      </div>
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300">
                        {quoteNumber || 'DRAFT'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                      <div>
                        <span className="text-gray-500 dark:text-gray-400 block text-[11px]">Material Subtotal</span>
                        <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                          ₹{totals.materialsCost.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400 block text-[11px]">Labour Subtotal</span>
                        <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                          ₹{totals.laborCost.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400 block text-[11px]">GST / Tax (18%)</span>
                        <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                          ₹{totals.totalTax.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500 dark:text-gray-400 block text-[11px]">Gross Total</span>
                        <span className="font-bold text-gray-900 dark:text-gray-100 text-sm">
                          ₹{totals.grandTotal.toLocaleString()}
                        </span>
                      </div>
                    </div>

                    <div className="pt-3 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-300">
                          Adjust Inspection Fee (₹):
                        </label>
                        <input
                          type="number"
                          value={inspectionFeeAdjusted}
                          onChange={(e) => setInspectionFeeAdjusted(parseFloat(e.target.value) || 0)}
                          className="w-24 text-xs font-semibold rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 p-1.5 text-right"
                        />
                      </div>

                      <div className="flex items-center gap-3">
                        <span className="text-xs font-bold text-gray-700 dark:text-gray-300">Net Payable:</span>
                        <span className="text-xl font-black text-blue-600 dark:text-blue-400">
                          ₹{totals.netPayable.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Summary of Items */}
                  <div>
                    <h5 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-2">
                      Line Items Breakdown ({items.length})
                    </h5>
                    <div className="divide-y divide-gray-100 dark:divide-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden text-xs">
                      {items.map((item, idx) => (
                        <div key={idx} className="p-3 flex items-center justify-between bg-white dark:bg-gray-800">
                          <div>
                            <span className="text-[10px] font-bold text-blue-600 dark:text-blue-400 mr-2">
                              [{item.section}]
                            </span>
                            <span className="font-medium text-gray-900 dark:text-gray-100">{item.name}</span>
                            <span className="text-gray-400 text-[11px] ml-2">
                              ({item.quantity} {item.unit} @ ₹{item.unit_price})
                            </span>
                          </div>
                          <span className="font-bold text-gray-900 dark:text-gray-100">
                            ₹
                            {(
                              Math.max(0, (item.quantity || 1) * (item.unit_price || 0) - (item.discount_amount || 0))
                            ).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Navigation */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50/80 dark:bg-gray-800/50 flex items-center justify-between">
          <div>
            {step > 1 ? (
              <button
                onClick={() => setStep(step - 1)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
            ) : (
              <span />
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSaveDraft}
              disabled={saving || sending}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 shadow-sm disabled:opacity-50"
            >
              <Save className="w-4 h-4 text-gray-500" />
              {saving ? 'Saving...' : 'Save Draft'}
            </button>

            {step < 4 ? (
              <button
                onClick={() => setStep(step + 1)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-5 py-2 rounded-xl bg-blue-600 text-white hover:bg-blue-700 shadow-md shadow-blue-600/20"
              >
                Next Step
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleSendQuote}
                disabled={sending || saving || items.length === 0}
                className="inline-flex items-center gap-1.5 text-xs font-bold px-5 py-2 rounded-xl bg-green-600 text-white hover:bg-green-700 shadow-md shadow-green-600/20 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                {sending ? 'Sending to Customer...' : 'Send Quote to Customer'}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
