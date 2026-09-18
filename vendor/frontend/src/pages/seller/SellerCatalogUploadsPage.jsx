import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  UploadCloud,
  FileSpreadsheet,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock,
  PauseCircle,
  XCircle,
  FileEdit,
  Trash2,
  Send,
  Eye,
  Download,
  Layers,
  ArrowRight,
  Sparkles,
  ChevronDown,
  RefreshCw,
  Image as ImageIcon,
  Tag,
  ShieldCheck,
  Building2,
  Info,
  Check,
  X,
  History,
  AlertTriangle,
  FileCheck,
  ChevronRight,
} from 'lucide-react';

const STATUS_CONFIG = {
  ALL: { label: 'All Products', bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' },
  DRAFT: { label: 'Draft', bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-300', icon: FileEdit },
  SUBMITTED: { label: 'Submitted', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: Send },
  UNDER_REVIEW: { label: 'Under Review', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock },
  CHANGES_REQUESTED: { label: 'Changes Requested', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', icon: AlertTriangle },
  APPROVED: { label: 'Approved', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle2 },
  REJECTED: { label: 'Rejected', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', icon: XCircle },
  PAUSED: { label: 'Paused', bg: 'bg-zinc-100', text: 'text-zinc-600', border: 'border-zinc-300', icon: PauseCircle },
};

export function SellerCatalogUploadsPage() {
  const { user, token, isPlatformAdmin, isAdmin } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Active view: 'catalog' | 'bulk_upload' | 'batches'
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'catalog');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Data states
  const [products, setProducts] = useState([]);
  const [leafCategories, setLeafCategories] = useState([]);
  const [batches, setBatches] = useState([]);
  const [metrics, setMetrics] = useState({
    catalogs_awaiting_approval: 0,
    approved_products: 0,
    draft_products: 0,
    changes_requested: 0,
    rejected_products: 0,
    paused_products: 0,
    total_products: 0,
  });

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Modals state
  const [showProductModal, setShowProductModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productForm, setProductForm] = useState({
    title: '',
    brand: '',
    sku: '',
    barcode: '',
    category: '',
    unit: 'piece',
    pack_size: '1',
    mrp: '',
    selling_price: '',
    tax_rate: '0.00',
    hsn_code: '',
    storage_info: '',
    expiry_info: '',
    description: '',
    images: [],
    status: 'DRAFT',
  });
  const [formErrors, setFormErrors] = useState({});

  // Review Decision Modal (Superadmin / Admin)
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [selectedProductForReview, setSelectedProductForReview] = useState(null);
  const [reviewAction, setReviewAction] = useState('approve'); // approve, reject, request_changes, pause
  const [reviewNote, setReviewNote] = useState('');

  // Detail & Audit Log Modal
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [detailedProduct, setDetailedProduct] = useState(null);

  // Bulk Upload state
  const [uploadFile, setUploadFile] = useState(null);
  const [previewResult, setPreviewResult] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [importLoading, setImportLoading] = useState(false);
  const fileInputRef = useRef(null);

  // Fetch initial data
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const authHeader = { Authorization: `Bearer ${token}` };

      // Fetch products, categories, metrics, and batches in parallel
      const [prodRes, catRes, metRes, batRes] = await Promise.all([
        fetch('/api/workforce/seller-hub/products/', { headers: authHeader }),
        fetch('/api/workforce/seller-hub/categories/active/', { headers: authHeader }),
        fetch('/api/workforce/seller-hub/metrics/', { headers: authHeader }),
        fetch('/api/workforce/seller-hub/products/batches/', { headers: authHeader }),
      ]);

      if (!prodRes.ok) throw new Error('Failed to load products');
      const prodData = await prodRes.json();
      setProducts(prodData || []);

      if (catRes.ok) {
        const catData = await catRes.json();
        setLeafCategories(catData || []);
      }

      if (metRes.ok) {
        const metData = await metRes.json();
        setMetrics(metData);
      }

      if (batRes.ok) {
        const batData = await batRes.json();
        setBatches(batData || []);
      }
    } catch (err) {
      console.error('Error fetching catalog data:', err);
      setError(err.message || 'Failed to load catalog records');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchData();
    }
  }, [token]);

  // Filtered Products
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      // Status filter
      if (statusFilter !== 'ALL' && p.status !== statusFilter) return false;
      // Category filter
      if (categoryFilter && String(p.category) !== String(categoryFilter)) return false;
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesTitle = p.title?.toLowerCase().includes(q);
        const matchesSku = p.sku?.toLowerCase().includes(q);
        const matchesBrand = p.brand?.toLowerCase().includes(q);
        const matchesBarcode = p.barcode?.toLowerCase().includes(q);
        if (!matchesTitle && !matchesSku && !matchesBrand && !matchesBarcode) return false;
      }
      return true;
    });
  }, [products, statusFilter, categoryFilter, searchQuery]);

  // Open single product creator / editor
  const handleOpenProductModal = (prod = null) => {
    setFormErrors({});
    if (prod) {
      setEditingProduct(prod);
      setProductForm({
        title: prod.title || '',
        brand: prod.brand || '',
        sku: prod.sku || '',
        barcode: prod.barcode || '',
        category: prod.category || '',
        unit: prod.unit || 'piece',
        pack_size: prod.pack_size || '1',
        mrp: prod.mrp || '',
        selling_price: prod.selling_price || '',
        tax_rate: prod.tax_rate || '0.00',
        hsn_code: prod.hsn_code || '',
        storage_info: prod.storage_info || '',
        expiry_info: prod.expiry_info || '',
        description: prod.description || '',
        images: prod.primary_image ? [prod.primary_image] : [],
        status: prod.status || 'DRAFT',
      });
    } else {
      setEditingProduct(null);
      setProductForm({
        title: '',
        brand: '',
        sku: '',
        barcode: '',
        category: leafCategories[0]?.id || '',
        unit: 'piece',
        pack_size: '1',
        mrp: '',
        selling_price: '',
        tax_rate: '0.00',
        hsn_code: '',
        storage_info: '',
        expiry_info: '',
        description: '',
        images: [],
        status: 'DRAFT',
      });
    }
    setShowProductModal(true);
  };

  // Image upload handler
  const handleImageFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      alert('Image file size must be less than 5MB');
      return;
    }

    const formData = new FormData();
    formData.append('image', file);

    try {
      setActionLoading(true);
      const res = await fetch('/api/workforce/seller-hub/products/upload-image/', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to upload image');
      setProductForm((prev) => ({
        ...prev,
        images: [...prev.images, data.image_url],
      }));
    } catch (err) {
      alert(err.message || 'Image upload failed');
    } finally {
      setActionLoading(false);
    }
  };

  // Save product form (Draft or Submit)
  const handleSaveProduct = async (submitNow = false) => {
    setFormErrors({});
    const errors = {};

    if (!productForm.title.trim()) errors.title = 'Product title is required';
    if (!productForm.sku.trim()) errors.sku = 'SKU is required';
    if (!productForm.category) errors.category = 'Category is required';
    if (!productForm.mrp || Number(productForm.mrp) <= 0) errors.mrp = 'Valid MRP is required';
    if (!productForm.selling_price || Number(productForm.selling_price) <= 0) errors.selling_price = 'Valid selling price is required';
    if (Number(productForm.selling_price) > Number(productForm.mrp)) {
      errors.selling_price = 'Selling price cannot exceed MRP';
    }
    if (submitNow && productForm.images.length === 0) {
      errors.images = 'At least one product image is required to submit for review';
    }

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setActionLoading(true);
    try {
      const payload = {
        ...productForm,
        status: submitNow ? 'SUBMITTED' : (editingProduct ? productForm.status : 'DRAFT'),
      };

      const url = editingProduct
        ? `/api/workforce/seller-hub/products/${editingProduct.id}/`
        : '/api/workforce/seller-hub/products/';
      const method = editingProduct ? 'PATCH' : 'POST';

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        if (data.details) {
          setFormErrors(data.details);
        }
        throw new Error(data.error || 'Failed to save product');
      }

      setSuccessMessage(data.message || 'Product saved successfully!');
      setShowProductModal(false);
      fetchData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      alert(err.message || 'Failed to save product');
    } finally {
      setActionLoading(false);
    }
  };

  // Submit product for review
  const handleSubmitProduct = async (prodId) => {
    if (!confirm('Are you sure you want to submit this product for catalog review?')) return;
    setActionLoading(true);
    try {
      const res = await fetch(`/api/workforce/seller-hub/products/${prodId}/submit/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to submit product');
      setSuccessMessage(data.message);
      fetchData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Delete product
  const handleDeleteProduct = async (prodId, title) => {
    if (!confirm(`Are you sure you want to delete '${title}'? This action cannot be undone.`)) return;
    setActionLoading(true);
    try {
      const res = await fetch(`/api/workforce/seller-hub/products/${prodId}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to delete product');
      setSuccessMessage(data.message);
      fetchData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Open Product Detail Modal
  const handleOpenDetailModal = async (prodId) => {
    try {
      const res = await fetch(`/api/workforce/seller-hub/products/${prodId}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) {
        setDetailedProduct(data);
        setShowDetailModal(true);
      }
    } catch (err) {
      console.error('Error opening detail modal:', err);
    }
  };

  // Admin Review Decision Handler
  const handleOpenReviewModal = (prod) => {
    setSelectedProductForReview(prod);
    setReviewAction('approve');
    setReviewNote('');
    setShowReviewModal(true);
  };

  const handleExecuteReviewDecision = async () => {
    if (!selectedProductForReview) return;
    if (['reject', 'request_changes', 'pause'].includes(reviewAction) && !reviewNote.trim()) {
      alert('Please enter a feedback reason/note for this decision.');
      return;
    }

    setActionLoading(true);
    try {
      const res = await fetch(`/api/workforce/seller-hub/products/${selectedProductForReview.id}/review/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action: reviewAction,
          note: reviewNote.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to execute review decision');

      setSuccessMessage(data.message);
      setShowReviewModal(false);
      fetchData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err) {
      alert(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Bulk Upload Handlers
  const handleSelectBulkFile = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadFile(file);
      setPreviewResult(null);
    }
  };

  const handleValidatePreview = async () => {
    if (!uploadFile) return;
    setPreviewLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);

      const res = await fetch('/api/workforce/seller-hub/products/bulk-upload/?preview=true', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Failed to parse file');
      setPreviewResult(data);
    } catch (err) {
      alert(err.message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleConfirmBulkImport = async () => {
    if (!uploadFile) return;
    setImportLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', uploadFile);

      const res = await fetch('/api/workforce/seller-hub/products/bulk-upload/', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Bulk import failed');

      setSuccessMessage(data.message);
      setUploadFile(null);
      setPreviewResult(null);
      setActiveTab('catalog');
      fetchData();
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      alert(err.message);
    } finally {
      setImportLoading(false);
    }
  };

  const handleDownloadTemplate = () => {
    window.open('/api/workforce/seller-hub/products/template/', '_blank');
  };

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-200">
              <UploadCloud className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Catalog Uploads & Products</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded-full">
                  Phase 2 Active
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Single item creator, bulk CSV/Excel feeds, leaf category tagging, and admin verification workflow
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => handleOpenProductModal()}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Single Product</span>
            </button>
            <button
              onClick={() => setActiveTab('bulk_upload')}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg border transition-colors ${
                activeTab === 'bulk_upload'
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
              }`}
            >
              <FileSpreadsheet className="w-4 h-4 text-indigo-500" />
              <span>Bulk Feed</span>
            </button>
            <button
              onClick={fetchData}
              className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors"
              title="Refresh catalog"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-600' : ''}`} />
            </button>
          </div>
        </header>

        {/* Global Notification Banner */}
        {successMessage && (
          <div className="mx-8 mt-4 p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-900 rounded-xl text-xs font-medium flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} className="text-emerald-700 hover:text-emerald-900">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Content Body */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Top Real Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3.5">
            <div
              onClick={() => { setStatusFilter('ALL'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'ALL' && activeTab === 'catalog'
                  ? 'border-slate-900 ring-2 ring-slate-900/10 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <span className="text-[11px] font-semibold text-slate-500">Total Items</span>
              <p className="text-2xl font-black text-slate-900 font-mono mt-1">{metrics.total_products}</p>
              <span className="text-[10px] text-slate-400">All registered</span>
            </div>

            <div
              onClick={() => { setStatusFilter('APPROVED'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'APPROVED' && activeTab === 'catalog'
                  ? 'border-emerald-600 ring-2 ring-emerald-600/10 shadow-xs'
                  : 'border-slate-200 hover:border-emerald-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-emerald-700">Approved</span>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              </div>
              <p className="text-2xl font-black text-emerald-900 font-mono mt-1">{metrics.approved_products}</p>
              <span className="text-[10px] text-emerald-600">Verified & Active</span>
            </div>

            <div
              onClick={() => { setStatusFilter('SUBMITTED'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'SUBMITTED' && activeTab === 'catalog'
                  ? 'border-blue-600 ring-2 ring-blue-600/10 shadow-xs'
                  : 'border-slate-200 hover:border-blue-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-blue-700">Awaiting Review</span>
                <Clock className="w-3.5 h-3.5 text-blue-600" />
              </div>
              <p className="text-2xl font-black text-blue-900 font-mono mt-1">{metrics.catalogs_awaiting_approval}</p>
              <span className="text-[10px] text-blue-600">Submitted Queue</span>
            </div>

            <div
              onClick={() => { setStatusFilter('CHANGES_REQUESTED'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'CHANGES_REQUESTED' && activeTab === 'catalog'
                  ? 'border-orange-500 ring-2 ring-orange-500/10 shadow-xs'
                  : 'border-slate-200 hover:border-orange-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-orange-700">Action Required</span>
                <AlertTriangle className="w-3.5 h-3.5 text-orange-600" />
              </div>
              <p className="text-2xl font-black text-orange-900 font-mono mt-1">{metrics.changes_requested}</p>
              <span className="text-[10px] text-orange-600">Changes Requested</span>
            </div>

            <div
              onClick={() => { setStatusFilter('DRAFT'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'DRAFT' && activeTab === 'catalog'
                  ? 'border-slate-600 ring-2 ring-slate-600/10 shadow-xs'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-slate-600">Drafts</span>
                <FileEdit className="w-3.5 h-3.5 text-slate-500" />
              </div>
              <p className="text-2xl font-black text-slate-800 font-mono mt-1">{metrics.draft_products}</p>
              <span className="text-[10px] text-slate-500">Unsubmitted items</span>
            </div>

            <div
              onClick={() => { setStatusFilter('REJECTED'); setActiveTab('catalog'); }}
              className={`p-3.5 bg-white rounded-xl border cursor-pointer transition-all ${
                statusFilter === 'REJECTED' && activeTab === 'catalog'
                  ? 'border-rose-500 ring-2 ring-rose-500/10 shadow-xs'
                  : 'border-slate-200 hover:border-rose-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-rose-700">Rejected</span>
                <XCircle className="w-3.5 h-3.5 text-rose-600" />
              </div>
              <p className="text-2xl font-black text-rose-900 font-mono mt-1">{metrics.rejected_products}</p>
              <span className="text-[10px] text-rose-600">Format / Compliance</span>
            </div>
          </div>

          {/* Navigation View Tabs */}
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('catalog')}
                className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
                  activeTab === 'catalog'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                Product Catalog ({products.length})
              </button>
              <button
                onClick={() => setActiveTab('bulk_upload')}
                className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
                  activeTab === 'bulk_upload'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                Bulk CSV / Excel Ingestion
              </button>
              <button
                onClick={() => setActiveTab('batches')}
                className={`px-4 py-2 text-xs font-bold rounded-lg transition-all ${
                  activeTab === 'batches'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                }`}
              >
                Upload Batches ({batches.length})
              </button>
            </div>

            {/* Category Directory Link */}
            <Link
              to="/workforce/admin/seller-hub/categories"
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-900 flex items-center gap-1"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Seller Hub Categories ({leafCategories.length} Leaf Available)</span>
            </Link>
          </div>

          {/* ════════════════════════════════════════════════════════════════════ */}
          {/* TAB 1: PRODUCT CATALOG LIST                                        */}
          {/* ════════════════════════════════════════════════════════════════════ */}
          {activeTab === 'catalog' && (
            <div className="space-y-4">
              {/* Search & Status Filters Bar */}
              <div className="p-4 bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-3">
                {/* Search input */}
                <div className="relative w-full md:w-80">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search by Title, SKU, Brand, Barcode..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-500"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Filters */}
                <div className="flex items-center gap-2 w-full md:w-auto overflow-x-auto">
                  <select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="">All Categories</option>
                    {leafCategories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.path}
                      </option>
                    ))}
                  </select>

                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                  >
                    <option value="ALL">All Statuses</option>
                    <option value="DRAFT">Draft</option>
                    <option value="SUBMITTED">Submitted</option>
                    <option value="UNDER_REVIEW">Under Review</option>
                    <option value="CHANGES_REQUESTED">Changes Requested</option>
                    <option value="APPROVED">Approved</option>
                    <option value="REJECTED">Rejected</option>
                    <option value="PAUSED">Paused</option>
                  </select>
                </div>
              </div>

              {/* Products Table */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
                {loading ? (
                  <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
                    <RefreshCw className="w-6 h-6 animate-spin text-emerald-600" />
                    <span className="text-xs font-medium">Loading store products...</span>
                  </div>
                ) : filteredProducts.length === 0 ? (
                  <div className="p-12 text-center flex flex-col items-center justify-center">
                    <div className="w-14 h-14 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-3 shadow-xs">
                      <ImageIcon className="w-7 h-7 text-slate-400" />
                    </div>
                    <h3 className="text-sm font-bold text-slate-800">No products found</h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm">
                      {searchQuery || statusFilter !== 'ALL' || categoryFilter
                        ? 'No products matched your search or status filter criteria.'
                        : 'Your store catalog is currently empty. Click below to add your first product or use bulk CSV ingestion.'}
                    </p>
                    <div className="mt-5 flex items-center gap-2">
                      <button
                        onClick={() => handleOpenProductModal()}
                        className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-bold shadow-xs hover:bg-emerald-700"
                      >
                        Add First Product
                      </button>
                      <button
                        onClick={() => setActiveTab('bulk_upload')}
                        className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-xs font-bold hover:bg-slate-200"
                      >
                        Upload Bulk File
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                        <tr>
                          <th className="px-4 py-3.5">Product & SKU</th>
                          <th className="px-4 py-3.5">Category</th>
                          <th className="px-4 py-3.5">Pricing</th>
                          <th className="px-4 py-3.5">Pack & Tax</th>
                          <th className="px-4 py-3.5">Status & Review</th>
                          <th className="px-4 py-3.5 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium">
                        {filteredProducts.map((p) => {
                          const statusConf = STATUS_CONFIG[p.status] || STATUS_CONFIG.DRAFT;
                          const StatusIcon = statusConf.icon || Info;
                          const discountPercent =
                            p.mrp > p.selling_price
                              ? Math.round(((p.mrp - p.selling_price) / p.mrp) * 100)
                              : 0;

                          return (
                            <tr key={p.id} className="hover:bg-slate-50/80 transition-colors">
                              {/* Product Info */}
                              <td className="px-4 py-3.5">
                                <div className="flex items-center gap-3">
                                  <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 shrink-0 overflow-hidden flex items-center justify-center">
                                    {p.primary_image ? (
                                      <img
                                        src={p.primary_image}
                                        alt={p.title}
                                        className="w-full h-full object-cover"
                                        onError={(e) => {
                                          e.target.style.display = 'none';
                                        }}
                                      />
                                    ) : (
                                      <ImageIcon className="w-5 h-5 text-slate-300" />
                                    )}
                                  </div>
                                  <div className="min-w-0 max-w-xs">
                                    <span className="font-bold text-slate-900 block truncate text-xs" title={p.title}>
                                      {p.title}
                                    </span>
                                    <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-slate-500 font-mono">
                                      <span className="bg-slate-100 px-1.5 py-0.2 rounded text-slate-700 font-bold">
                                        {p.sku}
                                      </span>
                                      {p.brand && <span>• {p.brand}</span>}
                                    </div>
                                  </div>
                                </div>
                              </td>

                              {/* Category */}
                              <td className="px-4 py-3.5">
                                <span
                                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-slate-100 text-slate-700 rounded-lg text-[11px] font-medium max-w-[200px] truncate"
                                  title={p.category_path || p.category_name}
                                >
                                  <Layers className="w-3 h-3 text-slate-400 shrink-0" />
                                  <span className="truncate">{p.category_path || p.category_name || 'Leaf Category'}</span>
                                </span>
                              </td>

                              {/* Pricing */}
                              <td className="px-4 py-3.5">
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-1.5 font-bold text-slate-900">
                                    <span className="text-emerald-700 text-xs">₹{p.selling_price}</span>
                                    {discountPercent > 0 && (
                                      <span className="text-[10px] text-slate-400 line-through">
                                        ₹{p.mrp}
                                      </span>
                                    )}
                                  </div>
                                  {discountPercent > 0 && (
                                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.2 rounded">
                                      {discountPercent}% OFF
                                    </span>
                                  )}
                                </div>
                              </td>

                              {/* Pack & Tax */}
                              <td className="px-4 py-3.5 text-slate-600">
                                <p className="text-[11px]">
                                  {p.pack_size} {p.unit}
                                </p>
                                <p className="text-[10px] text-slate-400 font-mono">
                                  GST: {p.tax_rate}% {p.hsn_code ? `• HSN: ${p.hsn_code}` : ''}
                                </p>
                              </td>

                              {/* Status & Review Notes */}
                              <td className="px-4 py-3.5">
                                <div className="space-y-1">
                                  <span
                                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${statusConf.bg} ${statusConf.text} ${statusConf.border}`}
                                  >
                                    <StatusIcon className="w-3 h-3 shrink-0" />
                                    <span>{statusConf.label}</span>
                                  </span>

                                  {/* Review feedback alert for rejected/changes requested */}
                                  {p.admin_review_note && (
                                    <div
                                      className="text-[10px] text-slate-600 bg-slate-50 border border-slate-200 p-1.5 rounded-lg max-w-xs line-clamp-2"
                                      title={p.admin_review_note}
                                    >
                                      <span className="font-bold text-slate-800">Review Note:</span> {p.admin_review_note}
                                    </div>
                                  )}
                                </div>
                              </td>

                              {/* Actions */}
                              <td className="px-4 py-3.5 text-right">
                                <div className="flex items-center justify-end gap-1.5">
                                  {/* View Detail & Audit Log */}
                                  <button
                                    onClick={() => handleOpenDetailModal(p.id)}
                                    className="p-1.5 text-slate-500 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                                    title="View Audit Timeline & Details"
                                  >
                                    <History className="w-3.5 h-3.5" />
                                  </button>

                                  {/* Submit for Review (if Draft or Changes Requested) */}
                                  {['DRAFT', 'CHANGES_REQUESTED', 'PAUSED'].includes(p.status) && (
                                    <button
                                      onClick={() => handleSubmitProduct(p.id)}
                                      className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
                                      title="Submit product for approval"
                                    >
                                      <Send className="w-3 h-3" />
                                      <span>Submit</span>
                                    </button>
                                  )}

                                  {/* Edit Product */}
                                  <button
                                    onClick={() => handleOpenProductModal(p)}
                                    className="p-1.5 text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                                    title="Edit Product Details"
                                  >
                                    <FileEdit className="w-3.5 h-3.5" />
                                  </button>

                                  {/* Admin Review Action Button */}
                                  {(isPlatformAdmin || isAdmin) && (
                                    <button
                                      onClick={() => handleOpenReviewModal(p)}
                                      className="px-2.5 py-1 text-[11px] font-bold bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200 rounded-lg transition-colors"
                                      title="Review Product Status"
                                    >
                                      Review
                                    </button>
                                  )}

                                  {/* Delete (if draft or rejected) */}
                                  {['DRAFT', 'REJECTED'].includes(p.status) && (
                                    <button
                                      onClick={() => handleDeleteProduct(p.id, p.title)}
                                      className="p-1.5 text-rose-500 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 rounded-lg transition-colors"
                                      title="Delete Product"
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  )}
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
          )}

          {/* ════════════════════════════════════════════════════════════════════ */}
          {/* TAB 2: BULK CSV / EXCEL INGESTION                                  */}
          {/* ════════════════════════════════════════════════════════════════════ */}
          {activeTab === 'bulk_upload' && (
            <div className="space-y-6">
              {/* Instructions Banner */}
              <div className="p-6 bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/60 rounded-2xl border border-indigo-100 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-indigo-600 text-white rounded-2xl shrink-0 shadow-xs">
                    <FileSpreadsheet className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-slate-900 text-sm">Bulk Catalog Spreadsheet Ingestion</h3>
                    <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                      Download the standardized template, fill in your product catalog items with their leaf category slugs, pricing, and image URLs, then upload below. Use the preview validator to test for SKU conflicts or missing leaf categories before importing.
                    </p>
                  </div>
                </div>

                <button
                  onClick={handleDownloadTemplate}
                  className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-indigo-200 text-indigo-700 hover:bg-indigo-50 font-bold text-xs rounded-xl shadow-xs shrink-0 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  <span>Download CSV Template</span>
                </button>
              </div>

              {/* Upload Dropzone */}
              <div className="p-8 bg-white rounded-2xl border-2 border-dashed border-slate-200 hover:border-indigo-400 transition-colors text-center flex flex-col items-center justify-center">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleSelectBulkFile}
                  accept=".csv, .xlsx, .xls"
                  className="hidden"
                />

                <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 mb-3 shadow-xs">
                  <UploadCloud className="w-8 h-8" />
                </div>

                {uploadFile ? (
                  <div className="space-y-2">
                    <p className="text-xs font-bold text-slate-900 flex items-center justify-center gap-1.5">
                      <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                      <span>{uploadFile.name}</span>
                      <span className="text-slate-400 font-normal">({Math.round(uploadFile.size / 1024)} KB)</span>
                    </p>
                    <div className="flex items-center justify-center gap-2 mt-4">
                      <button
                        onClick={handleValidatePreview}
                        disabled={previewLoading}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs transition-colors"
                      >
                        {previewLoading ? 'Validating File...' : 'Validate & Preview'}
                      </button>
                      <button
                        onClick={() => { setUploadFile(null); setPreviewResult(null); }}
                        className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl text-xs font-bold"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-bold text-slate-800">
                      Drag and drop your completed catalog file here, or{' '}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-indigo-600 hover:underline"
                      >
                        browse from computer
                      </button>
                    </p>
                    <p className="text-[11px] text-slate-400 mt-1">Supports CSV, XLSX up to 500 rows per batch</p>
                  </div>
                )}
              </div>

              {/* Validation Preview Result Container */}
              {previewResult && (
                <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-xs space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm">Batch Validation Results</h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Total Rows: <span className="font-bold font-mono text-slate-800">{previewResult.total_rows}</span> • Valid:{' '}
                        <span className="font-bold font-mono text-emerald-700">{previewResult.valid_rows_count}</span> • Errors:{' '}
                        <span className="font-bold font-mono text-rose-700">{previewResult.invalid_rows_count}</span>
                      </p>
                    </div>

                    <button
                      onClick={handleConfirmBulkImport}
                      disabled={!previewResult.can_import || importLoading}
                      className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 shadow-xs transition-colors ${
                        previewResult.can_import
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                          : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      }`}
                    >
                      <CheckCircle2 className="w-4 h-4" />
                      <span>{importLoading ? 'Importing Products...' : 'Confirm & Import Valid Rows'}</span>
                    </button>
                  </div>

                  {/* Errors Breakdown Alert */}
                  {previewResult.errors?.length > 0 && (
                    <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-900 space-y-2">
                      <div className="font-bold flex items-center gap-1.5 text-rose-800">
                        <AlertCircle className="w-4 h-4" />
                        <span>Validation Errors Detected ({previewResult.errors.length} rows)</span>
                      </div>
                      <div className="max-h-40 overflow-y-auto space-y-1 text-[11px] divide-y divide-rose-100">
                        {previewResult.errors.map((err, i) => (
                          <div key={i} className="pt-1">
                            <span className="font-bold">Row {err.row} ({err.sku}):</span> {err.errors.join(', ')}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Preview Items Table */}
                  <div className="border border-slate-200 rounded-xl overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[10px] uppercase">
                        <tr>
                          <th className="px-3 py-2">Row</th>
                          <th className="px-3 py-2">Title</th>
                          <th className="px-3 py-2">SKU</th>
                          <th className="px-3 py-2">Category</th>
                          <th className="px-3 py-2">MRP / Price</th>
                          <th className="px-3 py-2">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-medium">
                        {previewResult.items?.map((item, idx) => (
                          <tr key={idx} className={item.has_errors ? 'bg-rose-50/40' : ''}>
                            <td className="px-3 py-2 text-slate-400 font-mono text-[10px]">{item.row_number}</td>
                            <td className="px-3 py-2 font-bold text-slate-900">{item.title}</td>
                            <td className="px-3 py-2 font-mono text-[11px] text-slate-600">{item.sku}</td>
                            <td className="px-3 py-2 text-slate-600">{item.category_name}</td>
                            <td className="px-3 py-2 font-mono">
                              ₹{item.selling_price} / <span className="text-slate-400">₹{item.mrp}</span>
                            </td>
                            <td className="px-3 py-2">
                              {item.has_errors ? (
                                <span className="text-[10px] font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-full">
                                  Error
                                </span>
                              ) : (
                                <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                                  Valid
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ════════════════════════════════════════════════════════════════════ */}
          {/* TAB 3: UPLOAD BATCHES HISTORY                                      */}
          {/* ════════════════════════════════════════════════════════════════════ */}
          {activeTab === 'batches' && (
            <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">
                  Bulk Catalog Feed History
                </h3>
              </div>

              {batches.length === 0 ? (
                <div className="p-12 text-center text-slate-400 flex flex-col items-center justify-center">
                  <FileSpreadsheet className="w-8 h-8 text-slate-300 mb-2" />
                  <p className="text-xs font-bold text-slate-700">No batch history recorded yet</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Uploaded CSV and Excel batches will appear here.</p>
                </div>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold text-[10px] uppercase">
                    <tr>
                      <th className="px-4 py-3">Batch ID & File</th>
                      <th className="px-4 py-3">Uploaded By</th>
                      <th className="px-4 py-3">Total Rows</th>
                      <th className="px-4 py-3">Imported</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Date</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium">
                    {batches.map((b) => (
                      <tr key={b.id} className="hover:bg-slate-50/80">
                        <td className="px-4 py-3 font-bold text-slate-900">
                          #{b.id} • {b.file_name}
                        </td>
                        <td className="px-4 py-3 text-slate-600">{b.uploaded_by_name}</td>
                        <td className="px-4 py-3 font-mono">{b.total_rows}</td>
                        <td className="px-4 py-3 font-mono text-emerald-700 font-bold">{b.imported_rows}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                              b.status === 'COMPLETED'
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : b.status === 'FAILED'
                                ? 'bg-rose-50 text-rose-700 border-rose-200'
                                : 'bg-amber-50 text-amber-700 border-amber-200'
                            }`}
                          >
                            {b.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                          {new Date(b.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>

        {/* ════════════════════════════════════════════════════════════════════ */}
        {/* MODAL 1: ADD / EDIT SINGLE PRODUCT                                 */}
        {/* ════════════════════════════════════════════════════════════════════ */}
        {showProductModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full my-8 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Tag className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-bold text-slate-900 text-sm">
                    {editingProduct ? `Edit Product: ${editingProduct.title}` : 'Add Single Product to Catalog'}
                  </h3>
                </div>
                <button
                  onClick={() => setShowProductModal(false)}
                  className="text-slate-400 hover:text-slate-600 p-1"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
                {/* Basic Details */}
                <div className="space-y-3">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1">
                    1. General Information
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Product Title <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Fortune Sunlite Refined Sunflower Oil 1L"
                        value={productForm.title}
                        onChange={(e) => setProductForm({ ...productForm, title: e.target.value })}
                        className={`w-full px-3.5 py-2 bg-slate-50 border rounded-xl text-xs text-slate-800 ${
                          formErrors.title ? 'border-rose-500 ring-1 ring-rose-500/20' : 'border-slate-200'
                        }`}
                      />
                      {formErrors.title && <p className="text-[10px] text-rose-600 mt-0.5">{formErrors.title}</p>}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        SKU (Store Unique) <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. FORT-SUN-1L"
                        value={productForm.sku}
                        onChange={(e) => setProductForm({ ...productForm, sku: e.target.value })}
                        className={`w-full px-3.5 py-2 bg-slate-50 border rounded-xl text-xs text-slate-800 font-mono ${
                          formErrors.sku ? 'border-rose-500 ring-1 ring-rose-500/20' : 'border-slate-200'
                        }`}
                      />
                      {formErrors.sku && <p className="text-[10px] text-rose-600 mt-0.5">{formErrors.sku}</p>}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Brand Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Fortune, Tata, Aashirvaad"
                        value={productForm.brand}
                        onChange={(e) => setProductForm({ ...productForm, brand: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Barcode / EAN (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. 8901234567890"
                        value={productForm.barcode}
                        onChange={(e) => setProductForm({ ...productForm, barcode: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Seller Hub Category <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={productForm.category}
                        onChange={(e) => setProductForm({ ...productForm, category: e.target.value })}
                        className={`w-full px-3.5 py-2 bg-slate-50 border rounded-xl text-xs text-slate-800 ${
                          formErrors.category ? 'border-rose-500 ring-1 ring-rose-500/20' : 'border-slate-200'
                        }`}
                      >
                        <option value="">Select an active leaf category...</option>
                        {leafCategories.map((cat) => (
                          <option key={cat.id} value={cat.id}>
                            {cat.path}
                          </option>
                        ))}
                      </select>
                      {formErrors.category && (
                        <p className="text-[10px] text-rose-600 mt-0.5">{formErrors.category}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Pricing & Taxes */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1">
                    2. Pricing, Margin & Taxes
                  </h4>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        MRP (₹) <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="180.00"
                        value={productForm.mrp}
                        onChange={(e) => setProductForm({ ...productForm, mrp: e.target.value })}
                        className={`w-full px-3.5 py-2 bg-slate-50 border rounded-xl text-xs text-slate-800 font-mono ${
                          formErrors.mrp ? 'border-rose-500' : 'border-slate-200'
                        }`}
                      />
                      {formErrors.mrp && <p className="text-[10px] text-rose-600 mt-0.5">{formErrors.mrp}</p>}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Selling Price (₹) <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="165.00"
                        value={productForm.selling_price}
                        onChange={(e) => setProductForm({ ...productForm, selling_price: e.target.value })}
                        className={`w-full px-3.5 py-2 bg-slate-50 border rounded-xl text-xs text-slate-800 font-mono ${
                          formErrors.selling_price ? 'border-rose-500' : 'border-slate-200'
                        }`}
                      />
                      {formErrors.selling_price && (
                        <p className="text-[10px] text-rose-600 mt-0.5">{formErrors.selling_price}</p>
                      )}
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">GST Tax Rate (%)</label>
                      <input
                        type="number"
                        step="0.01"
                        placeholder="5.00"
                        value={productForm.tax_rate}
                        onChange={(e) => setProductForm({ ...productForm, tax_rate: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-mono"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">HSN Code</label>
                      <input
                        type="text"
                        placeholder="1512"
                        value={productForm.hsn_code}
                        onChange={(e) => setProductForm({ ...productForm, hsn_code: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-mono"
                      />
                    </div>
                  </div>
                </div>

                {/* Packaging & Storage */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1">
                    3. Packaging & Grocery Specs
                  </h4>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Unit</label>
                      <select
                        value={productForm.unit}
                        onChange={(e) => setProductForm({ ...productForm, unit: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      >
                        <option value="piece">piece</option>
                        <option value="pack">pack</option>
                        <option value="g">g (Grams)</option>
                        <option value="kg">kg (Kilograms)</option>
                        <option value="ml">ml (Millilitres)</option>
                        <option value="litre">litre (Litres)</option>
                        <option value="box">box</option>
                        <option value="bottle">bottle</option>
                        <option value="can">can</option>
                        <option value="bunch">bunch</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Pack Size / Value</label>
                      <input
                        type="text"
                        placeholder="e.g. 1L, 500g, Pack of 3"
                        value={productForm.pack_size}
                        onChange={(e) => setProductForm({ ...productForm, pack_size: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 mb-1">Storage Instructions</label>
                      <input
                        type="text"
                        placeholder="e.g. Store in a cool and dry place away from heat"
                        value={productForm.storage_info}
                        onChange={(e) => setProductForm({ ...productForm, storage_info: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      />
                    </div>

                    <div className="sm:col-span-4">
                      <label className="block text-xs font-bold text-slate-700 mb-1">Expiry / Shelf Life Info</label>
                      <input
                        type="text"
                        placeholder="e.g. Best before 9 months from date of packaging"
                        value={productForm.expiry_info}
                        onChange={(e) => setProductForm({ ...productForm, expiry_info: e.target.value })}
                        className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                {/* Product Media */}
                <div className="space-y-3 pt-2">
                  <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b pb-1">
                    4. Product Image Media
                  </h4>

                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      <label className="cursor-pointer px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold border border-slate-200 transition-colors inline-flex items-center gap-1.5">
                        <ImageIcon className="w-4 h-4 text-slate-500" />
                        <span>Upload Photo File</span>
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleImageFileUpload}
                          className="hidden"
                        />
                      </label>
                      <span className="text-[11px] text-slate-400">or paste a direct web image URL below</span>
                    </div>

                    {/* Image URL input */}
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="https://example.com/product-image.jpg"
                        value={productForm.images[0] || ''}
                        onChange={(e) => {
                          const val = e.target.value.trim();
                          setProductForm({ ...productForm, images: val ? [val] : [] });
                        }}
                        className="flex-1 px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                      />
                    </div>
                    {formErrors.images && <p className="text-[10px] text-rose-600">{formErrors.images}</p>}

                    {/* Thumbnail preview */}
                    {productForm.images.length > 0 && (
                      <div className="flex items-center gap-2 pt-1">
                        {productForm.images.map((img, idx) => (
                          <div
                            key={idx}
                            className="relative w-16 h-16 rounded-xl border border-slate-200 overflow-hidden bg-slate-50"
                          >
                            <img src={img} alt="Product" className="w-full h-full object-cover" />
                            <button
                              type="button"
                              onClick={() => setProductForm({ ...productForm, images: [] })}
                              className="absolute top-1 right-1 bg-slate-900/80 text-white rounded-full p-0.5"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Description */}
                <div className="space-y-1.5 pt-2">
                  <label className="block text-xs font-bold text-slate-700">Detailed Product Description</label>
                  <textarea
                    rows={3}
                    placeholder="Enter detailed description, ingredients, benefits..."
                    value={productForm.description}
                    onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                    className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                  />
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => setShowProductModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900"
                >
                  Cancel
                </button>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleSaveProduct(false)}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl transition-colors"
                  >
                    Save as Draft
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSaveProduct(true)}
                    disabled={actionLoading}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Submit for Review</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════════ */}
        {/* MODAL 2: ADMIN REVIEW DECISION MODAL                               */}
        {/* ════════════════════════════════════════════════════════════════════ */}
        {showReviewModal && selectedProductForReview && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-purple-50/50">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-purple-600" />
                  <h3 className="font-bold text-slate-900 text-sm">Platform Catalog Review</h3>
                </div>
                <button onClick={() => setShowReviewModal(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1">
                  <p className="font-bold text-slate-900">{selectedProductForReview.title}</p>
                  <p className="text-slate-500 font-mono">
                    SKU: {selectedProductForReview.sku} • {selectedProductForReview.company_name}
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="block text-xs font-bold text-slate-700">Select Review Decision</label>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { id: 'approve', label: 'Approve & Publish', color: 'emerald' },
                      { id: 'request_changes', label: 'Request Changes', color: 'orange' },
                      { id: 'reject', label: 'Reject Item', color: 'rose' },
                      { id: 'pause', label: 'Pause Product', color: 'zinc' },
                    ].map((act) => (
                      <button
                        key={act.id}
                        type="button"
                        onClick={() => setReviewAction(act.id)}
                        className={`p-2.5 rounded-xl text-xs font-bold border transition-all text-left ${
                          reviewAction === act.id
                            ? 'bg-purple-600 text-white border-purple-600 shadow-xs'
                            : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                        }`}
                      >
                        {act.label}
                      </button>
                    ))}
                  </div>
                </div>

                {['reject', 'request_changes', 'pause'].includes(reviewAction) && (
                  <div className="space-y-1.5">
                    <label className="block text-xs font-bold text-slate-700">
                      Mandatory Feedback Reason <span className="text-rose-500">*</span>
                    </label>
                    <textarea
                      rows={3}
                      placeholder="Explain clearly what changes are needed or why this item was rejected..."
                      value={reviewNote}
                      onChange={(e) => setReviewNote(e.target.value)}
                      className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800"
                    />
                  </div>
                )}
              </div>

              <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between">
                <button
                  onClick={() => setShowReviewModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecuteReviewDecision}
                  disabled={actionLoading}
                  className="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors"
                >
                  {actionLoading ? 'Recording Decision...' : 'Confirm Decision'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════════ */}
        {/* MODAL 3: AUDIT TIMELINE & PRODUCT DETAILS                          */}
        {/* ════════════════════════════════════════════════════════════════════ */}
        {showDetailModal && detailedProduct && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-2xl w-full my-8 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-indigo-600" />
                  <h3 className="font-bold text-slate-900 text-sm">Product Detail & Audit History</h3>
                </div>
                <button onClick={() => setShowDetailModal(false)} className="text-slate-400 hover:text-slate-600">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
                {/* Product Snapshot */}
                <div className="flex items-start gap-4 p-4 bg-slate-50 rounded-2xl border border-slate-200">
                  <div className="w-16 h-16 rounded-xl bg-white border border-slate-200 shrink-0 overflow-hidden">
                    {detailedProduct.images?.[0] ? (
                      <img
                        src={detailedProduct.images[0].image_url}
                        alt=""
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-300">
                        <ImageIcon className="w-6 h-6" />
                      </div>
                    )}
                  </div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <span className="text-sm font-bold text-slate-900 block truncate">{detailedProduct.title}</span>
                    <p className="text-xs text-slate-500 font-mono">
                      SKU: <span className="font-bold text-slate-700">{detailedProduct.sku}</span> • Selling Price:{' '}
                      <span className="font-bold text-emerald-700">₹{detailedProduct.selling_price}</span> (MRP: ₹{detailedProduct.mrp})
                    </p>
                    <p className="text-[11px] text-slate-600">
                      Category: <span className="font-semibold">{detailedProduct.category_path}</span>
                    </p>
                  </div>
                </div>

                {/* Audit Timeline */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Decision & Lifecycle Timeline
                  </h4>

                  {detailedProduct.audit_logs?.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No audit events recorded.</p>
                  ) : (
                    <div className="space-y-2.5 border-l-2 border-indigo-200 pl-4 ml-2">
                      {detailedProduct.audit_logs.map((log) => (
                        <div key={log.id} className="relative space-y-0.5 text-xs">
                          <div className="w-2.5 h-2.5 bg-indigo-600 rounded-full absolute -left-[21px] top-1 ring-4 ring-white" />
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900">{log.action}</span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {new Date(log.created_at).toLocaleString()}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-600">{log.notes}</p>
                          <p className="text-[10px] text-slate-400">By: {log.actor_name}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/50 text-right">
                <button
                  onClick={() => setShowDetailModal(false)}
                  className="px-4 py-2 bg-slate-900 text-white font-bold text-xs rounded-xl shadow-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default SellerCatalogUploadsPage;
