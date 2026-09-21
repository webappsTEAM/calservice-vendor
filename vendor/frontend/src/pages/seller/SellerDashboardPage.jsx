import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetSellerHubCategories,
  apiGetSellerHubCoupons,
} from '../../api/workforceService.js';
import {
  Store,
  Layers,
  Tag,
  ShoppingBag,
  RotateCcw,
  ShieldAlert,
  Package,
  UploadCloud,
  ArrowRight,
  Plus,
  Clock,
  Truck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  TrendingUp,
  DollarSign,
  Sparkles,
  Info,
  ChevronRight,
  Boxes,
  BarChart3,
} from 'lucide-react';

export function SellerDashboardPage() {
  const { user, token, isPlatformAdmin, isAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [categoriesCount, setCategoriesCount] = useState(0);
  const [couponsCount, setCouponsCount] = useState(0);
  const [catalogsAwaitingCount, setCatalogsAwaitingCount] = useState(0);
  const [approvedProductsCount, setApprovedProductsCount] = useState(0);
  const [lowStockCount, setLowStockCount] = useState(0);
  const [outOfStockCount, setOutOfStockCount] = useState(0);
  const [totalInventoryCount, setTotalInventoryCount] = useState(0);
  const [todayOrdersCount, setTodayOrdersCount] = useState(0);
  const [pendingOrdersCount, setPendingOrdersCount] = useState(0);
  const [inPrepOrdersCount, setInPrepOrdersCount] = useState(0);
  const [completedOrdersCount, setCompletedOrdersCount] = useState(0);
  const [totalReturnsCount, setTotalReturnsCount] = useState(0);
  const [pendingReturnsCount, setPendingReturnsCount] = useState(0);
  const [openClaimsCount, setOpenClaimsCount] = useState(0);
  const [claimsRequiringResponseCount, setClaimsRequiringResponseCount] = useState(0);
  const [totalClaimsCount, setTotalClaimsCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadStats() {
      try {
        setLoading(true);
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const [cats, coups, metRes] = await Promise.all([
          apiGetSellerHubCategories().catch(() => []),
          apiGetSellerHubCoupons().catch(() => []),
          fetch('/api/workforce/seller-hub/metrics/', { headers }).then((r) => r.ok ? r.json() : null).catch(() => null),
        ]);
        setCategoriesCount(Array.isArray(cats) ? cats.length : 0);
        setCouponsCount(Array.isArray(coups) ? coups.length : 0);
        if (metRes) {
          setCatalogsAwaitingCount(metRes.catalogs_awaiting_approval || 0);
          setApprovedProductsCount(metRes.approved_products || 0);
          setLowStockCount(metRes.low_stock_items_count || 0);
          setOutOfStockCount(metRes.out_of_stock_items_count || 0);
          setTotalInventoryCount(metRes.total_inventory_products || 0);
          setTodayOrdersCount(metRes.today_orders_count || 0);
          setPendingOrdersCount(metRes.pending_orders_count || 0);
          setInPrepOrdersCount(metRes.in_prep_orders_count || 0);
          setCompletedOrdersCount(metRes.completed_orders_count || 0);
          setTotalReturnsCount(metRes.total_returns_count || 0);
          setPendingReturnsCount(metRes.pending_returns_count || 0);
          setOpenClaimsCount(metRes.open_claims_count || 0);
          setClaimsRequiringResponseCount(metRes.claims_requiring_response_count || 0);
          setTotalClaimsCount(metRes.total_claims_count || 0);
          if (metRes.active_categories !== undefined) setCategoriesCount(metRes.active_categories);
          if (metRes.active_coupons !== undefined) setCouponsCount(metRes.active_coupons);
        }
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, [token]);

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Top Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100">
              <Store className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  {user?.companyName || 'Seller Hub'}
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full">
                  Merchant Center
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Central command dashboard for your catalog, orders, inventory, and promotions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            {isPlatformAdmin || isAdmin ? (
              <Link
                to="/workforce/admin/seller-hub/categories"
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <Layers className="w-3.5 h-3.5 text-emerald-600" />
                <span>Categories</span>
              </Link>
            ) : (
              <Link
                to="/workforce/seller-hub/catalog-uploads"
                className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center gap-1.5"
              >
                <UploadCloud className="w-3.5 h-3.5 text-emerald-600" />
                <span>Add Products</span>
              </Link>
            )}
            <Link
              to="/workforce/admin/seller-hub/coupons"
              className="px-3.5 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Coupon</span>
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-8">
          {/* Phase 1 Live Overview Banner */}
          <div className="p-5 bg-gradient-to-r from-emerald-50 via-teal-50 to-white rounded-2xl border border-emerald-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2.5 bg-emerald-600 text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">
                  Seller Hub Foundation & Catalog Engine
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                  Catalog categories and store coupons are powered by live records. Orders, inventory sync, returns, claims and catalog feeds are managed from this hub.
                </p>
              </div>
            </div>
          </div>

          {/* ── SECTION 1: LIVE CATALOG & STORE METRICS ── */}
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Live Store Configurations
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Categories Card (Real DB) */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs relative overflow-hidden group hover:border-emerald-300 transition-all">
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 flex items-center justify-center">
                    <Layers className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    Live Data
                  </span>
                </div>
                <div className="mt-4">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : categoriesCount}
                  </span>
                  <p className="text-xs font-bold text-slate-800 mt-1">Catalog Categories</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Hierarchical grocery department classifications</p>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                  {isPlatformAdmin || isAdmin ? (
                    <Link
                      to="/workforce/admin/seller-hub/categories"
                      className="font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 group-hover:underline"
                    >
                      <span>Manage Categories</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  ) : (
                    <Link
                      to="/workforce/seller-hub/catalog-uploads"
                      className="font-bold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 group-hover:underline"
                    >
                      <span>View Products</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  )}
                </div>
              </div>

              {/* Coupons Card (Real DB) */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs relative overflow-hidden group hover:border-indigo-300 transition-all">
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 flex items-center justify-center">
                    <Tag className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
                    Live Data
                  </span>
                </div>
                <div className="mt-4">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : couponsCount}
                  </span>
                  <p className="text-xs font-bold text-slate-800 mt-1">Active Store Coupons</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Marketing vouchers, flat & % discounts</p>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                  <Link
                    to="/workforce/admin/seller-hub/coupons"
                    className="font-bold text-indigo-700 hover:text-indigo-800 flex items-center gap-1 group-hover:underline"
                  >
                    <span>Manage Coupons</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>

              {/* Store Operational Status Card */}
              <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs relative overflow-hidden group hover:border-blue-300 transition-all">
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 flex items-center justify-center">
                    <Store className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2.5 py-0.5 rounded-full border border-blue-200">
                    Active
                  </span>
                </div>
                <div className="mt-4">
                  <span className="text-base font-extrabold text-slate-900 block truncate">
                    {user?.companyName || 'Verified Merchant Store'}
                  </span>
                  <p className="text-xs font-bold text-slate-800 mt-1">Merchant Store Status</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Ready for catalog listings & fulfillment</p>
                </div>
                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
                  <Link
                    to="/workforce/seller-hub/inventory"
                    className="font-bold text-blue-700 hover:text-blue-800 flex items-center gap-1 group-hover:underline"
                  >
                    <span>Store Inventory</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* ── SECTION 2: OPERATIONAL SUMMARY CARDS (PHASE 2 ENGINE) ── */}
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <div className="flex items-center gap-2">
                <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  Store Operational Pipelines
                </h2>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              {/* 1. Today's Orders */}
              <Link
                to="/workforce/seller-hub/orders"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Today's Orders</span>
                  <ShoppingBag className="w-4 h-4 text-blue-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{todayOrdersCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Incoming queue</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-blue-600 transition-colors" />
                </div>
              </Link>

              {/* 2. Action Required / New */}
              <Link
                to="/workforce/seller-hub/orders"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Action Required</span>
                  <Package className="w-4 h-4 text-amber-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{pendingOrdersCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">New orders</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-amber-600 transition-colors" />
                </div>
              </Link>

              {/* 3. In Preparation */}
              <Link
                to="/workforce/seller-hub/orders"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">In Preparation</span>
                  <Truck className="w-4 h-4 text-purple-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{inPrepOrdersCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Picking / Packed</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-purple-600 transition-colors" />
                </div>
              </Link>

              {/* 4. Completed Orders */}
              <Link
                to="/workforce/seller-hub/orders"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Completed Orders</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{completedOrdersCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Fulfilled</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-emerald-600 transition-colors" />
                </div>
              </Link>

              {/* 5. Return Requests */}
              <Link
                to="/workforce/seller-hub/returns"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Return Requests</span>
                  <RotateCcw className="w-4 h-4 text-amber-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{pendingReturnsCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">{totalReturnsCount} total cases</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-amber-600 transition-colors" />
                </div>
              </Link>

              {/* 6. Open Claims */}
              <Link
                to="/workforce/seller-hub/claims"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Open Claims</span>
                  <ShieldAlert className="w-4 h-4 text-red-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{openClaimsCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">
                    {claimsRequiringResponseCount > 0 ? `${claimsRequiringResponseCount} need response` : `${totalClaimsCount} total cases`}
                  </span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-red-600 transition-colors" />
                </div>
              </Link>

              {/* 7. Low Stock Items */}
              <Link
                to="/workforce/seller-hub/inventory"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Low Stock Items</span>
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{lowStockCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Reorder alert</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-orange-600 transition-colors" />
                </div>
              </Link>

              {/* 8. Out of Stock Items */}
              <Link
                to="/workforce/seller-hub/inventory"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Out of Stock</span>
                  <XCircle className="w-4 h-4 text-rose-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">{outOfStockCount}</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Zero inventory</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-rose-600 transition-colors" />
                </div>
              </Link>

              {/* 9. Catalogs Awaiting Approval */}
              <Link
                to="/workforce/seller-hub/catalog-uploads"
                className="bg-white p-4 rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-xs transition-all group block"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Pending Catalogs</span>
                  <UploadCloud className="w-4 h-4 text-indigo-500" />
                </div>
                <p className="text-2xl font-extrabold text-indigo-900 font-mono mt-2">
                  {loading ? '...' : catalogsAwaitingCount}
                </p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Items in review</span>
                  <ChevronRight className="w-3 h-3 text-slate-300 group-hover:text-indigo-600 transition-colors" />
                </div>
              </Link>

              {/* 10. Today's / Current Sales */}
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-600">Today's Sales</span>
                  <TrendingUp className="w-4 h-4 text-emerald-500" />
                </div>
                <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">₹0.00</p>
                <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-100">
                  <span className="text-[10px] text-slate-400">Settled orders</span>
                  <span className="text-[10px] font-bold text-emerald-600">₹ INR</span>
                </div>
              </div>
            </div>
          </div>

          {/* ── SECTION 3: EIGHT SELLER HUB MODULES DIRECT DIRECTORY ── */}
          <div>
            <div className="flex items-center justify-between mb-3.5">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Seller Hub Modules Directory
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* 1. Home */}
              <Link
                to="/workforce/seller/dashboard"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center font-bold mb-3">
                    <Store className="w-4 h-4 text-emerald-600" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">1. Home</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Merchant command center overview and store health telemetry.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700">
                  <span>Current Page</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 2. Orders */}
              <Link
                to="/workforce/seller-hub/orders"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-blue-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold mb-3">
                    <ShoppingBag className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">2. Orders</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Customer order routing, packing slips, and delivery rider handoffs.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-700">
                  <span>Open Orders</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 3. Returns */}
              <Link
                to="/workforce/seller-hub/returns"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-amber-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold mb-3">
                    <RotateCcw className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">3. Returns</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Customer return requests, inspection decisions, and reverse pickup.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-amber-700">
                  <span>Open Returns</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 4. Claims */}
              <Link
                to="/workforce/seller-hub/claims"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-red-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-red-50 text-red-700 flex items-center justify-center font-bold mb-3">
                    <ShieldAlert className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">4. Claims</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    In-transit damage claims, delivery losses, and merchant protections.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-red-700">
                  <span>Open Claims</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 5. Inventory */}
              <Link
                to="/workforce/seller-hub/inventory"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold mb-3">
                    <Package className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">5. Inventory</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Stock levels, warehouse allocation, and low-stock reorder thresholds.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700">
                  <span>Open Inventory</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 6. Catalog Uploads */}
              <Link
                to="/workforce/seller-hub/catalog-uploads"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-indigo-300 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold mb-3">
                    <UploadCloud className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">6. Catalog Uploads</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Bulk Excel/CSV item ingestion feeds and image archive uploads.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-indigo-700">
                  <span>Open Feeds</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 7. Categories */}
              <Link
                to={isPlatformAdmin || isAdmin ? "/workforce/admin/seller-hub/categories" : "/workforce/seller-hub/catalog-uploads"}
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-emerald-400 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-emerald-100 text-emerald-800 flex items-center justify-center font-bold mb-3">
                    <Layers className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">7. Catalog Categories</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    {isPlatformAdmin || isAdmin
                      ? "Multi-level expandable folder tree for merchandise organization."
                      : "Hierarchical department structure. Picked during single & bulk product cataloging."}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-emerald-700">
                  <span>{isPlatformAdmin || isAdmin ? `Manage (${categoriesCount})` : 'Browse Catalog'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 8. Coupons */}
              <Link
                to="/workforce/admin/seller-hub/coupons"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-indigo-400 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-800 flex items-center justify-center font-bold mb-3">
                    <Tag className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">8. Coupons</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Discount vouchers, promotional rules, thresholds, and limits.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-indigo-700">
                  <span>Manage ({couponsCount})</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>

              {/* 9. Reports & Quality */}
              <Link
                to="/workforce/seller-hub/reports"
                className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs hover:border-blue-400 transition-all flex flex-col justify-between group"
              >
                <div>
                  <div className="w-9 h-9 rounded-xl bg-blue-100 text-blue-800 flex items-center justify-center font-bold mb-3">
                    <BarChart3 className="w-4 h-4" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-sm">9. Reports & Quality</h3>
                  <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                    Quality scorecards, inventory velocity, returns/claims audits, and CSV data exports.
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs font-semibold text-blue-700">
                  <span>Open Reports</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default SellerDashboardPage;
