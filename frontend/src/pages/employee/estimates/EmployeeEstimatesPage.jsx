import React, { useState, useEffect, useCallback } from 'react';
import {
  Calculator,
  Search,
  Filter,
  Plus,
  ArrowRight,
  Clock,
  CheckCircle2,
  AlertTriangle,
  FileText,
  RotateCcw,
  Sparkles,
  ExternalLink,
  ChevronRight,
  RefreshCw,
  Send,
  Building,
} from 'lucide-react';
import {
  apiGetQuotes,
  apiGetQuoteDetail,
  apiReviseQuote,
} from '../../../api/workforceService.js';
import { AppShell } from '../../../components/common/AppShell.jsx';
import QuotationBuilderModal from '../../../components/estimates/QuotationBuilderModal.jsx';

const STATUS_TABS = [
  { id: 'all', label: 'All Quotes' },
  { id: 'draft', label: 'Drafts' },
  { id: 'pending_review', label: 'Pending Review' },
  { id: 'sent', label: 'Sent to Customer' },
  { id: 'accepted', label: 'Accepted' },
  { id: 'changes_requested', label: 'Changes Requested' },
  { id: 'declined', label: 'Declined' },
  { id: 'expired', label: 'Expired' },
  { id: 'converted', label: 'Converted' },
];

