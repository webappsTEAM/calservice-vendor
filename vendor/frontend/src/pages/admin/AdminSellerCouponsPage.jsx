import React, { useState, useEffect } from 'react';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetSellerHubCoupons,
  apiCreateSellerHubCoupon,
  apiUpdateSellerHubCoupon,
  apiDeleteSellerHubCoupon,
} from '../../api/workforceService.js';
import {
  Tag,
  Percent,
  Search,
  Plus,
  Edit2,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  X,
  Copy,
  Check,
  Calendar,
  Layers,
  Store,
  Clock,
  TrendingUp,
} from 'lucide-react';

export function AdminSellerCouponsPage() {
  const { user, isPlatformAdmin, isAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all'); // 'all', 'active', 'expired', 'inactive'
  const [typeFilter, setTypeFilter] = useState('all'); // 'all', 'percent', 'flat'
  const [copiedCode, setCopiedCode] = useState(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCoupon, setEditingCoupon] = useState(null);
  const [modalForm, setModalForm] = useState({
    code: '',
    description: '',
    discount_type: 'percent',
    discount_value: '',
    min_order_amount: '0.00',
    max_discount_amount: '',
    usage_limit_total: '',
    usage_limit_per_user: '1',
    valid_from: '',
    valid_until: '',
    is_active: true,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Delete State
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const fetchCoupons = async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (statusFilter !== 'all') params.status = statusFilter;
      if (typeFilter !== 'all') params.discount_type = typeFilter;

      const data = await apiGetSellerHubCoupons(params);
      setCoupons(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.data?.error || err.message || 'Failed to load coupons');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchCoupons();
    }, 250);
    return () => clearTimeout(timer);
  }, [search, statusFilter, typeFilter]);

  const handleCopyCode = (code) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const handleOpenCreate = () => {
    setEditingCoupon(null);
    setModalForm({
      code: '',
      description: '',
      discount_type: 'percent',
      discount_value: '10',
      min_order_amount: '0.00',
      max_discount_amount: '',
      usage_limit_total: '',
      usage_limit_per_user: '1',
      valid_from: '',
      valid_until: '',
      is_active: true,
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleOpenEdit = (coupon) => {
    setEditingCoupon(coupon);
    setModalForm({
      code: coupon.code || '',
      description: coupon.description || '',
      discount_type: coupon.discount_type || 'percent',
      discount_value: coupon.discount_value || '',
      min_order_amount: coupon.min_order_amount || '0.00',
      max_discount_amount: coupon.max_discount_amount || '',
      usage_limit_total: coupon.usage_limit_total ?? '',
      usage_limit_per_user: coupon.usage_limit_per_user ?? '1',
      valid_from: coupon.valid_from ? coupon.valid_from.substring(0, 16) : '',
      valid_until: coupon.valid_until ? coupon.valid_until.substring(0, 16) : '',
      is_active: Boolean(coupon.is_active),
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleModalSubmit = async (e) => {
    e.preventDefault();
    if (!modalForm.code.trim()) {
      setFormError('Coupon code is required.');
      return;
    }
    if (!modalForm.discount_value || parseFloat(modalForm.discount_value) <= 0) {
      setFormError('A valid positive discount value is required.');
      return;
    }

    try {
      setFormSubmitting(true);
      setFormError('');
      const payload = {
        ...modalForm,
        code: modalForm.code.trim().toUpperCase(),
        discount_value: parseFloat(modalForm.discount_value),
        min_order_amount: parseFloat(modalForm.min_order_amount || '0'),
        max_discount_amount: modalForm.max_discount_amount ? parseFloat(modalForm.max_discount_amount) : null,
        usage_limit_total: modalForm.usage_limit_total ? parseInt(modalForm.usage_limit_total, 10) : null,
        usage_limit_per_user: parseInt(modalForm.usage_limit_per_user || '1', 10),
        valid_from: modalForm.valid_from ? new Date(modalForm.valid_from).toISOString() : null,
        valid_until: modalForm.valid_until ? new Date(modalForm.valid_until).toISOString() : null,
      };

      if (editingCoupon) {
        await apiUpdateSellerHubCoupon(editingCoupon.id, payload);
      } else {
        await apiCreateSellerHubCoupon(payload);
      }
      setIsModalOpen(false);
      await fetchCoupons();
    } catch (err) {
      setFormError(err?.data?.error || err.message || 'Failed to save coupon');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleToggleActive = async (coupon) => {
    try {
      await apiUpdateSellerHubCoupon(coupon.id, { is_active: !coupon.is_active });
      setCoupons(prev =>
        prev.map(item => (item.id === coupon.id ? { ...item, is_active: !item.is_active } : item))
      );
    } catch (err) {
      alert(err?.data?.error || 'Failed to update coupon status');
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      setDeleting(true);
      setDeleteError('');
      await apiDeleteSellerHubCoupon(deleteTarget.id);
      setDeleteTarget(null);
      await fetchCoupons();
    } catch (err) {
      setDeleteError(err?.data?.error || err.message || 'Failed to delete coupon');
    } finally {
      setDeleting(false);
    }
  };

  const getCouponStatusBadge = (coupon) => {
    if (!coupon.is_active) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
          <XCircle className="w-3 h-3 text-slate-400" />
          Inactive
        </span>
      );
    }
    if (coupon.valid_until && new Date(coupon.valid_until) < new Date()) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">
          <Clock className="w-3 h-3 text-rose-500" />
          Expired
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        Active
      </span>
    );
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans antialiased text-slate-900 overflow-hidden">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 z-10 shadow-xs">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 mb-1">
              <Store className="w-4 h-4 text-indigo-600" />
              <span>Seller Hub</span>
              <span>/</span>
              <span className="text-slate-900 font-bold">Coupons & Promotions</span>
            </div>
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Promotional Coupons
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Create and manage discount codes, percentage vouchers, and customer incentives.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchCoupons}
              disabled={loading}
              className="px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all flex items-center gap-1.5 shadow-xs"
              title="Refresh"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handleOpenCreate}
              className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-all flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-4 h-4" />
              <span>Create Coupon</span>
            </button>
          </div>
        </header>

        {/* Content Container */}
        <div className="p-6 max-w-7xl w-full mx-auto space-y-6">
          {/* Filter Bar */}
          <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-xs flex flex-col md:flex-row gap-4 justify-between items-center">
            {/* Search */}
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search coupon code, description..."
                className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all font-mono"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
              <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200 text-xs font-medium">
                <button
                  onClick={() => setStatusFilter('all')}
                  className={`px-3 py-1.5 rounded-md transition-all ${
                    statusFilter === 'all'
                      ? 'bg-white text-slate-900 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  All Status
                </button>
                <button
                  onClick={() => setStatusFilter('active')}
                  className={`px-3 py-1.5 rounded-md transition-all ${
                    statusFilter === 'active'
                      ? 'bg-white text-emerald-700 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Active
                </button>
                <button
                  onClick={() => setStatusFilter('expired')}
                  className={`px-3 py-1.5 rounded-md transition-all ${
                    statusFilter === 'expired'
                      ? 'bg-white text-rose-700 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Expired
                </button>
                <button
                  onClick={() => setStatusFilter('inactive')}
                  className={`px-3 py-1.5 rounded-md transition-all ${
                    statusFilter === 'inactive'
                      ? 'bg-white text-slate-700 font-bold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Disabled
                </button>
              </div>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="text-xs bg-white border border-slate-200 rounded-lg px-2.5 py-1.5 font-medium text-slate-700 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Discount Types</option>
                <option value="percent">Percentage (%)</option>
                <option value="flat">Flat Amount (₹)</option>
              </select>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 p-4 rounded-xl flex items-start gap-3 text-xs">
              <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-bold">Error loading coupons</p>
                <p className="mt-0.5">{error}</p>
              </div>
              <button
                onClick={fetchCoupons}
                className="px-2.5 py-1 bg-rose-600 text-white rounded font-bold hover:bg-rose-700 transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* Main Content Area */}
          {loading ? (
            <div className="bg-white rounded-xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center gap-3 shadow-xs">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-semibold text-slate-500">Loading coupons and promotions...</p>
            </div>
          ) : coupons.length === 0 ? (
            <div className="bg-white rounded-xl p-12 border border-slate-200 text-center flex flex-col items-center justify-center gap-3 shadow-xs">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                <Tag className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800">No coupons found</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                  {search || statusFilter !== 'all' || typeFilter !== 'all'
                    ? 'Try adjusting your search query or filters.'
                    : 'Create your first discount coupon to boost customer orders.'}
                </p>
              </div>
              {!search && (
                <button
                  onClick={handleOpenCreate}
                  className="mt-2 px-4 py-2 text-xs font-bold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-all shadow-xs"
                >
                  Create First Coupon
                </button>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="px-4 py-3.5">Coupon Code</th>
                      {isSuperAdmin && <th className="px-4 py-3.5">Store / Vendor</th>}
                      <th className="px-4 py-3.5">Discount Rule</th>
                      <th className="px-4 py-3.5">Limits & Thresholds</th>
                      <th className="px-4 py-3.5 text-center">Usage</th>
                      <th className="px-4 py-3.5">Validity</th>
                      <th className="px-4 py-3.5 text-center">Status</th>
                      <th className="px-4 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {coupons.map((c) => {
                      const isPercent = c.discount_type === 'percent';
                      const usagePercent = c.usage_limit_total
                        ? Math.min(100, Math.round((c.times_used / c.usage_limit_total) * 100))
                        : null;

                      return (
                        <tr key={c.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="px-4 py-3.5">
                            <div className="flex items-center gap-2">
                              <div className="px-2.5 py-1 rounded-md bg-indigo-50 border border-indigo-200/80 font-mono font-black text-indigo-700 tracking-wider text-xs">
                                {c.code}
                              </div>
                              <button
                                onClick={() => handleCopyCode(c.code)}
                                className="p-1 text-slate-400 hover:text-indigo-600 rounded transition-colors"
                                title="Copy code"
                              >
                                {copiedCode === c.code ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <Copy className="w-3.5 h-3.5" />
                                )}
                              </button>
                            </div>
                            {c.description && (
                              <p className="text-[11px] text-slate-500 mt-1 max-w-xs truncate">{c.description}</p>
                            )}
                          </td>

                          {isSuperAdmin && (
                            <td className="px-4 py-3.5">
                              <div className="flex items-center gap-1.5 font-medium text-slate-800">
                                <Store className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                <span className="truncate max-w-[140px]">{c.company_name || 'Platform Universal'}</span>
                              </div>
                            </td>
                          )}

                          <td className="px-4 py-3.5">
                            <div className="font-bold text-slate-900 flex items-center gap-1.5">
                              {isPercent ? (
                                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono">
                                  {c.discount_value}% OFF
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-mono">
                                  ₹{c.discount_value} FLAT
                                </span>
                              )}
                            </div>
                            {isPercent && c.max_discount_amount && (
                              <span className="text-[10px] text-slate-500 block mt-0.5">
                                Capped at ₹{c.max_discount_amount}
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-3.5 space-y-0.5 text-slate-600 text-[11px]">
                            <div>
                              Min Order: <strong className="text-slate-800">₹{c.min_order_amount || '0'}</strong>
                            </div>
                            <div>
                              Per User: <span className="font-medium text-slate-700">{c.usage_limit_per_user || 1}x</span>
                            </div>
                          </td>

                          <td className="px-4 py-3.5 text-center">
                            <div className="inline-flex flex-col items-center">
                              <span className="font-mono font-bold text-slate-800">
                                {c.times_used}{' '}
                                <span className="text-slate-400 font-normal">
                                  / {c.usage_limit_total ? c.usage_limit_total : '∞'}
                                </span>
                              </span>
                              {usagePercent !== null && (
                                <div className="w-16 bg-slate-100 rounded-full h-1.5 mt-1 overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      usagePercent >= 90 ? 'bg-rose-500' : 'bg-indigo-600'
                                    }`}
                                    style={{ width: `${usagePercent}%` }}
                                  />
                                </div>
                              )}
                            </div>
                          </td>

                          <td className="px-4 py-3.5 space-y-0.5 text-[11px] text-slate-500">
                            {c.valid_until ? (
                              <div className="flex items-center gap-1 text-slate-700 font-medium">
                                <Calendar className="w-3 h-3 text-slate-400 shrink-0" />
                                <span>Until {new Date(c.valid_until).toLocaleDateString()}</span>
                              </div>
                            ) : (
                              <span className="text-emerald-600 font-medium">No Expiry Date</span>
                            )}
                          </td>

                          <td className="px-4 py-3.5 text-center">{getCouponStatusBadge(c)}</td>

                          <td className="px-4 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => handleOpenEdit(c)}
                                className="p-1.5 text-slate-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg transition-colors"
                                title="Edit Coupon"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  setDeleteTarget(c);
                                  setDeleteError('');
                                }}
                                className="p-1.5 text-slate-600 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition-colors"
                                title="Delete Coupon"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* ── CREATE / EDIT COUPON MODAL ── */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">
                    {editingCoupon ? 'Edit Discount Coupon' : 'Create New Coupon'}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {editingCoupon
                      ? 'Update discount rules, limits, and validity dates.'
                      : 'Define code and redemption constraints for your store.'}
                  </p>
                </div>
                <button
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 text-slate-400 hover:text-slate-700 rounded-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <form onSubmit={handleModalSubmit} className="p-6 space-y-4 text-xs">
                {formError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{formError}</span>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      Coupon Code <span className="text-rose-600">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={modalForm.code}
                      onChange={(e) => setModalForm({ ...modalForm, code: e.target.value.toUpperCase() })}
                      placeholder="e.g. WELCOME20, FESTIVE100"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 font-mono font-bold uppercase text-indigo-700"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Discount Type</label>
                    <select
                      value={modalForm.discount_type}
                      onChange={(e) => setModalForm({ ...modalForm, discount_type: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 bg-white font-medium"
                    >
                      <option value="percent">Percentage (%)</option>
                      <option value="flat">Flat Amount (₹)</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">
                      Discount Value <span className="text-rose-600">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        step="0.01"
                        required
                        value={modalForm.discount_value}
                        onChange={(e) => setModalForm({ ...modalForm, discount_value: e.target.value })}
                        placeholder={modalForm.discount_type === 'percent' ? '15' : '100'}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-bold"
                      />
                      <span className="absolute right-3 top-1/2 -translate-y-1/2 font-bold text-slate-400">
                        {modalForm.discount_type === 'percent' ? '%' : '₹'}
                      </span>
                    </div>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Min Order Amount (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={modalForm.min_order_amount}
                      onChange={(e) => setModalForm({ ...modalForm, min_order_amount: e.target.value })}
                      placeholder="0.00"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-medium"
                    />
                  </div>
                </div>

                {modalForm.discount_type === 'percent' && (
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Max Discount Cap (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={modalForm.max_discount_amount}
                      onChange={(e) => setModalForm({ ...modalForm, max_discount_amount: e.target.value })}
                      placeholder="Leave blank for no upper limit"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-medium"
                    />
                  </div>
                )}

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Description / Customer Note</label>
                  <input
                    type="text"
                    value={modalForm.description}
                    onChange={(e) => setModalForm({ ...modalForm, description: e.target.value })}
                    placeholder="e.g. 20% discount on orders above ₹500"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Total Usage Limit</label>
                    <input
                      type="number"
                      value={modalForm.usage_limit_total}
                      onChange={(e) => setModalForm({ ...modalForm, usage_limit_total: e.target.value })}
                      placeholder="Unlimited (Leave blank)"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-medium"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Limit Per Customer</label>
                    <input
                      type="number"
                      value={modalForm.usage_limit_per_user}
                      onChange={(e) => setModalForm({ ...modalForm, usage_limit_per_user: e.target.value })}
                      placeholder="1"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 font-medium"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Valid From</label>
                    <input
                      type="datetime-local"
                      value={modalForm.valid_from}
                      onChange={(e) => setModalForm({ ...modalForm, valid_from: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 text-[11px]"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Valid Until (Expiry)</label>
                    <input
                      type="datetime-local"
                      value={modalForm.valid_until}
                      onChange={(e) => setModalForm({ ...modalForm, valid_until: e.target.value })}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-500 text-[11px]"
                    />
                  </div>
                </div>

                <div className="pt-2">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={modalForm.is_active}
                      onChange={(e) => setModalForm({ ...modalForm, is_active: e.target.checked })}
                      className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300"
                    />
                    <span className="font-bold text-slate-800">Coupon Active and Redeemable</span>
                  </label>
                </div>

                <div className="pt-4 border-t border-slate-200 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    className="px-4 py-2 font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
                  >
                    {formSubmitting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                    <span>{editingCoupon ? 'Save Changes' : 'Create Coupon'}</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── DELETE MODAL ── */}
        {deleteTarget && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
                  <AlertCircle className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">Delete Coupon</h3>
                  <p className="text-xs text-slate-500">
                    Are you sure you want to delete coupon <strong className="text-slate-800 font-mono">"{deleteTarget.code}"</strong>?
                  </p>
                </div>
              </div>

              {deleteError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs">
                  {deleteError}
                </div>
              )}

              <p className="text-xs text-slate-500 leading-relaxed">
                Customers will no longer be able to apply this coupon code on checkout. Existing completed orders will preserve their historic redemption records.
              </p>

              <div className="pt-2 flex items-center justify-end gap-2 text-xs">
                <button
                  onClick={() => {
                    setDeleteTarget(null);
                    setDeleteError('');
                  }}
                  className="px-4 py-2 font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={deleting}
                  className="px-4 py-2 font-bold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
                >
                  {deleting && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Delete Coupon</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default AdminSellerCouponsPage;
