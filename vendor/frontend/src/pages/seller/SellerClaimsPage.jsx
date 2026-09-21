import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  ShieldAlert,
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
  MessageSquare,
  DollarSign,
  Plus,
  Send,
  HelpCircle,
  RotateCcw,
} from 'lucide-react';

export function SellerClaimsPage() {
  const { user, token, isPlatformAdmin } = useAuth();
  const isSuperAdmin = isPlatformAdmin || user?.is_superuser;

  const [claimsList, setClaimsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Metrics
  const [metrics, setMetrics] = useState({
    total_claims_count: 0,
    open_claims_count: 0,
    claims_requiring_response_count: 0,
    escalated_claims_count: 0,
    resolved_claims_count: 0,
  });

  // Selected Claim for Detail & Action Drawer
  const [selectedClaimId, setSelectedClaimId] = useState(null);
  const [selectedClaimDetail, setSelectedClaimDetail] = useState(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Create Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    claim_type: 'DAMAGED_ITEM',
    order_id: '',
    return_id: '',
    description: '',
    claimed_amount: '',
    evidence_urls: '',
    customer_name: '',
    customer_phone: '',
  });

  // Form states for drawer actions
  const [actionLoading, setActionLoading] = useState(false);
  const [responseForm, setResponseForm] = useState({ seller_response: '', evidence_urls: '' });
  const [adminDecisionForm, setAdminDecisionForm] = useState({ decision: 'APPROVE', reason: '' });
  const [escalateNotes, setEscalateNotes] = useState('');
  const [closeNotes, setCloseNotes] = useState('');

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
          total_claims_count: data.total_claims_count || 0,
          open_claims_count: data.open_claims_count || 0,
          claims_requiring_response_count: data.claims_requiring_response_count || 0,
          escalated_claims_count: data.escalated_claims_count || 0,
          resolved_claims_count: data.resolved_claims_count || 0,
        });
      }
    } catch (err) {
      console.error('Failed to load claims metrics:', err);
    }
  }, [token]);

  // Load claims list
  const loadClaims = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams();
      if (statusFilter !== 'ALL') params.append('status', statusFilter);
      if (typeFilter) params.append('claim_type', typeFilter);
      if (debouncedSearch) params.append('search', debouncedSearch);

      const res = await fetch(`/api/workforce/seller-hub/claims/?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load claims list');
      const data = await res.json();
      setClaimsList(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Error loading claims');
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter, typeFilter, debouncedSearch]);

  useEffect(() => {
    loadClaims();
    loadMetrics();
  }, [loadClaims, loadMetrics]);

  // Load Claim Detail
  const openClaimDetail = async (claimId) => {
    setSelectedClaimId(claimId);
    setIsDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const res = await fetch(`/api/workforce/seller-hub/claims/${claimId}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load claim detail');
      const data = await res.json();
      setSelectedClaimDetail(data);
      // Reset forms
      setResponseForm({ seller_response: '', evidence_urls: '' });
      setAdminDecisionForm({ decision: 'APPROVE', reason: '' });
      setEscalateNotes('');
      setCloseNotes('');
    } catch (err) {
      alert(err.message || 'Error loading claim details');
    } finally {
      setDrawerLoading(false);
    }
  };

  const closeDrawer = () => {
    setIsDrawerOpen(false);
    setSelectedClaimId(null);
    setSelectedClaimDetail(null);
  };

  // 1. Create Internal Dispute
  const handleCreateClaim = async (e) => {
    e.preventDefault();
    if (!createForm.description.trim()) {
      alert('Description is required.');
      return;
    }
    try {
      setActionLoading(true);
      const evidenceList = createForm.evidence_urls
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

      const payload = {
        claim_type: createForm.claim_type,
        description: createForm.description.trim(),
        order_id: createForm.order_id ? parseInt(createForm.order_id) : null,
        return_id: createForm.return_id ? parseInt(createForm.return_id) : null,
        claimed_amount: createForm.claimed_amount ? parseFloat(createForm.claimed_amount) : 0.0,
        evidence_urls: evidenceList,
        customer_name: createForm.customer_name.trim(),
        customer_phone: createForm.customer_phone.trim(),
      };

      const res = await fetch('/api/workforce/seller-hub/claims/', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setIsCreateModalOpen(false);
      setCreateForm({
        claim_type: 'DAMAGED_ITEM',
        order_id: '',
        return_id: '',
        description: '',
        claimed_amount: '',
        evidence_urls: '',
        customer_name: '',
        customer_phone: '',
      });
      loadClaims();
      loadMetrics();
      alert(`Claim #${data.claim?.claim_number || ''} created successfully.`);
    } catch (err) {
      alert(err.message || 'Failed to create claim');
    } finally {
      setActionLoading(false);
    }
  };

  // 2. Submit Seller Response
  const handleSellerResponse = async (e) => {
    e.preventDefault();
    if (!responseForm.seller_response.trim()) {
      alert('Seller response explanation is required.');
      return;
    }
    try {
      setActionLoading(true);
      const evidenceList = responseForm.evidence_urls
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

      const res = await fetch(`/api/workforce/seller-hub/claims/${selectedClaimId}/respond/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          seller_response: responseForm.seller_response.trim(),
          evidence_urls: evidenceList,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setSelectedClaimDetail(data.claim);
      loadClaims();
      loadMetrics();
      alert('Response submitted successfully.');
    } catch (err) {
      alert(err.message || 'Failed to submit response');
    } finally {
      setActionLoading(false);
    }
  };

  // 3. Escalate to Platform Admin
  const handleEscalate = async () => {
    if (!confirm('Are you sure you want to escalate this claim to the Platform Admin for arbitration?')) return;
    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/claims/${selectedClaimId}/escalate/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: escalateNotes.trim() || 'Escalated to Platform Admin for dispute review.' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setSelectedClaimDetail(data.claim);
      loadClaims();
      loadMetrics();
      alert('Claim successfully escalated to Platform Admin.');
    } catch (err) {
      alert(err.message || 'Failed to escalate claim');
    } finally {
      setActionLoading(false);
    }
  };

  // 4. Admin Arbitration Decision
  const handleAdminDecision = async (e) => {
    e.preventDefault();
    if (!adminDecisionForm.reason.trim()) {
      alert('A detailed rationale is mandatory for all admin decisions.');
      return;
    }
    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/claims/${selectedClaimId}/admin-decision/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(adminDecisionForm),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setSelectedClaimDetail(data.claim);
      loadClaims();
      loadMetrics();
      alert(`Admin decision '${adminDecisionForm.decision}' recorded successfully.`);
    } catch (err) {
      alert(err.message || 'Failed to submit admin decision');
    } finally {
      setActionLoading(false);
    }
  };

  // 5. Close Claim
  const handleCloseClaim = async () => {
    if (!confirm('Are you sure you want to close and archive this claim?')) return;
    try {
      setActionLoading(true);
      const res = await fetch(`/api/workforce/seller-hub/claims/${selectedClaimId}/close/`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ notes: closeNotes.trim() || 'Claim resolved and archived.' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data));

      setSelectedClaimDetail(data.claim);
      loadClaims();
      loadMetrics();
      alert('Claim marked as closed.');
    } catch (err) {
      alert(err.message || 'Failed to close claim');
    } finally {
      setActionLoading(false);
    }
  };

  // Status Badge Helper
  const renderStatusBadge = (st) => {
    switch (st) {
      case 'OPEN':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded-full">
            <Clock className="w-3 h-3" />
            Open
          </span>
        );
      case 'SELLER_RESPONSE_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded-full animate-pulse">
            <AlertCircle className="w-3 h-3" />
            Response Required
          </span>
        );
      case 'UNDER_REVIEW':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full">
            <Clock className="w-3 h-3" />
            Under Review
          </span>
        );
      case 'ESCALATED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200 rounded-full">
            <AlertTriangle className="w-3 h-3" />
            Escalated to Admin
          </span>
        );
      case 'APPROVED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Approved
          </span>
        );
      case 'REJECTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 rounded-full">
            <Ban className="w-3 h-3" />
            Rejected
          </span>
        );
      case 'SETTLED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-teal-50 text-teal-700 border border-teal-200 rounded-full">
            <DollarSign className="w-3 h-3" />
            Settled
          </span>
        );
      case 'CLOSED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 rounded-full">
            <Check className="w-3 h-3" />
            Closed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold bg-slate-100 text-slate-600 border border-slate-200 rounded-full">
            {st}
          </span>
        );
    }
  };

  // Type Badge Helper
  const renderTypeBadge = (tp, label) => {
    const map = {
      DAMAGED_ITEM: 'bg-orange-50 text-orange-700 border-orange-200',
      MISSING_ITEM: 'bg-rose-50 text-rose-700 border-rose-200',
      WRONG_ITEM: 'bg-purple-50 text-purple-700 border-purple-200',
      QUALITY_ISSUE: 'bg-amber-50 text-amber-700 border-amber-200',
      DELIVERY_DAMAGE: 'bg-red-50 text-red-700 border-red-200',
      SELLER_DISPUTE: 'bg-blue-50 text-blue-700 border-blue-200',
      SETTLEMENT_DISPUTE: 'bg-teal-50 text-teal-700 border-teal-200',
      OTHER: 'bg-slate-50 text-slate-700 border-slate-200',
    };
    const cls = map[tp] || 'bg-slate-50 text-slate-700 border-slate-200';
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border rounded-md ${cls}`}>
        {label || tp}
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
            <span className="p-2.5 bg-red-50 text-red-600 rounded-xl border border-red-100">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  Claims & Dispute Management
                </h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full">
                  Phase 6 Active
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Merchant protections, in-transit damage claims, delivery losses, and operational dispute arbitration
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => {
                loadClaims();
                loadMetrics();
              }}
              className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors shadow-xs"
              title="Refresh Claims"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>File Dispute / Claim</span>
            </button>
            <Link
              to="/workforce/seller-hub/dashboard"
              className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Seller Home
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Real Metrics KPI Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Open Claims</span>
                <Clock className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">
                {metrics.open_claims_count}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">Active under review</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Needs Response</span>
                <AlertCircle className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2 text-amber-600">
                {metrics.claims_requiring_response_count}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">Awaiting seller reply</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Escalated</span>
                <AlertTriangle className="w-4 h-4 text-red-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2 text-red-600">
                {metrics.escalated_claims_count}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">Admin arbitration</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Resolved</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2 text-emerald-600">
                {metrics.resolved_claims_count}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">Approved & settled</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Total Claims</span>
                <Layers className="w-4 h-4 text-slate-400" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">
                {metrics.total_claims_count}
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">All logged tickets</p>
            </div>
          </div>

          {/* Filter Tabs and Search Bar */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-5 space-y-4">
            {/* Status Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-100">
              {[
                { id: 'ALL', label: 'All Claims' },
                { id: 'OPEN', label: 'Open' },
                { id: 'NEEDS_RESPONSE', label: 'Needs Response' },
                { id: 'UNDER_REVIEW', label: 'Under Review' },
                { id: 'ESCALATED', label: 'Escalated' },
                { id: 'APPROVED', label: 'Approved' },
                { id: 'REJECTED', label: 'Rejected' },
                { id: 'SETTLED', label: 'Settled' },
                { id: 'CLOSED', label: 'Closed' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStatusFilter(tab.id)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                    statusFilter === tab.id
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search & Type Filter Toolbar */}
            <div className="flex flex-col sm:flex-row items-center gap-3">
              <div className="relative flex-1 w-full">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by Claim #, Order #, Return #, Customer, or Description..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10 transition-all"
                />
              </div>

              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="w-full sm:w-56 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10 transition-all"
              >
                <option value="">All Claim Types</option>
                <option value="DAMAGED_ITEM">Damaged Item</option>
                <option value="MISSING_ITEM">Missing / Undelivered Item</option>
                <option value="WRONG_ITEM">Wrong Item Delivered</option>
                <option value="QUALITY_ISSUE">Quality / Freshness Issue</option>
                <option value="DELIVERY_DAMAGE">Damage During Delivery</option>
                <option value="SELLER_DISPUTE">Seller Operational Dispute</option>
                <option value="SETTLEMENT_DISPUTE">Settlement / Fee Dispute</option>
                <option value="OTHER">Other Claim / Dispute</option>
              </select>
            </div>
          </div>

          {/* Claims Table Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
            {loading ? (
              <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center">
                <RefreshCw className="w-6 h-6 animate-spin text-slate-300 mb-2" />
                <span>Loading claims records from database...</span>
              </div>
            ) : error ? (
              <div className="p-12 text-center text-red-600 text-xs flex flex-col items-center justify-center">
                <AlertCircle className="w-6 h-6 text-red-500 mb-2" />
                <span>{error}</span>
              </div>
            ) : claimsList.length === 0 ? (
              /* Clean Empty State */
              <div className="p-12 text-center flex flex-col items-center justify-center">
                <div className="w-16 h-16 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-4 shadow-xs">
                  <ShieldAlert className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-base font-bold text-slate-900">No Claims Found</h3>
                <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed">
                  {searchQuery || typeFilter || statusFilter !== 'ALL'
                    ? 'No claims matched your filter criteria. Try adjusting the search query or status tab.'
                    : 'Your store currently has zero operational claims or dispute filings logged in the system.'}
                </p>
                <div className="mt-6 flex items-center gap-2.5">
                  <button
                    onClick={() => setIsCreateModalOpen(true)}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
                  >
                    File a New Dispute
                  </button>
                  <button
                    onClick={() => {
                      setStatusFilter('ALL');
                      setTypeFilter('');
                      setSearchQuery('');
                    }}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                  >
                    Reset Filters
                  </button>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <th className="px-6 py-3.5">Claim Details</th>
                      <th className="px-6 py-3.5">Related Records</th>
                      <th className="px-6 py-3.5">Claim Type</th>
                      <th className="px-6 py-3.5">Claimed Amount</th>
                      <th className="px-6 py-3.5">Created Date</th>
                      <th className="px-6 py-3.5">Status</th>
                      <th className="px-6 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
                    {claimsList.map((clm) => (
                      <tr
                        key={clm.id}
                        className="hover:bg-slate-50/75 transition-colors cursor-pointer"
                        onClick={() => openClaimDetail(clm.id)}
                      >
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-900 font-mono">
                              #{clm.claim_number}
                            </span>
                            <span className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                              {clm.description}
                            </span>
                          </div>
                        </td>

                        <td className="px-6 py-4">
                          <div className="flex flex-col gap-0.5">
                            {clm.order_number ? (
                              <span className="font-mono text-slate-800 text-[11px]">
                                Ord: #{clm.order_number}
                              </span>
                            ) : (
                              <span className="text-slate-400 text-[11px]">No order linked</span>
                            )}
                            {clm.return_number && (
                              <span className="font-mono text-amber-700 text-[11px]">
                                Ret: #{clm.return_number}
                              </span>
                            )}
                          </div>
                        </td>

                        <td className="px-6 py-4">
                          {renderTypeBadge(clm.claim_type, clm.claim_type_display)}
                        </td>

                        <td className="px-6 py-4 font-mono font-bold text-slate-900">
                          {clm.claimed_amount && parseFloat(clm.claimed_amount) > 0
                            ? `₹${parseFloat(clm.claimed_amount).toFixed(2)}`
                            : '—'}
                        </td>

                        <td className="px-6 py-4 text-slate-500 text-[11px]">
                          {new Date(clm.created_at).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })}
                        </td>

                        <td className="px-6 py-4">
                          {renderStatusBadge(clm.status)}
                        </td>

                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              openClaimDetail(clm.id);
                            }}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            <span>View</span>
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

      {/* Claim Detail & Action Sliding Drawer */}
      {isDrawerOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-2xl h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-y-auto">
            {/* Drawer Top Header */}
            <div className="p-6 border-b border-slate-200 flex items-center justify-between sticky top-0 bg-white z-10">
              <div className="flex items-center gap-3">
                <span className="p-2 bg-red-50 text-red-600 rounded-xl border border-red-100">
                  <ShieldAlert className="w-5 h-5" />
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900 font-mono">
                      #{selectedClaimDetail?.claim_number || 'Loading...'}
                    </h2>
                    {selectedClaimDetail && renderStatusBadge(selectedClaimDetail.status)}
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Filed on{' '}
                    {selectedClaimDetail?.created_at
                      ? new Date(selectedClaimDetail.created_at).toLocaleString()
                      : '—'}
                  </p>
                </div>
              </div>
              <button
                onClick={closeDrawer}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body Content */}
            {drawerLoading || !selectedClaimDetail ? (
              <div className="p-12 text-center text-slate-400 text-xs flex flex-col items-center justify-center flex-1">
                <RefreshCw className="w-6 h-6 animate-spin text-slate-300 mb-2" />
                <span>Loading claim details...</span>
              </div>
            ) : (
              <div className="p-6 space-y-6 flex-1">
                {/* 1. Quick Info Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                      Claim Type
                    </span>
                    <div className="mt-1">
                      {renderTypeBadge(
                        selectedClaimDetail.claim_type,
                        selectedClaimDetail.claim_type_display
                      )}
                    </div>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                      Claimed Amount
                    </span>
                    <p className="text-sm font-bold text-slate-900 font-mono mt-1">
                      {selectedClaimDetail.claimed_amount &&
                      parseFloat(selectedClaimDetail.claimed_amount) > 0
                        ? `₹${parseFloat(selectedClaimDetail.claimed_amount).toFixed(2)}`
                        : 'Not Specified'}
                    </p>
                  </div>

                  <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
                    <span className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                      Company
                    </span>
                    <p className="text-xs font-semibold text-slate-800 mt-1 truncate">
                      {selectedClaimDetail.company_name || 'Own Store'}
                    </p>
                  </div>
                </div>

                {/* 2. Linked Records */}
                <div className="p-4 bg-slate-50/75 border border-slate-200 rounded-xl space-y-2 text-xs">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <Layers className="w-4 h-4 text-slate-500" />
                    <span>Linked Operational Records</span>
                  </h4>
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div>
                      <span className="text-slate-400 text-[11px]">Related Order:</span>
                      <p className="font-mono font-bold text-slate-800">
                        {selectedClaimDetail.order_number
                          ? `#${selectedClaimDetail.order_number}`
                          : 'None'}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px]">Related Return:</span>
                      <p className="font-mono font-bold text-slate-800">
                        {selectedClaimDetail.return_number
                          ? `#${selectedClaimDetail.return_number}`
                          : 'None'}
                      </p>
                    </div>
                    {selectedClaimDetail.customer_name && (
                      <div className="col-span-2">
                        <span className="text-slate-400 text-[11px]">Customer Contact:</span>
                        <p className="text-slate-800 font-medium">
                          {selectedClaimDetail.customer_name}{' '}
                          {selectedClaimDetail.customer_phone
                            ? `(${selectedClaimDetail.customer_phone})`
                            : ''}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* 3. Claim Narrative / Description */}
                <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-1 text-xs">
                  <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-slate-500" />
                    <span>Claim Description</span>
                  </h4>
                  <p className="text-slate-700 leading-relaxed pt-1 whitespace-pre-wrap">
                    {selectedClaimDetail.description}
                  </p>
                </div>

                {/* 4. Photographic Proof / Evidence Gallery */}
                <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2 text-xs">
                  <h4 className="font-bold text-slate-900 flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    <span>Evidence & Attachments</span>
                  </h4>
                  {selectedClaimDetail.evidence_urls &&
                  selectedClaimDetail.evidence_urls.length > 0 ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                      {selectedClaimDetail.evidence_urls.map((url, idx) => (
                        <a
                          key={idx}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="p-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg flex items-center gap-2 text-slate-700 text-xs font-semibold truncate transition-colors group"
                        >
                          <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-slate-900 shrink-0" />
                          <span className="truncate">Evidence #{idx + 1}</span>
                        </a>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-xs italic pt-1">No file attachments or photos submitted.</p>
                  )}
                </div>

                {/* 5. Seller Response Section */}
                {selectedClaimDetail.seller_response ? (
                  <div className="p-4 bg-indigo-50/60 border border-indigo-200 rounded-xl space-y-1 text-xs">
                    <h4 className="font-bold text-indigo-950 flex items-center gap-1.5">
                      <MessageSquare className="w-4 h-4 text-indigo-600" />
                      <span>Seller Statement / Response</span>
                    </h4>
                    <p className="text-indigo-900 whitespace-pre-wrap pt-1 leading-relaxed">
                      {selectedClaimDetail.seller_response}
                    </p>
                    <p className="text-[10px] text-indigo-500 pt-1">
                      Responded by {selectedClaimDetail.seller_responded_by_name || 'Seller'} on{' '}
                      {selectedClaimDetail.seller_responded_at
                        ? new Date(selectedClaimDetail.seller_responded_at).toLocaleString()
                        : '—'}
                    </p>
                  </div>
                ) : selectedClaimDetail.status === 'SELLER_RESPONSE_REQUIRED' ||
                  selectedClaimDetail.status === 'OPEN' ||
                  selectedClaimDetail.status === 'UNDER_REVIEW' ? (
                  <form
                    onSubmit={handleSellerResponse}
                    className="p-4 bg-amber-50/50 border border-amber-200 rounded-xl space-y-3 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-amber-950 flex items-center gap-1.5">
                        <MessageSquare className="w-4 h-4 text-amber-600" />
                        <span>Submit Seller Response</span>
                      </h4>
                      {selectedClaimDetail.status === 'SELLER_RESPONSE_REQUIRED' && (
                        <span className="text-[10px] font-bold bg-amber-200 text-amber-900 px-2 py-0.5 rounded-full animate-pulse">
                          Action Required
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-amber-800">
                      Provide your operational explanation, warehouse packing proof, or courier handover confirmation.
                    </p>
                    <textarea
                      rows={3}
                      placeholder="Type your response narrative here..."
                      value={responseForm.seller_response}
                      onChange={(e) => setResponseForm({ ...responseForm, seller_response: e.target.value })}
                      required
                      className="w-full p-2.5 bg-white border border-amber-300 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                    />
                    <input
                      type="text"
                      placeholder="Optional new evidence URLs (separated by comma or newline)"
                      value={responseForm.evidence_urls}
                      onChange={(e) => setResponseForm({ ...responseForm, evidence_urls: e.target.value })}
                      className="w-full p-2 bg-white border border-amber-300 rounded-lg text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500/20"
                    />
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white rounded-lg font-semibold text-xs transition-colors flex items-center gap-1.5 shadow-xs"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{actionLoading ? 'Submitting...' : 'Submit Statement'}</span>
                    </button>
                  </form>
                ) : null}

                {/* 6. Admin Decision / Arbitration Panel */}
                {selectedClaimDetail.admin_decision &&
                selectedClaimDetail.admin_decision !== 'PENDING' ? (
                  <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-xl space-y-1 text-xs">
                    <h4 className="font-bold text-purple-950 flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-purple-600" />
                      <span>Platform Admin Decision ({selectedClaimDetail.admin_decision})</span>
                    </h4>
                    <p className="text-purple-900 whitespace-pre-wrap pt-1 leading-relaxed">
                      {selectedClaimDetail.admin_decision_reason || 'Decision applied without extra notes.'}
                    </p>
                    <p className="text-[10px] text-purple-500 pt-1">
                      Arbitrated by {selectedClaimDetail.admin_decided_by_name || 'Admin'} on{' '}
                      {selectedClaimDetail.admin_decided_at
                        ? new Date(selectedClaimDetail.admin_decided_at).toLocaleString()
                        : '—'}
                    </p>
                  </div>
                ) : null}

                {/* Admin Action Controls (Visible to Superadmin / Platform Admin) */}
                {isSuperAdmin &&
                selectedClaimDetail.status !== 'CLOSED' &&
                selectedClaimDetail.status !== 'SETTLED' ? (
                  <form
                    onSubmit={handleAdminDecision}
                    className="p-4 bg-slate-900 text-white rounded-xl space-y-3 text-xs shadow-md"
                  >
                    <h4 className="font-bold text-white text-xs flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span>Platform Admin Arbitration Decision</span>
                    </h4>
                    <p className="text-[11px] text-slate-300">
                      Select decision outcome. A mandatory documented rationale is required.
                    </p>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                      {[
                        { id: 'APPROVE', label: 'Approve Claim', color: 'bg-emerald-600' },
                        { id: 'REJECT', label: 'Reject Claim', color: 'bg-rose-600' },
                        { id: 'REQUEST_SELLER_RESPONSE', label: 'Req. Response', color: 'bg-amber-600' },
                        { id: 'SETTLE', label: 'Mark Settled', color: 'bg-teal-600' },
                      ].map((btn) => (
                        <button
                          key={btn.id}
                          type="button"
                          onClick={() => setAdminDecisionForm({ ...adminDecisionForm, decision: btn.id })}
                          className={`py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
                            adminDecisionForm.decision === btn.id
                              ? `${btn.color} text-white ring-2 ring-white/50 shadow-xs`
                              : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                          }`}
                        >
                          {btn.label}
                        </button>
                      ))}
                    </div>
                    <textarea
                      rows={2}
                      placeholder="Enter mandatory arbitration decision rationale..."
                      value={adminDecisionForm.reason}
                      onChange={(e) => setAdminDecisionForm({ ...adminDecisionForm, reason: e.target.value })}
                      required
                      className="w-full p-2.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                    />
                    <button
                      type="submit"
                      disabled={actionLoading}
                      className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-bold rounded-lg text-xs transition-colors shadow-xs"
                    >
                      {actionLoading ? 'Recording Decision...' : 'Apply Admin Decision'}
                    </button>
                  </form>
                ) : null}

                {/* 7. Escalation & Case Closure Actions */}
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                  {selectedClaimDetail.status !== 'ESCALATED' &&
                  selectedClaimDetail.status !== 'CLOSED' &&
                  selectedClaimDetail.status !== 'SETTLED' ? (
                    <button
                      onClick={handleEscalate}
                      disabled={actionLoading}
                      className="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded-lg font-semibold text-xs transition-colors flex items-center gap-1.5"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Escalate to Admin</span>
                    </button>
                  ) : null}

                  {selectedClaimDetail.status !== 'CLOSED' ? (
                    <button
                      onClick={handleCloseClaim}
                      disabled={actionLoading}
                      className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold text-xs transition-colors flex items-center gap-1.5 ml-auto"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Close Claim</span>
                    </button>
                  ) : null}
                </div>

                {/* 8. Chronological Audit Trail Timeline */}
                <div className="space-y-3 pt-4 border-t border-slate-200">
                  <h4 className="font-bold text-slate-900 text-xs flex items-center gap-1.5">
                    <Clock className="w-4 h-4 text-slate-500" />
                    <span>Immutable Audit History</span>
                  </h4>
                  {selectedClaimDetail.audit_logs && selectedClaimDetail.audit_logs.length > 0 ? (
                    <div className="space-y-2.5">
                      {selectedClaimDetail.audit_logs.map((log) => (
                        <div
                          key={log.id}
                          className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between text-slate-500 text-[11px]">
                            <span className="font-semibold text-slate-800">
                              {log.action}
                            </span>
                            <span>{new Date(log.created_at).toLocaleString()}</span>
                          </div>
                          {log.from_status || log.to_status ? (
                            <div className="text-[10px] text-slate-400 font-mono">
                              Status: {log.from_status || 'INITIAL'} ➔ {log.to_status}
                            </div>
                          ) : null}
                          {log.notes && (
                            <p className="text-slate-600 text-xs italic whitespace-pre-wrap pt-0.5">
                              "{log.notes}"
                            </p>
                          )}
                          <div className="text-[10px] text-slate-400 pt-0.5">
                            Actor: {log.actor_name}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-xs italic">No prior audit records.</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* File Dispute / Claim Creation Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="p-6 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="p-2 bg-red-50 text-red-600 rounded-xl">
                  <ShieldAlert className="w-5 h-5" />
                </span>
                <div>
                  <h3 className="text-base font-bold text-slate-900">File Operational Claim / Dispute</h3>
                  <p className="text-xs text-slate-500">Record in-transit damage or order delivery loss</p>
                </div>
              </div>
              <button
                onClick={() => setIsCreateModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateClaim} className="p-6 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Claim Type</label>
                <select
                  value={createForm.claim_type}
                  onChange={(e) => setCreateForm({ ...createForm, claim_type: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 font-medium focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                >
                  <option value="DAMAGED_ITEM">Damaged Item</option>
                  <option value="MISSING_ITEM">Missing / Undelivered Item</option>
                  <option value="WRONG_ITEM">Wrong Item Delivered</option>
                  <option value="QUALITY_ISSUE">Quality / Freshness Issue</option>
                  <option value="DELIVERY_DAMAGE">Damage During Delivery / In-Transit</option>
                  <option value="SELLER_DISPUTE">Seller Operational Dispute</option>
                  <option value="SETTLEMENT_DISPUTE">Settlement / Fee Dispute</option>
                  <option value="OTHER">Other Claim / Dispute</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Related Order ID (Optional)</label>
                  <input
                    type="number"
                    placeholder="e.g. 101"
                    value={createForm.order_id}
                    onChange={(e) => setCreateForm({ ...createForm, order_id: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Related Return ID (Optional)</label>
                  <input
                    type="number"
                    placeholder="e.g. 5"
                    value={createForm.return_id}
                    onChange={(e) => setCreateForm({ ...createForm, return_id: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Claim Valuation / Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={createForm.claimed_amount}
                  onChange={(e) => setCreateForm({ ...createForm, claimed_amount: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10 font-mono"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Detailed Incident Description *</label>
                <textarea
                  rows={3}
                  placeholder="Describe the defect, transit damage, or reason for claim dispute..."
                  value={createForm.description}
                  onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                  required
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Evidence URLs (Photos/Docs)</label>
                <textarea
                  rows={2}
                  placeholder="Paste URL references (one per line)..."
                  value={createForm.evidence_urls}
                  onChange={(e) => setCreateForm({ ...createForm, evidence_urls: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/10 font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-semibold text-xs transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-xl font-bold text-xs transition-colors shadow-xs"
                >
                  {actionLoading ? 'Creating Claim...' : 'Submit Claim'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default SellerClaimsPage;
