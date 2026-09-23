import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  Package,
  Plus,
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  Clock,
  RotateCcw,
  Edit2,
  History,
  Sparkles,
  RefreshCw,
  FileText,
  Layers,
  ShieldAlert,
  X,
  ChevronDown,
  Calendar,
  Box,
  Info,
  SlidersHorizontal,
  ChevronRight,
  Truck,
  TrendingDown,
  Store,
  Check,
  Scan,
  Barcode as BarcodeIcon,
} from 'lucide-react';
import { BarcodeScannerModal } from '../../components/common/BarcodeScannerModal.jsx';
import { BarcodeRenderer } from '../../components/common/BarcodeRenderer.jsx';

export function SellerInventoryPage() {
  const { user, token } = useAuth();
  const isSuperAdmin = user?.role === 'superadmin' || user?.is_superuser || user?.is_platform_admin;

  // ── States ────────────────────────────────────────────────────────────────
  const [inventoryItems, setInventoryItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Filters & Search
  const [activeTab, setActiveTab] = useState('ALL'); // ALL, IN_STOCK, LOW_STOCK, OUT_OF_STOCK, EXPIRING_SOON, EXPIRED, PAUSED
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [categories, setCategories] = useState([]);
  const [showInventoryScanner, setShowInventoryScanner] = useState(false);

  // Selected Item for Detail / Drawer
  const [selectedItem, setSelectedItem] = useState(null);
  const [ledgerMovements, setLedgerMovements] = useState([]);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [movementFilter, setMovementFilter] = useState('');
  const [activeDrawerTab, setActiveDrawerTab] = useState('LEDGER'); // LEDGER, BATCHES

  // Modals
  const [stockInModalItem, setStockInModalItem] = useState(null);
  const [adjustModalItem, setAdjustModalItem] = useState(null);
  const [damageModalItem, setDamageModalItem] = useState(null);
  const [expiredModalItem, setExpiredModalItem] = useState(null);
  const [thresholdModalItem, setThresholdModalItem] = useState(null);
  const [initModalOpen, setInitModalOpen] = useState(false);

  // Uninitialized approved products list
  const [approvedProducts, setApprovedProducts] = useState([]);
  const [approvedCount, setApprovedCount] = useState(null);
  const [initLoading, setInitLoading] = useState(false);

  // Form Submitting
  const [actionLoading, setActionLoading] = useState(false);
  const [formErrors, setFormErrors] = useState({});

  // ── Forms ─────────────────────────────────────────────────────────────────
  const [stockInForm, setStockInForm] = useState({
    quantity: '',
    batch_number: '',
    expiry_date: '',
    cost_price: '',
    reason: '',
    reference_id: '',
  });

  const [adjustForm, setAdjustForm] = useState({
    movement_type: 'ADJUSTMENT_INCREASE', // ADJUSTMENT_INCREASE, ADJUSTMENT_DECREASE
    quantity: '',
    reason: '',
    reference_id: '',
  });

  const [damageForm, setDamageForm] = useState({
    quantity: '',
    reason: '',
    reference_id: '',
  });

  const [expiredForm, setExpiredForm] = useState({
    quantity: '',
    batch_number: '',
    reason: '',
    reference_id: '',
  });

  const [thresholdForm, setThresholdForm] = useState({
    low_stock_threshold: '10.000',
    reorder_level: '20.000',
  });

  const [initForm, setInitForm] = useState({
    product_id: '',
    on_hand_qty: '0.000',
    low_stock_threshold: '10.000',
    reorder_level: '20.000',
    batch_number: '',
    expiry_date: '',
    cost_price: '',
    reason: 'Initial opening stock setup.',
  });

  // ── Data Fetching ─────────────────────────────────────────────────────────
  const fetchInventory = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      let url = `/api/workforce/seller-hub/inventory/?status=${activeTab}`;
      if (searchQuery.trim()) {
        url += `&search=${encodeURIComponent(searchQuery.trim())}`;
      }
      if (selectedCategory) {
        url += `&category_id=${selectedCategory}`;
      }

      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load inventory (HTTP ${res.status})`);
      }

      const data = await res.json();
      const items = Array.isArray(data) ? data : [];
      setInventoryItems(items);

      // Check count of approved products when inventory is empty
      if (items.length === 0 && !searchQuery.trim() && !selectedCategory && activeTab === 'ALL') {
        try {
          const appRes = await fetch('/api/workforce/seller-hub/products/?status=APPROVED', {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (appRes.ok) {
            const appData = await appRes.json();
            const list = Array.isArray(appData)
              ? appData
              : Array.isArray(appData?.results)
              ? appData.results
              : [];
            setApprovedCount(list.length);
          } else {
            setApprovedCount(0);
          }
        } catch (ignored) {
          setApprovedCount(0);
        }
      }
    } catch (err) {
      setError(err.message || 'Error fetching store inventory.');
    } finally {
      setLoading(false);
    }
  }, [token, activeTab, searchQuery, selectedCategory]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await fetch('/api/workforce/seller-hub/categories/active/?leaf_only=true', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCategories(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.warn('Could not fetch categories', e);
    }
  }, [token]);

  const fetchApprovedProductsForInit = useCallback(async () => {
    setInitLoading(true);
    try {
      const res = await fetch('/api/workforce/seller-hub/products/?status=APPROVED', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data)
          ? data
          : Array.isArray(data?.results)
          ? data.results
          : [];
        // Exclude products that already have inventory
        const existingProdIds = new Set(inventoryItems.map((i) => i.product));
        const uninitialized = list.filter(
          (p) => !existingProdIds.has(p.id)
        );
        setApprovedProducts(uninitialized);
        if (uninitialized.length > 0 && !initForm.product_id) {
          setInitForm((prev) => ({ ...prev, product_id: uninitialized[0].id }));
        }
      }
    } catch (e) {
      console.warn('Error fetching approved products', e);
    } finally {
      setInitLoading(false);
    }
  }, [token, inventoryItems, initForm.product_id]);

  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // ── Fetch Movement History for Drawer ─────────────────────────────────────
  const fetchLedger = async (invId) => {
    setLedgerLoading(true);
    try {
      let url = `/api/workforce/seller-hub/inventory/${invId}/movements/`;
      if (movementFilter) {
        url += `?movement_type=${movementFilter}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setLedgerMovements(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.warn('Failed to load ledger', e);
    } finally {
      setLedgerLoading(false);
    }
  };

  const openItemDetail = async (item) => {
    setSelectedItem(item);
    setActiveDrawerTab('LEDGER');
    setMovementFilter('');
    fetchLedger(item.id);
  };

  // ── Metrics Calculation ───────────────────────────────────────────────────
  const metrics = useMemo(() => {
    const total = inventoryItems.length;
    let inStock = 0;
    let lowStock = 0;
    let outOfStock = 0;
    let expiring = 0;
    let totalValue = 0;

    inventoryItems.forEach((i) => {
      const onHand = parseFloat(i.on_hand_qty) || 0;
      const thresh = parseFloat(i.low_stock_threshold) || 10;
      const price = parseFloat(i.product_selling_price) || 0;

      if (onHand <= 0) {
        outOfStock++;
      } else if (onHand <= thresh) {
        lowStock++;
      } else {
        inStock++;
      }

      if (i.has_expiring_batches) {
        expiring++;
      }

      totalValue += onHand * price;
    });

    return { total, inStock, lowStock, outOfStock, expiring, totalValue };
  }, [inventoryItems]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleStockInSubmit = async (e) => {
    e.preventDefault();
    if (!stockInModalItem) return;
    setFormErrors({});
    setActionLoading(true);

    try {
      const payload = {
        movement_type: 'STOCK_IN',
        quantity: stockInForm.quantity,
        batch_number: stockInForm.batch_number,
        expiry_date: stockInForm.expiry_date || null,
        cost_price: stockInForm.cost_price || null,
        reason: stockInForm.reason || 'Warehouse stock-in / replenishment.',
        reference_id: stockInForm.reference_id,
      };

      const res = await fetch(`/api/workforce/seller-hub/inventory/${stockInModalItem.id}/adjust/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.details) setFormErrors(data.details);
        throw new Error(data.error || 'Failed to record stock in.');
      }

      setSuccessMsg(`Successfully added ${stockInForm.quantity} ${stockInModalItem.product_unit} to stock!`);
      setStockInModalItem(null);
      setStockInForm({ quantity: '', batch_number: '', expiry_date: '', cost_price: '', reason: '', reference_id: '' });
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAdjustSubmit = async (e) => {
    e.preventDefault();
    if (!adjustModalItem) return;
    setFormErrors({});
    setActionLoading(true);

    try {
      const payload = {
        movement_type: adjustForm.movement_type,
        quantity: adjustForm.quantity,
        reason: adjustForm.reason,
        reference_id: adjustForm.reference_id,
      };

      const res = await fetch(`/api/workforce/seller-hub/inventory/${adjustModalItem.id}/adjust/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.details) setFormErrors(data.details);
        throw new Error(data.error || 'Failed to record stock adjustment.');
      }

      setSuccessMsg(`Stock adjustment of ${adjustForm.quantity} ${adjustModalItem.product_unit} recorded successfully.`);
      setAdjustModalItem(null);
      setAdjustForm({ movement_type: 'ADJUSTMENT_INCREASE', quantity: '', reason: '', reference_id: '' });
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDamageSubmit = async (e) => {
    e.preventDefault();
    if (!damageModalItem) return;
    setFormErrors({});
    setActionLoading(true);

    try {
      const payload = {
        movement_type: 'DAMAGE',
        quantity: damageForm.quantity,
        reason: damageForm.reason,
        reference_id: damageForm.reference_id,
      };

      const res = await fetch(`/api/workforce/seller-hub/inventory/${damageModalItem.id}/adjust/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.details) setFormErrors(data.details);
        throw new Error(data.error || 'Failed to record damaged stock.');
      }

      setSuccessMsg(`Recorded ${damageForm.quantity} ${damageModalItem.product_unit} as damaged/broken.`);
      setDamageModalItem(null);
      setDamageForm({ quantity: '', reason: '', reference_id: '' });
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleExpiredSubmit = async (e) => {
    e.preventDefault();
    if (!expiredModalItem) return;
    setFormErrors({});
    setActionLoading(true);

    try {
      const payload = {
        movement_type: 'EXPIRED',
        quantity: expiredForm.quantity,
        batch_number: expiredForm.batch_number,
        reason: expiredForm.reason,
        reference_id: expiredForm.reference_id,
      };

      const res = await fetch(`/api/workforce/seller-hub/inventory/${expiredModalItem.id}/adjust/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.details) setFormErrors(data.details);
        throw new Error(data.error || 'Failed to record expired stock.');
      }

      setSuccessMsg(`Recorded ${expiredForm.quantity} ${expiredModalItem.product_unit} as expired stock write-off.`);
      setExpiredModalItem(null);
      setExpiredForm({ quantity: '', batch_number: '', reason: '', reference_id: '' });
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleThresholdSubmit = async (e) => {
    e.preventDefault();
    if (!thresholdModalItem) return;
    setActionLoading(true);

    try {
      const payload = {
        low_stock_threshold: thresholdForm.low_stock_threshold,
        reorder_level: thresholdForm.reorder_level,
      };

      const res = await fetch(`/api/workforce/seller-hub/inventory/${thresholdModalItem.id}/`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to update thresholds.');
      }

      setSuccessMsg('Inventory thresholds updated successfully.');
      setThresholdModalItem(null);
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleInitSubmit = async (e) => {
    e.preventDefault();
    setActionLoading(true);
    setFormErrors({});

    try {
      const payload = {
        product_id: parseInt(initForm.product_id, 10),
        on_hand_qty: initForm.on_hand_qty,
        low_stock_threshold: initForm.low_stock_threshold,
        reorder_level: initForm.reorder_level,
        batch_number: initForm.batch_number,
        expiry_date: initForm.expiry_date || null,
        cost_price: initForm.cost_price || null,
        reason: initForm.reason,
      };

      const res = await fetch('/api/workforce/seller-hub/inventory/initialize/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to initialize inventory.');
      }

      setSuccessMsg('Product inventory initialized with initial stock levels.');
      setInitModalOpen(false);
      fetchInventory();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50/50 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col pb-16">
        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-20 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-2xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100 shadow-2xs">
              <Package className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Store Stock & Inventory</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300 px-2 py-0.5 rounded-full">
                  Live Stock Engine
                </span>
                {isSuperAdmin && (
                  <span className="text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-300 px-2 py-0.5 rounded-full">
                    Admin Oversight
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Physical warehouse balance, grocery batch expiration tracking, stock adjustments, and ledger movements
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                fetchApprovedProductsForInit();
                setInitModalOpen(true);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs transition-all active:scale-95"
            >
              <Plus className="w-4 h-4" />
              <span>Initialize Product Stock</span>
            </button>

            <button
              onClick={fetchInventory}
              disabled={loading}
              className="p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors"
              title="Refresh inventory"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
          </div>
        </header>

        {/* ── NOTIFICATIONS / ALERTS ───────────────────────────────────────── */}
        <div className="px-6 max-w-7xl w-full mx-auto mt-4 space-y-3">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-between text-rose-700 text-xs shadow-2xs">
              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4 shrink-0 text-rose-500" />
                <span className="font-semibold">{error}</span>
              </div>
              <button onClick={() => setError('')} className="text-rose-400 hover:text-rose-700">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-emerald-800 text-xs shadow-2xs animate-fade-in">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                <span className="font-semibold">{successMsg}</span>
              </div>
              <button onClick={() => setSuccessMsg('')} className="text-emerald-500 hover:text-emerald-800">
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ── TOP METRICS SUMMARY CARDS ──────────────────────────────────── */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5 pt-2">
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-slate-600">Tracked SKUs</span>
                <Box className="w-4 h-4 text-slate-400" />
              </div>
              <p className="text-2xl font-black text-slate-900 font-mono mt-2">{metrics.total}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Active catalog items</p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-emerald-700">In Stock</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-black text-emerald-600 font-mono mt-2">{metrics.inStock}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Above reorder point</p>
            </div>

            <div className={`p-4 rounded-2xl border shadow-2xs transition-colors ${metrics.lowStock > 0 ? 'bg-amber-50/60 border-amber-300' : 'bg-white border-slate-200'}`}>
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-amber-800">Low Stock</span>
                <AlertTriangle className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-black text-amber-700 font-mono mt-2">{metrics.lowStock}</p>
              <p className="text-[11px] text-amber-600/80 mt-0.5">Needs replenishment</p>
            </div>

            <div className={`p-4 rounded-2xl border shadow-2xs transition-colors ${metrics.outOfStock > 0 ? 'bg-rose-50/60 border-rose-300' : 'bg-white border-slate-200'}`}>
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-rose-800">Out of Stock</span>
                <XCircle className="w-4 h-4 text-rose-500" />
              </div>
              <p className="text-2xl font-black text-rose-700 font-mono mt-2">{metrics.outOfStock}</p>
              <p className="text-[11px] text-rose-600/80 mt-0.5">Zero physical balance</p>
            </div>

            <div className={`p-4 rounded-2xl border shadow-2xs transition-colors ${metrics.expiring > 0 ? 'bg-orange-50/60 border-orange-300' : 'bg-white border-slate-200'}`}>
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-orange-800">Expiring Soon</span>
                <Clock className="w-4 h-4 text-orange-500" />
              </div>
              <p className="text-2xl font-black text-orange-700 font-mono mt-2">{metrics.expiring}</p>
              <p className="text-[11px] text-orange-600/80 mt-0.5">Within 30 days</p>
            </div>

            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-semibold text-slate-600">Total Value</span>
                <span className="text-xs font-bold text-slate-400">₹</span>
              </div>
              <p className="text-xl font-black text-slate-900 font-mono mt-2 truncate">
                ₹{metrics.totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">At selling price</p>
            </div>
          </div>

          {/* ── SEARCH & FILTER CONTROLS ───────────────────────────────────── */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 mt-4">
            {/* Search Input with Scan to Search */}
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by Product Title, SKU, Brand, Barcode..."
                className="w-full pl-9 pr-24 py-2 bg-slate-50 border border-slate-200 focus:bg-white focus:border-emerald-500 rounded-xl text-xs outline-none transition-all shadow-2xs"
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => setSearchQuery('')}
                    className="text-slate-400 hover:text-slate-600 p-1 rounded-md"
                    title="Clear search"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowInventoryScanner(true)}
                  className="inline-flex items-center gap-1 text-[11px] font-bold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-1 rounded-lg transition-colors shadow-2xs cursor-pointer"
                  title="Scan barcode with camera to filter instantly"
                >
                  <Scan className="w-3 h-3 text-emerald-600" />
                  <span>Scan</span>
                </button>
              </div>
            </div>

            {/* Category Dropdown */}
            <div className="w-full md:w-64">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 outline-none focus:bg-white focus:border-emerald-500"
              >
                <option value="">All Leaf Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.path}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* ── STATUS TABS ────────────────────────────────────────────────── */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 scrollbar-none border-b border-slate-200 pt-2">
            {[
              { key: 'ALL', label: 'All Items', count: metrics.total },
              { key: 'IN_STOCK', label: 'In Stock', count: metrics.inStock },
              { key: 'LOW_STOCK', label: 'Low Stock Alert', count: metrics.lowStock, alert: metrics.lowStock > 0 },
              { key: 'OUT_OF_STOCK', label: 'Out of Stock', count: metrics.outOfStock, alert: metrics.outOfStock > 0 },
              { key: 'EXPIRING_SOON', label: 'Expiring Soon', count: metrics.expiring, alert: metrics.expiring > 0 },
              { key: 'EXPIRED', label: 'Expired' },
              { key: 'PAUSED', label: 'Paused Products' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap flex items-center gap-1.5 ${
                  activeTab === tab.key
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                      activeTab === tab.key
                        ? 'bg-emerald-700 text-emerald-100'
                        : tab.alert
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-slate-200 text-slate-700'
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* ── INVENTORY TABLE ────────────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
            {loading ? (
              <div className="p-16 text-center space-y-3">
                <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto" />
                <p className="text-xs font-semibold text-slate-500">Loading store stock balances...</p>
              </div>
            ) : inventoryItems.length === 0 ? (
              <div className="p-16 text-center space-y-3">
                <div className="w-12 h-12 bg-emerald-50 rounded-2xl text-emerald-600 flex items-center justify-center mx-auto border border-emerald-100">
                  <Package className="w-6 h-6" />
                </div>
                {searchQuery || selectedCategory || activeTab !== 'ALL' ? (
                  <>
                    <h3 className="font-bold text-slate-900 text-sm">No Matching Inventory Found</h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      No inventory records match your current filter or search criteria.
                    </p>
                  </>
                ) : approvedCount === null ? (
                  <>
                    <div className="flex items-center justify-center gap-2 text-slate-500 py-3">
                      <RefreshCw className="w-4 h-4 animate-spin text-emerald-600" />
                      <span className="text-xs font-semibold">Checking catalog status...</span>
                    </div>
                  </>
                ) : approvedCount === 0 ? (
                  <>
                    <h3 className="font-bold text-slate-900 text-sm">No Approved Products in Inventory</h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      Products appear here after admin approval. Upload your products and submit them for review in Catalog Uploads.
                    </p>
                    <div className="pt-2 flex items-center justify-center gap-2">
                      <Link
                        to="/workforce/seller-hub/catalog-uploads"
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl shadow-xs transition-all"
                      >
                        <span>Go to Catalog Uploads</span>
                      </Link>
                    </div>
                  </>
                ) : (
                  <>
                    <h3 className="font-bold text-slate-900 text-sm">No Stock Initialized Yet</h3>
                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                      You have approved catalog products ready. Initialize opening stock to start managing and tracking inventory.
                    </p>
                    <div className="pt-2 flex items-center justify-center gap-2">
                      <button
                        onClick={() => {
                          fetchApprovedProductsForInit();
                          setInitModalOpen(true);
                        }}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shadow-xs transition-all"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Initialize Stock</span>
                      </button>
                      <Link
                        to="/workforce/seller-hub/catalog-uploads"
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl shadow-xs transition-all"
                      >
                        <span>Catalog Uploads</span>
                      </Link>
                    </div>
                  </>
                )}
              </div>

            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                      <th className="py-3 px-4">Product / SKU</th>
                      <th className="py-3 px-4">Category</th>
                      <th className="py-3 px-4 text-right">On Hand</th>
                      <th className="py-3 px-4 text-right">Reserved</th>
                      <th className="py-3 px-4 text-right">Available</th>
                      <th className="py-3 px-4 text-center">Status</th>
                      <th className="py-3 px-4 text-center">Batches / Expiry</th>
                      <th className="py-3 px-4 text-right">Threshold</th>
                      <th className="py-3 px-4 text-right">Quick Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {inventoryItems.map((item) => {
                      const onHand = parseFloat(item.on_hand_qty) || 0;
                      const available = parseFloat(item.available_qty) || 0;
                      const reserved = parseFloat(item.reserved_qty) || 0;
                      const lowThresh = parseFloat(item.low_stock_threshold) || 10;

                      return (
                        <tr key={item.id} className="hover:bg-slate-50/70 transition-colors group">
                          {/* Product Info */}
                          <td className="py-3.5 px-4">
                            <div className="flex items-center gap-3">
                              <div className="w-11 h-11 rounded-xl bg-slate-100 border border-slate-200 shrink-0 overflow-hidden flex items-center justify-center">
                                {item.product_image ? (
                                  <img
                                    src={item.product_image}
                                    alt={item.product_title}
                                    className="w-full h-full object-cover"
                                  />
                                ) : (
                                  <Package className="w-5 h-5 text-slate-400" />
                                )}
                              </div>
                              <div className="min-w-0">
                                <span className="font-bold text-slate-900 block truncate hover:text-emerald-700 cursor-pointer" onClick={() => openItemDetail(item)}>
                                  {item.product_title}
                                </span>
                                <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
                                  <span className="font-mono bg-slate-100 px-1.5 py-0.2 rounded text-slate-600 font-semibold">
                                    {item.product_sku}
                                  </span>
                                  {item.product_brand && <span>• {item.product_brand}</span>}
                                  <span>• {item.product_pack_size} {item.product_unit}</span>
                                </div>
                                {item.product_barcode && (
                                  <div className="flex items-center gap-1 mt-1 text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200/80 px-1.5 py-0.5 rounded max-w-fit" title={`Barcode: ${item.product_barcode}`}>
                                    <BarcodeIcon className="w-3 h-3 text-emerald-600 shrink-0" />
                                    <span>{item.product_barcode}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>

                          {/* Category */}
                          <td className="py-3.5 px-4 text-slate-500 max-w-[160px] truncate" title={item.product_category_path}>
                            <span className="bg-slate-100 px-2 py-0.5 rounded-lg text-[11px] text-slate-600 block truncate">
                              {item.product_category_name}
                            </span>
                          </td>

                          {/* On Hand */}
                          <td className="py-3.5 px-4 text-right font-mono font-bold text-slate-900">
                            {onHand.toFixed(3)}
                            <span className="text-[10px] text-slate-400 font-sans ml-1 font-normal">
                              {item.product_unit}
                            </span>
                          </td>

                          {/* Reserved */}
                          <td className="py-3.5 px-4 text-right font-mono text-slate-500">
                            {reserved.toFixed(3)}
                          </td>

                          {/* Available */}
                          <td className="py-3.5 px-4 text-right font-mono font-black text-emerald-700">
                            <span className={`px-2 py-0.5 rounded-lg ${available <= 0 ? 'bg-rose-50 text-rose-700' : available <= lowThresh ? 'bg-amber-50 text-amber-800' : 'bg-emerald-50 text-emerald-800'}`}>
                              {available.toFixed(3)}
                            </span>
                          </td>

                          {/* Stock Status Badge */}
                          <td className="py-3.5 px-4 text-center">
                            {onHand <= 0 ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-100 text-rose-800 border border-rose-200">
                                <XCircle className="w-3 h-3" />
                                Out of Stock
                              </span>
                            ) : available <= lowThresh ? (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-200">
                                <AlertTriangle className="w-3 h-3" />
                                Low Stock
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3" />
                                In Stock
                              </span>
                            )}
                          </td>

                          {/* Batches / Expiry indicator */}
                          <td className="py-3.5 px-4 text-center">
                            {item.has_expiring_batches ? (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-orange-100 text-orange-800 border border-orange-200" title="Has batches expiring within 30 days">
                                <Clock className="w-3 h-3 text-orange-600" />
                                Expiring Soon
                              </span>
                            ) : item.batches_count > 0 ? (
                              <span className="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                                {item.batches_count} {item.batches_count === 1 ? 'batch' : 'batches'}
                              </span>
                            ) : (
                              <span className="text-[11px] text-slate-300">—</span>
                            )}
                          </td>

                          {/* Threshold */}
                          <td className="py-3.5 px-4 text-right">
                            <button
                              onClick={() => {
                                setThresholdModalItem(item);
                                setThresholdForm({
                                  low_stock_threshold: item.low_stock_threshold,
                                  reorder_level: item.reorder_level,
                                });
                              }}
                              className="inline-flex items-center gap-1 text-[11px] font-mono text-slate-500 hover:text-emerald-700 bg-slate-50 hover:bg-slate-100 px-2 py-0.5 rounded border border-slate-200 transition-colors"
                              title="Edit low stock threshold & reorder level"
                            >
                              <span>≤ {parseFloat(item.low_stock_threshold).toFixed(1)}</span>
                              <Edit2 className="w-2.5 h-2.5" />
                            </button>
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => {
                                  setStockInModalItem(item);
                                  setStockInForm({
                                    quantity: '',
                                    batch_number: '',
                                    expiry_date: '',
                                    cost_price: '',
                                    reason: '',
                                    reference_id: '',
                                  });
                                }}
                                className="px-2.5 py-1 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg border border-emerald-200 transition-colors"
                                title="Add stock replenishment"
                              >
                                Stock In
                              </button>

                              <button
                                onClick={() => {
                                  setAdjustModalItem(item);
                                  setAdjustForm({
                                    movement_type: 'ADJUSTMENT_INCREASE',
                                    quantity: '',
                                    reason: '',
                                    reference_id: '',
                                  });
                                }}
                                className="px-2 py-1 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                                title="Adjust count (+/-)"
                              >
                                Adjust
                              </button>

                              <button
                                onClick={() => {
                                  setDamageModalItem(item);
                                  setDamageForm({ quantity: '', reason: '', reference_id: '' });
                                }}
                                className="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors"
                                title="Record damaged / broken stock"
                              >
                                <ShieldAlert className="w-4 h-4" />
                              </button>

                              <button
                                onClick={() => openItemDetail(item)}
                                className="p-1 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                title="View Movement Ledger"
                              >
                                <History className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* ── MODAL: STOCK IN / REPLENISH ─────────────────────────────────── */}
        {stockInModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-scale-up">
              <div className="p-5 bg-emerald-50 border-b border-emerald-100 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-xs">
                    <ArrowUpRight className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Stock In / Replenish</h3>
                    <p className="text-xs text-slate-500">{stockInModalItem.product_title}</p>
                  </div>
                </div>
                <button onClick={() => setStockInModalItem(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleStockInSubmit} className="p-6 space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Quantity to Add ({stockInModalItem.product_unit}) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    required
                    value={stockInForm.quantity}
                    onChange={(e) => setStockInForm({ ...stockInForm, quantity: e.target.value })}
                    placeholder="e.g. 50.000"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm focus:bg-white focus:border-emerald-500 outline-none"
                  />
                  {formErrors.quantity && <p className="text-rose-600 text-[11px] mt-1">{formErrors.quantity}</p>}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Batch / Lot # (Optional)</label>
                    <input
                      type="text"
                      value={stockInForm.batch_number}
                      onChange={(e) => setStockInForm({ ...stockInForm, batch_number: e.target.value })}
                      placeholder="e.g. LOT-2026-09"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Expiry Date (Optional)</label>
                    <input
                      type="date"
                      value={stockInForm.expiry_date}
                      onChange={(e) => setStockInForm({ ...stockInForm, expiry_date: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">Cost Price (₹, Optional)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={stockInForm.cost_price}
                      onChange={(e) => setStockInForm({ ...stockInForm, cost_price: e.target.value })}
                      placeholder="e.g. 140.00"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-semibold text-slate-700 mb-1">PO / Invoice # (Optional)</label>
                    <input
                      type="text"
                      value={stockInForm.reference_id}
                      onChange={(e) => setStockInForm({ ...stockInForm, reference_id: e.target.value })}
                      placeholder="e.g. PO-9821"
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Notes / Reason</label>
                  <input
                    type="text"
                    value={stockInForm.reason}
                    onChange={(e) => setStockInForm({ ...stockInForm, reason: e.target.value })}
                    placeholder="e.g. Fresh wholesale stock received from vendor."
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setStockInModalItem(null)}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Confirm Stock In</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── MODAL: STOCK ADJUSTMENT (+ / -) ─────────────────────────────── */}
        {adjustModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-scale-up">
              <div className="p-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Stock Count Adjustment</h3>
                  <p className="text-xs text-slate-500">{adjustModalItem.product_title}</p>
                </div>
                <button onClick={() => setAdjustModalItem(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleAdjustSubmit} className="p-6 space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Adjustment Direction *</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setAdjustForm({ ...adjustForm, movement_type: 'ADJUSTMENT_INCREASE' })}
                      className={`p-2.5 rounded-xl border text-center font-bold flex items-center justify-center gap-1.5 transition-all ${
                        adjustForm.movement_type === 'ADJUSTMENT_INCREASE'
                          ? 'bg-emerald-50 border-emerald-500 text-emerald-800'
                          : 'bg-slate-50 border-slate-200 text-slate-600'
                      }`}
                    >
                      <ArrowUpRight className="w-4 h-4 text-emerald-600" />
                      <span>Increase (+)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAdjustForm({ ...adjustForm, movement_type: 'ADJUSTMENT_DECREASE' })}
                      className={`p-2.5 rounded-xl border text-center font-bold flex items-center justify-center gap-1.5 transition-all ${
                        adjustForm.movement_type === 'ADJUSTMENT_DECREASE'
                          ? 'bg-amber-50 border-amber-500 text-amber-800'
                          : 'bg-slate-50 border-slate-200 text-slate-600'
                      }`}
                    >
                      <ArrowDownRight className="w-4 h-4 text-amber-600" />
                      <span>Decrease (-)</span>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Adjustment Quantity ({adjustModalItem.product_unit}) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    required
                    value={adjustForm.quantity}
                    onChange={(e) => setAdjustForm({ ...adjustForm, quantity: e.target.value })}
                    placeholder="e.g. 5.000"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm focus:bg-white focus:border-emerald-500 outline-none"
                  />
                  {formErrors.quantity && <p className="text-rose-600 text-[11px] mt-1">{formErrors.quantity}</p>}
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Mandatory Audit Reason *
                  </label>
                  <input
                    type="text"
                    required
                    value={adjustForm.reason}
                    onChange={(e) => setAdjustForm({ ...adjustForm, reason: e.target.value })}
                    placeholder="e.g. Physical inventory count discrepancy correction."
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-emerald-500"
                  />
                  {formErrors.reason && <p className="text-rose-600 text-[11px] mt-1">{formErrors.reason}</p>}
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Audit Reference / Note (Optional)</label>
                  <input
                    type="text"
                    value={adjustForm.reference_id}
                    onChange={(e) => setAdjustForm({ ...adjustForm, reference_id: e.target.value })}
                    placeholder="e.g. AUDIT-2026-Q3"
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setAdjustModalItem(null)}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2 bg-slate-900 hover:bg-black text-white font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Confirm Adjustment</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── MODAL: RECORD DAMAGE ────────────────────────────────────────── */}
        {damageModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-scale-up">
              <div className="p-5 bg-rose-50 border-b border-rose-100 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-rose-600 text-white rounded-xl shadow-xs">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Record Damaged / Broken Stock</h3>
                    <p className="text-xs text-slate-500">{damageModalItem.product_title}</p>
                  </div>
                </div>
                <button onClick={() => setDamageModalItem(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleDamageSubmit} className="p-6 space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Damaged Quantity ({damageModalItem.product_unit}) *
                  </label>
                  <input
                    type="number"
                    step="0.001"
                    min="0.001"
                    max={damageModalItem.available_qty}
                    required
                    value={damageForm.quantity}
                    onChange={(e) => setDamageForm({ ...damageForm, quantity: e.target.value })}
                    placeholder={`Max ${damageModalItem.available_qty}`}
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm focus:bg-white focus:border-rose-500 outline-none"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Available to write off: {damageModalItem.available_qty} {damageModalItem.product_unit}</p>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Damage Description / Reason *
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={damageForm.reason}
                    onChange={(e) => setDamageForm({ ...damageForm, reason: e.target.value })}
                    placeholder="e.g. Packaging seal breached during transit, oil bottle cracked."
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:bg-white focus:border-rose-500"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setDamageModalItem(null)}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Record Damage</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── MODAL: THRESHOLDS ────────────────────────────────────────────── */}
        {thresholdModalItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-sm w-full shadow-2xl border border-slate-200 overflow-hidden animate-scale-up">
              <div className="p-5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Stock Alert Thresholds</h3>
                  <p className="text-xs text-slate-500">{thresholdModalItem.product_title}</p>
                </div>
                <button onClick={() => setThresholdModalItem(null)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleThresholdSubmit} className="p-6 space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Low Stock Alert Level ({thresholdModalItem.product_unit}) *
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    value={thresholdForm.low_stock_threshold}
                    onChange={(e) => setThresholdForm({ ...thresholdForm, low_stock_threshold: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm outline-none focus:bg-white focus:border-emerald-500"
                  />
                  <p className="text-[11px] text-slate-400 mt-1">Triggers amber warning when stock reaches or drops below this point.</p>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Suggested Reorder Level ({thresholdModalItem.product_unit}) *
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    required
                    value={thresholdForm.reorder_level}
                    onChange={(e) => setThresholdForm({ ...thresholdForm, reorder_level: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm outline-none focus:bg-white focus:border-emerald-500"
                  />
                </div>

                <div className="pt-2 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setThresholdModalItem(null)}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                  >
                    {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Save Levels</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── MODAL: INITIALIZE PRODUCT STOCK ──────────────────────────────── */}
        {initModalOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-2xs flex items-center justify-center p-4">
            <div className="bg-white rounded-3xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-scale-up">
              <div className="p-5 bg-emerald-50 border-b border-emerald-100 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-xs">
                    <Plus className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Initialize Product Inventory</h3>
                    <p className="text-xs text-slate-500">Add an approved catalog item to active warehouse stock</p>
                  </div>
                </div>
                <button onClick={() => setInitModalOpen(false)} className="text-slate-400 hover:text-slate-700">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {initLoading ? (
                <div className="p-12 text-center">
                  <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mx-auto" />
                  <p className="text-xs text-slate-500 mt-2">Checking approved catalog products...</p>
                </div>
              ) : approvedProducts.length === 0 ? (
                <div className="p-8 text-center space-y-3 text-xs">
                  <div className="w-10 h-10 bg-amber-50 rounded-xl text-amber-600 flex items-center justify-center mx-auto border border-amber-200">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <h4 className="font-bold text-slate-900">No Uninitialized Approved Products</h4>
                  <p className="text-slate-500 leading-relaxed max-w-sm mx-auto">
                    All your approved catalog products are already being tracked in inventory. To add more stock items, create new products and submit them for review in Catalog Uploads.
                  </p>
                  <div className="pt-2">
                    <Link
                      to="/workforce/seller-hub/catalog-uploads"
                      className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold inline-block"
                    >
                      Go to Catalog Uploads
                    </Link>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleInitSubmit} className="p-6 space-y-4 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Select Approved Product *</label>
                    <select
                      value={initForm.product_id}
                      onChange={(e) => setInitForm({ ...initForm, product_id: e.target.value })}
                      required
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-medium outline-none focus:bg-white focus:border-emerald-500"
                    >
                      {approvedProducts.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.title} ({p.sku}) — ₹{p.selling_price}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Opening Stock</label>
                      <input
                        type="number"
                        step="0.001"
                        min="0"
                        value={initForm.on_hand_qty}
                        onChange={(e) => setInitForm({ ...initForm, on_hand_qty: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono outline-none"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Low Threshold</label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={initForm.low_stock_threshold}
                        onChange={(e) => setInitForm({ ...initForm, low_stock_threshold: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono outline-none"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Reorder Point</label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        value={initForm.reorder_level}
                        onChange={(e) => setInitForm({ ...initForm, reorder_level: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl font-mono outline-none"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Batch # (Optional)</label>
                      <input
                        type="text"
                        value={initForm.batch_number}
                        onChange={(e) => setInitForm({ ...initForm, batch_number: e.target.value })}
                        placeholder="e.g. BATCH-01"
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">Expiry Date (Optional)</label>
                      <input
                        type="date"
                        value={initForm.expiry_date}
                        onChange={(e) => setInitForm({ ...initForm, expiry_date: e.target.value })}
                        className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none"
                      />
                    </div>
                  </div>

                  <div className="pt-2 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setInitModalOpen(false)}
                      className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl font-bold"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl shadow-xs transition-all flex items-center gap-1.5"
                    >
                      {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                      <span>Initialize Inventory</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* ── DRAWER: PRODUCT INVENTORY LEDGER & BATCHES ───────────────────── */}
        {selectedItem && (
          <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-2xs flex justify-end">
            <div className="bg-white w-full max-w-xl h-full shadow-2xl flex flex-col animate-slide-in-right overflow-hidden border-l border-slate-200">
              {/* Drawer Header */}
              <div className="p-6 bg-slate-900 text-white flex items-start justify-between">
                <div className="flex items-center gap-3.5">
                  <div className="w-12 h-12 rounded-xl bg-white/10 shrink-0 overflow-hidden flex items-center justify-center">
                    {selectedItem.product_image ? (
                      <img src={selectedItem.product_image} alt="" className="w-full h-full object-cover" />
                    ) : (
                      <Package className="w-6 h-6 text-white/60" />
                    )}
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-white tracking-tight">{selectedItem.product_title}</h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      SKU: {selectedItem.product_sku} • {selectedItem.product_category_name}
                    </p>
                    {selectedItem.product_barcode && (
                      <div className="mt-2.5 bg-slate-800/90 border border-slate-700/80 p-2.5 rounded-xl flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 text-xs text-slate-300">
                          <BarcodeIcon className="w-3.5 h-3.5 text-emerald-400" />
                          <span className="font-bold text-[11px]">Barcode:</span>
                        </div>
                        <BarcodeRenderer
                          value={selectedItem.product_barcode}
                          height={30}
                          width={1.2}
                          fontSize={9}
                          showCopyButton={true}
                        />
                      </div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedItem(null)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Stock Summary Strip */}
              <div className="grid grid-cols-3 bg-slate-800 text-white text-center p-3 divide-x divide-white/10 border-t border-slate-700 text-xs">
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">On Hand</span>
                  <p className="text-lg font-black font-mono mt-0.5 text-white">
                    {parseFloat(selectedItem.on_hand_qty).toFixed(3)}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 uppercase font-semibold">Reserved</span>
                  <p className="text-lg font-black font-mono mt-0.5 text-slate-300">
                    {parseFloat(selectedItem.reserved_qty).toFixed(3)}
                  </p>
                </div>
                <div>
                  <span className="text-[10px] text-emerald-400 uppercase font-semibold">Available</span>
                  <p className="text-lg font-black font-mono mt-0.5 text-emerald-400">
                    {parseFloat(selectedItem.available_qty).toFixed(3)}
                  </p>
                </div>
              </div>

              {/* Drawer Tabs */}
              <div className="flex border-b border-slate-200 bg-slate-50 px-6 pt-3 text-xs font-bold gap-4">
                <button
                  onClick={() => setActiveDrawerTab('LEDGER')}
                  className={`pb-2.5 border-b-2 flex items-center gap-1.5 transition-colors ${
                    activeDrawerTab === 'LEDGER'
                      ? 'border-emerald-600 text-emerald-800'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <History className="w-4 h-4" />
                  <span>Movement Ledger</span>
                </button>
                <button
                  onClick={() => setActiveDrawerTab('BATCHES')}
                  className={`pb-2.5 border-b-2 flex items-center gap-1.5 transition-colors ${
                    activeDrawerTab === 'BATCHES'
                      ? 'border-emerald-600 text-emerald-800'
                      : 'border-transparent text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Active Batches & Expiry</span>
                </button>
              </div>

              {/* Drawer Body */}
              <div className="flex-1 overflow-y-auto p-6">
                {activeDrawerTab === 'LEDGER' ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                        Immutable Audit History
                      </h4>
                      <select
                        value={movementFilter}
                        onChange={(e) => {
                          setMovementFilter(e.target.value);
                          fetchLedger(selectedItem.id);
                        }}
                        className="text-xs px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-lg font-medium text-slate-600 outline-none"
                      >
                        <option value="">All Movement Types</option>
                        <option value="OPENING_STOCK">Opening Stock</option>
                        <option value="STOCK_IN">Stock In</option>
                        <option value="ADJUSTMENT_INCREASE">Adjustment (+)</option>
                        <option value="ADJUSTMENT_DECREASE">Adjustment (-)</option>
                        <option value="DAMAGE">Damaged Stock</option>
                        <option value="EXPIRED">Expired Stock</option>
                      </select>
                    </div>

                    {ledgerLoading ? (
                      <div className="p-8 text-center">
                        <RefreshCw className="w-6 h-6 text-emerald-600 animate-spin mx-auto" />
                      </div>
                    ) : ledgerMovements.length === 0 ? (
                      <div className="p-8 text-center text-xs text-slate-400">
                        No movement transactions recorded yet.
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {ledgerMovements.map((mov) => {
                          const isPositive = parseFloat(mov.quantity_change) > 0;
                          return (
                            <div key={mov.id} className="p-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-xs space-y-1.5 shadow-2xs">
                              <div className="flex items-center justify-between">
                                <span
                                  className={`px-2 py-0.5 rounded-md font-bold text-[10px] uppercase tracking-wider ${
                                    mov.movement_type === 'STOCK_IN' || mov.movement_type === 'OPENING_STOCK'
                                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                      : mov.movement_type === 'DAMAGE' || mov.movement_type === 'EXPIRED'
                                      ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                      : 'bg-slate-200 text-slate-800'
                                  }`}
                                >
                                  {mov.movement_type_display || mov.movement_type}
                                </span>
                                <span className={`font-mono font-black text-sm ${isPositive ? 'text-emerald-700' : 'text-rose-700'}`}>
                                  {isPositive ? '+' : ''}{parseFloat(mov.quantity_change).toFixed(3)}
                                </span>
                              </div>

                              <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                                <span>Balance: {parseFloat(mov.balance_before).toFixed(3)} → {parseFloat(mov.balance_after).toFixed(3)}</span>
                                <span>{new Date(mov.created_at).toLocaleString()}</span>
                              </div>

                              {mov.reason && (
                                <p className="text-[11px] text-slate-700 bg-white p-2 rounded-lg border border-slate-200 font-sans">
                                  {mov.reason}
                                </p>
                              )}

                              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                                <span>Actor: {mov.actor_name}</span>
                                {mov.reference_id && <span>Ref: {mov.reference_id}</span>}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ) : (
                  /* Batches List */
                  <div className="space-y-4">
                    <h4 className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                      Tracked Grocery Batches
                    </h4>

                    {selectedItem.batches && selectedItem.batches.length > 0 ? (
                      <div className="space-y-3">
                        {selectedItem.batches.map((batch) => (
                          <div key={batch.id} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold font-mono text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                                #{batch.batch_number}
                              </span>
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                                  batch.status === 'ACTIVE'
                                    ? 'bg-emerald-100 text-emerald-800'
                                    : batch.status === 'EXPIRING_SOON'
                                    ? 'bg-orange-100 text-orange-800'
                                    : batch.status === 'EXPIRED'
                                    ? 'bg-rose-100 text-rose-800'
                                    : 'bg-slate-200 text-slate-600'
                                }`}
                              >
                                {batch.status}
                              </span>
                            </div>

                            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-600 font-mono">
                              <div>Current Qty: <strong className="text-slate-900">{parseFloat(batch.current_quantity).toFixed(3)}</strong></div>
                              <div>Initial Qty: {parseFloat(batch.initial_quantity).toFixed(3)}</div>
                              <div>Received: {batch.received_date}</div>
                              <div>Expiry: {batch.expiry_date || 'N/A'}</div>
                            </div>

                            {batch.days_until_expiry !== null && batch.days_until_expiry !== undefined && (
                              <div className={`text-[11px] font-semibold px-2 py-1 rounded-lg ${batch.days_until_expiry < 0 ? 'bg-rose-50 text-rose-700' : batch.days_until_expiry <= 30 ? 'bg-orange-50 text-orange-700' : 'bg-slate-100 text-slate-600'}`}>
                                {batch.days_until_expiry < 0
                                  ? `Expired ${Math.abs(batch.days_until_expiry)} days ago`
                                  : `Expires in ${batch.days_until_expiry} days`}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center text-xs text-slate-400">
                        No specific grocery lot / batches registered for this product.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── BARCODE SCANNER MODAL (SCAN-TO-SEARCH) ────────────────────────── */}
        <BarcodeScannerModal
          isOpen={showInventoryScanner}
          onClose={() => setShowInventoryScanner(false)}
          onScan={(scannedBarcode) => {
            setSearchQuery(scannedBarcode);
            setSuccessMsg(`Filtered inventory by barcode: ${scannedBarcode}`);
            setTimeout(() => setSuccessMsg(''), 4000);
          }}
          title="Scan to Search Store Stock"
          description="Point your camera at a physical product barcode to jump directly to its stock record"
        />
      </main>
    </div>
  );
}

export default SellerInventoryPage;