export default function EmployeeEstimatesPage() {
  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected quote for modal
  const [selectedQuoteId, setSelectedQuoteId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);

  const fetchQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGetQuotes({
        tab: activeTab !== 'all' ? activeTab : undefined,
        search: searchQuery || undefined,
      });
      setQuotes(data || []);
    } catch (err) {
      console.error('Failed to load estimates:', err);
      setError(err.message || 'Failed to load quotations list.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, searchQuery]);

  useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  const handleOpenQuote = (quote) => {
    setSelectedQuoteId(quote.id);
    setSelectedJob(quote.job_details || { id: quote.job_id, issue_title: quote.service_name, customer_name: quote.customer_name });
    setIsModalOpen(true);
  };

  const handleRevise = async (quote, e) => {
    e.stopPropagation();
    try {
      const revised = await apiReviseQuote(quote.id, 'Employee initiated revision');
      handleOpenQuote(revised);
      fetchQuotes();
    } catch (err) {
      alert(err.message || 'Failed to revise quotation.');
    }
  };

  // Metrics summary
  const totalCount = quotes.length;
  const draftCount = quotes.filter((q) => q.status === 'DRAFT').length;
  const sentCount = quotes.filter((q) => q.status === 'SENT_TO_CUSTOMER').length;
  const acceptedCount = quotes.filter(
    (q) => q.status === 'CUSTOMER_ACCEPTED' || q.status === 'CONVERTED'
  ).length;

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/employee/dashboard' }, { label: 'Estimates' }]}>
      <div className="max-w-6xl mx-auto space-y-6 text-xs">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-zinc-200/90 p-5 rounded-md shadow-card">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-200 text-zinc-900 flex items-center justify-center shadow-xs">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-bold text-zinc-950 tracking-tight">
                Estimates & Quotes
              </h1>
              <p className="text-xs text-zinc-500 mt-0.5">
                Create quotation proposals, manage rate-card items, and track customer approvals.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchQuotes}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 min-h-[38px] text-xs font-bold rounded-lg border border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50 active:bg-zinc-100 shadow-xs transition-all cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-zinc-500 font-bold">Total Quotations</span>
          <p className="text-xl font-extrabold text-zinc-950 font-mono mt-1">{totalCount}</p>
        </div>
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-amber-900 font-bold">Drafts in Progress</span>
          <p className="text-xl font-extrabold text-zinc-950 font-mono mt-1">{draftCount}</p>
        </div>
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-zinc-700 font-bold">Sent to Customers</span>
          <p className="text-xl font-extrabold text-zinc-950 font-mono mt-1">{sentCount}</p>
        </div>
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-emerald-900 font-bold">Approved / Converted</span>
          <p className="text-xl font-extrabold text-emerald-800 font-mono mt-1">{acceptedCount}</p>
        </div>
      </div>

      {/* Search & Tabs */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by quote number (e.g. QT-0001), service name, or customer..."
            className="w-full pl-10 pr-4 py-2 text-xs rounded-lg border border-zinc-300 bg-white text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs min-h-[38px]"
          />
        </div>

        {/* Tab pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          {STATUS_TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                  isActive
                    ? 'bg-slate-800 text-white shadow-xs'
                    : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Quotes List */}
      {loading ? (
        <div className="py-20 text-center text-zinc-500 text-xs">
          <div className="w-7 h-7 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          Loading quotations...
        </div>
      ) : error ? (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-900 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-700" />
          <span>{error}</span>
        </div>
      ) : quotes.length === 0 ? (
        <div className="py-16 text-center border border-zinc-200/90 rounded-md bg-white shadow-card">
          <FileText className="w-10 h-10 text-zinc-300 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-zinc-900">No Quotations Found</h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto mt-1 leading-relaxed">
            Estimation jobs from Home & Active Jobs will appear here once initial inspection and quote drafting begins.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotes.map((quote) => {
            const isAccepted = quote.status === 'CUSTOMER_ACCEPTED' || quote.status === 'CONVERTED';
            const isPending = quote.status === 'SENT_TO_CUSTOMER';
            const isDraft = quote.status === 'DRAFT';
            const isChangesRequested = quote.status === 'CHANGES_REQUESTED';

            return (
              <div
                key={quote.id}
                onClick={() => handleOpenQuote(quote)}
                className="p-5 rounded-md border border-zinc-200/90 bg-white hover:border-zinc-300 hover:shadow-card transition-all cursor-pointer flex flex-col justify-between space-y-4 shadow-card"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-zinc-950 font-mono">
                          {quote.quote_number}
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-zinc-100 text-zinc-700 border border-zinc-200">
                          v{quote.quote_version}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-zinc-950 mt-1">
                        {quote.service_name || quote.title}
                      </h3>
                      <p className="text-xs text-zinc-500 mt-0.5">
                        Customer: {quote.customer_name || 'Customer'}
                      </p>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                        isAccepted
                          ? 'bg-emerald-50 text-emerald-900 border border-emerald-200'
                          : isPending
                          ? 'bg-zinc-100 text-zinc-800 border border-zinc-200'
                          : isChangesRequested
                          ? 'bg-amber-50 text-amber-900 border border-amber-200'
                          : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
                      }`}
                    >
                      {quote.status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {quote.structural_impact && quote.structural_impact !== 'NONE' && (
                    <div className="mt-3 p-2.5 rounded-lg bg-amber-50 border border-amber-200 flex items-center gap-2 text-[11px] text-amber-900 font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />

                      <span>
                        Structural Gate: {quote.structural_impact.replace(/_/g, ' ')}
                        {quote.is_structurally_cleared ? ' (Cleared ✓)' : ' (Clearance Required)'}
                      </span>
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">Total Amount</span>
                    <span className="text-base font-extrabold text-gray-900 dark:text-gray-100">
                      ₹{parseFloat(quote.net_payable || quote.total_amount || 0).toLocaleString()}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {isChangesRequested && (
                      <button
                        onClick={(e) => handleRevise(quote, e)}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 hover:bg-purple-100 flex items-center gap-1"
                      >
                        <RotateCcw className="w-3 h-3" />
                        Revise (V{quote.quote_version + 1})
                      </button>
                    )}

                    <button className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 hover:bg-blue-100">
                      {isDraft ? 'Continue Draft' : 'View Quote'}
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

        {/* Quotation Builder Modal */}
        {isModalOpen && (
          <QuotationBuilderModal
            job={selectedJob}
            quoteId={selectedQuoteId}
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onQuoteSaved={() => {
              fetchQuotes();
            }}
          />
        )}
      </div>
    </AppShell>
  );
}
