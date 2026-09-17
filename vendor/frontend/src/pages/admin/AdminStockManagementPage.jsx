/**
 * AdminStockManagementPage.jsx
 *
 * VENDOR_STOCK_MANAGEMENT_IMPLEMENTATION_PLAN.md Phase 3.
 *
 * Where a vendor manages their own Daily Essentials / produce stock:
 * restocking, marking items out of stock, and price changes. Talks to the
 * company-scoped endpoints in vendor/backend/inventory/views.py -- every
 * write here only ever touches this vendor's own company (enforced
 * server-side, not just hidden client-side). Mounted at
 * /workforce/admin/stock.
 *
 * Mirrors the *shape* of the stock cards the Customer app's now-retired
 * Super Admin Edit Mode used to show (state, today available, price/MRP,
 * reorder & restock levels) so the transition is familiar, but every action
 * here is scoped to this vendor instead of being a platform-wide edit.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle, CheckCircle2, Loader2, RefreshCw, PackagePlus, PackageX,
  Pencil, History, X, Lock,
} from 'lucide-react';
import {
  fetchVendorStock,
  restockProduct,
  markProductOutOfStock,
  adjustProductStock,
  updateProductDetails,
  fetchProductStockHistory,
  extractStockErrorMessage,
} from '../../api/stockService.js';

const STATE_BADGE = {
  in_stock: { label: 'In stock', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  out_of_stock: { label: 'Out of stock', className: 'bg-rose-50 text-rose-700 border-rose-200' },
  not_tracked: { label: 'Not tracked', className: 'bg-slate-100 text-slate-600 border-slate-200' },
};

export function AdminStockManagementPage() {
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [flash, setFlash] = useState(null);
  const [openPanel, setOpenPanel] = useState(null); // { productId, mode: 'restock'|'adjust'|'edit'|'history' }

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await fetchVendorStock();
      setProducts(Array.isArray(res?.data) ? res.data : []);
      setError(null);
    } catch (err) {
      setError(extractStockErrorMessage(err, 'Could not load your stock.'));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  function flashThenClear(message) {
    setFlash(message);
    window.clearTimeout(flashThenClear._t);
    flashThenClear._t = window.setTimeout(() => setFlash(null), 4000);
  }

  async function refreshOne(productId, patchFromResponse) {
    setProducts((prev) => prev.map((p) => (
      p.product_id === productId ? { ...p, ...patchFromResponse } : p
    )));
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Stock management</h1>
          <p className="text-sm text-slate-600 mt-1">
            Restock, mark items out of stock, and update prices for your Daily Essentials
            products. Changes here only affect stock you own -- a product another vendor
            already manages shows as read-only.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-2 text-sm text-slate-600 border border-slate-300 rounded-lg px-3 py-2 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {flash && (
        <div className="mb-4 bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <p className="text-sm text-emerald-900">{flash}</p>
        </div>
      )}

      {error && (
        <div className="mb-4 bg-rose-50 border border-rose-200 rounded-xl p-4 flex gap-3">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-rose-900">{error}</p>
            <button type="button" onClick={load} className="text-sm text-rose-700 underline mt-1">
              Try again
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="py-16 flex justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-slate-400" />
        </div>
      ) : products.length === 0 ? (
        <p className="py-16 text-center text-sm text-slate-500">
          No Daily Essentials products found.
        </p>
      ) : (
        <div className="space-y-4">
          {products.map((p) => (
            <StockCard
              key={p.product_id}
              product={p}
              isPanelOpen={openPanel?.productId === p.product_id ? openPanel.mode : null}
              onTogglePanel={(mode) => setOpenPanel((prev) => (
                prev?.productId === p.product_id && prev.mode === mode ? null : { productId: p.product_id, mode }
              ))}
              onClosePanel={() => setOpenPanel(null)}
              onError={(err) => setError(extractStockErrorMessage(err))}
              onSuccess={(message, patch) => {
                flashThenClear(message);
                setError(null);
                if (patch) refreshOne(p.product_id, patch);
                else load();
              }}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function StockCard({ product: p, isPanelOpen, onTogglePanel, onClosePanel, onError, onSuccess }) {
  const badge = STATE_BADGE[p.state] || STATE_BADGE.not_tracked;
  const locked = p.is_claimed && p.is_mine === false;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3 min-w-0">
          {p.image ? (
            <img src={p.image} alt="" className="w-12 h-12 rounded-lg object-cover border border-slate-200 shrink-0" />
          ) : (
            <div className="w-12 h-12 rounded-lg bg-slate-100 shrink-0" />
          )}
          <div className="min-w-0">
            <h2 className="font-medium text-slate-900 truncate">{p.name}</h2>
            <p className="text-xs text-slate-500">{p.vegetable_gram}</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1 shrink-0 text-xs font-semibold border rounded-full px-2.5 py-1 ${badge.className}`}>
          {badge.label}
        </span>
      </div>

      {locked && (
        <div className="mb-4 flex items-center gap-2 text-xs font-medium text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          <Lock className="w-3.5 h-3.5 shrink-0" />
          Managed by another vendor -- you can view this product but not change it.
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-4">
        <Stat label="Available today" value={p.today_available_display} />
        <Stat label="Price" value={`₹${p.price}`} sub={p.offer_price ? `MRP ₹${p.mrp}` : null} />
        <Stat label="Reorder level" value={p.reorder_level_display} />
        <Stat label="Restock level" value={p.restock_level_display} />
      </div>

      <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-4">
        <ActionButton icon={PackagePlus} label="Restock" disabled={locked} onClick={() => onTogglePanel('restock')} active={isPanelOpen === 'restock'} />
        <ActionButton icon={PackageX} label="Mark out of stock" disabled={locked} onClick={() => onTogglePanel('adjust-out')} active={isPanelOpen === 'adjust-out'} />
        <ActionButton icon={Pencil} label="Edit price" disabled={locked} onClick={() => onTogglePanel('edit')} active={isPanelOpen === 'edit'} />
        <ActionButton icon={History} label="History" onClick={() => onTogglePanel('history')} active={isPanelOpen === 'history'} />
      </div>

      {isPanelOpen === 'restock' && (
        <RestockPanel productId={p.product_id} onClose={onClosePanel} onError={onError} onSuccess={onSuccess} />
      )}
      {isPanelOpen === 'adjust-out' && (
        <MarkOutOfStockPanel productId={p.product_id} productName={p.name} onClose={onClosePanel} onError={onError} onSuccess={onSuccess} />
      )}
      {isPanelOpen === 'edit' && (
        <EditDetailsPanel product={p} onClose={onClosePanel} onError={onError} onSuccess={onSuccess} />
      )}
      {isPanelOpen === 'history' && (
        <HistoryPanel productId={p.product_id} onClose={onClosePanel} onError={onError} />
      )}
    </div>
  );
}

function Stat({ label, value, sub }) {
  return (
    <div>
      <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function ActionButton({ icon: Icon, label, onClick, active, disabled }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 text-xs font-semibold rounded-lg px-3 py-2 border transition-colors disabled:opacity-30 disabled:cursor-not-allowed ${
        active ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
      }`}
    >
      <Icon className="w-3.5 h-3.5" />
      {label}
    </button>
  );
}

function PanelShell({ title, onClose, children }) {
  return (
    <div className="mt-4 border border-slate-200 rounded-lg p-4 bg-slate-50">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
        <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-700">
          <X className="w-4 h-4" />
        </button>
      </div>
      {children}
    </div>
  );
}

function RestockPanel({ productId, onClose, onError, onSuccess }) {
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('kg');
  const [saving, setSaving] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!quantity || Number(quantity) <= 0) {
      onError({ message: 'Enter a quantity greater than zero.' });
      return;
    }
    setSaving(true);
    try {
      const res = await restockProduct(productId, { quantity: Number(quantity), unit });
      onSuccess(res?.message || 'Restocked.', res?.data);
      onClose();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <PanelShell title="Restock" onClose={onClose}>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <Field label="Quantity to add">
          <input
            type="number" step="0.01" min="0.01" value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            className="w-32 rounded-lg border border-slate-300 px-3 py-2 text-sm"
            autoFocus
          />
        </Field>
        <Field label="Unit">
          <select value={unit} onChange={(e) => setUnit(e.target.value)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="kg">kg</option>
            <option value="g">g</option>
          </select>
        </Field>
        <SubmitButton saving={saving} label="Add stock" />
      </form>
    </PanelShell>
  );
}

function MarkOutOfStockPanel({ productId, productName, onClose, onError, onSuccess }) {
  const [saving, setSaving] = useState(false);

  async function confirm() {
    setSaving(true);
    try {
      const res = await markProductOutOfStock(productId);
      onSuccess(res?.message || `Marked ${productName} as out of stock.`, res?.data);
      onClose();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <PanelShell title="Mark out of stock" onClose={onClose}>
      <p className="text-sm text-slate-600 mb-3">
        This sets live stock to zero immediately -- customers won't be able to add {productName} to
        their cart until you restock it.
      </p>
      <button
        type="button"
        disabled={saving}
        onClick={confirm}
        className="inline-flex items-center gap-2 rounded-lg bg-rose-600 text-white text-sm font-semibold px-4 py-2 disabled:opacity-50"
      >
        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <PackageX className="w-4 h-4" />}
        Confirm — mark out of stock
      </button>
    </PanelShell>
  );
}

function EditDetailsPanel({ product, onClose, onError, onSuccess }) {
  const [price, setPrice] = useState(product.price ?? '');
  const [offerPrice, setOfferPrice] = useState(product.mrp && product.mrp !== product.price ? product.mrp : '');
  const [reorderQty, setReorderQty] = useState('');
  const [restockQty, setRestockQty] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {};
      if (price !== '') payload.price = price;
      if (offerPrice !== '') payload.offer_price = offerPrice;
      if (reorderQty !== '') { payload.reorder_level_quantity = Number(reorderQty); payload.reorder_level_unit = 'kg'; }
      if (restockQty !== '') { payload.restock_level_quantity = Number(restockQty); payload.restock_level_unit = 'kg'; }

      const res = await updateProductDetails(product.product_id, payload);
      onSuccess(res?.message || 'Details updated.', res?.data);
      onClose();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <PanelShell title="Edit price & levels" onClose={onClose}>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="Selling price (₹)">
          <input type="number" step="0.01" min="0" value={price} onChange={(e) => setPrice(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="MRP / offer price (₹)" hint="Leave blank for no strike-through price.">
          <input type="number" step="0.01" min="0" value={offerPrice} onChange={(e) => setOfferPrice(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Reorder level (kg)" hint="Leave blank to keep current.">
          <input type="number" step="0.01" min="0" value={reorderQty} onChange={(e) => setReorderQty(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </Field>
        <Field label="Restock level (kg)" hint="Leave blank to keep current.">
          <input type="number" step="0.01" min="0" value={restockQty} onChange={(e) => setRestockQty(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        </Field>
        <div className="sm:col-span-2">
          <SubmitButton saving={saving} label="Save changes" />
        </div>
      </form>
    </PanelShell>
  );
}

function HistoryPanel({ productId, onClose, onError }) {
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchProductStockHistory(productId)
      .then((res) => { if (!cancelled) setRows(Array.isArray(res?.data) ? res.data : []); })
      .catch((err) => { if (!cancelled) onError(err); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [productId]);

  return (
    <PanelShell title="Last 7 days" onClose={onClose}>
      {loading ? (
        <div className="py-6 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-slate-400" /></div>
      ) : !rows || rows.length === 0 ? (
        <p className="text-sm text-slate-500">No activity in this window.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-400 uppercase tracking-wide">
                <th className="py-1.5 pr-4">Date</th>
                <th className="py-1.5 pr-4">Opening</th>
                <th className="py-1.5 pr-4">Restocked</th>
                <th className="py-1.5 pr-4">Sold</th>
                <th className="py-1.5 pr-4">Closing</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.date} className="border-t border-slate-100">
                  <td className="py-1.5 pr-4 font-medium text-slate-700">{r.date}</td>
                  <td className="py-1.5 pr-4 text-slate-600">{r.opening_display}</td>
                  <td className="py-1.5 pr-4 text-emerald-700">{r.restocked_grams ? `+${r.restocked_grams}g` : '—'}</td>
                  <td className="py-1.5 pr-4 text-rose-700">{r.sold_grams ? `-${r.sold_grams}g` : '—'}</td>
                  <td className="py-1.5 pr-4 text-slate-600">{r.closing_display}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PanelShell>
  );
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-xs font-semibold text-slate-600 mb-1">{label}</label>
      {children}
      {hint && <p className="text-[11px] text-slate-400 mt-1">{hint}</p>}
    </div>
  );
}

function SubmitButton({ saving, label }) {
  return (
    <button
      type="submit"
      disabled={saving}
      className="inline-flex items-center gap-2 rounded-lg bg-slate-900 text-white text-sm font-semibold px-4 py-2 disabled:opacity-50"
    >
      {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
      {label}
    </button>
  );
}

export default AdminStockManagementPage;
