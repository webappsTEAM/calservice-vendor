/**
 * AdminStoreProfilePage.jsx
 * Dedicated Amazon-style Seller Store Profile & Operating Controls.
 */
import React, { useEffect, useState } from 'react';
import {
  apiGetVendorStoreProfile,
  apiUpdateVendorStoreProfile,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import {
  Store,
  Save,
  CheckCircle2,
  AlertCircle,
  Clock,
  MapPin,
  ShieldCheck,
  Image,
  Power,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';

export default function AdminStoreProfilePage() {
  const [store, setStore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });

  // Form State
  const [storeName, setStoreName] = useState('');
  const [tagline, setTagline] = useState('');
  const [description, setDescription] = useState('');
  const [logoUrl, setLogoUrl] = useState('');
  const [bannerUrl, setBannerUrl] = useState('');
  const [fssaiLicense, setFssaiLicense] = useState('');
  const [storeAddress, setStoreAddress] = useState('');
  const [deliveryRadius, setDeliveryRadius] = useState(5.0);
  const [minOrder, setMinOrder] = useState('0.00');
  const [deliveryMins, setDeliveryMins] = useState(30);
  const [isAccepting, setIsAccepting] = useState(true);

  useEffect(() => {
    loadStore();
  }, []);

  const loadStore = async () => {
    setLoading(true);
    setMsg({ type: '', text: '' });
    try {
      const res = await apiGetVendorStoreProfile();
      if (res) {
        setStore(res);
        setStoreName(res.store_name || '');
        setTagline(res.tagline || '');
        setDescription(res.description || '');
        setLogoUrl(res.logo_url || '');
        setBannerUrl(res.banner_url || '');
        setFssaiLicense(res.fssai_license_number || '');
        setStoreAddress(res.store_address || '');
        setDeliveryRadius(res.delivery_radius_km || 5.0);
        setMinOrder(res.minimum_order_amount || '0.00');
        setDeliveryMins(res.estimated_delivery_mins || 30);
        setIsAccepting(Boolean(res.is_accepting_orders));
      }
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to load store profile.' });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMsg({ type: '', text: '' });
    try {
      await apiUpdateVendorStoreProfile({
        store_name: storeName,
        tagline,
        description,
        logo_url: logoUrl,
        banner_url: bannerUrl,
        fssai_license_number: fssaiLicense,
        store_address: storeAddress,
        delivery_radius_km: deliveryRadius,
        minimum_order_amount: minOrder,
        estimated_delivery_mins: deliveryMins,
        is_accepting_orders: isAccepting,
      });
      setMsg({ type: 'success', text: 'Store profile and operational settings saved successfully!' });
      setTimeout(() => setMsg({ type: '', text: '' }), 4000);
    } catch (err) {
      setMsg({ type: 'error', text: err.message || 'Failed to update store profile.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppShell activeNav="/workforce/admin/store-profile">
      <div className="max-w-5xl mx-auto space-y-6 pb-16">
        <PageHeader
          title="Seller Storefront Profile"
          subtitle="Configure your public store presence, rapid fulfillment parameters, and live order acceptance."
          badge="Marketplace"
          icon={Store}
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

        {loading ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-slate-200 shadow-sm">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-3" />
            <p className="text-slate-500 font-medium text-sm">Loading store details...</p>
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-6">
            {/* Top Quick-Controls Bar */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div
                  className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                    isAccepting ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'
                  }`}
                >
                  <Power className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-800 text-base">Store Status: {isAccepting ? 'OPEN' : 'CLOSED'}</h3>
                  <p className="text-xs text-slate-500">
                    {isAccepting
                      ? 'Your store is active and accepting grocery orders on the customer app.'
                      : 'Orders are paused. Customers will see your store as temporarily closed.'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setIsAccepting(!isAccepting)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    isAccepting
                      ? 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
                      : 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-700'
                  }`}
                >
                  {isAccepting ? 'Pause Store Orders' : 'Open Store Now'}
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-md shadow-indigo-200 flex items-center gap-2 disabled:opacity-50"
                >
                  <Save className="w-4 h-4" />
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </div>

            {/* Store Branding Section */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Image className="w-4 h-4 text-indigo-600" />
                  Store Identity & Branding
                </h3>
                <p className="text-xs text-slate-500">Presented to customers on search results and your dedicated store page.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Store Name *</label>
                  <input
                    type="text"
                    required
                    value={storeName}
                    onChange={(e) => setStoreName(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g. GreenFresh Farm Store"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Store Tagline</label>
                  <input
                    type="text"
                    value={tagline}
                    onChange={(e) => setTagline(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="e.g. Freshly harvested vegetables delivered in 30 mins"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">About Store / Description</label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Describe your produce sourcing, organic certification, hygiene standards..."
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Store Logo Image URL</label>
                  <input
                    type="text"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="https://.../logo.png"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Store Banner Image URL</label>
                  <input
                    type="text"
                    value={bannerUrl}
                    onChange={(e) => setBannerUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="https://.../banner.jpg"
                  />
                </div>
              </div>
            </div>

            {/* Delivery & Fulfillment Section */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-5">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-emerald-600" />
                  Fulfillment & Delivery Coverage
                </h3>
                <p className="text-xs text-slate-500">Define your local delivery zone and speed guarantee.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">
                    Delivery Radius (km): <span className="text-indigo-600">{deliveryRadius} km</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="25"
                    step="0.5"
                    value={deliveryRadius}
                    onChange={(e) => setDeliveryRadius(parseFloat(e.target.value))}
                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                  />
                  <span className="text-[11px] text-slate-400">Covers customers within {deliveryRadius} km radius</span>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Estimated Delivery (Mins)</label>
                  <div className="relative">
                    <Clock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="number"
                      min="15"
                      max="180"
                      value={deliveryMins}
                      onChange={(e) => setDeliveryMins(parseInt(e.target.value) || 30)}
                      className="w-full pl-9 pr-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="30"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Minimum Order Value (₹)</label>
                  <input
                    type="number"
                    min="0"
                    step="10"
                    value={minOrder}
                    onChange={(e) => setMinOrder(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="100.00"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Physical Store / Warehouse Address</label>
                <textarea
                  rows={2}
                  value={storeAddress}
                  onChange={(e) => setStoreAddress(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder="Shop #12, Market Road, Hosur, Tamil Nadu"
                />
              </div>
            </div>

            {/* Compliance Section */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-amber-600" />
                  Food Safety Compliance & Licensing
                </h3>
                <p className="text-xs text-slate-500">Government mandated for all fresh grocery & produce suppliers.</p>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">FSSAI License / Registration Number</label>
                <input
                  type="text"
                  value={fssaiLicense}
                  onChange={(e) => setFssaiLicense(e.target.value)}
                  className="w-full max-w-md px-3 py-2 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase font-mono"
                  placeholder="e.g. 12422002000123"
                />
              </div>
            </div>

            {/* Submit Action */}
            <div className="flex justify-end gap-3 pt-4">
              <button
                type="submit"
                disabled={saving}
                className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-lg shadow-indigo-200 flex items-center gap-2 disabled:opacity-50 transition-all"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving Store Changes...' : 'Save & Publish Storefront'}
              </button>
            </div>
          </form>
        )}
      </div>
    </AppShell>
  );
}
