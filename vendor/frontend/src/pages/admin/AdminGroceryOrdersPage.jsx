import React, { useState, useEffect } from 'react';
import { 
  ShoppingBag, CheckCircle, Clock, Truck, XCircle, AlertCircle, 
  ChevronRight, RefreshCw, MapPin, Phone, User, Tag, ArrowRight, Check, X
} from 'lucide-react';
import { workforceService } from '../../api/workforceService';

export default function AdminGroceryOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const res = await workforceService.getGroceryOrders(filterStatus === 'ALL' ? null : filterStatus);
      setOrders(res || []);
    } catch (err) {
      console.error('Failed to load orders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [filterStatus]);

  const handleAccept = async (orderId) => {
    try {
      setActionLoading(orderId);
      await workforceService.acceptGroceryOrder(orderId);
      await fetchOrders();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to accept order.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async () => {
    if (!selectedOrder) return;
    try {
      setActionLoading(selectedOrder.id);
      await workforceService.rejectGroceryOrder(selectedOrder.id, rejectReason);
      setRejectModalOpen(false);
      setRejectReason('');
      setSelectedOrder(null);
      await fetchOrders();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to reject order.');
    } finally {
      setActionLoading(null);
    }
  };

  const handleUpdateStatus = async (orderId, nextStatus) => {
    try {
      setActionLoading(orderId);
      await workforceService.updateGroceryOrderStatus(orderId, nextStatus);
      await fetchOrders();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update order status.');
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'CONFIRMED':
      case 'PENDING_PAYMENT':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"><Clock className="w-3 h-3" /> New Order</span>;
      case 'ACCEPTED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200"><Check className="w-3 h-3" /> Accepted</span>;
      case 'PICKING':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200"><RefreshCw className="w-3 h-3 animate-spin" /> Picking</span>;
      case 'PACKED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-200"><ShoppingBag className="w-3 h-3" /> Packed</span>;
      case 'OUT_FOR_DELIVERY':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200"><Truck className="w-3 h-3" /> Out for Delivery</span>;
      case 'DELIVERED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle className="w-3 h-3" /> Delivered</span>;
      case 'CANCELLED':
      case 'VENDOR_REJECTED':
        return <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200"><XCircle className="w-3 h-3" /> Rejected</span>;
      default:
        return <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-800">{status}</span>;
    }
  };

  const tabs = [
    { label: 'All Orders', value: 'ALL' },
    { label: 'New / Confirmed', value: 'CONFIRMED' },
    { label: 'Accepted', value: 'ACCEPTED' },
    { label: 'Preparing', value: 'PICKING' },
    { label: 'Packed', value: 'PACKED' },
    { label: 'Out for Delivery', value: 'OUT_FOR_DELIVERY' },
    { label: 'Delivered', value: 'DELIVERED' },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <ShoppingBag className="w-7 h-7 text-emerald-600" />
            Store Orders Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Accept, prepare, and fulfill fresh produce customer orders received by your store.
          </p>
        </div>
        <button
          onClick={fetchOrders}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Orders
        </button>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto gap-2 border-b border-slate-200 pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setFilterStatus(tab.value)}
            className={`px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition ${
              filterStatus === tab.value
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Orders List */}
      {loading ? (
        <div className="py-20 text-center">
          <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto mb-3" />
          <p className="text-slate-500 font-medium">Loading store orders...</p>
        </div>
      ) : orders.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-12 text-center">
          <ShoppingBag className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-bold text-slate-800">No Orders in this Status</h3>
          <p className="text-sm text-slate-400 mt-1">When customers place orders from your store, they will appear here in real-time.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <div key={order.id} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden hover:border-slate-300 transition">
              {/* Order Card Top */}
              <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-50/50">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <span className="font-extrabold text-slate-900 text-base">#{order.order_number}</span>
                    {getStatusBadge(order.status)}
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                      {order.payment_method}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Placed on {new Date(order.placed_at || order.created_at).toLocaleString()}
                  </p>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Total Amount</span>
                  <span className="text-lg font-black text-slate-900">₹{parseFloat(order.total_amount).toFixed(2)}</span>
                  {order.vendor_coupon_discount > 0 && (
                    <span className="text-xs font-medium text-emerald-600 block">
                      Coupon -₹{parseFloat(order.vendor_coupon_discount).toFixed(2)}
                    </span>
                  )}
                </div>
              </div>

              {/* Order Details Body */}
              <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Customer Details */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Customer & Delivery</h4>
                  <div className="text-sm space-y-1 text-slate-700">
                    <p className="font-semibold flex items-center gap-2">
                      <User className="w-4 h-4 text-slate-400" />
                      {order.customer_name}
                    </p>
                    {order.customer_phone && (
                      <p className="flex items-center gap-2 text-slate-600">
                        <Phone className="w-4 h-4 text-slate-400" />
                        {order.customer_phone}
                      </p>
                    )}
                    <p className="flex items-start gap-2 text-xs text-slate-500">
                      <MapPin className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                      {order.delivery_address || 'Customer Delivery Address'}
                    </p>
                  </div>
                </div>

                {/* Items List */}
                <div className="space-y-2 md:col-span-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Items Snapshot ({order.items?.length || 0})
                  </h4>
                  <div className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
                    {order.items?.map((item) => (
                      <div key={item.id} className="py-2 flex items-center justify-between text-sm">
                        <div>
                          <span className="font-bold text-slate-800">{item.product_name_snapshot}</span>
                          <span className="text-xs text-slate-400 ml-2">
                            {item.quantity}{item.unit_snapshot} @ ₹{parseFloat(item.final_unit_price).toFixed(2)}
                          </span>
                        </div>
                        <span className="font-bold text-slate-900">₹{parseFloat(item.total_price).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="p-4 bg-slate-50 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  {order.delivery?.delivery_otp && order.status === 'OUT_FOR_DELIVERY' && (
                    <div className="px-3 py-1 bg-amber-100 border border-amber-300 rounded-lg text-xs font-bold text-amber-800">
                      Handover OTP: {order.delivery.delivery_otp}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {/* Action transitions */}
                  {(order.status === 'CONFIRMED' || order.status === 'PENDING_PAYMENT') && (
                    <>
                      <button
                        onClick={() => {
                          setSelectedOrder(order);
                          setRejectModalOpen(true);
                        }}
                        disabled={actionLoading === order.id}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-white border border-red-200 text-red-600 hover:bg-red-50 transition"
                      >
                        Reject Order
                      </button>
                      <button
                        onClick={() => handleAccept(order.id)}
                        disabled={actionLoading === order.id}
                        className="px-4 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center gap-1 shadow-sm"
                      >
                        Accept Order <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}

                  {order.status === 'ACCEPTED' && (
                    <button
                      onClick={() => handleUpdateStatus(order.id, 'PICKING')}
                      disabled={actionLoading === order.id}
                      className="px-4 py-1.5 rounded-lg text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition"
                    >
                      Start Picking
                    </button>
                  )}

                  {order.status === 'PICKING' && (
                    <button
                      onClick={() => handleUpdateStatus(order.id, 'PACKED')}
                      disabled={actionLoading === order.id}
                      className="px-4 py-1.5 rounded-lg text-xs font-bold bg-purple-600 text-white hover:bg-purple-700 transition"
                    >
                      Mark Packed & Ready
                    </button>
                  )}

                  {order.status === 'PACKED' && (
                    <button
                      onClick={() => handleUpdateStatus(order.id, 'OUT_FOR_DELIVERY')}
                      disabled={actionLoading === order.id}
                      className="px-4 py-1.5 rounded-lg text-xs font-bold bg-sky-600 text-white hover:bg-sky-700 transition flex items-center gap-1"
                    >
                      <Truck className="w-3.5 h-3.5" /> Dispatch for Delivery
                    </button>
                  )}

                  {order.status === 'OUT_FOR_DELIVERY' && (
                    <button
                      onClick={() => handleUpdateStatus(order.id, 'DELIVERED')}
                      disabled={actionLoading === order.id}
                      className="px-4 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 transition flex items-center gap-1 shadow-sm"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Mark Delivered
                    </button>
                  )}

                  {order.status === 'DELIVERED' && (
                    <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" /> Completed & Credited
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Reject Modal */}
      {rejectModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900">Reject Order #{selectedOrder?.order_number}</h3>
            <p className="text-xs text-slate-500">
              Rejecting this order will immediately release the reserved stock back to your available inventory.
            </p>
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">Reason for Rejection</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., Produce out of stock, shop closing early..."
                rows={3}
                className="w-full border border-slate-200 rounded-xl p-3 text-sm focus:ring-2 focus:ring-emerald-500 outline-none"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setRejectModalOpen(false)}
                className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={actionLoading}
                className="px-4 py-2 bg-red-600 text-white rounded-xl text-xs font-bold hover:bg-red-700 transition"
              >
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
