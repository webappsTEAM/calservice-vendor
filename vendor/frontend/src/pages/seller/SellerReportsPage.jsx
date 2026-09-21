import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  BarChart3,
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Package,
  ShoppingBag,
  RotateCcw,
  Layers,
  Download,
  Calendar,
  FileSpreadsheet,
  ArrowUpRight,
  ArrowRight,
  RefreshCw,
  Info,
  Boxes,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Search,
  Filter,
} from 'lucide-react';

export function SellerReportsPage() {
  const { token, user, isPlatformAdmin, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'audit', 'fulfilment', 'inventory', 'returns_claims', 'exports'
  const [dateRange, setDateRange] = useState('30'); // '7', '30', '90', 'all'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Real Database Data
  const [summaryData, setSummaryData] = useState(null);
  const [performanceData, setPerformanceData] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [exportingType, setExportingType] = useState(null);

  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};

  // Load Summary KPIs
  const loadSummary = useCallback(async () => {
    try {
      const res = await fetch(`/api/workforce/seller-hub/reports/summary/?days=${dateRange}`, {
        headers: authHeader,
      });
      if (!res.ok) {
        throw new Error('Failed to load seller reports summary');
      }
      const data = await res.json();
      setSummaryData(data);
    } catch (err) {
      console.error('Error loading reports summary:', err);
      setError(err.message || 'Error loading summary KPIs');
    }
  }, [dateRange, token]);

  // Load Performance Breakdown
  const loadPerformance = useCallback(async () => {
    try {
      const res = await fetch(`/api/workforce/seller-hub/reports/performance/?days=${dateRange}`, {
        headers: authHeader,
      });
      if (res.ok) {
        const data = await res.json();
        setPerformanceData(data);
      }
    } catch (err) {
      console.error('Error loading performance analytics:', err);
    }
  }, [dateRange, token]);

  // Load Quality Audit Checklist
  const loadAudit = useCallback(async () => {
    try {
      const res = await fetch('/api/workforce/seller-hub/reports/quality-audit/', {
        headers: authHeader,
      });
      if (res.ok) {
        const data = await res.json();
        setAuditData(data);
      }
    } catch (err) {
      console.error('Error loading quality audit:', err);
    }
  }, [token]);

  // Reload all
  const reloadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([loadSummary(), loadPerformance(), loadAudit()]);
    } finally {
      setLoading(false);
    }
  }, [loadSummary, loadPerformance, loadAudit]);

  useEffect(() => {
    reloadAll();
  }, [reloadAll]);

  // CSV Export Trigger
  const handleExportCSV = async (type) => {
    try {
      setExportingType(type);
      const res = await fetch(`/api/workforce/seller-hub/reports/export-csv/?type=${type}&days=${dateRange}`, {
        headers: authHeader,
      });
      if (!res.ok) {
        throw new Error(`Failed to export ${type} report`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sevo_seller_${type}_report_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      alert(`Export error: ${err.message}`);
    } finally {
      setExportingType(null);
    }
  };

  // Safe formatting helpers
  const formatCurrency = (val) => {
    const num = Number(val) || 0;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(num);
  };

  const formatPercent = (val) => {
    const num = Number(val) || 0;
    return `${num.toFixed(1)}%`;
  };

  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Sticky Top Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-20 px-8 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  Seller Reports & Quality Controls
                </h1>
                <span className="px-2 py-0.5 text-[11px] font-bold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  Real DB Feed
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Authoritative scorecard, inventory health, order fulfillment rates, returns diagnostics, and data exports.
              </p>
            </div>
          </div>

          {/* Controls: Date Filter & Action */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-slate-50 p-1 rounded-xl border border-slate-200 text-xs font-semibold">
              <span className="text-slate-400 pl-2 pr-1 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Period:
              </span>
              <button
                onClick={() => setDateRange('7')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  dateRange === '7'
                    ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                7 Days
              </button>
              <button
                onClick={() => setDateRange('30')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  dateRange === '30'
                    ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                30 Days
              </button>
              <button
                onClick={() => setDateRange('90')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  dateRange === '90'
                    ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                90 Days
              </button>
              <button
                onClick={() => setDateRange('all')}
                className={`px-3 py-1 rounded-lg transition-all ${
                  dateRange === 'all'
                    ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Time
              </button>
            </div>

            <button
              onClick={reloadAll}
              disabled={loading}
              title="Refresh Real Data"
              className="p-2 rounded-xl border border-slate-200 bg-white text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all shadow-xs disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-blue-600' : ''}`} />
            </button>
          </div>
        </header>

        {/* Tab Navigation */}
        <div className="bg-white border-b border-slate-200 px-8 py-2 flex items-center gap-2 overflow-x-auto select-none">
          {[
            { id: 'overview', label: 'Executive Scorecard', icon: TrendingUp },
            { id: 'audit', label: 'Quality Audit Checklist', icon: ShieldCheck, badge: auditData?.total_issues_count },
            { id: 'fulfilment', label: 'Fulfilment & Revenue', icon: ShoppingBag },
            { id: 'inventory', label: 'Inventory Health', icon: Package, badge: summaryData?.expiring_batches_count > 0 ? summaryData?.expiring_batches_count : null, badgeColor: 'bg-amber-100 text-amber-800' },
            { id: 'returns_claims', label: 'Returns & Claims', icon: RotateCcw },
            { id: 'exports', label: 'Export Center (CSV)', icon: FileSpreadsheet },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all shrink-0 ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 border border-blue-200/80 font-bold shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge !== null && tab.badge > 0 && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      tab.badgeColor || 'bg-rose-100 text-rose-800 border border-rose-200'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Body Content */}
        <div className="p-8 space-y-6">
          {error && (
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 font-medium">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
              <button
                onClick={reloadAll}
                className="font-bold underline hover:text-rose-900"
              >
                Retry
              </button>
            </div>
          )}

          {/* ── TOP KPI SCORECARD BANNERS ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Catalog Quality Score */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500">Catalog Quality</span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      (summaryData?.catalog_quality_score || 0) >= 80
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : (summaryData?.catalog_quality_score || 0) >= 50
                        ? 'bg-amber-50 text-amber-700 border border-amber-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {(summaryData?.catalog_quality_score || 0) >= 80 ? 'Optimal' : (summaryData?.catalog_quality_score || 0) >= 50 ? 'Fair' : 'Needs Review'}
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : formatPercent(summaryData?.catalog_quality_score || 0)}
                  </span>
                  <span className="text-xs text-slate-400">score</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1.5">
                  <span className="font-semibold text-slate-700">{summaryData?.approved_products_count || 0}</span> approved
                  <span className="text-slate-300">•</span>
                  <span className="font-semibold text-slate-700">{summaryData?.pending_products_count || 0}</span> in review
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Missing Images: <b className="text-slate-700">{summaryData?.missing_images_count || 0}</b></span>
                <button
                  onClick={() => setActiveTab('audit')}
                  className="font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  Audit <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            </div>

            {/* 2. Fulfilment Success & Gross Fulfilled Value */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500">Fulfilled Order Value</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                    Gross
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : formatCurrency(summaryData?.fulfilled_order_gross_value || 0)}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1.5">
                  <span className="font-semibold text-emerald-600">{summaryData?.delivered_orders_count || 0}</span> delivered
                  <span className="text-slate-300">•</span>
                  <span className="font-semibold text-slate-700">{summaryData?.total_orders_count || 0}</span> total orders
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Success Rate: <b className="text-emerald-700">{formatPercent(summaryData?.fulfilment_success_rate || 0)}</b></span>
                <Link
                  to="/workforce/seller-hub/orders"
                  className="font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  Orders <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* 3. Inventory Health Index */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500">Inventory Health</span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      (summaryData?.out_of_stock_count || 0) === 0
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                  >
                    {(summaryData?.out_of_stock_count || 0) === 0 ? 'Fully Stocked' : `${summaryData?.out_of_stock_count || 0} Out of Stock`}
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : formatPercent(summaryData?.inventory_health_index || 0)}
                  </span>
                  <span className="text-xs text-slate-400">in-stock rate</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1.5">
                  <span className="font-semibold text-slate-700">{summaryData?.total_inventory_items_count || 0}</span> SKUs tracked
                  <span className="text-slate-300">•</span>
                  <span className="font-semibold text-amber-600">{summaryData?.low_stock_count || 0}</span> low stock
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Expiring &lt;30d: <b className="text-rose-600">{summaryData?.expiring_batches_count || 0}</b></span>
                <Link
                  to="/workforce/seller-hub/inventory"
                  className="font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  Inventory <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* 4. Return & Claim Ratio */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500">Return & Claim Rates</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200">
                    Disputes
                  </span>
                </div>
                <div className="flex items-baseline gap-2 mt-2">
                  <span className="text-3xl font-extrabold text-slate-900 font-mono">
                    {loading ? '...' : formatPercent(summaryData?.return_rate || 0)}
                  </span>
                  <span className="text-xs text-slate-400">return rate</span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2 flex items-center gap-1.5">
                  <span className="font-semibold text-slate-700">{summaryData?.total_returns_count || 0}</span> returns
                  <span className="text-slate-300">•</span>
                  <span className="font-semibold text-slate-700">{summaryData?.total_claims_count || 0}</span> claims
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
                <span>Action Needed: <b className="text-amber-700">{summaryData?.claims_requiring_response_count || 0} claims</b></span>
                <Link
                  to="/workforce/seller-hub/claims"
                  className="font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  Claims <ChevronRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>

          {/* ── TAB CONTENT AREA ── */}

          {/* TAB 1: EXECUTIVE SCORECARD OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Detailed Performance Metrics Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Catalog Quality Breakdown Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                      <div className="p-2 bg-indigo-50 text-indigo-700 rounded-xl">
                        <Layers className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Catalog Quality Breakdown</h3>
                        <p className="text-xs text-slate-500">Listing completeness and admin review status</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3 text-xs">
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-slate-600 font-medium">Total Products</span>
                        <span className="font-bold text-slate-900 font-mono">{summaryData?.total_products_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/60 border border-emerald-100 text-emerald-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          Approved & Active
                        </span>
                        <span className="font-bold font-mono">{summaryData?.approved_products_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-50/60 border border-amber-100 text-amber-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-amber-600" />
                          Pending Review
                        </span>
                        <span className="font-bold font-mono">{summaryData?.pending_products_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-rose-50/60 border border-rose-100 text-rose-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 text-rose-600" />
                          Rejected / Action Needed
                        </span>
                        <span className="font-bold font-mono">{summaryData?.rejected_products_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-slate-700">
                        <span className="font-medium">Missing Primary Image</span>
                        <span className="font-bold text-amber-600 font-mono">{summaryData?.missing_images_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-slate-700">
                        <span className="font-medium">Missing Detailed Description</span>
                        <span className="font-bold text-amber-600 font-mono">{summaryData?.missing_descriptions_count || 0}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100">
                    <Link
                      to="/workforce/seller-hub/catalog-uploads"
                      className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-slate-900 text-white hover:bg-slate-800 text-xs font-bold transition-all shadow-xs"
                    >
                      <span>Manage Catalog Listings</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>

                {/* Inventory Health & Batches Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                      <div className="p-2 bg-emerald-50 text-emerald-700 rounded-xl">
                        <Package className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Inventory Health & Valuation</h3>
                        <p className="text-xs text-slate-500">Warehouse stock valuation and shelf life</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3 text-xs">
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-slate-600 font-medium">Total On-Hand Quantity</span>
                        <span className="font-bold text-slate-900 font-mono">{summaryData?.total_on_hand_quantity || 0} units</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-slate-600 font-medium">Estimated Inventory Value</span>
                        <span className="font-bold text-slate-900 font-mono">{formatCurrency(summaryData?.inventory_valuation || 0)}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-50/60 border border-amber-100 text-amber-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          Low Stock Threshold Alert
                        </span>
                        <span className="font-bold font-mono">{summaryData?.low_stock_count || 0} SKUs</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-rose-50/60 border border-rose-100 text-rose-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <XCircle className="w-3.5 h-3.5 text-rose-600" />
                          Out-of-Stock SKUs
                        </span>
                        <span className="font-bold font-mono">{summaryData?.out_of_stock_count || 0} SKUs</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-rose-50/60 border border-rose-100 text-rose-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-rose-600" />
                          Expiring Batches (&lt; 30 Days)
                        </span>
                        <span className="font-bold font-mono">{summaryData?.expiring_batches_count || 0} batches</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100">
                    <Link
                      to="/workforce/seller-hub/inventory"
                      className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-bold transition-all shadow-xs"
                    >
                      <span>Adjust & Restock Inventory</span>
                      <ArrowRight className="w-4 h-4" />
                    </Link>
                  </div>
                </div>

                {/* Operations & Reverse Logistics Card */}
                <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
                      <div className="p-2 bg-blue-50 text-blue-700 rounded-xl">
                        <ShoppingBag className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900">Order & Reverse Operations</h3>
                        <p className="text-xs text-slate-500">Pick-pack velocity and reverse dispute pipeline</p>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3 text-xs">
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-slate-600 font-medium">Pending Orders</span>
                        <span className="font-bold text-slate-900 font-mono">{summaryData?.pending_orders_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-blue-50/60 border border-blue-100 text-blue-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-blue-600" />
                          In Preparation / Picking
                        </span>
                        <span className="font-bold font-mono">{summaryData?.in_prep_orders_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-emerald-50/60 border border-emerald-100 text-emerald-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                          Delivered / Completed
                        </span>
                        <span className="font-bold font-mono">{summaryData?.delivered_orders_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                        <span className="text-slate-600 font-medium">Returns Pending Review</span>
                        <span className="font-bold text-amber-700 font-mono">{summaryData?.pending_returns_count || 0}</span>
                      </div>
                      <div className="flex items-center justify-between p-2.5 rounded-xl bg-amber-50/60 border border-amber-100 text-amber-950">
                        <span className="font-medium flex items-center gap-1.5">
                          <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                          Claims Requiring Response
                        </span>
                        <span className="font-bold font-mono">{summaryData?.claims_requiring_response_count || 0}</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-slate-100 flex gap-2">
                    <Link
                      to="/workforce/seller-hub/orders"
                      className="flex-1 flex items-center justify-center gap-1 py-2 px-3 rounded-xl bg-blue-600 text-white hover:bg-blue-700 text-xs font-bold transition-all shadow-xs"
                    >
                      <span>Orders</span>
                    </Link>
                    <Link
                      to="/workforce/seller-hub/claims"
                      className="flex-1 flex items-center justify-center gap-1 py-2 px-3 rounded-xl bg-slate-100 text-slate-800 hover:bg-slate-200 text-xs font-bold transition-all"
                    >
                      <span>Claims</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: QUALITY CONTROL AUDIT CHECKLIST */}
          {activeTab === 'audit' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-100">
                  <div>
                    <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-blue-600" />
                      Quality Control Action Center
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">
                      Automated audit findings derived directly from live database tables requiring merchant attention.
                    </p>
                  </div>
                  <span className="px-3 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded-xl border border-slate-200">
                    {auditData?.total_issues_count || 0} Action Items
                  </span>
                </div>

                {/* Audit Checklist Items */}
                <div className="mt-6 space-y-4">
                  {/* 1. Out of Stock Approved Products */}
                  <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-amber-100 text-amber-800 rounded-lg shrink-0 mt-0.5">
                        <Package className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-amber-950">
                          Approved Products with Zero Stock ({auditData?.out_of_stock_approved_count || 0})
                        </h4>
                        <p className="text-[11px] text-amber-800 mt-0.5">
                          Approved products with zero inventory on hand will not appear in customer storefront search.
                        </p>
                      </div>
                    </div>
                    <Link
                      to="/workforce/seller-hub/inventory"
                      className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 transition-all shrink-0 flex items-center gap-1"
                    >
                      <span>Restock Now</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  {/* 2. Expiring Inventory Batches */}
                  <div className="p-4 rounded-xl border border-rose-200 bg-rose-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-rose-100 text-rose-800 rounded-lg shrink-0 mt-0.5">
                        <Clock className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-rose-950">
                          Expiring Batches within 30 Days ({auditData?.expiring_batches_count || 0})
                        </h4>
                        <p className="text-[11px] text-rose-800 mt-0.5">
                          Perishable or dated stock approaching expiry must be prioritized or marked down to prevent loss.
                        </p>
                      </div>
                    </div>
                    <Link
                      to="/workforce/seller-hub/inventory"
                      className="px-3 py-1.5 bg-rose-600 text-white rounded-lg text-xs font-bold hover:bg-rose-700 transition-all shrink-0 flex items-center gap-1"
                    >
                      <span>View Batches</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  {/* 3. Catalog Products Missing Primary Image */}
                  <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-slate-200 text-slate-800 rounded-lg shrink-0 mt-0.5">
                        <Layers className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">
                          Products Missing Primary Images ({auditData?.missing_images_count || 0})
                        </h4>
                        <p className="text-[11px] text-slate-600 mt-0.5">
                          Upload high-resolution image assets to pass platform quality compliance checks.
                        </p>
                      </div>
                    </div>
                    <Link
                      to="/workforce/seller-hub/catalog-uploads"
                      className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-bold hover:bg-slate-800 transition-all shrink-0 flex items-center gap-1"
                    >
                      <span>Upload Media</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  {/* 4. Claims Requiring Response */}
                  <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-blue-100 text-blue-800 rounded-lg shrink-0 mt-0.5">
                        <ShieldAlert className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-blue-950">
                          Open Claims Awaiting Merchant Response ({auditData?.claims_requiring_response_count || 0})
                        </h4>
                        <p className="text-[11px] text-blue-800 mt-0.5">
                          Provide dispute comments or supporting proof of dispatch before claims are auto-escalated.
                        </p>
                      </div>
                    </div>
                    <Link
                      to="/workforce/seller-hub/claims"
                      className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 transition-all shrink-0 flex items-center gap-1"
                    >
                      <span>Respond to Claims</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  {/* 5. Returns Pending Intake / QC */}
                  <div className="p-4 rounded-xl border border-indigo-200 bg-indigo-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-indigo-100 text-indigo-800 rounded-lg shrink-0 mt-0.5">
                        <RotateCcw className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-indigo-950">
                          Returns Pending Intake / Quality Inspection ({auditData?.returns_pending_qc_count || 0})
                        </h4>
                        <p className="text-[11px] text-indigo-800 mt-0.5">
                          Items received at warehouse must be inspected for restock or scrap classification.
                        </p>
                      </div>
                    </div>
                    <Link
                      to="/workforce/seller-hub/returns"
                      className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-bold hover:bg-indigo-700 transition-all shrink-0 flex items-center gap-1"
                    >
                      <span>Perform QC</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: FULFILMENT & REVENUE INSIGHTS */}
          {activeTab === 'fulfilment' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Daily Fulfilment Trends</h3>
                    <p className="text-xs text-slate-500">Real-time daily order volume and fulfilled gross value</p>
                  </div>
                  <span className="text-xs font-semibold text-slate-500">
                    Total: {performanceData?.daily_trends?.length || 0} days recorded
                  </span>
                </div>

                {(!performanceData?.daily_trends || performanceData.daily_trends.length === 0) ? (
                  <div className="py-12 text-center text-slate-400">
                    <ShoppingBag className="w-10 h-10 mx-auto opacity-30 mb-2" />
                    <p className="text-xs font-medium">No order activity recorded in selected date range.</p>
                  </div>
                ) : (
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500">
                          <th className="py-2.5 px-3 font-semibold">Date</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Orders Placed</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Delivered</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Cancelled</th>
                          <th className="py-2.5 px-3 font-semibold text-right">Fulfilled Value</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {performanceData.daily_trends.map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="py-2.5 px-3 font-mono font-medium text-slate-700">{item.date}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-semibold text-slate-900">{item.orders_count}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-emerald-600 font-semibold">{item.delivered_count}</td>
                            <td className="py-2.5 px-3 text-right font-mono text-rose-600 font-semibold">{item.cancelled_count}</td>
                            <td className="py-2.5 px-3 text-right font-mono font-bold text-slate-900">{formatCurrency(item.fulfilled_gross_value)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: INVENTORY HEALTH */}
          {activeTab === 'inventory' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Inventory Movement Ledger by Type</h3>
                    <p className="text-xs text-slate-500">Breakdown of warehouse receipts, dispatches, restocks, and adjustments</p>
                  </div>
                  <Link
                    to="/workforce/seller-hub/inventory"
                    className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    <span>Full Ledger</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>

                {(!performanceData?.movement_breakdown || performanceData.movement_breakdown.length === 0) ? (
                  <div className="py-12 text-center text-slate-400">
                    <Boxes className="w-10 h-10 mx-auto opacity-30 mb-2" />
                    <p className="text-xs font-medium">No inventory movements recorded in selected period.</p>
                  </div>
                ) : (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {performanceData.movement_breakdown.map((item, idx) => (
                      <div key={idx} className="p-4 rounded-xl border border-slate-100 bg-slate-50">
                        <span className="text-xs font-bold text-slate-700 block uppercase tracking-wider">{item.movement_type}</span>
                        <div className="flex items-baseline justify-between mt-2">
                          <span className="text-xl font-extrabold text-slate-900 font-mono">{item.total_quantity}</span>
                          <span className="text-[11px] text-slate-500 font-semibold">{item.events_count} transactions</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: RETURNS & CLAIMS */}
          {activeTab === 'returns_claims' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Return Reasons Breakdown */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="pb-4 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-900">Returns by Customer Reason</h3>
                  <p className="text-xs text-slate-500">Root-cause classification of reverse logistics</p>
                </div>

                {(!performanceData?.return_reasons || performanceData.return_reasons.length === 0) ? (
                  <div className="py-12 text-center text-slate-400">
                    <RotateCcw className="w-10 h-10 mx-auto opacity-30 mb-2" />
                    <p className="text-xs font-medium">No returns recorded in selected period.</p>
                  </div>
                ) : (
                  <div className="mt-4 space-y-3">
                    {performanceData.return_reasons.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                        <span className="font-semibold text-slate-700">{item.reason || 'Unspecified'}</span>
                        <span className="font-bold text-slate-900 font-mono">{item.count} cases</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Claims Breakdown by Type */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="pb-4 border-b border-slate-100">
                  <h3 className="text-sm font-bold text-slate-900">Claims by Dispute Type</h3>
                  <p className="text-xs text-slate-500">Damage, transit loss, and merchant disputes</p>
                </div>

                {(!performanceData?.claim_types || performanceData.claim_types.length === 0) ? (
                  <div className="py-12 text-center text-slate-400">
                    <ShieldAlert className="w-10 h-10 mx-auto opacity-30 mb-2" />
                    <p className="text-xs font-medium">No claims or disputes recorded in selected period.</p>
                  </div>
                ) : (
                  <div className="mt-4 space-y-3">
                    {performanceData.claim_types.map((item, idx) => (
                      <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                        <span className="font-semibold text-slate-700">{item.claim_type}</span>
                        <span className="font-bold text-slate-900 font-mono">{item.count} cases</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: DATA EXPORT CENTER (CSV) */}
          {activeTab === 'exports' && (
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-xs">
                <div className="pb-5 border-b border-slate-100">
                  <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <FileSpreadsheet className="w-5 h-5 text-blue-600" />
                    Real-Time CSV Export Center
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Download authentic, row-level CSV data extracts scoped to your authenticated merchant business for offline auditing and reporting.
                  </p>
                </div>

                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {/* Export 1: Orders */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between">
                    <div>
                      <div className="p-2.5 bg-blue-100 text-blue-800 rounded-xl w-fit mb-3">
                        <ShoppingBag className="w-5 h-5" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">Order Fulfilment Ledger</h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        Line-item order records, delivery statuses, customer names, delivery pin codes, and gross amounts.
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportCSV('orders')}
                      disabled={exportingType === 'orders'}
                      className="mt-5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-blue-600 text-white hover:bg-blue-700 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      <span>{exportingType === 'orders' ? 'Exporting...' : 'Export Orders CSV'}</span>
                    </button>
                  </div>

                  {/* Export 2: Inventory */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between">
                    <div>
                      <div className="p-2.5 bg-emerald-100 text-emerald-800 rounded-xl w-fit mb-3">
                        <Package className="w-5 h-5" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">Inventory Stock & Batches</h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        SKU stock counts, reorder thresholds, batch numbers, manufacturing/expiry dates, and valuation.
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportCSV('inventory')}
                      disabled={exportingType === 'inventory'}
                      className="mt-5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      <span>{exportingType === 'inventory' ? 'Exporting...' : 'Export Inventory CSV'}</span>
                    </button>
                  </div>

                  {/* Export 3: Returns */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between">
                    <div>
                      <div className="p-2.5 bg-amber-100 text-amber-800 rounded-xl w-fit mb-3">
                        <RotateCcw className="w-5 h-5" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">Returns & QC Log</h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        Return RMA numbers, original order references, customer return reasons, QC decisions, and restock movement logs.
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportCSV('returns')}
                      disabled={exportingType === 'returns'}
                      className="mt-5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-amber-600 text-white hover:bg-amber-700 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      <span>{exportingType === 'returns' ? 'Exporting...' : 'Export Returns CSV'}</span>
                    </button>
                  </div>

                  {/* Export 4: Claims */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between">
                    <div>
                      <div className="p-2.5 bg-rose-100 text-rose-800 rounded-xl w-fit mb-3">
                        <ShieldAlert className="w-5 h-5" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">Claims & Operational Disputes</h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        Claim case references, claim types, claimed amounts, admin decisions, and dispute timeline events.
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportCSV('claims')}
                      disabled={exportingType === 'claims'}
                      className="mt-5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-rose-600 text-white hover:bg-rose-700 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      <span>{exportingType === 'claims' ? 'Exporting...' : 'Export Claims CSV'}</span>
                    </button>
                  </div>

                  {/* Export 5: Quality Audit */}
                  <div className="p-5 rounded-2xl border border-slate-200 bg-slate-50/60 flex flex-col justify-between">
                    <div>
                      <div className="p-2.5 bg-indigo-100 text-indigo-800 rounded-xl w-fit mb-3">
                        <ShieldCheck className="w-5 h-5" />
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">Catalog Quality Audit</h4>
                      <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                        Catalog items status, missing images flag, missing descriptions flag, approval states, and compliance checklist.
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportCSV('quality')}
                      disabled={exportingType === 'quality'}
                      className="mt-5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-indigo-600 text-white hover:bg-indigo-700 text-xs font-bold transition-all shadow-xs disabled:opacity-50"
                    >
                      <Download className="w-4 h-4" />
                      <span>{exportingType === 'quality' ? 'Exporting...' : 'Export Quality Audit CSV'}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default SellerReportsPage;
