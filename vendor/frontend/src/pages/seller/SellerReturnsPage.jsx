import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  RotateCcw,
  Clock,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Search,
  RefreshCw,
  ChevronRight,
  Eye,
  X,
  FileText,
  User,
  Phone,
  MapPin,
  Calendar,
  Check,
  Ban,
  Package,
  Truck,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  ExternalLink,
  Layers,
  Inbox,
  CheckSquare,
} from 'lucide-react';

export function SellerReturnsPage() {
  const { user, token, isPlatformAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [returnsList, setReturnsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Metrics
  const [metrics, setMetrics] = useState({
    total_returns_count: 0,
    pending_returns_count: 0,
    under_inspection_returns_count: 0,
    resolved_returns_count: 0,
  });

  // Selected Return for Detail & Action Drawer
  const [selectedReturnId, setSelectedReturnId] = useState(null);
  const [selectedReturnDetail, setSelectedReturnDetail] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Form states for drawer actions
  const [actionLoading, setActionLoading] = useState(false);
  const [reviewForm, setReviewForm] = useState({ decision: 'approve', seller_notes: '', rejection_reason: '' });
  const [pickupForm, setPickupForm] = useState({ pickup_ref: '', notes: '' });
  const [receiveForm, setReceiveForm] = useState({ notes: '' });
  const [qcForm, setQcForm] = useState({
    quality_check_status: 'PASSED',
    quality_check_notes: '',
    items_qc: [],
  });
  const [restockForm, setRestockForm] = useState({
    restock_decision: 'FULL_RESTOCK',
    restock_notes: '',
    items_breakdown: [],
  });
  const [closeForm, setCloseForm] = useState({ notes: '' });

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Load metrics
  const loadMetrics = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch('/api/workforce/seller-hub/metrics/', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics({
          total_returns_count: data.total_returns_count || 0,
          pending_returns_count: data.pending_returns_count || 0,
          under_inspection_returns_count: data.under_inspection_returns_count || 0,
          resolved_returns_count: data.resolved_returns_count || 0,
        });
      }
    } catch (e) {
      console.error('Failed to load metrics', e);
    }
  }, [token]);

  // Load Returns
  const loadReturns = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'ALL') {
        params.append('status', statusFilter);
      }
      if (debouncedSearch) {
        params.append('search', debouncedSearch);
      }

      const res = await fetch(`/api/workforce/seller-hub/returns/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error('Failed to fetch returns from server.');
      }

      const data = await res.json();
      setReturnsList(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      setError(e.message || 'Error loading returns');
      setReturnsList([]);
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, debouncedSearch]);

  useEffect(() => {
    loadReturns();
    loadMetrics();
  }, [loadReturns, loadMetrics]);

  // Fetch Return Detail
  const openReturnDetail = async (retId) => {
    setSelectedReturnId(retId);
    setIsDrawerOpen(true);
    setDrawerLoading(true);

    try {
      const res = await fetch(`/api/workforce/seller-hub/returns/${retId}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedReturnDetail(data);

        // Prepopulate QC form items
        if (data.items) {
          setQcForm({
            quality_check_status: data.quality_check_status || 'PASSED',
            quality_check_notes: data.quality_check_notes || '',
            items_qc: data.items.map((it) => ({
              item_id: it.id,
              item_condition: it.item_condition || 'SEALED_INTACT',
              qc_result: it.qc_result || 'PASSED',
              qc_notes: it.qc_notes || '',
            })),
          });

          // Prepopulate Restock form items
          setRestockForm({
            restock_decision: data.restock_decision || 'FULL_RESTOCK',
            restock_notes: data.restock_notes || '',
            items_breakdown: data.items.map((it) => ({
              item_id: it.id,
              restocked_quantity: it.restocked_quantity || it.returned_quantity,
              scrapped_quantity: it.scrapped_quantity || 0,
            })),
          });
        }
      }
    } catch (e) {
      console.error('Failed to load return detail', e);
    } finally {
      setDrawerLoading(false);
    }
  };

  // Perform Review Decision
  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/review/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(reviewForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || errData.rejection_reason || 'Review action failed.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Schedule Pickup
  const handleSchedulePickup = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/schedule-pickup/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(pickupForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to schedule pickup.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Mark Received
  const handleMarkReceived = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/receive/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(receiveForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to acknowledge receipt.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Submit QC Inspection
  const handleQcSubmit = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/quality-check/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(qcForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to submit quality check.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Submit Restock
  const handleRestockSubmit = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    if (!window.confirm('Are you sure you want to restock these items? Verified quantities will be atomically added back to your active store inventory ledger.')) {
      return;
    }

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/restock/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(restockForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to complete restocking.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Close Return Case
  const handleCloseSubmit = async (e) => {
    e.preventDefault();
    if (!selectedReturnId) return;

    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/returns/${selectedReturnId}/close/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(closeForm),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || 'Failed to close return case.');
      }

      await openReturnDetail(selectedReturnId);
      loadReturns();
      loadMetrics();
    } catch (e) {
      alert(e.message);
    } finally {
      setActionLoading(false);
    }
  };

  // Status Badge Helper
  const getStatusBadge = (status) => {
    const map = {
      REQUESTED: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Requested' },
      UNDER_SELLER_REVIEW: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', label: 'Under Review' },
      APPROVED: { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', label: 'Approved' },
      PICKUP_SCHEDULED: { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', label: 'Pickup Scheduled' },
      RECEIVED: { bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200', label: 'Received at Store' },
      QUALITY_CHECK: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', label: 'Quality Check' },
      RESTOCKED: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Restocked' },
      CLOSED: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300', label: 'Closed' },
      REJECTED: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', label: 'Rejected' },
      DISCARDED: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', label: 'Scrapped' },
      ESCALATED_TO_ADMIN: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Escalated' },
    };
    const s = map[status] || { bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', label: status };
    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${s.bg} ${s.text} ${s.border}`}>
        {s.label}
      </span>
    );
  };

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-amber-50 text-amber-600 rounded-xl border border-amber-100">
              <RotateCcw className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Returns & Reverse Logistics</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">
                  Seller Hub
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Process customer returns, parcel receipts, physical quality inspections, and stock-in adjustments
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadReturns();
                loadMetrics();
              }}
              className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
              title="Refresh Returns"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <Link
              to="/workforce/seller/dashboard"
              className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Seller Home
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div
              onClick={() => setStatusFilter('PENDING')}
              className={`bg-white p-4 rounded-xl border transition-all cursor-pointer shadow-xs ${
                statusFilter === 'PENDING' ? 'border-amber-500 ring-2 ring-amber-100' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Pending Review</span>
                <Clock className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{metrics.pending_returns_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Action required</p>
            </div>

            <div
              onClick={() => setStatusFilter('IN_INSPECTION')}
              className={`bg-white p-4 rounded-xl border transition-all cursor-pointer shadow-xs ${
                statusFilter === 'IN_INSPECTION' ? 'border-purple-500 ring-2 ring-purple-100' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Under Inspection</span>
                <AlertTriangle className="w-4 h-4 text-purple-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{metrics.under_inspection_returns_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Pickup / Store QC</p>
            </div>

            <div
              onClick={() => setStatusFilter('RESOLVED')}
              className={`bg-white p-4 rounded-xl border transition-all cursor-pointer shadow-xs ${
                statusFilter === 'RESOLVED' ? 'border-emerald-500 ring-2 ring-emerald-100' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Resolved / Restocked</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{metrics.resolved_returns_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Closed & restocked</p>
            </div>

            <div
              onClick={() => setStatusFilter('ALL')}
              className={`bg-white p-4 rounded-xl border transition-all cursor-pointer shadow-xs ${
                statusFilter === 'ALL' ? 'border-blue-500 ring-2 ring-blue-100' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Total Returns</span>
                <RotateCcw className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{metrics.total_returns_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">All time cases</p>
            </div>
          </div>

          {/* Controls Bar */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Filter Pills */}
            <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto">
              {[
                { id: 'ALL', label: 'All Returns' },
                { id: 'PENDING', label: 'Pending Review' },
                { id: 'APPROVED', label: 'Approved' },
                { id: 'PICKUP_SCHEDULED', label: 'Pickup Scheduled' },
                { id: 'RECEIVED', label: 'Received' },
                { id: 'QUALITY_CHECK', label: 'Quality Check' },
                { id: 'RESTOCKED', label: 'Restocked' },
                { id: 'CLOSED', label: 'Closed' },
                { id: 'REJECTED', label: 'Rejected' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    statusFilter === tab.id
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="relative w-full md:w-72">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search Return #, Order #, customer..."
                className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-slate-900 focus:bg-white transition-all"
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
          </div>

          {/* Table Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            {loading ? (
              <div className="p-16 flex flex-col items-center justify-center gap-3">
                <RefreshCw className="w-6 h-6 text-slate-400 animate-spin" />
                <p className="text-xs text-slate-500 font-medium">Loading return cases...</p>
              </div>
            ) : returnsList.length === 0 ? (
              <div className="p-16 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-4 shadow-xs">
                  <Inbox className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-base font-bold text-slate-900">No Return Cases Found</h3>
                <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed">
                  {debouncedSearch || statusFilter !== 'ALL'
                    ? 'No returns matching your search criteria. Try adjusting your filter parameters.'
                    : 'There are currently no active customer return requests for your store. When customers initiate return requests, they will appear here.'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                      <th className="py-3.5 px-4">Return Number</th>
                      <th className="py-3.5 px-4">Order Ref</th>
                      <th className="py-3.5 px-4">Customer</th>
                      <th className="py-3.5 px-4">Items / Reason</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">QC Result</th>
                      <th className="py-3.5 px-4">Date</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {returnsList.map((ret) => (
                      <tr
                        key={ret.id}
                        className="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                        onClick={() => openReturnDetail(ret.id)}
                      >
                        <td className="py-3.5 px-4">
                          <div className="font-bold text-slate-900 font-mono">{ret.return_number}</div>
                          {ret.source_return_id && (
                            <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                              Src: {ret.source_return_id}
                            </div>
                          )}
                        </td>
                        <td className="py-3.5 px-4 font-mono font-medium text-blue-600">
                          #{ret.order_number || 'N/A'}
                        </td>
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-slate-900">{ret.customer_name || 'Customer'}</div>
                          <div className="text-[10px] text-slate-400">{ret.customer_phone || 'No phone'}</div>
                        </td>
                        <td className="py-3.5 px-4 max-w-xs">
                          <div className="font-medium text-slate-800 truncate">{ret.items_summary || `${ret.items_count} items`}</div>
                          <div className="text-[11px] text-slate-500 truncate mt-0.5 font-sans">
                            Reason: <span className="font-medium text-slate-700">{ret.reason}</span>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">{getStatusBadge(ret.status)}</td>
                        <td className="py-3.5 px-4">
                          {ret.quality_check_status ? (
                            <span className="text-[11px] font-semibold text-slate-700">
                              {ret.quality_check_status}
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-400 italic">Pending QC</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-[11px] text-slate-500 whitespace-nowrap">
                          {ret.created_at ? new Date(ret.created_at).toLocaleDateString('en-GB') : '-'}
                        </td>
                        <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => openReturnDetail(ret.id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors shadow-xs"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>Manage</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Return Case Management Drawer */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-white shadow-2xl h-full flex flex-col overflow-hidden border-l border-slate-200">
            {/* Drawer Header */}
            <div className="p-6 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-slate-900 font-mono">
                    {selectedReturnDetail?.return_number || `Return #${selectedReturnId}`}
                  </h2>
                  {selectedReturnDetail && getStatusBadge(selectedReturnDetail.status)}
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  Order Ref: <span className="font-mono font-medium text-slate-700">#{selectedReturnDetail?.order_number || 'N/A'}</span>
                  {selectedReturnDetail?.source_return_id && ` · Source Ref: ${selectedReturnDetail.source_return_id}`}
                </p>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {drawerLoading ? (
                <div className="py-24 flex flex-col items-center justify-center gap-3">
                  <RefreshCw className="w-6 h-6 text-slate-400 animate-spin" />
                  <p className="text-xs text-slate-500 font-medium">Loading return dossier...</p>
                </div>
              ) : selectedReturnDetail ? (
                <>
                  {/* Customer & Reason Summary */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-700 uppercase tracking-wider">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>Customer Information</span>
                      </div>
                      <span className="text-[11px] text-slate-500">
                        {selectedReturnDetail.created_at ? new Date(selectedReturnDetail.created_at).toLocaleString() : ''}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase">Name</span>
                        <span className="font-semibold text-slate-900">{selectedReturnDetail.customer_name || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase">Phone</span>
                        <span className="font-medium text-slate-700 font-mono">{selectedReturnDetail.customer_phone || 'N/A'}</span>
                      </div>
                    </div>

                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase">Reason for Return</span>
                      <p className="text-xs font-medium text-amber-900 bg-amber-50 p-2.5 rounded-lg border border-amber-200 mt-1">
                        {selectedReturnDetail.reason}
                        {selectedReturnDetail.customer_notes && (
                          <span className="block text-[11px] text-slate-600 mt-1 font-normal italic">
                            "{selectedReturnDetail.customer_notes}"
                          </span>
                        )}
                      </p>
                    </div>

                    {/* Photo Evidence Snapshots */}
                    {selectedReturnDetail.evidence_urls && selectedReturnDetail.evidence_urls.length > 0 && (
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase mb-1.5">Submitted Evidence</span>
                        <div className="flex flex-wrap gap-2">
                          {selectedReturnDetail.evidence_urls.map((url, idx) => (
                            <a
                              key={idx}
                              href={url}
                              target="_blank"
                              rel="noreferrer"
                              className="group relative block w-16 h-16 rounded-lg overflow-hidden border border-slate-200 bg-slate-100"
                            >
                              <img src={url} alt="Evidence" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                              <div className="absolute inset-0 bg-slate-900/40 opacity-0 group-hover:opacity-100 flex items-center justify-center text-white transition-opacity">
                                <ExternalLink className="w-3.5 h-3.5" />
                              </div>
                            </a>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Return Line Items */}
                  <div>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Package className="w-3.5 h-3.5" />
                      <span>Returned Items ({selectedReturnDetail.items?.length || 0})</span>
                    </h3>

                    <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100">
                      {selectedReturnDetail.items?.map((it) => (
                        <div key={it.id} className="p-3 bg-white flex items-center justify-between text-xs">
                          <div>
                            <div className="font-semibold text-slate-900">{it.product_title}</div>
                            <div className="text-[11px] text-slate-400 font-mono">
                              SKU: {it.sku} · Qty Returned: <span className="font-bold text-slate-700">{it.returned_quantity}</span>
                            </div>
                            {it.item_condition && (
                              <div className="text-[10px] text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 inline-block mt-1 font-semibold">
                                Condition: {it.item_condition}
                              </div>
                            )}
                          </div>
                          <div className="text-right">
                            {it.restocked_quantity > 0 && (
                              <div className="text-[11px] font-bold text-emerald-600">
                                +{it.restocked_quantity} Restocked
                              </div>
                            )}
                            {it.scrapped_quantity > 0 && (
                              <div className="text-[11px] font-semibold text-orange-600">
                                {it.scrapped_quantity} Scrapped
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Operational Action Panels based on State Machine */}

                  {/* 1. Seller Review Step */}
                  {(selectedReturnDetail.status === 'REQUESTED' || selectedReturnDetail.status === 'UNDER_SELLER_REVIEW') && (
                    <div className="p-4 bg-amber-50/50 rounded-xl border border-amber-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-amber-900">
                        <CheckSquare className="w-4 h-4 text-amber-600" />
                        <span>Step 1: Seller Review Decision</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Review customer claim. Approve to schedule return pickup, or reject with a documented rationale.
                      </p>

                      <form onSubmit={handleReviewSubmit} className="space-y-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Decision</label>
                          <select
                            value={reviewForm.decision}
                            onChange={(e) => setReviewForm({ ...reviewForm, decision: e.target.value })}
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-slate-900"
                          >
                            <option value="approve">Approve Return (Accept Item Return)</option>
                            <option value="reject">Reject Return</option>
                            <option value="escalate">Escalate to Platform Admin</option>
                          </select>
                        </div>

                        {reviewForm.decision === 'reject' && (
                          <div>
                            <label className="block text-[11px] font-semibold text-red-700 mb-1">Rejection Reason *</label>
                            <input
                              type="text"
                              required
                              value={reviewForm.rejection_reason}
                              onChange={(e) => setReviewForm({ ...reviewForm, rejection_reason: e.target.value })}
                              placeholder="e.g. Return window expired, non-returnable grocery category"
                              className="w-full p-2 bg-white border border-red-200 rounded-lg text-xs focus:ring-2 focus:ring-red-500"
                            />
                          </div>
                        )}

                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Seller Notes (Optional)</label>
                          <textarea
                            rows={2}
                            value={reviewForm.seller_notes}
                            onChange={(e) => setReviewForm({ ...reviewForm, seller_notes: e.target.value })}
                            placeholder="Internal instructions or notes..."
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-slate-900"
                          />
                        </div>

                        <button
                          type="submit"
                          disabled={actionLoading}
                          className="w-full py-2.5 px-4 bg-slate-900 hover:bg-black text-white rounded-lg text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                        >
                          {actionLoading ? 'Recording Decision...' : 'Confirm Review Decision'}
                        </button>
                      </form>
                    </div>
                  )}

                  {/* 2. Schedule Pickup Step */}
                  {selectedReturnDetail.status === 'APPROVED' && (
                    <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-indigo-900">
                        <Truck className="w-4 h-4 text-indigo-600" />
                        <span>Step 2: Reverse Pickup / Courier Dispatch</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Record pickup reference or courier tracking number.
                      </p>

                      <form onSubmit={handleSchedulePickup} className="space-y-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Pickup Tracking / Ref #</label>
                          <input
                            type="text"
                            value={pickupForm.pickup_ref}
                            onChange={(e) => setPickupForm({ ...pickupForm, pickup_ref: e.target.value })}
                            placeholder="e.g. SEVO-RIDER-PICKUP-8902"
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>

                        <div className="flex gap-2">
                          <button
                            type="submit"
                            disabled={actionLoading}
                            className="flex-1 py-2 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                          >
                            {actionLoading ? 'Scheduling...' : 'Mark Pickup Scheduled'}
                          </button>
                          <button
                            type="button"
                            onClick={handleMarkReceived}
                            disabled={actionLoading}
                            className="flex-1 py-2 px-3 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                          >
                            Mark Received Directly
                          </button>
                        </div>
                      </form>
                    </div>
                  )}

                  {/* 3. Acknowledge Receipt Step */}
                  {selectedReturnDetail.status === 'PICKUP_SCHEDULED' && (
                    <div className="p-4 bg-cyan-50/50 rounded-xl border border-cyan-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-cyan-900">
                        <Inbox className="w-4 h-4 text-cyan-600" />
                        <span>Step 3: Parcel Arrival at Store</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Acknowledge physical receipt of the returned item package at your store warehouse.
                      </p>

                      <button
                        onClick={handleMarkReceived}
                        disabled={actionLoading}
                        className="w-full py-2.5 px-4 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                      >
                        {actionLoading ? 'Updating...' : 'Acknowledge Package Received'}
                      </button>
                    </div>
                  )}

                  {/* 4. Quality Inspection Step */}
                  {(selectedReturnDetail.status === 'RECEIVED' || selectedReturnDetail.status === 'QUALITY_CHECK') && (
                    <div className="p-4 bg-yellow-50/50 rounded-xl border border-yellow-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-yellow-900">
                        <ShieldCheck className="w-4 h-4 text-yellow-600" />
                        <span>Step 4: Quality Inspection (QC)</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Perform physical check on seal integrity, expiry date, and condition.
                      </p>

                      <form onSubmit={handleQcSubmit} className="space-y-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Overall QC Result</label>
                          <select
                            value={qcForm.quality_check_status}
                            onChange={(e) => setQcForm({ ...qcForm, quality_check_status: e.target.value })}
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-yellow-500"
                          >
                            <option value="PASSED">Passed (Fit for Restock)</option>
                            <option value="FAILED">Failed (Damaged / Unusable / Expired)</option>
                            <option value="PARTIAL_PASS">Partial Pass</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">QC Notes</label>
                          <input
                            type="text"
                            value={qcForm.quality_check_notes}
                            onChange={(e) => setQcForm({ ...qcForm, quality_check_notes: e.target.value })}
                            placeholder="e.g. Seal intact, expiry in 6 months, original packaging verified"
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                          />
                        </div>

                        <button
                          type="submit"
                          disabled={actionLoading}
                          className="w-full py-2 px-3 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                        >
                          {actionLoading ? 'Saving Inspection...' : 'Save Quality Inspection Result'}
                        </button>
                      </form>
                    </div>
                  )}

                  {/* 5. Restock & Disposal Step */}
                  {(selectedReturnDetail.status === 'QUALITY_CHECK' || selectedReturnDetail.status === 'RECEIVED') && (
                    <div className="p-4 bg-emerald-50/50 rounded-xl border border-emerald-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-emerald-900">
                        <Layers className="w-4 h-4 text-emerald-600" />
                        <span>Step 5: Restocking & Inventory Ledger Update</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Put fit goods back into active stock. Immutable <span className="font-semibold text-emerald-700">STOCK_IN</span> movements will be recorded.
                      </p>

                      <form onSubmit={handleRestockSubmit} className="space-y-3">
                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Restock Mode</label>
                          <select
                            value={restockForm.restock_decision}
                            onChange={(e) => setRestockForm({ ...restockForm, restock_decision: e.target.value })}
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs font-medium focus:ring-2 focus:ring-emerald-500"
                          >
                            <option value="FULL_RESTOCK">Full Restock (All Returned Units)</option>
                            <option value="PARTIAL_RESTOCK">Partial Restock</option>
                            <option value="SCRAP_DISPOSE">Scrap / Dispose All (0 Units Restocked)</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-[11px] font-semibold text-slate-700 mb-1">Restock Notes</label>
                          <input
                            type="text"
                            value={restockForm.restock_notes}
                            onChange={(e) => setRestockForm({ ...restockForm, restock_notes: e.target.value })}
                            placeholder="e.g. Restocked shelf A-04"
                            className="w-full p-2 bg-white border border-slate-200 rounded-lg text-xs"
                          />
                        </div>

                        <button
                          type="submit"
                          disabled={actionLoading}
                          className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors shadow-xs disabled:opacity-50"
                        >
                          {actionLoading ? 'Updating Inventory Ledger...' : 'Execute Restock & Balance Update'}
                        </button>
                      </form>
                    </div>
                  )}

                  {/* 6. Close Return Case Step */}
                  {['RESTOCKED', 'DISCARDED', 'REJECTED'].includes(selectedReturnDetail.status) && (
                    <div className="p-4 bg-slate-100 rounded-xl border border-slate-200 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-bold text-slate-800">
                        <CheckCircle2 className="w-4 h-4 text-slate-600" />
                        <span>Final Step: Close Return Case</span>
                      </div>
                      <p className="text-[11px] text-slate-600">
                        Mark this return case as fully resolved and closed.
                      </p>

                      <button
                        onClick={handleCloseSubmit}
                        disabled={actionLoading}
                        className="w-full py-2 px-3 bg-slate-900 hover:bg-black text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                      >
                        {actionLoading ? 'Closing...' : 'Close Return Case'}
                      </button>
                    </div>
                  )}

                  {/* Audit Log Timeline */}
                  <div>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      <span>Audit Trail & State History</span>
                    </h3>

                    <div className="space-y-3 border-l-2 border-slate-200 pl-4 ml-2">
                      {selectedReturnDetail.audit_logs?.map((log) => (
                        <div key={log.id} className="relative text-xs">
                          <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-slate-400 border-2 border-white" />
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-900">{log.action}</span>
                            <span className="text-[10px] text-slate-400">
                              {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                            </span>
                          </div>
                          {log.notes && <p className="text-[11px] text-slate-600 mt-0.5">{log.notes}</p>}
                          <p className="text-[10px] text-slate-400 mt-0.5">By {log.actor_name || 'System'}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default SellerReturnsPage;
