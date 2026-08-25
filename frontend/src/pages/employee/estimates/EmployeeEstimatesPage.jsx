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
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-xl bg-blue-600/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <Calculator className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Estimates & Commercial Quotations
              </h1>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                Manage commercial quotation proposals, rate-card line items, and customer decisions.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchQuotes}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-xl border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700/60 shadow-sm"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm">
          <span className="text-xs text-gray-500 font-medium">Total Quotations</span>
          <p className="text-xl font-extrabold text-gray-900 dark:text-gray-100 mt-1">{totalCount}</p>
        </div>
        <div className="p-4 rounded-2xl border border-amber-200/60 dark:border-amber-900/40 bg-amber-50/40 dark:bg-amber-950/20 shadow-sm">
          <span className="text-xs text-amber-700 dark:text-amber-300 font-medium">Drafts in Progress</span>
          <p className="text-xl font-extrabold text-amber-900 dark:text-amber-200 mt-1">{draftCount}</p>
        </div>
        <div className="p-4 rounded-2xl border border-blue-200/60 dark:border-blue-900/40 bg-blue-50/40 dark:bg-blue-950/20 shadow-sm">
          <span className="text-xs text-blue-700 dark:text-blue-300 font-medium">Sent to Customers</span>
          <p className="text-xl font-extrabold text-blue-900 dark:text-blue-200 mt-1">{sentCount}</p>
        </div>
        <div className="p-4 rounded-2xl border border-green-200/60 dark:border-green-900/40 bg-green-50/40 dark:bg-green-950/20 shadow-sm">
          <span className="text-xs text-green-700 dark:text-green-300 font-medium">Approved / Converted</span>
          <p className="text-xl font-extrabold text-green-900 dark:text-green-200 mt-1">{acceptedCount}</p>
        </div>
      </div>

      {/* Search & Tabs */}
      <div className="space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by quote number (e.g. QT-0001), service name, or customer..."
            className="w-full pl-10 pr-4 py-2.5 text-xs rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          />
        </div>

        {/* Tab pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {STATUS_TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                    : 'bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-800'
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
        <div className="py-20 text-center text-gray-500 text-xs">
          <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          Loading quotations...
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 text-xs text-red-700 dark:text-red-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      ) : quotes.length === 0 ? (
        <div className="py-16 text-center border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-2xl bg-gray-50/50 dark:bg-gray-900/50">
          <FileText className="w-10 h-10 text-gray-400 mx-auto mb-3 opacity-50" />
          <h3 className="text-sm font-bold text-gray-800 dark:text-gray-200">No Quotations Found</h3>
          <p className="text-xs text-gray-500 max-w-sm mx-auto mt-1">
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
                className="p-5 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-blue-300 dark:hover:border-blue-700/60 hover:shadow-md transition-all cursor-pointer flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-blue-600 dark:text-blue-400">
                          {quote.quote_number}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                          v{quote.quote_version}
                        </span>
                      </div>
                      <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 mt-1">
                        {quote.service_name || quote.title}
                      </h3>
                      <p className="text-xs text-gray-500 mt-0.5">
                        Customer: {quote.customer_name || 'Customer'}
                      </p>
                    </div>

                    <span
                      className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                        isAccepted
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
                          : isPending
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                          : isChangesRequested
                          ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
                      }`}
                    >
                      {quote.status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {quote.structural_impact && quote.structural_impact !== 'NONE' && (
                    <div className="mt-3 p-2 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/40 flex items-center gap-2 text-[11px] text-amber-800 dark:text-amber-300">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
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
  );
}
