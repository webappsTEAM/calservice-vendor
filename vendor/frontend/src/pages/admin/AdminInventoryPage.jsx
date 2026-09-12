/**
 * AdminInventoryPage.jsx
 * Full inventory management page for vendor admins.
 */
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  apiGetInventoryItems,
  apiAddInventoryItem,
  apiUpdateInventoryItem,
  apiDeleteInventoryItem,
  apiGetInventoryCatalogue,
  apiSyncInventoryCatalogue,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import {
  Package, Plus, Search, RefreshCw, Edit2, Trash2, X,
  ChevronDown, CheckCircle2, AlertTriangle, XCircle,
  MinusCircle, LayoutGrid, List, AlertCircle, RotateCcw, Leaf,
} from 'lucide-react';

const STATUS_META = {
  IN_STOCK:    { label: 'In Stock',    cls: 'bg-emerald-50 text-emerald-700 border-emerald-200', Icon: CheckCircle2 },
  LOW_STOCK:   { label: 'Low Stock',   cls: 'bg-amber-50 text-amber-700 border-amber-200',       Icon: AlertTriangle },
  OUT_OF_STOCK:{ label: 'Out of Stock',cls: 'bg-red-50 text-red-700 border-red-200',             Icon: XCircle },
  UNAVAILABLE: { label: 'Unavailable', cls: 'bg-zinc-100 text-zinc-500 border-zinc-200',         Icon: MinusCircle },
};

