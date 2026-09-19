import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
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
  Briefcase,
} from 'lucide-react';
import {
  apiGetQuotes,
  apiGetQuoteDetail,
  apiReviseQuote,
  apiGetWorkforceJobs,
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
  const [searchParams] = useSearchParams();
  const urlJobId = searchParams.get('job_id');

  const [activeTab, setActiveTab] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [quotes, setQuotes] = useState([]);
  const [activeJobs, setActiveJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected quote for modal
  const [selectedQuoteId, setSelectedQuoteId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showJobPicker, setShowJobPicker] = useState(false);

  const fetchQuotes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [quotesData, jobsData] = await Promise.all([
        apiGetQuotes({
          tab: activeTab !== 'all' ? activeTab : undefined,
          search: searchQuery || undefined,
        }),
        apiGetWorkforceJobs('all').catch(() => []),
      ]);
      setQuotes(quotesData || []);
      const activeList = (jobsData || []).filter((j) =>
        ['assigned', 'received', 'on_the_way', 'en_route', 'arrived', 'in_progress'].includes(
          (j.status || '').toLowerCase()
        )
      );
      setActiveJobs(activeList);

      // If URL specified a job_id, auto-open quote builder for that job
      if (urlJobId && !selectedJob) {
        const matchingJob = (jobsData || []).find((j) => String(j.id) === String(urlJobId) || String(j.request_id) === String(urlJobId));
        if (matchingJob) {
          setSelectedQuoteId(null);
          setSelectedJob(matchingJob);
          setIsModalOpen(true);
        }
      }
    } catch (err) {
      console.error('Failed to load estimates:', err);
      setError(err.message || 'Failed to load quotations list.');
    } finally {
      setLoading(false);
    }
  }, [activeTab, searchQuery, urlJobId, selectedJob]);

  useEffect(() => {
    fetchQuotes();
  }, [fetchQuotes]);

  const handleOpenQuote = (quote) => {
    setSelectedQuoteId(quote.id);
    setSelectedJob(quote.job_details || { id: quote.job_id, issue_title: quote.service_name, customer_name: quote.customer_name });
    setIsModalOpen(true);
  };

  const handleCreateNewQuote = (jobToUse = null) => {
    if (jobToUse) {
      setSelectedQuoteId(null);
      setSelectedJob(jobToUse);
      setIsModalOpen(true);
      setShowJobPicker(false);
      return;
    }

    if (activeJobs.length === 1) {
      setSelectedQuoteId(null);
      setSelectedJob(activeJobs[0]);
      setIsModalOpen(true);
    } else if (activeJobs.length > 1) {
      setShowJobPicker(true);
    } else {
      alert('No active assigned jobs available to create a quotation for.');
    }
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
  const draftCount = quotes.filter((q) => q.status === 'DRAFT' && !(q.customer_decision === 'CHANGES_REQUESTED' || q.quote_version > 1)).length;
  const changesCount = quotes.filter((q) => q.status === 'CHANGES_REQUESTED' || q.customer_decision === 'CHANGES_REQUESTED' || (q.quote_version > 1 && q.status === 'DRAFT')).length;
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

        <div className="flex items-center gap-2">
          {activeJobs.length > 0 && (
            <button
              onClick={() => handleCreateNewQuote()}
              className="inline-flex items-center gap-2 px-4 py-2 min-h-[38px] text-xs font-bold rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Create Quote</span>
            </button>
          )}

          <button
            onClick={fetchQuotes}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 min-h-[38px] text-xs font-bold rounded-lg border border-zinc-300 bg-white text-zinc-800 hover:bg-zinc-50 active:bg-zinc-100 shadow-xs transition-all cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-zinc-500 font-bold">Total Quotations</span>
          <p className="text-xl font-extrabold text-zinc-950 font-mono mt-1">{totalCount}</p>
        </div>
        <div className="p-4 rounded-md border border-zinc-200/90 bg-white shadow-card space-y-1">
          <span className="text-xs text-amber-900 font-bold">Changes / Re-Quotes</span>
          <p className="text-xl font-extrabold text-amber-700 font-mono mt-1">{changesCount}</p>
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

      {/* Active Jobs Ready for Quotation Banner */}
      {activeJobs.length > 0 && (
        <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-blue-700" />
              <h3 className="text-xs font-bold text-blue-950 uppercase tracking-wide">
                Active On-Site Jobs Ready for Quotation ({activeJobs.length})
              </h3>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {activeJobs.map((job) => (
              <div
                key={job.id}
                className="p-3.5 bg-white rounded-lg border border-blue-200 shadow-xs flex items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-zinc-900">{job.issue_title || job.service_category}</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                      #{job.request_id || job.id}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    Customer: <span className="font-semibold text-zinc-700">{job.customer_name || 'Customer'}</span>
                  </p>
                </div>
                <button
                  onClick={() => handleCreateNewQuote(job)}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-all flex items-center gap-1 shrink-0 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Build Quote</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

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
        <div className="py-16 text-center border border-zinc-200/90 rounded-md bg-white shadow-card space-y-3">
          <FileText className="w-10 h-10 text-zinc-300 mx-auto" />
          <div>
            <h3 className="text-sm font-bold text-zinc-900">No Quotations Drafted Yet</h3>
            <p className="text-xs text-zinc-500 max-w-sm mx-auto mt-1 leading-relaxed">
              You have {activeJobs.length} active on-site consultation job(s). Click below to begin drafting line items and pricing for the customer.
            </p>
          </div>
          {activeJobs.length > 0 && (
            <button
              onClick={() => handleCreateNewQuote(activeJobs[0])}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs rounded-lg transition-all shadow-xs cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Draft Quotation for {activeJobs[0].issue_title || activeJobs[0].request_id}</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quotes.map((quote) => {
            const isAccepted = quote.status === 'CUSTOMER_ACCEPTED' || quote.status === 'CONVERTED';
            const isPending = quote.status === 'SENT_TO_CUSTOMER';
            const isChangesRequested = quote.status === 'CHANGES_REQUESTED' || quote.customer_decision === 'CHANGES_REQUESTED' || (quote.quote_version > 1 && quote.status === 'DRAFT');
            const isDraft = quote.status === 'DRAFT' && !isChangesRequested;

            return (
              <div
                key={quote.id}
                onClick={() => handleOpenQuote(quote)}
                className={`p-5 rounded-md border bg-white hover:shadow-card transition-all cursor-pointer flex flex-col justify-between space-y-4 shadow-card ${
                  isChangesRequested ? 'border-amber-300 ring-1 ring-amber-200' : 'border-zinc-200/90 hover:border-zinc-300'
                }`}
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
                        {isChangesRequested && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
                            Re-Quote Requested
                          </span>
                        )}
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
                      {isChangesRequested ? 'RE-QUOTE REQUESTED' : quote.status.replace(/_/g, ' ')}
                    </span>
                  </div>

                  {/* Customer Revision Request Notes */}
                  {(quote.customer_notes || (quote.description && quote.description.includes('Revision'))) && (
                    <div className="mt-3 p-2.5 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2 text-[11px] text-amber-950">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold text-amber-900 block">Customer Feedback / Note:</span>
                        <span className="text-amber-900 leading-snug">
                          {quote.customer_notes || quote.description}
                        </span>
                      </div>
                    </div>
                  )}

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
                    {quote.status === 'CHANGES_REQUESTED' && (
                      <button
                        onClick={(e) => handleRevise(quote, e)}
                        className="px-2.5 py-1.5 text-xs font-semibold rounded-lg border border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 hover:bg-purple-100 flex items-center gap-1"
                      >
                        <RotateCcw className="w-3 h-3" />
                        Revise (V{quote.quote_version + 1})
                      </button>
                    )}

                    <button className="inline-flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 hover:bg-blue-100">
                      {isChangesRequested ? `Edit Re-Quote (v${quote.quote_version})` : isDraft ? 'Continue Draft' : 'View Quote'}
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
