import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Filter,
  ArrowLeft,
  Store,
  Layers,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  Eye,
  ChevronRight,
  ShieldCheck,
  Tag,
  Package,
  FileText,
  Building2,
  Calendar,
  AlertCircle,
  HelpCircle,
  ChevronDown,
  History,
  Info,
} from 'lucide-react';

export function AdminCategoriesApprovalPage() {
  const { user, token } = useAuth();
  const { sellerId } = useParams();
  const navigate = useNavigate();

  // ── Seller List (Screen 1) State ──────────────────────────────────────────
  const [sellers, setSellers] = useState([]);
  const [sellersLoading, setSellersLoading] = useState(true);
  const [sellersError, setSellersError] = useState('');
  const [sellerSearch, setSellerSearch] = useState('');
  const [hasPendingOnly, setHasPendingOnly] = useState(false);
  const [sellerPage, setSellerPage] = useState(1);
  const [sellerTotalPages, setSellerTotalPages] = useState(1);
  const [sellerTotalCount, setSellerTotalCount] = useState(0);

  // ── Products List (Screen 2) State ────────────────────────────────────────
  const [selectedSeller, setSelectedSeller] = useState(null);
  const [products, setProducts] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productsError, setProductsError] = useState('');
  const [productTab, setProductTab] = useState('PENDING'); // PENDING | APPROVED | REJECTED | ALL
  const [productSearch, setProductSearch] = useState('');
  const [productCategoryFilter, setProductCategoryFilter] = useState('');
  const [categoryTree, setCategoryTree] = useState([]);
  const [productPage, setProductPage] = useState(1);
  const [productTotalPages, setProductTotalPages] = useState(1);
  const [productTotalCount, setProductTotalCount] = useState(0);

  // Selection & Bulk Actions
  const [selectedProductIds, setSelectedProductIds] = useState(new Set());
  const [actionLoading, setActionLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  // Modals & Drawers
  const [detailProduct, setDetailProduct] = useState(null);
  const [detailDrawerOpen, setDetailDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const [rejectModalItem, setRejectModalItem] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [rejectError, setRejectError] = useState('');

  const [approveConfirmItem, setApproveConfirmItem] = useState(null);
  const [bulkApproveOpen, setBulkApproveOpen] = useState(false);

  // ── Headers Setup ─────────────────────────────────────────────────────────
  const authHeaders = useMemo(() => {
    return {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    };
  }, [token]);

  // ── Fetch Sellers (Screen 1) ──────────────────────────────────────────────
  const fetchSellers = useCallback(async () => {
    if (!token) return;
    setSellersLoading(true);
    setSellersError('');
    try {
      const params = new URLSearchParams();
      if (sellerSearch.trim()) params.append('search', sellerSearch.trim());
      if (hasPendingOnly) params.append('has_pending', 'true');
      params.append('page', sellerPage);
      params.append('page_size', '20');

      const res = await fetch(`/api/workforce/admin/seller-hub/approval/sellers/?${params.toString()}`, {
        headers: authHeaders,
      });

      if (!res.ok) {
        throw new Error(`Failed to load sellers (HTTP ${res.status})`);
      }

      const data = await res.json();
      setSellers(data.results || []);
      setSellerTotalPages(data.total_pages || 1);
      setSellerTotalCount(data.count || 0);
    } catch (err) {
      setSellersError(err.message || 'Failed to fetch sellers list.');
    } finally {
      setSellersLoading(false);
    }
  }, [token, sellerSearch, hasPendingOnly, sellerPage, authHeaders]);

  useEffect(() => {
    if (!sellerId) {
      fetchSellers();
    }
  }, [sellerId, fetchSellers]);

  // ── Fetch Category Tree for Filter ────────────────────────────────────────
  useEffect(() => {
    if (!token) return;
    const loadCategories = async () => {
      try {
        const res = await fetch('/api/workforce/seller-hub/categories/tree/', { headers: authHeaders });
        if (res.ok) {
          const data = await res.json();
          setCategoryTree(data || []);
        }
      } catch (_) {}
    };
    loadCategories();
  }, [token, authHeaders]);

  // Flatten Category tree for select dropdown
  const flattenedCategories = useMemo(() => {
    const list = [];
    const traverse = (nodes, prefix = '') => {
      for (const node of nodes) {
        const path = prefix ? `${prefix} > ${node.name}` : node.name;
        list.push({ id: node.id, name: node.name, path, is_leaf: node.is_leaf });
        if (node.children && node.children.length > 0) {
          traverse(node.children, path);
        }
      }
    };
    traverse(categoryTree);
    return list;
  }, [categoryTree]);

  // ── Fetch Products for Selected Seller (Screen 2) ─────────────────────────
  const fetchSellerProducts = useCallback(async () => {
    if (!token || !sellerId) return;
    setProductsLoading(true);
    setProductsError('');
    setSelectedProductIds(new Set());
    try {
      const params = new URLSearchParams();
      if (productTab !== 'ALL') {
        params.append('status', productTab);
      } else {
        params.append('status', 'ALL');
      }
      if (productSearch.trim()) params.append('search', productSearch.trim());
      if (productCategoryFilter) params.append('category_id', productCategoryFilter);
      params.append('page', productPage);
      params.append('page_size', '20');

      const res = await fetch(
        `/api/workforce/admin/seller-hub/approval/sellers/${sellerId}/products/?${params.toString()}`,
        { headers: authHeaders }
      );

      if (!res.ok) {
        throw new Error(`Failed to load products (HTTP ${res.status})`);
      }

      const data = await res.json();
      setSelectedSeller(data.seller || null);
      setProducts(data.results || []);
      setProductTotalPages(data.total_pages || 1);
      setProductTotalCount(data.count || 0);
    } catch (err) {
      setProductsError(err.message || 'Failed to fetch seller products.');
    } finally {
      setProductsLoading(false);
    }
  }, [token, sellerId, productTab, productSearch, productCategoryFilter, productPage, authHeaders]);

  useEffect(() => {
    if (sellerId) {
      fetchSellerProducts();
    }
  }, [sellerId, fetchSellerProducts]);

  // ── Fetch Full Product Detail for Review Drawer ───────────────────────────
  const openProductDetail = async (productId) => {
    setDetailLoading(true);
    setDetailDrawerOpen(true);
    try {
      const res = await fetch(`/api/workforce/admin/seller-hub/approval/products/${productId}/`, {
        headers: authHeaders,
      });
      if (res.ok) {
        const data = await res.json();
        setDetailProduct(data);
      }
    } catch (err) {
      setErrorMsg('Failed to load product full details.');
    } finally {
      setDetailLoading(false);
    }
  };

  // ── Approve Product Action ────────────────────────────────────────────────
  const handleApprove = async (product) => {
    setActionLoading(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await fetch(`/api/workforce/admin/seller-hub/approval/products/${product.id}/approve/`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({}),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to approve product.');
      }

      setSuccessMsg(data.message || `Product '${product.title}' approved successfully.`);
      setApproveConfirmItem(null);
      if (detailDrawerOpen && detailProduct?.id === product.id) {
        setDetailProduct(data.product);
      }
      fetchSellerProducts();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Reject Product Action ─────────────────────────────────────────────────
  const handleReject = async () => {
    if (!rejectModalItem) return;
    if (!rejectReason.trim() || rejectReason.trim().length < 5) {
      setRejectError('Please enter a descriptive rejection reason (minimum 5 characters).');
      return;
    }

    setActionLoading(true);
    setRejectError('');
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await fetch(`/api/workforce/admin/seller-hub/approval/products/${rejectModalItem.id}/reject/`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ reason: rejectReason.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Failed to reject product.');
      }

      setSuccessMsg(data.message || `Product '${rejectModalItem.title}' rejected.`);
      setRejectModalItem(null);
      setRejectReason('');
      if (detailDrawerOpen && detailProduct?.id === rejectModalItem.id) {
        setDetailProduct(data.product);
      }
      fetchSellerProducts();
    } catch (err) {
      setRejectError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ── Bulk Approve Action ───────────────────────────────────────────────────
  const handleBulkApprove = async () => {
    const ids = Array.from(selectedProductIds);
    if (ids.length === 0) return;

    setActionLoading(true);
    setErrorMsg('');
    setSuccessMsg('');
    try {
      const res = await fetch('/api/workforce/admin/seller-hub/approval/products/bulk-approve/', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ product_ids: ids }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Bulk approval failed.');
      }

      const successCount = (data.results || []).filter((r) => r.success).length;
      setSuccessMsg(`Bulk approved ${successCount} of ${ids.length} product(s) successfully.`);
      setBulkApproveOpen(false);
      setSelectedProductIds(new Set());
      fetchSellerProducts();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Checkbox helpers
  const toggleSelectAll = () => {
    if (selectedProductIds.size === products.length && products.length > 0) {
      setSelectedProductIds(new Set());
    } else {
      setSelectedProductIds(new Set(products.map((p) => p.id)));
    }
  };

  const toggleSelectProduct = (id) => {
    const next = new Set(selectedProductIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setSelectedProductIds(next);
  };

  // Status Badge Helper
  const renderStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5" /> Approved
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3.5 h-3.5" /> Rejected
          </span>
        );
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
      case 'CHANGES_REQUESTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200">
            <Clock className="w-3.5 h-3.5" /> Pending Review
          </span>
        );
      case 'PAUSED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-zinc-100 text-zinc-700 border border-zinc-300">
            Paused
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            {status || 'Draft'}
          </span>
        );
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: SCREEN 2 (SELLER PRODUCTS REVIEW)
  // ═══════════════════════════════════════════════════════════════════════════
  if (sellerId) {
    return (
      <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-800">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
          {/* Header */}
          <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10 shadow-xs">
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3 min-w-0">
                <button
                  onClick={() => navigate('/workforce/admin/seller-hub/categories-approval')}
                  className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                  title="Back to Sellers List"
                >
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-bold text-slate-900 truncate">
                      {selectedSeller?.name || 'Seller Catalog Review'}
                    </h1>
                    <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-mono">
                      ID #{sellerId}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Review and approve product category assignments for this merchant
                  </p>
                </div>
              </div>

              {/* Counts Badges */}
              {selectedSeller && (
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs font-bold flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-amber-600" />
                    <span>{selectedSeller.pending_count} Pending</span>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-bold flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>{selectedSeller.approved_count} Approved</span>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-900 text-xs font-bold flex items-center gap-1.5">
                    <XCircle className="w-3.5 h-3.5 text-rose-600" />
                    <span>{selectedSeller.rejected_count} Rejected</span>
                  </div>
                  <div className="px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-800 text-xs font-bold">
                    <span>{selectedSeller.total_count} Total</span>
                  </div>
                </div>
              )}
            </div>

            {/* Notification Banners */}
            {successMsg && (
              <div className="mt-3 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>{successMsg}</span>
                </div>
                <button onClick={() => setSuccessMsg('')} className="text-emerald-700 hover:text-emerald-900">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
            {errorMsg && (
              <div className="mt-3 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
                <button onClick={() => setErrorMsg('')} className="text-rose-700 hover:text-rose-900">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

          {/* Filters & Tabs */}
          <div className="p-6 space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              {/* Status Tabs */}
              <div className="flex items-center gap-1 p-1 bg-slate-200/80 rounded-xl max-w-fit">
                {[
                  { id: 'PENDING', label: 'Pending Review', count: selectedSeller?.pending_count },
                  { id: 'APPROVED', label: 'Approved', count: selectedSeller?.approved_count },
                  { id: 'REJECTED', label: 'Rejected', count: selectedSeller?.rejected_count },
                  { id: 'ALL', label: 'All Products', count: selectedSeller?.total_count },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setProductTab(tab.id);
                      setProductPage(1);
                    }}
                    className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                      productTab === tab.id
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    }`}
                  >
                    <span>{tab.label}</span>
                    {tab.count !== undefined && (
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                          productTab === tab.id ? 'bg-slate-100 text-slate-800' : 'bg-slate-300/80 text-slate-700'
                        }`}
                      >
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Category & Search Filters */}
              <div className="flex items-center gap-3 flex-wrap">
                {/* Category Filter */}
                <div className="relative min-w-[200px]">
                  <select
                    value={productCategoryFilter}
                    onChange={(e) => {
                      setProductCategoryFilter(e.target.value);
                      setProductPage(1);
                    }}
                    className="w-full pl-3 pr-8 py-2 text-xs rounded-lg border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 appearance-none font-medium"
                  >
                    <option value="">All Categories (Tree)</option>
                    {flattenedCategories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.path} {!c.is_leaf ? '(Sub-tree)' : ''}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
                </div>

                {/* Search Box */}
                <div className="relative min-w-[220px]">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={productSearch}
                    onChange={(e) => {
                      setProductSearch(e.target.value);
                      setProductPage(1);
                    }}
                    placeholder="Search Title, SKU, Brand..."
                    className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                {/* Bulk Actions Button */}
                {selectedProductIds.size > 0 && (
                  <button
                    onClick={() => setBulkApproveOpen(true)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-xs transition-all flex items-center gap-2"
                  >
                    <Check className="w-4 h-4" />
                    <span>Approve Selected ({selectedProductIds.size})</span>
                  </button>
                )}
              </div>
            </div>

            {/* Products Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                      <th className="p-3.5 w-10 text-center">
                        <input
                          type="checkbox"
                          checked={selectedProductIds.size === products.length && products.length > 0}
                          onChange={toggleSelectAll}
                          className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                        />
                      </th>
                      <th className="p-3.5 min-w-[240px]">Product Details</th>
                      <th className="p-3.5 min-w-[200px]">Category Lineage</th>
                      <th className="p-3.5 min-w-[120px]">Pricing</th>
                      <th className="p-3.5 min-w-[120px]">Status</th>
                      <th className="p-3.5 min-w-[130px]">Submitted At</th>
                      <th className="p-3.5 min-w-[160px] text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {productsLoading ? (
                      <tr>
                        <td colSpan={7} className="p-12 text-center text-slate-500">
                          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
                          <span>Loading products for review...</span>
                        </td>
                      </tr>
                    ) : products.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="p-12 text-center text-slate-500">
                          <Package className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                          <p className="font-semibold text-slate-700">No products found</p>
                          <p className="text-xs text-slate-400 mt-1">
                            No products match the selected status or category filters.
                          </p>
                        </td>
                      </tr>
                    ) : (
                      products.map((prod) => (
                        <tr key={prod.id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="p-3.5 text-center">
                            <input
                              type="checkbox"
                              checked={selectedProductIds.has(prod.id)}
                              onChange={() => toggleSelectProduct(prod.id)}
                              className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                            />
                          </td>
                          <td className="p-3.5">
                            <div className="flex items-center gap-3">
                              {prod.primary_image ? (
                                <img
                                  src={prod.primary_image}
                                  alt={prod.title}
                                  className="w-10 h-10 rounded-lg object-cover border border-slate-200 bg-white shrink-0"
                                />
                              ) : (
                                <div className="w-10 h-10 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-400 shrink-0">
                                  <Package className="w-5 h-5" />
                                </div>
                              )}
                              <div className="min-w-0">
                                <span
                                  onClick={() => openProductDetail(prod.id)}
                                  className="font-bold text-slate-900 hover:text-emerald-700 cursor-pointer block truncate"
                                  title={prod.title}
                                >
                                  {prod.title}
                                </span>
                                <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                                  <span className="font-mono bg-slate-100 px-1.5 py-0.2 rounded text-[10px]">
                                    {prod.sku}
                                  </span>
                                  {prod.brand && <span>Brand: {prod.brand}</span>}
                                </div>
                              </div>
                            </div>
                          </td>
                          <td className="p-3.5">
                            <div className="text-[11px] text-slate-700 font-medium">
                              {prod.category_path || prod.category_name || '—'}
                            </div>
                          </td>
                          <td className="p-3.5">
                            <div className="text-xs font-bold text-slate-900">₹{prod.selling_price}</div>
                            <div className="text-[10px] text-slate-400 line-through">MRP: ₹{prod.mrp}</div>
                          </td>
                          <td className="p-3.5">
                            {renderStatusBadge(prod.status)}
                            {prod.status === 'REJECTED' && prod.rejection_reason && (
                              <div
                                className="text-[10px] text-rose-600 mt-1 truncate max-w-[150px]"
                                title={prod.rejection_reason}
                              >
                                Reason: {prod.rejection_reason}
                              </div>
                            )}
                          </td>
                          <td className="p-3.5 text-[11px] text-slate-500">
                            {prod.submitted_at
                              ? new Date(prod.submitted_at).toLocaleDateString(undefined, {
                                  month: 'short',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })
                              : '—'}
                          </td>
                          <td className="p-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => openProductDetail(prod.id)}
                                className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
                                title="View Details"
                              >
                                <Eye className="w-4 h-4" />
                              </button>
                              {prod.status !== 'APPROVED' && (
                                <button
                                  onClick={() => setApproveConfirmItem(prod)}
                                  className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-xs font-bold transition-colors flex items-center gap-1 shadow-2xs"
                                >
                                  <Check className="w-3.5 h-3.5" /> Approve
                                </button>
                              )}
                              {prod.status !== 'REJECTED' && (
                                <button
                                  onClick={() => {
                                    setRejectModalItem(prod);
                                    setRejectReason('');
                                    setRejectError('');
                                  }}
                                  className="px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-md text-xs font-bold transition-colors flex items-center gap-1"
                                >
                                  <X className="w-3.5 h-3.5" /> Reject
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {productTotalPages > 1 && (
                <div className="p-3.5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
                  <span>
                    Showing {products.length} of {productTotalCount} products
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      disabled={productPage <= 1}
                      onClick={() => setProductPage((p) => p - 1)}
                      className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                    >
                      Previous
                    </button>
                    <span className="px-2 font-bold text-slate-700">
                      Page {productPage} of {productTotalPages}
                    </span>
                    <button
                      disabled={productPage >= productTotalPages}
                      onClick={() => setProductPage((p) => p + 1)}
                      className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Product Detail Drawer ─────────────────────────────────────────── */}
          {detailDrawerOpen && (
            <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex justify-end">
              <div className="w-full max-w-xl bg-white h-full shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right duration-200">
                <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Package className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-bold text-slate-900 text-sm">Product Catalog Review</h3>
                  </div>
                  <button
                    onClick={() => setDetailDrawerOpen(false)}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-700"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                  {detailLoading || !detailProduct ? (
                    <div className="py-20 text-center text-slate-500">
                      <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
                      <span>Loading specifications...</span>
                    </div>
                  ) : (
                    <>
                      {/* Product Header Card */}
                      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h2 className="text-base font-bold text-slate-900">{detailProduct.title}</h2>
                            <div className="text-xs text-slate-500 font-mono mt-0.5">SKU: {detailProduct.sku}</div>
                          </div>
                          {renderStatusBadge(detailProduct.status)}
                        </div>
                        {detailProduct.rejection_reason && (
                          <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium">
                            <span className="font-bold">Rejection Feedback:</span> {detailProduct.rejection_reason}
                          </div>
                        )}
                      </div>

                      {/* Image Gallery */}
                      {detailProduct.images && detailProduct.images.length > 0 && (
                        <div>
                          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
                            Product Images ({detailProduct.images.length})
                          </label>
                          <div className="grid grid-cols-3 gap-3">
                            {detailProduct.images.map((img, idx) => (
                              <div
                                key={img.id || idx}
                                className="relative rounded-lg overflow-hidden border border-slate-200 bg-slate-50 aspect-square"
                              >
                                <img src={img.image_url} alt="Product" className="w-full h-full object-cover" />
                                {img.is_primary && (
                                  <span className="absolute top-1 left-1 bg-emerald-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-xs">
                                    Primary
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Specifications Grid */}
                      <div>
                        <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2">
                          Attributes & Taxonomy
                        </label>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Assigned Category</span>
                            <span className="font-semibold text-slate-800">
                              {detailProduct.category_path || detailProduct.category_name}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Brand</span>
                            <span className="font-semibold text-slate-800">{detailProduct.brand || '—'}</span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Selling Price / MRP</span>
                            <span className="font-semibold text-emerald-700">
                              ₹{detailProduct.selling_price}{' '}
                              <span className="text-slate-400 font-normal line-through text-[10px]">
                                (MRP: ₹{detailProduct.mrp})
                              </span>
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Tax Rate / HSN</span>
                            <span className="font-semibold text-slate-800">
                              {detailProduct.tax_rate}% {detailProduct.hsn_code ? `(HSN: ${detailProduct.hsn_code})` : ''}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Unit & Pack Size</span>
                            <span className="font-semibold text-slate-800">
                              {detailProduct.pack_size} {detailProduct.unit}
                            </span>
                          </div>
                          <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                            <span className="text-slate-400 block text-[10px]">Barcode</span>
                            <span className="font-semibold text-slate-800">{detailProduct.barcode || '—'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Description */}
                      {detailProduct.description && (
                        <div>
                          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                            Description
                          </label>
                          <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed whitespace-pre-line">
                            {detailProduct.description}
                          </p>
                        </div>
                      )}

                      {/* Audit History Timeline */}
                      {detailProduct.audit_logs && detailProduct.audit_logs.length > 0 && (
                        <div>
                          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
                            <History className="w-3.5 h-3.5 text-slate-500" /> Review History
                          </label>
                          <div className="space-y-2">
                            {detailProduct.audit_logs.map((log) => (
                              <div
                                key={log.id}
                                className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 text-xs space-y-1"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-bold text-slate-800">{log.action}</span>
                                  <span className="text-[10px] text-slate-400">
                                    {new Date(log.created_at).toLocaleString()}
                                  </span>
                                </div>
                                {log.notes && <p className="text-slate-600 text-[11px]">{log.notes}</p>}
                                <div className="text-[10px] text-slate-400">
                                  Actor: {log.actor_name || 'System'} | Transition: {log.from_status || '—'} →{' '}
                                  {log.to_status}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </div>

                {/* Drawer Footer Actions */}
                {detailProduct && (
                  <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
                    {detailProduct.status !== 'APPROVED' && (
                      <button
                        disabled={actionLoading}
                        onClick={() => handleApprove(detailProduct)}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-all shadow-xs flex items-center gap-1.5 disabled:opacity-50"
                      >
                        <Check className="w-4 h-4" /> Approve Product
                      </button>
                    )}
                    {detailProduct.status !== 'REJECTED' && (
                      <button
                        disabled={actionLoading}
                        onClick={() => {
                          setRejectModalItem(detailProduct);
                          setRejectReason('');
                          setRejectError('');
                        }}
                        className="px-4 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
                      >
                        <X className="w-4 h-4" /> Reject Product
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Reject Modal ─────────────────────────────────────────────────── */}
          {rejectModalItem && (
            <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div className="flex items-center gap-3 text-rose-600">
                  <div className="w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center">
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Reject Product Catalog</h3>
                    <p className="text-xs text-slate-500">Provide feedback for {rejectModalItem.title}</p>
                  </div>
                </div>

                {rejectError && (
                  <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium">
                    {rejectError}
                  </div>
                )}

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Rejection Reason <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={3}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="e.g. Inappropriate category selection, image resolution too low, or incorrect brand description..."
                    className="w-full p-3 rounded-lg border border-slate-300 text-xs focus:ring-2 focus:ring-rose-500 focus:outline-none"
                  />
                  <span className="text-[10px] text-slate-400 block mt-1">Minimum 5 characters required</span>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    disabled={actionLoading}
                    onClick={() => setRejectModalItem(null)}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    disabled={actionLoading}
                    onClick={handleReject}
                    className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-xs disabled:opacity-50"
                  >
                    {actionLoading ? 'Rejecting...' : 'Confirm Rejection'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── Approve Confirmation Modal ────────────────────────────────────── */}
          {approveConfirmItem && (
            <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div className="flex items-center gap-3 text-emerald-600">
                  <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Approve Product Catalog</h3>
                    <p className="text-xs text-slate-500">Publish '{approveConfirmItem.title}'</p>
                  </div>
                </div>

                <p className="text-xs text-slate-600">
                  Approving this product will make it eligible for inventory inwarding and marketplace visibility.
                </p>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    disabled={actionLoading}
                    onClick={() => setApproveConfirmItem(null)}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    disabled={actionLoading}
                    onClick={() => handleApprove(approveConfirmItem)}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs disabled:opacity-50"
                  >
                    {actionLoading ? 'Approving...' : 'Approve Now'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ── Bulk Approve Modal ────────────────────────────────────────────── */}
          {bulkApproveOpen && (
            <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
              <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div className="flex items-center gap-3 text-emerald-600">
                  <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">Bulk Approve Products</h3>
                    <p className="text-xs text-slate-500">{selectedProductIds.size} products selected</p>
                  </div>
                </div>

                <p className="text-xs text-slate-600">
                  Are you sure you want to bulk approve all {selectedProductIds.size} selected products? Each product's
                  category eligibility will be validated.
                </p>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    disabled={actionLoading}
                    onClick={() => setBulkApproveOpen(false)}
                    className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-xs font-bold hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    disabled={actionLoading}
                    onClick={handleBulkApprove}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs disabled:opacity-50"
                  >
                    {actionLoading ? 'Approving...' : 'Confirm Bulk Approval'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // RENDER: SCREEN 1 (SELLERS APPROVAL LIST)
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-800">
      <Sidebar />
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-10 shadow-xs">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-6 h-6 text-emerald-600" />
                <h1 className="text-xl font-bold text-slate-900">Categories Approval</h1>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Manage and verify merchant catalog category submissions across registered stores
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3 flex-1 min-w-[240px]">
              <div className="relative flex-1 max-w-md">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={sellerSearch}
                  onChange={(e) => {
                    setSellerSearch(e.target.value);
                    setSellerPage(1);
                  }}
                  placeholder="Search store name, merchant slug..."
                  className="w-full pl-9 pr-3 py-2 text-xs rounded-lg border border-slate-300 bg-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={hasPendingOnly}
                  onChange={(e) => {
                    setHasPendingOnly(e.target.checked);
                    setSellerPage(1);
                  }}
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>Has Pending Submissions</span>
              </label>
            </div>

            <button
              onClick={fetchSellers}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
              title="Refresh List"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>

          {/* Sellers Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider">
                    <th className="p-3.5 min-w-[220px]">Merchant Store</th>
                    <th className="p-3.5 text-center min-w-[120px]">Pending Approval</th>
                    <th className="p-3.5 text-center min-w-[100px]">Approved</th>
                    <th className="p-3.5 text-center min-w-[100px]">Rejected</th>
                    <th className="p-3.5 text-center min-w-[100px]">Total Catalogs</th>
                    <th className="p-3.5 min-w-[140px]">Last Submitted</th>
                    <th className="p-3.5 text-right min-w-[120px]">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sellersLoading ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center text-slate-500">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-emerald-600" />
                        <span>Loading merchant stores...</span>
                      </td>
                    </tr>
                  ) : sellers.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center text-slate-500">
                        <Store className="w-10 h-10 mx-auto mb-2 text-slate-300" />
                        <p className="font-semibold text-slate-700">No stores found</p>
                        <p className="text-xs text-slate-400 mt-1">
                          No merchants currently match the search criteria or pending filter.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    sellers.map((s) => (
                      <tr
                        key={s.id}
                        onClick={() => navigate(`/workforce/admin/seller-hub/categories-approval/${s.id}`)}
                        className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                      >
                        <td className="p-3.5">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center font-bold text-sm shrink-0">
                              <Store className="w-4 h-4" />
                            </div>
                            <div className="min-w-0">
                              <span className="font-bold text-slate-900 block truncate hover:text-emerald-700">
                                {s.name || s.company_name}
                              </span>
                              <span className="text-[11px] text-slate-400 font-mono">{s.slug}</span>
                            </div>
                          </div>
                        </td>
                        <td className="p-3.5 text-center">
                          {s.pending_count > 0 ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-900 border border-amber-200">
                              <Clock className="w-3 h-3 text-amber-600" />
                              <span>{s.pending_count} Pending</span>
                            </span>
                          ) : (
                            <span className="text-slate-400 font-semibold">0</span>
                          )}
                        </td>
                        <td className="p-3.5 text-center font-semibold text-emerald-700">{s.approved_count}</td>
                        <td className="p-3.5 text-center font-semibold text-rose-600">{s.rejected_count}</td>
                        <td className="p-3.5 text-center font-bold text-slate-800">{s.total_count}</td>
                        <td className="p-3.5 text-[11px] text-slate-500">
                          {s.latest_submitted_at
                            ? new Date(s.latest_submitted_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })
                            : '—'}
                        </td>
                        <td className="p-3.5 text-right">
                          <span className="inline-flex items-center gap-1 text-emerald-700 font-bold text-xs hover:underline">
                            Review Products <ChevronRight className="w-3.5 h-3.5" />
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {sellerTotalPages > 1 && (
              <div className="p-3.5 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
                <span>
                  Showing {sellers.length} of {sellerTotalCount} merchants
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    disabled={sellerPage <= 1}
                    onClick={() => setSellerPage((p) => p - 1)}
                    className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                  >
                    Previous
                  </button>
                  <span className="px-2 font-bold text-slate-700">
                    Page {sellerPage} of {sellerTotalPages}
                  </span>
                  <button
                    disabled={sellerPage >= sellerTotalPages}
                    onClick={() => setSellerPage((p) => p + 1)}
                    className="px-2.5 py-1 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