function StockBadge({ status }) {
  const { label, cls, Icon } = STATUS_META[status] || STATUS_META.IN_STOCK;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border ${cls}`}>
      <Icon className="w-2.5 h-2.5" />{label}
    </span>
  );
}

const UNITS = ['kg','g','litre','ml','piece','bunch','dozen','box','bag','packet'];
const UNIT_LBL = { kg:'kg',g:'g',litre:'L',ml:'ml',piece:'pc',bunch:'bunch',dozen:'dz',box:'box',bag:'bag',packet:'pkt' };

/* ============================================================================
   Main Page
============================================================================= */
export default function AdminInventoryPage() {
  const [items, setItems]             = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [search, setSearch]           = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [viewMode, setViewMode]       = useState('grid');
  const [syncing, setSyncing]         = useState(false);
  const [syncMsg, setSyncMsg]         = useState('');
  const [showAdd, setShowAdd]         = useState(false);
  const [editItem, setEditItem]       = useState(null);
  const [deleteItem, setDeleteItem]   = useState(null);
  const initialized = useRef(false);
  const debounce    = useRef(null);

  const loadItems = useCallback(async () => {
    try {
      setLoading(true); setError(null);
      const params = {};
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      const data = await apiGetInventoryItems(params);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) { setError(e?.message || 'Failed to load inventory.'); }
    finally { setLoading(false); }
  }, [search, statusFilter]);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    loadItems();
  }, []);

  useEffect(() => {
    if (!initialized.current) return;
    clearTimeout(debounce.current);
    debounce.current = setTimeout(loadItems, 350);
    return () => clearTimeout(debounce.current);
  }, [search, statusFilter, loadItems]);

  const handleSync = async () => {
    setSyncing(true); setSyncMsg('');
    try {
      const r = await apiSyncInventoryCatalogue();
      setSyncMsg(r?.message || 'Sync complete.'); loadItems();
    } catch { setSyncMsg('Sync failed.'); }
    finally { setSyncing(false); }
  };

  const handleDelete = async () => {
    if (!deleteItem) return;
    try { await apiDeleteInventoryItem(deleteItem.id); setDeleteItem(null); loadItems(); }
    catch (e) { alert(e?.message || 'Delete failed.'); }
  };

  const inStock    = items.filter(i => i.stock_status === 'IN_STOCK').length;
  const lowStock   = items.filter(i => i.stock_status === 'LOW_STOCK').length;
  const outOfStock = items.filter(i => i.stock_status === 'OUT_OF_STOCK').length;
  const unavail    = items.filter(i => i.stock_status === 'UNAVAILABLE').length;

  return (
    <AppShell breadcrumbs={[{ label: 'Admin', href: '/workforce/admin' }, { label: 'Inventory' }]}>
      <PageHeader
        title="Inventory Management"
        subtitle="Track stock levels for every catalogue item. Add from the service catalogue, set quantities, pricing overrides and availability."
        badge={<span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-blue-50 text-blue-600 border border-blue-200 text-[10px] font-bold"><Package className="w-3 h-3" />{items.length} items</span>}
      />

      {/* Metric strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label:'In Stock',    value:inStock,    cls:'text-emerald-600', bg:'bg-emerald-50 border-emerald-100' },
          { label:'Low Stock',   value:lowStock,   cls:'text-amber-600',   bg:'bg-amber-50 border-amber-100' },
          { label:'Out of Stock',value:outOfStock, cls:'text-red-600',     bg:'bg-red-50 border-red-100' },
          { label:'Unavailable', value:unavail,    cls:'text-zinc-400',    bg:'bg-zinc-50 border-zinc-200' },
        ].map(m => (
          <div key={m.label} className={`${m.bg} rounded-xl p-4 border shadow-xs flex flex-col gap-1`}>
            <span className={`text-2xl font-black ${m.cls}`}>{m.value}</span>
            <span className="text-xs font-semibold text-zinc-500">{m.label}</span>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-44">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
          <input id="inventory-search" type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search items or category…" className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-zinc-200 bg-white shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
        </div>
        <div className="relative">
          <select id="inventory-status-filter" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="appearance-none text-xs pl-3 pr-7 py-2 rounded-lg border border-zinc-200 bg-white shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500/30 cursor-pointer">
            <option value="">All Status</option>
            <option value="IN_STOCK">In Stock</option>
            <option value="LOW_STOCK">Low Stock</option>
            <option value="OUT_OF_STOCK">Out of Stock</option>
            <option value="UNAVAILABLE">Unavailable</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-400 pointer-events-none" />
        </div>
        <div className="flex items-center gap-0.5 bg-zinc-100 rounded-lg p-0.5 border border-zinc-200">
          <button id="inv-grid" onClick={() => setViewMode('grid')} className={`p-1.5 rounded-md transition-colors ${viewMode==='grid'?'bg-white shadow-xs text-blue-600':'text-zinc-400 hover:text-zinc-700'}`}><LayoutGrid className="w-3.5 h-3.5" /></button>
          <button id="inv-list" onClick={() => setViewMode('list')} className={`p-1.5 rounded-md transition-colors ${viewMode==='list'?'bg-white shadow-xs text-blue-600':'text-zinc-400 hover:text-zinc-700'}`}><List className="w-3.5 h-3.5" /></button>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button id="inv-sync" onClick={handleSync} disabled={syncing} title="Re-sync names & images from live catalogue"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border border-zinc-200 bg-white shadow-xs hover:bg-zinc-50 transition-colors disabled:opacity-50">
            <RotateCcw className={`w-3.5 h-3.5 ${syncing?'animate-spin':''}`} />
            <span className="hidden sm:inline">{syncing?'Syncing…':'Sync Catalogue'}</span>
          </button>
          <button id="inv-refresh" onClick={loadItems} className="p-2 rounded-lg border border-zinc-200 bg-white shadow-xs hover:bg-zinc-50 transition-colors"><RefreshCw className="w-3.5 h-3.5 text-zinc-500" /></button>
          <button id="inv-add" onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm transition-colors">
            <Plus className="w-3.5 h-3.5" /> Add Items
          </button>
        </div>
      </div>

      {syncMsg && (
        <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />{syncMsg}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <div className="w-7 h-7 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="text-center py-12 space-y-2">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
          <p className="text-sm text-red-600 font-semibold">{error}</p>
          <button onClick={loadItems} className="text-xs text-blue-600 underline">Retry</button>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mx-auto">
            <Leaf className="w-7 h-7 text-blue-400" />
          </div>
          <p className="text-sm font-bold text-zinc-700">No inventory items yet</p>
          <p className="text-xs text-zinc-400 max-w-xs mx-auto">Add items from the service catalogue to start tracking stock levels.</p>
          <button onClick={() => setShowAdd(true)} className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm">
            <Plus className="w-3.5 h-3.5" /> Add First Item
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        <InventoryGrid items={items} onEdit={setEditItem} onDelete={setDeleteItem} />
      ) : (
        <InventoryList items={items} onEdit={setEditItem} onDelete={setDeleteItem} />
      )}

      {showAdd && (
        <AddItemsModal
          onClose={() => setShowAdd(false)}
          onAdded={() => { setShowAdd(false); loadItems(); }}
          existingServiceIds={items.map(i => i.catalogue_service_id)}
        />
      )}
      {editItem && (
        <EditItemModal item={editItem} onClose={() => setEditItem(null)} onSaved={() => { setEditItem(null); loadItems(); }} />
      )}
      {deleteItem && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full space-y-4">
            <h3 className="font-bold text-sm text-zinc-900">Remove from Inventory?</h3>
            <p className="text-xs text-zinc-500">
              This will remove <span className="font-semibold text-zinc-800">&quot;{deleteItem.name}&quot;</span> from your inventory.
              The item stays in the catalogue and can be re-added any time.
            </p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setDeleteItem(null)} className="px-4 py-2 rounded-lg text-xs font-semibold border border-zinc-200 hover:bg-zinc-50">Cancel</button>
              <button onClick={handleDelete} className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-red-600 hover:bg-red-700">Remove</button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

/* ============================================================================
   Grid View
============================================================================= */
function InventoryGrid({ items, onEdit, onDelete }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
      {items.map(item => (
        <div key={item.id} className="bg-white rounded-xl border border-zinc-200 shadow-xs overflow-hidden flex flex-col hover:shadow-md transition-shadow group">
          <div className="relative h-28 bg-zinc-50 overflow-hidden">
            {item.image ? (
              <img src={item.image} alt={item.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" onError={e => { e.target.style.display='none'; }} />
            ) : (
              <div className="w-full h-full flex items-center justify-center"><Leaf className="w-8 h-8 text-zinc-200" /></div>
            )}
            <div className="absolute top-1.5 right-1.5"><StockBadge status={item.stock_status} /></div>
          </div>
          <div className="p-2.5 flex flex-col flex-1 gap-1">
            <p className="text-xs font-bold text-zinc-800 leading-tight line-clamp-2">{item.name}</p>
            <p className="text-[10px] text-zinc-400 font-medium">{item.category}</p>
            <div className="mt-auto pt-2 flex items-center justify-between">
              <span className="text-xs font-black text-zinc-900">
                {parseFloat(item.quantity_in_stock).toFixed(1)}{' '}
                <span className="text-[10px] text-zinc-400 font-semibold">{UNIT_LBL[item.unit]||item.unit}</span>
              </span>
              {item.custom_price && <span className="text-[10px] text-blue-600 font-bold">₹{parseFloat(item.custom_price).toFixed(2)}</span>}
            </div>
          </div>
          <div className="flex border-t border-zinc-100">
            <button onClick={() => onEdit(item)} className="flex-1 py-1.5 flex items-center justify-center gap-1 text-[10px] font-semibold text-zinc-500 hover:text-blue-600 hover:bg-blue-50 transition-colors">
              <Edit2 className="w-3 h-3" /> Edit
            </button>
            <div className="w-px bg-zinc-100" />
            <button onClick={() => onDelete(item)} className="flex-1 py-1.5 flex items-center justify-center gap-1 text-[10px] font-semibold text-zinc-500 hover:text-red-600 hover:bg-red-50 transition-colors">
              <Trash2 className="w-3 h-3" /> Remove
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

/* ============================================================================
   List View
============================================================================= */
function InventoryList({ items, onEdit, onDelete }) {
  return (
    <div className="bg-white rounded-xl border border-zinc-200 shadow-xs overflow-hidden">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-zinc-100 bg-zinc-50/80">
            <th className="text-left px-4 py-2.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wide">Item</th>
            <th className="text-left px-4 py-2.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wide hidden sm:table-cell">Category</th>
            <th className="text-right px-4 py-2.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wide">Stock</th>
            <th className="text-center px-4 py-2.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wide hidden md:table-cell">Price</th>
            <th className="text-center px-4 py-2.5 text-[10px] font-bold text-zinc-400 uppercase tracking-wide">Status</th>
            <th className="px-4 py-2.5"></th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, idx) => (
            <tr key={item.id} className={`border-b border-zinc-50 hover:bg-zinc-50/60 transition-colors ${idx%2===0?'':'bg-zinc-50/30'}`}>
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-zinc-100 overflow-hidden shrink-0 flex items-center justify-center">
                    {item.image ? <img src={item.image} alt="" className="w-full h-full object-cover" onError={e=>{e.target.style.display='none';}} /> : <Leaf className="w-4 h-4 text-zinc-300" />}
                  </div>
                  <span className="font-semibold text-zinc-800">{item.name}</span>
                </div>
              </td>
              <td className="px-4 py-2.5 text-zinc-400 hidden sm:table-cell">{item.category}</td>
              <td className="px-4 py-2.5 text-right font-bold text-zinc-800">
                {parseFloat(item.quantity_in_stock).toFixed(1)} <span className="text-zinc-400 font-normal">{UNIT_LBL[item.unit]||item.unit}</span>
              </td>
              <td className="px-4 py-2.5 text-center text-zinc-500 hidden md:table-cell">
                {item.custom_price ? `₹${parseFloat(item.custom_price).toFixed(2)}` : '—'}
              </td>
              <td className="px-4 py-2.5 text-center"><StockBadge status={item.stock_status} /></td>
              <td className="px-4 py-2.5">
                <div className="flex items-center gap-1">
                  <button onClick={() => onEdit(item)} className="p-1.5 rounded-lg text-zinc-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"><Edit2 className="w-3.5 h-3.5" /></button>
                  <button onClick={() => onDelete(item)} className="p-1.5 rounded-lg text-zinc-400 hover:text-red-600 hover:bg-red-50 transition-colors"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ============================================================================
   Add Items Modal
============================================================================= */
function AddItemsModal({ onClose, onAdded, existingServiceIds }) {
  const [categories, setCategories] = useState([]);
  const [catLoading, setCatLoading] = useState(true);
  const [catSearch, setCatSearch]   = useState('');
  const [selected, setSelected]     = useState({});
  const [adding, setAdding]         = useState(false);
  const [addError, setAddError]     = useState('');
  const existingSet = new Set(existingServiceIds);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setCatLoading(true);
      try {
        const data = await apiGetInventoryCatalogue(catSearch);
        if (!cancelled) setCategories(Array.isArray(data) ? data : []);
      } catch { if (!cancelled) setCategories([]); }
      finally { if (!cancelled) setCatLoading(false); }
    };
    const t = setTimeout(load, catSearch ? 300 : 0);
    return () => { cancelled = true; clearTimeout(t); };
  }, [catSearch]);

  const toggleSelect = (svc) => setSelected(prev => {
    const next = { ...prev };
    if (next[svc.id]) delete next[svc.id];
    else next[svc.id] = { unit:'kg', quantity:'', low_stock:'' };
    return next;
  });

  const updateField = (svcId, field, value) =>
    setSelected(prev => ({ ...prev, [svcId]: { ...prev[svcId], [field]: value } }));

  const handleAdd = async () => {
    const entries = Object.entries(selected);
    if (!entries.length) { setAddError('Select at least one item.'); return; }
    setAdding(true); setAddError('');
    try {
      for (const [svcId, cfg] of entries) {
        await apiAddInventoryItem({
          catalogue_service_id: parseInt(svcId),
          unit: cfg.unit,
          quantity_in_stock: cfg.quantity || 0,
          low_stock_threshold: cfg.low_stock || 0,
        });
      }
      onAdded();
    } catch (e) { setAddError(e?.message || 'Failed to add items.'); }
    finally { setAdding(false); }
  };

  const selectedCount = Object.keys(selected).length;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-zinc-100">
          <div>
            <h2 className="font-bold text-sm text-zinc-900">Add Catalogue Items to Inventory</h2>
            <p className="text-[10px] text-zinc-400 mt-0.5">Select items from the live service catalogue to track in your inventory.</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-3 border-b border-zinc-50">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-400" />
            <input type="text" value={catSearch} onChange={e => setCatSearch(e.target.value)} placeholder="Search catalogue items…"
              className="w-full pl-8 pr-3 py-2 text-xs rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {catLoading ? (
            <div className="flex justify-center py-8"><div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
          ) : categories.length === 0 ? (
            <p className="text-center text-xs text-zinc-400 py-8">No catalogue items found.</p>
          ) : categories.map(cat => (
            <div key={cat.id}>
              <h3 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 px-1">{cat.name}</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {cat.services.map(svc => {
                  const alreadyAdded = existingSet.has(svc.id);
                  const isSel = !!selected[svc.id];
                  return (
                    <div key={svc.id}
                      onClick={() => !alreadyAdded && toggleSelect(svc)}
                      className={`rounded-xl border p-2 transition-all cursor-pointer ${alreadyAdded ? 'opacity-40 cursor-not-allowed border-zinc-100 bg-zinc-50' : isSel ? 'border-blue-400 bg-blue-50 shadow-sm' : 'border-zinc-200 bg-white hover:border-blue-300 hover:bg-blue-50/30'}`}
                    >
                      <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-lg bg-zinc-100 overflow-hidden shrink-0 flex items-center justify-center">
                          {svc.image ? <img src={svc.image} alt="" className="w-full h-full object-cover" onError={e=>{e.target.style.display='none';}} /> : <Leaf className="w-4 h-4 text-zinc-300" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-semibold text-zinc-800 truncate">{svc.name}</p>
                          {alreadyAdded && <p className="text-[10px] text-zinc-400">Already in inventory</p>}
                        </div>
                        {isSel && <CheckCircle2 className="w-4 h-4 text-blue-500 shrink-0" />}
                      </div>
                      {isSel && (
                        <div className="mt-2 grid grid-cols-3 gap-1.5" onClick={e => e.stopPropagation()}>
                          <div>
                            <label className="text-[10px] text-zinc-400 block mb-0.5">Unit</label>
                            <select value={selected[svc.id].unit} onChange={e => updateField(svc.id,'unit',e.target.value)}
                              className="w-full text-[10px] px-1.5 py-1 rounded border border-zinc-200 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400">
                              {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="text-[10px] text-zinc-400 block mb-0.5">Qty</label>
                            <input type="number" min="0" step="0.001" value={selected[svc.id].quantity} onChange={e => updateField(svc.id,'quantity',e.target.value)} placeholder="0"
                              className="w-full text-[10px] px-1.5 py-1 rounded border border-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-400" />
                          </div>
                          <div>
                            <label className="text-[10px] text-zinc-400 block mb-0.5">Low alert</label>
                            <input type="number" min="0" step="0.001" value={selected[svc.id].low_stock} onChange={e => updateField(svc.id,'low_stock',e.target.value)} placeholder="0"
                              className="w-full text-[10px] px-1.5 py-1 rounded border border-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-400" />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-zinc-100 flex items-center gap-3">
          {addError && <p className="text-xs text-red-600 flex-1">{addError}</p>}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs text-zinc-400">{selectedCount} selected</span>
            <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-semibold border border-zinc-200 hover:bg-zinc-50">Cancel</button>
            <button onClick={handleAdd} disabled={adding||selectedCount===0} className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50">
              {adding ? 'Adding…' : `Add ${selectedCount} Item${selectedCount!==1?'s':''}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================================
   Edit Item Modal
============================================================================= */
function EditItemModal({ item, onClose, onSaved }) {
  const [form, setForm] = useState({
    custom_name: item.custom_name || '',
    custom_image_url: item.custom_image_url || '',
    custom_price: item.custom_price || '',
    quantity_in_stock: item.quantity_in_stock || '0',
    unit: item.unit || 'kg',
    low_stock_threshold: item.low_stock_threshold || '0',
    notes: item.notes || '',
    is_available: item.is_available,
  });
  const [saving, setSaving]   = useState(false);
  const [saveErr, setSaveErr] = useState('');
  const up = (k,v) => setForm(p => ({...p,[k]:v}));

  const handleSave = async () => {
    setSaving(true); setSaveErr('');
    try {
      await apiUpdateInventoryItem(item.id, {
        custom_name: form.custom_name,
        custom_image_url: form.custom_image_url,
        custom_price: form.custom_price !== '' ? form.custom_price : null,
        quantity_in_stock: form.quantity_in_stock,
        unit: form.unit,
        low_stock_threshold: form.low_stock_threshold,
        notes: form.notes,
        is_available: form.is_available,
      });
      onSaved();
    } catch (e) { setSaveErr(e?.message || 'Save failed.'); }
    finally { setSaving(false); }
  };

  const previewImage = form.custom_image_url || item.catalogue_image_url || '';

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-zinc-100">
          <div>
            <h2 className="font-bold text-sm text-zinc-900">Edit Inventory Item</h2>
            <p className="text-[10px] text-zinc-400">{item.name_snapshot} &middot; {item.category}</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-zinc-100 text-zinc-400"><X className="w-4 h-4" /></button>
        </div>
        <div className="p-4 space-y-3 overflow-y-auto max-h-[70vh]">
          <div className="flex items-start gap-3">
            <div className="w-16 h-16 rounded-xl bg-zinc-100 overflow-hidden shrink-0 flex items-center justify-center border border-zinc-200">
              {previewImage ? <img src={previewImage} alt="" className="w-full h-full object-cover" onError={e=>{e.target.style.display='none';}} /> : <Leaf className="w-6 h-6 text-zinc-300" />}
            </div>
            <div className="flex-1">
              <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Custom Image URL</label>
              <input type="url" value={form.custom_image_url} onChange={e => up('custom_image_url',e.target.value)} placeholder={item.catalogue_image_url||'Paste image URL…'}
                className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
              <p className="text-[9px] text-zinc-300 mt-0.5">Leave blank to use catalogue image</p>
            </div>
          </div>
          <div>
            <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Display Name Override</label>
            <input type="text" value={form.custom_name} onChange={e => up('custom_name',e.target.value)} placeholder={item.name_snapshot}
              className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Quantity in Stock</label>
              <input type="number" min="0" step="0.001" value={form.quantity_in_stock} onChange={e => up('quantity_in_stock',e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
            </div>
            <div>
              <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Unit</label>
              <select value={form.unit} onChange={e => up('unit',e.target.value)}
                className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30">
                {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Low Stock Alert Threshold</label>
            <input type="number" min="0" step="0.001" value={form.low_stock_threshold} onChange={e => up('low_stock_threshold',e.target.value)}
              className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Custom Price (₹) — optional</label>
            <input type="number" min="0" step="0.01" value={form.custom_price} onChange={e => up('custom_price',e.target.value)} placeholder="Leave blank to use catalogue price"
              className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30" />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-zinc-500 block mb-1">Notes</label>
            <textarea rows={2} value={form.notes} onChange={e => up('notes',e.target.value)} placeholder="Internal notes…"
              className="w-full text-xs px-3 py-2 rounded-lg border border-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500/30 resize-none" />
          </div>
          <div className="flex items-center gap-3 pt-1">
            <label className="text-xs font-semibold text-zinc-600">Available for orders</label>
            <button type="button" onClick={() => up('is_available',!form.is_available)}
              className={`relative w-10 h-5 rounded-full transition-colors ${form.is_available?'bg-emerald-500':'bg-zinc-200'}`}>
              <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${form.is_available?'translate-x-5':'translate-x-0'}`} />
            </button>
          </div>
          {saveErr && <p className="text-xs text-red-600">{saveErr}</p>}
        </div>
        <div className="p-4 border-t border-zinc-100 flex items-center gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-semibold border border-zinc-200 hover:bg-zinc-50">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="px-4 py-2 rounded-lg text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
