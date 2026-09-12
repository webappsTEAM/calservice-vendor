/**
 * AdminPromotionsPage.jsx
 * Management for Deals, Flash Sales, and Store-Scoped Coupons.
 */
import React, { useEffect, useState } from 'react';
import {
  apiGetVendorDeals,
  apiCreateVendorDeal,
  apiDeleteVendorDeal,
  apiGetVendorCoupons,
  apiCreateVendorCoupon,
  apiDeleteVendorCoupon,
  apiGetInventoryItems,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import {
  Tag,
  Zap,
  Ticket,
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  X,
  Percent,
  Calendar,
  Sparkles,
} from 'lucide-react';

export default function AdminPromotionsPage() {
  const [tab, setTab] = useState('deals'); // 'deals' | 'coupons'
  const [deals, setDeals] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState({ type: '', text: '' });

  // Modals
  const [showDealModal, setShowDealModal] = useState(false);
  const [showCouponModal, setShowCouponModal] = useState(false);

  // New Deal Form State
  const [dealItem, setDealItem] = useState('');
  const [dealType, setDealType] = useState('strike_through');
  const [dealPrice, setDealPrice] = useState('');
  const [dealOrigPrice, setDealOrigPrice] = useState('');
  const [dealBadge, setDealBadge] = useState('');

  // New Coupon Form State
  const [couponCode, setCouponCode] = useState('');
  const [couponDesc, setCouponDesc] = useState('');
  const [discountType, setDiscountType] = useState('percent');
  const [discountVal, setDiscountVal] = useState('');
  const [minOrder, setMinOrder] = useState('0.00');
  const [maxDiscount, setMaxDiscount] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dealsRes, couponsRes, itemsRes] = await Promise.all([
        apiGetVendorDeals().catch(() => []),
        apiGetVendorCoupons().catch(() => []),
        apiGetInventoryItems().catch(() => []),
      ]);
      setDeals(Array.isArray(dealsRes) ? dealsRes : []);
      setCoupons(Array.isArray(couponsRes) ? couponsRes : []);
      setInventory(Array.isArray(itemsRes) ? itemsRes : []);
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to load promotions.' });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDeal = async (e) => {
    e.preventDefault();
    if (!dealItem || !dealPrice) return;
    try {
      await apiCreateVendorDeal({
        inventory_item_id: dealItem,
        deal_type: dealType,
        original_price: dealOrigPrice,
        deal_price: dealPrice,
        badge_text: dealBadge,
      });
      setShowDealModal(false);
      setDealItem('');
      setDealPrice('');
      setDealOrigPrice('');
      setDealBadge('');
      setMsg({ type: 'success', text: 'Deal created and activated in store!' });
      loadData();
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to create deal.' });
    }
  };

  const handleDeleteDeal = async (id) => {
    if (!confirm('Are you sure you want to end this deal?')) return;
    try {
      await apiDeleteVendorDeal(id);
      setMsg({ type: 'success', text: 'Deal removed.' });
      loadData();
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to delete deal.' });
    }
  };

  const handleCreateCoupon = async (e) => {
    e.preventDefault();
    if (!couponCode || !discountVal) return;
    try {
      await apiCreateVendorCoupon({
        code: couponCode,
        description: couponDesc,
        discount_type: discountType,
        discount_value: discountVal,
        min_order_amount: minOrder,
        max_discount_amount: maxDiscount || null,
      });
      setShowCouponModal(false);
      setCouponCode('');
      setCouponDesc('');
      setDiscountVal('');
      setMinOrder('0.00');
      setMaxDiscount('');
      setMsg({ type: 'success', text: 'Store coupon created successfully!' });
      loadData();
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to create coupon.' });
    }
  };

  const handleDeleteCoupon = async (id) => {
    if (!confirm('Are you sure you want to delete this coupon?')) return;
    try {
      await apiDeleteVendorCoupon(id);
      setMsg({ type: 'success', text: 'Coupon deleted.' });
      loadData();
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to delete coupon.' });
    }
  };

  return (
    <AppShell activeNav="/workforce/admin/promotions">
      <div className="max-w-6xl mx-auto space-y-6 pb-16">
        <PageHeader
          title="Deals, Flash Sales & Coupons"
          subtitle="Drive customer conversion with strike-through discounts, time-limited flash deals, and store vouchers."
          badge="Promotions"
          icon={Tag}
        />

        {msg.text && (
          <div
            className={`p-4 rounded-xl flex items-center gap-3 text-sm font-medium border ${
              msg.type === 'error'
                ? 'bg-rose-50 text-rose-700 border-rose-200'
                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
            }`}
          >
            {msg.type === 'error' ? <AlertCircle className="w-5 h-5 flex-shrink-0" /> : <CheckCircle2 className="w-5 h-5 flex-shrink-0" />}
            <span>{msg.text}</span>
          </div>
        )}

        {/* Tab Navigation & Action Bar */}
        <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 bg-slate-100 p-1 rounded-xl">
            <button
              onClick={() => setTab('deals')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                tab === 'deals' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Zap className="w-4 h-4" />
              Product Deals & Flash Sales ({deals.length})
            </button>
            <button
              onClick={() => setTab('coupons')}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-2 ${
                tab === 'coupons' ? 'bg-white text-indigo-600 shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Ticket className="w-4 h-4" />
              Store Coupons ({coupons.length})
            </button>
          </div>

          <div>
            {tab === 'deals' ? (
              <button
                onClick={() => setShowDealModal(true)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-200 flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Launch New Deal
              </button>
            ) : (
              <button
                onClick={() => setShowCouponModal(true)}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-200 flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Create Store Coupon
              </button>
            )}
          </div>
        </div>

        {/* Content Tabs */}
        {loading ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-slate-200 shadow-sm">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
            <p className="text-slate-500 font-medium text-sm">Loading promotions data...</p>
          </div>
        ) : tab === 'deals' ? (
          /* DEALS VIEW */
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            {deals.length === 0 ? (
              <div className="p-12 text-center">
                <Sparkles className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h4 className="text-slate-700 font-bold text-sm">No Active Deals</h4>
                <p className="text-slate-400 text-xs mt-1">Create a strike-through discount or flash sale on any produce item.</p>
                <button
                  onClick={() => setShowDealModal(true)}
                  className="mt-4 px-4 py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-xl text-xs font-bold inline-flex items-center gap-2"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Create First Deal
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3.5 px-4">Produce Item</th>
                      <th className="py-3.5 px-4">Deal Type</th>
                      <th className="py-3.5 px-4">Regular Price</th>
                      <th className="py-3.5 px-4">Deal Price</th>
                      <th className="py-3.5 px-4">Discount</th>
                      <th className="py-3.5 px-4">Badge</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {deals.map((d) => (
                      <tr key={d.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-3">
                            <img
                              src={d.item_image || '/mockups/vegetables_realistic.png'}
                              alt=""
                              className="w-10 h-10 rounded-xl object-cover bg-slate-100 border border-slate-200"
                            />
                            <div>
                              <p className="font-bold text-slate-800 text-sm">{d.item_name}</p>
                              <span className="text-[10px] text-slate-400">ID #{d.inventory_item_id}</span>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200 uppercase">
                            {d.deal_type.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400 line-through">₹{d.original_price}</td>
                        <td className="py-3 px-4 font-bold text-emerald-600 font-mono text-base">₹{d.deal_price}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                            {d.discount_percent}% OFF
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs font-bold text-slate-600">{d.badge_text || '—'}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleDeleteDeal(d.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                            title="End Deal"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          /* COUPONS VIEW */
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            {coupons.length === 0 ? (
              <div className="p-12 text-center">
                <Ticket className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <h4 className="text-slate-700 font-bold text-sm">No Store Coupons</h4>
                <p className="text-slate-400 text-xs mt-1">Reward returning customers with store-exclusive promo codes.</p>
                <button
                  onClick={() => setShowCouponModal(true)}
                  className="mt-4 px-4 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-xl text-xs font-bold inline-flex items-center gap-2"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Create First Coupon
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3.5 px-4">Coupon Code</th>
                      <th className="py-3.5 px-4">Discount Value</th>
                      <th className="py-3.5 px-4">Min. Order</th>
                      <th className="py-3.5 px-4">Max. Discount</th>
                      <th className="py-3.5 px-4">Redemptions</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {coupons.map((c) => (
                      <tr key={c.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-4">
                          <div>
                            <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded-md text-xs border border-slate-200">
                              {c.code}
                            </span>
                            {c.description && <p className="text-[11px] text-slate-500 mt-1">{c.description}</p>}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-bold text-emerald-600">
                          {c.discount_type === 'percent' ? `${c.discount_value}% OFF` : `₹${c.discount_value} FLAT OFF`}
                        </td>
                        <td className="py-3 px-4 text-xs font-mono text-slate-600">₹{c.min_order_amount}</td>
                        <td className="py-3 px-4 text-xs font-mono text-slate-600">
                          {c.max_discount_amount ? `₹${c.max_discount_amount}` : 'No limit'}
                        </td>
                        <td className="py-3 px-4 text-xs text-slate-600">{c.times_used} used</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                              c.is_active
                                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                : 'bg-slate-100 text-slate-500 border-slate-200'
                            }`}
                          >
                            {c.is_active ? 'ACTIVE' : 'EXPIRED'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => handleDeleteCoupon(c.id)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                            title="Delete Coupon"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Modal: Create Deal */}
        {showDealModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Zap className="w-5 h-5 text-indigo-600" />
                  Launch New Product Deal
                </h3>
                <button onClick={() => setShowDealModal(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateDeal} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Select Produce Item *</label>
                  <select
                    required
                    value={dealItem}
                    onChange={(e) => {
                      setDealItem(e.target.value);
                      const selected = inventory.find((i) => String(i.id) === e.target.value);
                      if (selected) {
                        const basePrice = selected.custom_price || selected.mrp || '0';
                        setDealOrigPrice(basePrice);
                        setDealPrice(String(Math.max(1, Math.round(parseFloat(basePrice) * 0.85))));
                      }
                    }}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">-- Choose an in-stock vegetable --</option>
                    {inventory.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name} ({item.unit}) — Current: ₹{item.custom_price || item.mrp || '0'}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Original Price (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={dealOrigPrice}
                      onChange={(e) => setDealOrigPrice(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Deal Price (₹) *</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={dealPrice}
                      onChange={(e) => setDealPrice(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 font-bold text-emerald-600"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Badge Callout Text</label>
                  <input
                    type="text"
                    value={dealBadge}
                    onChange={(e) => setDealBadge(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g. 15% OFF, FLASH DEAL, DAILY SPECIAL"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowDealModal(false)}
                    className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-md shadow-indigo-200"
                  >
                    Activate Deal
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Modal: Create Coupon */}
        {showCouponModal && (
          <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Ticket className="w-5 h-5 text-emerald-600" />
                  Create Store Coupon
                </h3>
                <button onClick={() => setShowCouponModal(false)} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateCoupon} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Coupon Code *</label>
                  <input
                    type="text"
                    required
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase().replace(/\s/g, ''))}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm font-mono uppercase font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="e.g. GREEN20"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Description / Benefit</label>
                  <input
                    type="text"
                    value={couponDesc}
                    onChange={(e) => setCouponDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    placeholder="e.g. 20% off on all organic vegetables"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Discount Type</label>
                    <select
                      value={discountType}
                      onChange={(e) => setDiscountType(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="percent">Percentage (%)</option>
                      <option value="flat">Flat Cash (₹)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">
                      Discount Value {discountType === 'percent' ? '(%)' : '(₹)'} *
                    </label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={discountVal}
                      onChange={(e) => setDiscountVal(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      placeholder={discountType === 'percent' ? '15' : '50'}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Min. Store Order (₹)</label>
                    <input
                      type="number"
                      step="10"
                      value={minOrder}
                      onChange={(e) => setMinOrder(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      placeholder="200.00"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Max Discount Cap (₹)</label>
                    <input
                      type="number"
                      step="10"
                      value={maxDiscount}
                      onChange={(e) => setMaxDiscount(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      placeholder="Optional cap (e.g. 100)"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setShowCouponModal(false)}
                    className="px-4 py-2 border border-slate-200 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-200"
                  >
                    Create Coupon
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
