import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  ShoppingBag,
  Clock,
  Package,
  Truck,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Info,
  Sparkles,
  Search,
  Filter,
  RefreshCw,
  ChevronRight,
  Eye,
  Printer,
  X,
  FileText,
  User,
  Phone,
  MapPin,
  Calendar,
  CheckSquare,
  Square,
  AlertTriangle,
  ArrowUpRight,
  Check,
  Ban,
  Layers,
  Store,
  Loader2,
  Navigation,
  ShieldAlert,
  Barcode,
} from 'lucide-react';
import { CustomerLiveTrackingModal } from '../../components/common/CustomerLiveTrackingModal.jsx';

export function SellerOrdersPage() {
  const { user, token, isPlatformAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter States
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [fulfillmentFilter, setFulfillmentFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Pagination & Counts
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // Metrics
  const [metrics, setMetrics] = useState({
    today_orders_count: 0,
    pending_orders_count: 0,
    in_prep_orders_count: 0,
    completed_orders_count: 0,
    cancelled_orders_count: 0,
  });

  // Selected Order for Detail Drawer & Packing Slip
  const [selectedOrderId, setSelectedOrderId] = useState(null);
  const [selectedOrderDetail, setSelectedOrderDetail] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Packing Slip Modal
  const [packingSlipData, setPackingSlipData] = useState(null);
  const [packingSlipOrderId, setPackingSlipOrderId] = useState(null);
  const [isPackingSlipOpen, setIsPackingSlipOpen] = useState(false);

  // Transition & Action State
  const [actionLoading, setActionLoading] = useState(false);
  const [cancellationModal, setCancellationModal] = useState({ isOpen: false, orderId: null, reason: '' });
  const [adminOverrideModal, setAdminOverrideModal] = useState({ isOpen: false, orderId: null, action: '', reason: '' });
  const [trackingJobId, setTrackingJobId] = useState(null);

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setPage(1);
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
          today_orders_count: data.today_orders_count || 0,
          pending_orders_count: data.pending_orders_count || 0,
          in_prep_orders_count: data.in_prep_orders_count || 0,
          completed_orders_count: data.completed_orders_count || 0,
          cancelled_orders_count: data.cancelled_orders_count || 0,
        });
      }
    } catch (e) {
      console.error('Failed to load order metrics', e);
    }
  }, [token]);

  // Load Orders List
  const loadOrders = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (statusFilter && statusFilter !== 'ALL') {
        params.append('status', statusFilter);
      }
      if (fulfillmentFilter && fulfillmentFilter !== 'ALL') {
        params.append('fulfillment_type', fulfillmentFilter);
      }
      if (debouncedSearch) {
        params.append('search', debouncedSearch);
      }

      const res = await fetch(`/api/workforce/seller-hub/orders/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error('Failed to fetch orders from server.');
      }

      const data = await res.json();
      setOrders(data.results || []);
      setTotalCount(data.count || 0);
    } catch (err) {
      console.error('Error fetching orders:', err);
      setError(err.message || 'Error loading orders.');
    } finally {
      setLoading(false);
    }
  }, [token, page, pageSize, statusFilter, fulfillmentFilter, debouncedSearch]);

  useEffect(() => {
    loadOrders();
    loadMetrics();
  }, [loadOrders, loadMetrics]);

  // Open Order Detail Drawer
  const openOrderDetail = async (orderId) => {
    setSelectedOrderId(orderId);
    setIsDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedOrderDetail(data);
      }
    } catch (err) {
      console.error('Error loading order detail:', err);
    } finally {
      setDrawerLoading(false);
    }
  };

  // Open Packing Slip (quick on-screen preview)
  const openPackingSlip = async (orderId) => {
    try {
      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/packing-slip/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setPackingSlipData(data);
        setPackingSlipOrderId(orderId);
        setIsPackingSlipOpen(true);
      }
    } catch (err) {
      console.error('Error loading packing slip:', err);
    }
  };

  // Download / open the real shipping-label PDF (4x6, scannable barcode) --
  // this is what actually gets printed and taped to the package. Fetched as a
  // blob (rather than a plain window.open navigation) so the Authorization
  // header reaches the API.
  const [labelDownloadingId, setLabelDownloadingId] = useState(null);
  const downloadPackingSlipPdf = async (orderId) => {
    setLabelDownloadingId(orderId);
    try {
      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/packing-slip/pdf/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        window.open(blobUrl, '_blank');
        // Release the object URL once the new tab has had a chance to load it.
        setTimeout(() => URL.revokeObjectURL(blobUrl), 30000);
      } else {
        console.error('Error generating shipping label PDF:', res.status);
      }
    } catch (err) {
      console.error('Error generating shipping label PDF:', err);
    } finally {
      setLabelDownloadingId(null);
    }
  };

  // Execute State Transition Action
  const handleTransition = async (orderId, action, notes = '', cancellation_reason = '') => {
    if (!orderId) return;
    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/transition/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action,
          notes,
          cancellation_reason,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Failed to update order state.');
        return;
      }

      // Refresh list & metrics
      loadOrders();
      loadMetrics();

      if (selectedOrderId === orderId) {
        setSelectedOrderDetail(data.order);
      }

      if (cancellationModal.isOpen) {
        setCancellationModal({ isOpen: false, orderId: null, reason: '' });
      }
    } catch (err) {
      console.error('Error executing transition:', err);
      alert('Network error transitioning order.');
    } finally {
      setActionLoading(false);
    }
  };

  // Execute Platform Admin Manual Override
  const handleAdminOverride = async () => {
    const { orderId, action, reason } = adminOverrideModal;
    if (!orderId || !action) return;
    if (!reason.trim()) {
      alert('A mandatory justification reason is required for platform admin override.');
      return;
    }
    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/admin-override/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          action,
          reason: reason.trim(),
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.error || 'Failed to execute admin override.');
        return;
      }

      loadOrders();
      loadMetrics();
      if (selectedOrderId === orderId) {
        setSelectedOrderDetail(data.order);
      }
      setAdminOverrideModal({ isOpen: false, orderId: null, action: '', reason: '' });
    } catch (err) {
      console.error('Error executing admin override:', err);
      alert('Network error executing admin override.');
    } finally {
      setActionLoading(false);
    }
  };

  // Toggle Item Picking / Packing
  const handleItemPickToggle = async (orderId, itemId, field, value, fulfilledQty) => {
    try {
      const payload = { item_id: itemId };
      if (field === 'is_picked') payload.is_picked = value;
      if (field === 'is_packed') payload.is_packed = value;
      if (fulfilledQty !== undefined) payload.fulfilled_quantity = fulfilledQty;

      const res = await fetch(`/api/workforce/seller-hub/orders/${orderId}/item-pick/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const data = await res.json();
        // Update local order detail item
        setSelectedOrderDetail((prev) => {
          if (!prev) return prev;
          const updatedItems = prev.items.map((it) => (it.id === itemId ? { ...it, ...data.item } : it));
          return { ...prev, items: updatedItems };
        });
      }
    } catch (err) {
      console.error('Error toggling item pick:', err);
    }
  };

  // Helper: Status Badge Styles
  const renderStatusBadge = (status) => {
    switch (status) {
      case 'NEW':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3" />
            <span>New Order</span>
          </span>
        );
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            <Check className="w-3 h-3" />
            <span>Accepted</span>
          </span>
        );
      case 'PICKING':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Package className="w-3 h-3" />
            <span>Picking</span>
          </span>
        );
      case 'PACKED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
            <CheckSquare className="w-3 h-3" />
            <span>Packed</span>
          </span>
        );
      case 'READY_FOR_PICKUP':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-teal-50 text-teal-700 border border-teal-200">
            <Truck className="w-3 h-3" />
            <span>Ready for Pickup</span>
          </span>
        );
      case 'ASSIGNED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Truck className="w-3 h-3" />
            <span>Rider Assigned</span>
          </span>
        );
      case 'HANDED_OVER':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-purple-50 text-purple-700 border border-purple-200">
            <Truck className="w-3 h-3" />
            <span>Out for Delivery</span>
          </span>
        );
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3" />
            <span>Delivered</span>
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-rose-50 text-rose-700 border border-rose-200">
            <Ban className="w-3 h-3" />
            <span>Cancelled</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
              <ShoppingBag className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Seller Hub Orders</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200 px-2 py-0.5 rounded-full">
                  Real Fulfilment Engine
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Manage incoming orders, item picking, packing, delivery handoffs, and packing slips
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => {
                loadOrders();
                loadMetrics();
              }}
              disabled={loading}
              className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors"
              title="Refresh Orders"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <Link
              to="/workforce/seller/dashboard"
              className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Seller Home
            </Link>
            <Link
              to="/workforce/seller-hub/inventory"
              className="px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-xs"
            >
              Inventory Balance
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Top Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Today's Orders</span>
                <Clock className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{metrics.today_orders_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Incoming queue</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Action Required (New)</span>
                <Package className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold text-amber-600 font-mono mt-2">{metrics.pending_orders_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Awaiting acceptance</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">In Preparation</span>
                <Truck className="w-4 h-4 text-indigo-500" />
              </div>
              <p className="text-2xl font-extrabold text-indigo-600 font-mono mt-2">{metrics.in_prep_orders_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Picking / Packed / Ready</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Fulfilled & Completed</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-emerald-600 font-mono mt-2">{metrics.completed_orders_count}</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Handed over or delivered</p>
            </div>
          </div>

          {/* Filter Tabs and Search Bar */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs space-y-4">
            {/* Status Tabs */}
            <div className="flex flex-wrap items-center gap-1.5 border-b border-slate-100 pb-3">
              {[
                { id: 'ALL', label: 'All Orders' },
                { id: 'NEW', label: 'New / Action Required' },
                { id: 'IN_PREPARATION', label: 'In Preparation' },
                { id: 'READY_FOR_PICKUP', label: 'Ready for Pickup' },
                { id: 'COMPLETED', label: 'Completed' },
                { id: 'CANCELLED', label: 'Cancelled' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setStatusFilter(tab.id);
                    setPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    statusFilter === tab.id
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-slate-50 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Secondary Search & Fulfillment Filters */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by Order #, Customer Name, SKU..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white transition-all"
                />
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select
                  value={fulfillmentFilter}
                  onChange={(e) => {
                    setFulfillmentFilter(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 focus:outline-none focus:border-blue-500"
                >
                  <option value="ALL">All Fulfilment Types</option>
                  <option value="DELIVERY">Delivery</option>
                  <option value="STORE_PICKUP">Store Pickup</option>
                </select>
              </div>
            </div>
          </div>

          {/* Orders Table Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            {loading ? (
              <div className="p-16 flex flex-col items-center justify-center text-center">
                <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
                <p className="text-xs font-semibold text-slate-500">Loading orders from database...</p>
              </div>
            ) : error ? (
              <div className="p-12 text-center">
                <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
                <h3 className="text-sm font-bold text-slate-800">Error Loading Orders</h3>
                <p className="text-xs text-slate-500 mt-1">{error}</p>
                <button
                  onClick={loadOrders}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white text-xs font-semibold rounded-lg"
                >
                  Retry
                </button>
              </div>
            ) : orders.length === 0 ? (
              /* Empty State */
              <div className="p-16 flex flex-col items-center justify-center text-center">
                <div className="w-16 h-16 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-4 shadow-xs">
                  <ShoppingBag className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-base font-bold text-slate-900">No Orders in Queue</h3>
                <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed">
                  Real marketplace customer bookings will arrive here automatically when customers check out from your approved product catalog.
                </p>

                <div className="mt-6 flex items-center gap-3">
                  <Link
                    to="/workforce/seller-hub/inventory"
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-xs transition-colors"
                  >
                    <Package className="w-4 h-4" />
                    <span>Check Inventory Stock</span>
                  </Link>
                  <Link
                    to="/workforce/seller-hub/products"
                    className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                  >
                    <Layers className="w-4 h-4" />
                    <span>Manage Catalog</span>
                  </Link>
                </div>
              </div>
            ) : (
              /* Orders Table */
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="py-3.5 px-5">Order Reference</th>
                      <th className="py-3.5 px-4">Customer & Slot</th>
                      <th className="py-3.5 px-4">Items Summary</th>
                      <th className="py-3.5 px-4">Total Amount</th>
                      <th className="py-3.5 px-4">Fulfilment Status</th>
                      <th className="py-3.5 px-5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {orders.map((ord) => (
                      <tr key={ord.id} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-4 px-5 align-top">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-900 font-mono text-sm">{ord.order_number}</span>
                            <span className="text-[10px] font-mono text-slate-400 mt-0.5">
                              Src: {ord.source_order_id}
                            </span>
                            <span className="text-[10px] text-slate-400 mt-1">
                              {new Date(ord.created_at).toLocaleDateString('en-GB', {
                                day: '2-digit',
                                month: 'short',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          </div>
                        </td>

                        <td className="py-4 px-4 align-top">
                          <div className="flex flex-col max-w-[200px]">
                            <span className="font-semibold text-slate-800">{ord.customer_name}</span>
                            {ord.customer_phone && (
                              <span className="text-[11px] text-slate-500">{ord.customer_phone}</span>
                            )}
                            {ord.delivery_slot && (
                              <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded mt-1 inline-block w-fit">
                                Slot: {ord.delivery_slot}
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="py-4 px-4 align-top">
                          <div className="flex flex-col max-w-[260px]">
                            <span className="font-medium text-slate-700">{ord.items_count} item(s)</span>
                            <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">
                              {ord.items_summary}
                            </p>
                          </div>
                        </td>

                        <td className="py-4 px-4 align-top">
                          <div className="flex flex-col">
                            <span className="font-extrabold text-slate-900 font-mono text-sm">
                              ₹ {parseFloat(ord.total_amount || 0).toFixed(2)}
                            </span>
                            <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 w-fit mt-1">
                              {ord.payment_method} ({ord.payment_status})
                            </span>
                          </div>
                        </td>

                        <td className="py-4 px-4 align-top">
                          <div className="flex flex-col gap-1">
                            {renderStatusBadge(ord.status)}
                            <span className="text-[10px] text-slate-400 font-medium">
                              Type: {ord.fulfillment_type === 'STORE_PICKUP' ? 'Store Pickup' : 'Delivery'}
                            </span>
                          </div>
                        </td>

                        <td className="py-4 px-5 align-top text-right">
                          <div className="flex items-center justify-end gap-1.5 flex-wrap">
                            {/* State Transition Quick Actions */}
                            {ord.status === 'NEW' && (
                              <>
                                <button
                                  onClick={() => handleTransition(ord.id, 'accept')}
                                  disabled={actionLoading}
                                  className="px-2.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
                                >
                                  Accept
                                </button>
                                <button
                                  onClick={() => setCancellationModal({ isOpen: true, orderId: ord.id, reason: '' })}
                                  className="px-2 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-lg text-xs font-semibold transition-colors"
                                >
                                  Cancel
                                </button>
                              </>
                            )}

                            {ord.status === 'ACCEPTED' && (
                              <button
                                onClick={() => handleTransition(ord.id, 'start_picking')}
                                disabled={actionLoading}
                                className="px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
                              >
                                Start Picking
                              </button>
                            )}

                            {ord.status === 'PICKING' && (
                              <button
                                onClick={() => handleTransition(ord.id, 'mark_packed')}
                                disabled={actionLoading}
                                className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
                              >
                                Mark Packed
                              </button>
                            )}

                            {ord.status === 'PACKED' && (
                              <button
                                onClick={() => handleTransition(ord.id, 'mark_ready')}
                                disabled={actionLoading}
                                className="px-2.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs flex items-center gap-1"
                              >
                                <Truck className="w-3.5 h-3.5" />
                                <span>Dispatch Rider</span>
                              </button>
                            )}

                            {['READY_FOR_PICKUP', 'ASSIGNED'].includes(ord.status) && (
                              <div className="flex items-center gap-1.5">
                                {ord.handling_technician_name ? (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                                    <Truck className="w-3 h-3" />
                                    <span>{ord.handling_technician_name}</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded bg-amber-50 text-amber-700 animate-pulse border border-amber-200">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    <span>Assigning Rider...</span>
                                  </span>
                                )}
                                {ord.dispatch_job_id && (
                                  <button
                                    onClick={() => setTrackingJobId(ord.dispatch_job_id)}
                                    className="p-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors border border-indigo-200"
                                    title="Live Track Delivery Rider"
                                  >
                                    <Navigation className="w-4 h-4" />
                                  </button>
                                )}
                              </div>
                            )}

                            {ord.status === 'HANDED_OVER' && ord.dispatch_job_id && (
                              <button
                                onClick={() => setTrackingJobId(ord.dispatch_job_id)}
                                className="px-2.5 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-lg text-xs font-semibold transition-colors border border-purple-200 flex items-center gap-1"
                                title="Live Track Delivery Partner"
                              >
                                <Navigation className="w-3.5 h-3.5" />
                                <span>Track Rider</span>
                              </button>
                            )}

                            {/* View Details Drawer */}
                            <button
                              onClick={() => openOrderDetail(ord.id)}
                              className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                              title="Order Details & Picking List"
                            >
                              <Eye className="w-4 h-4" />
                            </button>

                            {/* Packing Slip (quick preview) */}
                            <button
                              onClick={() => openPackingSlip(ord.id)}
                              className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors"
                              title="Preview Packing Slip"
                            >
                              <Printer className="w-4 h-4" />
                            </button>

                            {/* Shipping Label PDF (barcode, primary print target) */}
                            <button
                              onClick={() => downloadPackingSlipPdf(ord.id)}
                              disabled={labelDownloadingId === ord.id}
                              className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors disabled:opacity-50"
                              title="Download Shipping Label (PDF, scannable barcode)"
                            >
                              {labelDownloadingId === ord.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Barcode className="w-4 h-4" />
                              )}
                            </button>
                          </div>
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

      {/* ── DRAWER: ORDER DETAIL & FULFILMENT CHECKLIST ── */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-3">
                <span className="p-2 bg-blue-100 text-blue-700 rounded-lg">
                  <ShoppingBag className="w-5 h-5" />
                </span>
                <div>
                  <h2 className="text-base font-bold text-slate-900 font-mono">
                    {selectedOrderDetail?.order_number || 'Loading Order...'}
                  </h2>
                  <p className="text-[11px] text-slate-500">
                    Marketplace Reference: {selectedOrderDetail?.source_order_id}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {selectedOrderDetail && renderStatusBadge(selectedOrderDetail.status)}
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Drawer Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {drawerLoading ? (
                <div className="py-20 flex flex-col items-center justify-center text-center">
                  <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mb-3" />
                  <p className="text-xs text-slate-500">Fetching order details & item checklist...</p>
                </div>
              ) : selectedOrderDetail ? (
                <>
                  {/* Customer & Fulfilment Snapshot */}
                  <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Customer & Delivery
                      </span>
                      <p className="font-bold text-slate-800">{selectedOrderDetail.customer_name}</p>
                      <p className="text-slate-600">{selectedOrderDetail.customer_phone}</p>
                      <p className="text-slate-500 mt-1 line-clamp-2">{selectedOrderDetail.delivery_address}</p>
                    </div>
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Fulfilment Info
                      </span>
                      <p className="text-slate-700 font-semibold">
                        Type: {selectedOrderDetail.fulfillment_type === 'STORE_PICKUP' ? 'Store Pickup' : 'Delivery'}
                      </p>
                      {selectedOrderDetail.delivery_slot && (
                        <p className="text-slate-600 mt-0.5">Slot: {selectedOrderDetail.delivery_slot}</p>
                      )}
                      <p className="text-slate-600 mt-0.5 font-mono font-bold">
                        Total: ₹ {parseFloat(selectedOrderDetail.total_amount || 0).toFixed(2)} ({selectedOrderDetail.payment_status})
                      </p>
                    </div>
                  </div>

                  {/* Item Picking & Packing Checklist */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                        <CheckSquare className="w-4 h-4 text-blue-600" />
                        <span>Item Picking Checklist ({selectedOrderDetail.items?.length || 0})</span>
                      </h3>
                      <span className="text-[11px] text-slate-400">Click checkboxes to update picking status</span>
                    </div>

                    <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
                      {selectedOrderDetail.items?.map((item) => (
                        <div key={item.id} className="p-3.5 bg-white hover:bg-slate-50/60 transition-colors flex items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <button
                              onClick={() => handleItemPickToggle(selectedOrderDetail.id, item.id, 'is_picked', !item.is_picked, item.ordered_quantity)}
                              className={`p-1.5 rounded-lg border transition-colors ${
                                item.is_picked
                                  ? 'bg-emerald-50 border-emerald-300 text-emerald-600'
                                  : 'bg-slate-50 border-slate-300 text-slate-400 hover:border-blue-400'
                              }`}
                              title="Mark as Picked"
                            >
                              {item.is_picked ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
                            </button>

                            <div>
                              <p className="font-bold text-xs text-slate-800">{item.product_title}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                                  {item.sku}
                                </span>
                                {item.unit && (
                                  <span className="text-[10px] text-slate-400">
                                    {item.pack_size || item.unit}
                                  </span>
                                )}
                                <span className="text-[10px] text-slate-400">
                                  Avail: {item.available_stock} in stock
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="text-right">
                            <span className="font-extrabold text-sm text-slate-900 font-mono">
                              x {item.ordered_quantity}
                            </span>
                            <p className="text-[10px] text-slate-400 font-mono">
                              ₹ {parseFloat(item.line_total || 0).toFixed(2)}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Rider Assignment & Pickup OTP Banner */}
                  {['READY_FOR_PICKUP', 'ASSIGNED', 'HANDED_OVER'].includes(selectedOrderDetail.status) && (
                    <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="p-2 bg-indigo-100 rounded-lg text-indigo-700">
                            <Truck className="w-4 h-4" />
                          </div>
                          <div>
                            <div className="text-xs font-bold text-slate-900">
                              {selectedOrderDetail.handling_technician_name ? `Assigned Rider: ${selectedOrderDetail.handling_technician_name}` : '2-Wheeler Rider Dispatch'}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              {selectedOrderDetail.handling_technician_phone ? `Contact: ${selectedOrderDetail.handling_technician_phone}` : 'Dispatching to nearest available 2-wheeler rider'}
                            </div>
                          </div>
                        </div>
                        {selectedOrderDetail.dispatch_job_id && (
                          <button
                            onClick={() => setTrackingJobId(selectedOrderDetail.dispatch_job_id)}
                            className="px-2.5 py-1 bg-white hover:bg-slate-100 text-indigo-700 border border-indigo-200 rounded-lg text-xs font-semibold flex items-center gap-1 shadow-2xs"
                          >
                            <Navigation className="w-3 h-3" />
                            <span>Track</span>
                          </button>
                        )}
                      </div>
                      {selectedOrderDetail.pickup_otp && (
                        <div className="p-2.5 bg-amber-50 border border-amber-200 rounded-lg flex items-center justify-between">
                          <div className="text-xs text-amber-900">
                            <span className="font-bold">Pickup Verification OTP: </span>
                            <span className="font-mono text-sm font-black text-amber-950 bg-amber-200/80 px-2 py-0.5 rounded ml-1 tracking-widest">{selectedOrderDetail.pickup_otp}</span>
                          </div>
                          <span className="text-[10px] text-amber-700 font-medium">Share with Rider at Handover</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Workflow Action Buttons */}
                  <div className="p-4 bg-blue-50/50 border border-blue-200 rounded-xl space-y-3">
                    <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">
                      Advance Fulfilment State
                    </span>
                    <div className="flex flex-wrap items-center gap-2">
                      {selectedOrderDetail.status === 'NEW' && (
                        <button
                          onClick={() => handleTransition(selectedOrderDetail.id, 'accept')}
                          disabled={actionLoading}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                        >
                          Accept Order & Reserve Stock
                        </button>
                      )}

                      {selectedOrderDetail.status === 'ACCEPTED' && (
                        <button
                          onClick={() => handleTransition(selectedOrderDetail.id, 'start_picking')}
                          disabled={actionLoading}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                        >
                          Start Picking Items
                        </button>
                      )}

                      {selectedOrderDetail.status === 'PICKING' && (
                        <button
                          onClick={() => handleTransition(selectedOrderDetail.id, 'mark_packed')}
                          disabled={actionLoading}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                        >
                          Mark Items Packed
                        </button>
                      )}

                      {selectedOrderDetail.status === 'PACKED' && (
                        <button
                          onClick={() => handleTransition(selectedOrderDetail.id, 'mark_ready')}
                          disabled={actionLoading}
                          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
                        >
                          <Truck className="w-3.5 h-3.5" />
                          <span>Dispatch 2-Wheeler Rider</span>
                        </button>
                      )}

                      {['READY_FOR_PICKUP', 'ASSIGNED', 'HANDED_OVER'].includes(selectedOrderDetail.status) && selectedOrderDetail.dispatch_job_id && (
                        <button
                          onClick={() => setTrackingJobId(selectedOrderDetail.dispatch_job_id)}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold shadow-xs transition-colors flex items-center gap-1.5"
                        >
                          <Navigation className="w-3.5 h-3.5" />
                          <span>Live Track Rider</span>
                        </button>
                      )}

                      {/* Cancel Button */}
                      {!['DELIVERED', 'CANCELLED'].includes(selectedOrderDetail.status) && (
                        <button
                          onClick={() => setCancellationModal({ isOpen: true, orderId: selectedOrderDetail.id, reason: '' })}
                          className="px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-lg text-xs font-semibold transition-colors"
                        >
                          Cancel Order
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Platform Admin Manual Override Controls (Superusers / Platform Admins Only) */}
                  {isSuperAdmin && !['DELIVERED', 'CANCELLED'].includes(selectedOrderDetail.status) && (
                    <div className="p-4 bg-amber-50/70 border border-amber-300 rounded-xl space-y-2.5">
                      <div className="flex items-center gap-2 text-amber-900">
                        <ShieldAlert className="w-4 h-4 text-amber-700" />
                        <span className="text-xs font-bold uppercase tracking-wider">
                          Platform Admin Manual Override
                        </span>
                      </div>
                      <p className="text-[11px] text-amber-800">
                        Emergency bypass for stuck orders (rider device died, OTP delivery failure, unreachable customer). Reason is required and logged in immutable audit history.
                      </p>
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {['READY_FOR_PICKUP', 'ASSIGNED'].includes(selectedOrderDetail.status) && (
                          <button
                            onClick={() => setAdminOverrideModal({
                              isOpen: true,
                              orderId: selectedOrderDetail.id,
                              action: 'admin_override_handover',
                              reason: '',
                            })}
                            disabled={actionLoading}
                            className="px-3.5 py-1.5 bg-amber-700 hover:bg-amber-800 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                          >
                            Override: Force Handover
                          </button>
                        )}
                        {['READY_FOR_PICKUP', 'ASSIGNED', 'HANDED_OVER'].includes(selectedOrderDetail.status) && (
                          <button
                            onClick={() => setAdminOverrideModal({
                              isOpen: true,
                              orderId: selectedOrderDetail.id,
                              action: 'admin_override_deliver',
                              reason: '',
                            })}
                            disabled={actionLoading}
                            className="px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                          >
                            Override: Force Deliver
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Immutable Audit Trail Timeline */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                      Fulfilment Audit History
                    </h3>

                    <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white">
                      {selectedOrderDetail.audit_logs?.length === 0 ? (
                        <p className="p-4 text-xs text-slate-400 text-center">No history logs recorded yet.</p>
                      ) : (
                        selectedOrderDetail.audit_logs?.map((log) => (
                          <div key={log.id} className="p-3 text-xs flex items-start justify-between gap-3">
                            <div>
                              <span className="font-bold text-slate-800">{log.action}</span>
                              <p className="text-[11px] text-slate-500 mt-0.5">
                                Actor: {log.actor_name} | From: {log.from_status || 'NEW'} → To: {log.to_status}
                              </p>
                              {log.notes && (
                                <p className="text-[11px] text-slate-600 mt-1 italic">Note: "{log.notes}"</p>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-400 shrink-0">
                              {new Date(log.created_at).toLocaleString('en-GB')}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              ) : null}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => selectedOrderDetail && downloadPackingSlipPdf(selectedOrderDetail.id)}
                  disabled={labelDownloadingId === selectedOrderDetail?.id}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg transition-colors shadow-xs disabled:opacity-50"
                >
                  {labelDownloadingId === selectedOrderDetail?.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Barcode className="w-4 h-4" />
                  )}
                  <span>Shipping Label (PDF)</span>
                </button>
                <button
                  onClick={() => selectedOrderDetail && openPackingSlip(selectedOrderDetail.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
                  title="Quick on-screen preview"
                >
                  <Printer className="w-4 h-4" />
                  <span>Preview</span>
                </button>
              </div>
              <button
                onClick={() => setIsDrawerOpen(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg transition-colors"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: CANCELLATION REASON ── */}
      {cancellationModal.isOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3 text-rose-600">
              <span className="p-2 bg-rose-50 rounded-xl border border-rose-200">
                <AlertTriangle className="w-5 h-5" />
              </span>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">Cancel Fulfilment Order</h3>
                <p className="text-[11px] text-slate-500">Reserved stock will be automatically released back to available balance.</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Cancellation Reason (Mandatory)
              </label>
              <textarea
                rows={3}
                placeholder="E.g. Item damaged in warehouse / Out of stock / Customer requested cancellation..."
                value={cancellationModal.reason}
                onChange={(e) => setCancellationModal((prev) => ({ ...prev, reason: e.target.value }))}
                className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setCancellationModal({ isOpen: false, orderId: null, reason: '' })}
                className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Back
              </button>
              <button
                onClick={() => handleTransition(cancellationModal.orderId, 'cancel', '', cancellationModal.reason)}
                disabled={!cancellationModal.reason.trim() || actionLoading}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-xs transition-colors"
              >
                Confirm Cancellation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL: PRINTABLE PACKING SLIP ── */}
      {isPackingSlipOpen && packingSlipData && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-8 shadow-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <h2 className="text-lg font-black text-slate-900 tracking-tight">PACKING SLIP</h2>
                <p className="text-xs font-mono text-slate-500 font-bold">Order #{packingSlipData.order_number}</p>
                <p className="text-[10px] text-slate-400 mt-0.5">On-screen preview &mdash; use "Shipping Label (PDF)" to print the actual barcode label</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => packingSlipOrderId && downloadPackingSlipPdf(packingSlipOrderId)}
                  disabled={labelDownloadingId === packingSlipOrderId}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg flex items-center gap-1.5 shadow-xs disabled:opacity-50"
                >
                  {labelDownloadingId === packingSlipOrderId ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Barcode className="w-3.5 h-3.5" />
                  )}
                  <span>Shipping Label (PDF)</span>
                </button>
                <button
                  onClick={() => window.print()}
                  className="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-bold rounded-lg flex items-center gap-1.5"
                  title="Print this on-screen preview"
                >
                  <Printer className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setIsPackingSlipOpen(false)}
                  className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Merchant & Customer Header */}
            <div className="grid grid-cols-2 gap-6 text-xs">
              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Merchant / Store
                </span>
                <p className="font-bold text-slate-900">{packingSlipData.seller?.name}</p>
                <p className="text-slate-600">{packingSlipData.seller?.address || 'Verified Merchant Store'}</p>
                {packingSlipData.seller?.phone && <p className="text-slate-600">Tel: {packingSlipData.seller?.phone}</p>}
              </div>

              <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-200">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Ship / Handover To
                </span>
                <p className="font-bold text-slate-900">{packingSlipData.customer?.name}</p>
                <p className="text-slate-600">{packingSlipData.customer?.delivery_address}</p>
                {packingSlipData.customer?.phone && <p className="text-slate-600">Tel: {packingSlipData.customer?.phone}</p>}
              </div>
            </div>

            {/* Item Table */}
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-100 border-b border-slate-200 text-[10px] font-bold text-slate-600 uppercase">
                  <th className="py-2 px-3">Check</th>
                  <th className="py-2 px-3">Product / SKU</th>
                  <th className="py-2 px-3 text-center">Unit / Pack</th>
                  <th className="py-2 px-3 text-right">Quantity</th>
                  <th className="py-2 px-3 text-right">Total Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {packingSlipData.items?.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50">
                    <td className="py-2.5 px-3">
                      <div className="w-4 h-4 border border-slate-400 rounded-sm"></div>
                    </td>
                    <td className="py-2.5 px-3">
                      <p className="font-bold text-slate-900">{item.title}</p>
                      <span className="text-[10px] font-mono text-slate-400">SKU: {item.sku}</span>
                    </td>
                    <td className="py-2.5 px-3 text-center text-slate-600">
                      {item.pack_size || item.unit || '–'}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">
                      {item.ordered_qty}
                    </td>
                    <td className="py-2.5 px-3 text-right font-mono text-slate-700">
                      ₹ {parseFloat(item.line_total || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Total Footer */}
            <div className="border-t border-slate-200 pt-3 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Payment: {packingSlipData.payment_method} ({packingSlipData.payment_status})
              </span>
              <div className="text-right">
                <span className="text-slate-400 text-[10px] uppercase font-bold block">Grand Total</span>
                <span className="text-base font-black text-slate-900 font-mono">
                  ₹ {parseFloat(packingSlipData.total_amount || 0).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Platform Admin Override Modal */}
      {adminOverrideModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-amber-200 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-2.5 text-amber-900 border-b border-amber-100 pb-3">
              <span className="p-2 bg-amber-100 text-amber-800 rounded-xl">
                <ShieldAlert className="w-5 h-5" />
              </span>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  {adminOverrideModal.action === 'admin_override_handover' ? 'Admin Override Handover' : 'Admin Override Delivery'}
                </h3>
                <p className="text-[11px] text-slate-500">Bypass OTP verification for order #{selectedOrderDetail?.order_number}</p>
              </div>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 space-y-1">
              <p className="font-semibold">Important Notice:</p>
              <p className="text-[11px] text-amber-800">
                This action forcefully advances the order status without requiring rider OTP entry. Your username, timestamp, and mandatory justification reason will be recorded in the immutable audit trail.
              </p>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Justification Reason <span className="text-rose-500">*</span>
              </label>
              <textarea
                value={adminOverrideModal.reason}
                onChange={(e) => setAdminOverrideModal(prev => ({ ...prev, reason: e.target.value }))}
                placeholder="e.g. Rider device battery failed at store; physical package handover confirmed by store manager via phone."
                rows={3}
                className="w-full text-xs p-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-amber-500 focus:outline-hidden"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setAdminOverrideModal({ isOpen: false, orderId: null, action: '', reason: '' })}
                disabled={actionLoading}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAdminOverride}
                disabled={actionLoading || !adminOverrideModal.reason.trim()}
                className="px-4 py-2 text-xs font-bold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
              >
                {actionLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm Override</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Customer / Rider Live Tracking Modal */}
      {trackingJobId && (
        <CustomerLiveTrackingModal
          jobId={trackingJobId}
          isOpen={Boolean(trackingJobId)}
          onClose={() => setTrackingJobId(null)}
          viewRole="admin"
        />
      )}
    </div>
  );
}

export default SellerOrdersPage;
