import React, { useEffect, useState, useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { apiGetAdminSellerApplications } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Pagination } from '../../components/enterprise/Pagination.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  Store,
  ArrowRight,
  User,
  Search,
  Building2,
  Phone,
  Mail,
  ShieldCheck,
  FileText,
  Clock,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export function AdminSellerApplicationsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialStatus = searchParams.get('status') || 'all';
  const initialQuery = searchParams.get('q') || '';

  const [applications, setApplications] = useState([]);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [searchQuery, setSearchQuery] = useState(initialQuery);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchApplications = async () => {
    try {
      setIsLoading(true);
      setError('');
      const apiStatus = statusFilter === 'all' ? '' : statusFilter;
      const data = await apiGetAdminSellerApplications(apiStatus);
      setApplications(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load seller applications.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter]);

  const filteredData = useMemo(() => {
    return applications.filter((app) => {
      const term = searchQuery.toLowerCase().trim();
      if (!term) return true;
      const storeName = (app.store_name || '').toLowerCase();
      const companyName = (app.company_name || '').toLowerCase();
      const ownerName = app.owner ? `${app.owner.first_name || ''} ${app.owner.last_name || ''}`.toLowerCase() : '';
      const email = app.owner ? (app.owner.email || '').toLowerCase() : '';
      const phone = app.owner ? (app.owner.mobile_number || '').toLowerCase() : '';
      const fssai = (app.fssai_license_number || '').toLowerCase();
      const gst = (app.gst_number || '').toLowerCase();

      return (
        storeName.includes(term) ||
        companyName.includes(term) ||
        ownerName.includes(term) ||
        email.includes(term) ||
        phone.includes(term) ||
        fssai.includes(term) ||
        gst.includes(term)
      );
    });
  }, [applications, searchQuery]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(filteredData.length / pageSize));
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  // Status counts
  const counts = useMemo(() => {
    let pending = 0;
    let approved = 0;
    let rejected = 0;
    let corrections = 0;

    applications.forEach((app) => {
      const s = (app.registration_status || '').toLowerCase();
      if (s === 'submitted' || s === 'under_review' || s === 'pending') pending++;
      else if (s === 'approved') approved++;
      else if (s === 'rejected') rejected++;
      else if (s === 'correction_required') corrections++;
    });

    return { total: applications.length, pending, approved, rejected, corrections };
  }, [applications]);

  return (
    <AppShell breadcrumbs={[{ label: 'Platform Governance' }, { label: 'Seller Applications' }]}>
      <div className="space-y-5">
        <PageHeader
          title="Grocery Seller Applications"
          description="Review, verify regulatory documents, and approve Sevo Seller Hub merchant dossiers."
        />

        {/* ── UNIFIED APPLICATION TABS ── */}
        <div className="flex items-center gap-2 border-b border-zinc-200/80 pb-3 text-xs">
          <Link
            to="/workforce/admin/applications"
            className="px-3.5 py-2 rounded-lg font-bold text-xs transition-all flex items-center gap-1.5 select-none bg-zinc-100 text-zinc-700 hover:bg-zinc-200 cursor-pointer"
          >
            <User className="w-3.5 h-3.5 text-zinc-600" />
            <span>Technician Applications</span>
          </Link>
          <button
            type="button"
            className="px-3.5 py-2 rounded-lg font-bold text-xs transition-all flex items-center gap-1.5 select-none bg-zinc-900 text-white shadow-xs"
          >
            <Store className="w-3.5 h-3.5 text-white" />
            <span>Seller Hub Applications ({applications.length})</span>
          </button>
          <Link
            to="/workforce/admin/applications"
            className="px-3.5 py-2 rounded-lg font-bold text-xs transition-all flex items-center gap-1.5 select-none bg-zinc-100 text-zinc-700 hover:bg-zinc-200 cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5 text-zinc-600" />
            <span>Profile Change Requests</span>
          </Link>
        </div>

        {/* ── METRIC SUMMARY CARDS ── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div
            onClick={() => {
              setStatusFilter('all');
              setCurrentPage(1);
            }}
            className={`p-3.5 rounded-md border bg-white cursor-pointer transition-all shadow-card ${
              statusFilter === 'all' ? 'border-zinc-900 ring-1 ring-zinc-900' : 'border-zinc-200/90 hover:border-zinc-300'
            }`}
          >
            <div className="flex items-center justify-between text-zinc-500">
              <span className="font-semibold uppercase tracking-wider text-[10px]">Total Sellers</span>
              <Store className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-zinc-950 mt-1">{counts.total}</div>
          </div>

          <div
            onClick={() => {
              setStatusFilter('pending');
              setCurrentPage(1);
            }}
            className={`p-3.5 rounded-md border bg-white cursor-pointer transition-all shadow-card ${
              statusFilter === 'pending' ? 'border-amber-600 ring-1 ring-amber-600' : 'border-zinc-200/90 hover:border-zinc-300'
            }`}
          >
            <div className="flex items-center justify-between text-amber-700">
              <span className="font-semibold uppercase tracking-wider text-[10px]">Under Review</span>
              <Clock className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-amber-800 mt-1">{counts.pending}</div>
          </div>

          <div
            onClick={() => {
              setStatusFilter('approved');
              setCurrentPage(1);
            }}
            className={`p-3.5 rounded-md border bg-white cursor-pointer transition-all shadow-card ${
              statusFilter === 'approved' ? 'border-emerald-600 ring-1 ring-emerald-600' : 'border-zinc-200/90 hover:border-zinc-300'
            }`}
          >
            <div className="flex items-center justify-between text-emerald-700">
              <span className="font-semibold uppercase tracking-wider text-[10px]">Approved Active</span>
              <CheckCircle2 className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-emerald-800 mt-1">{counts.approved}</div>
          </div>

          <div
            onClick={() => {
              setStatusFilter('correction_required');
              setCurrentPage(1);
            }}
            className={`p-3.5 rounded-md border bg-white cursor-pointer transition-all shadow-card ${
              statusFilter === 'correction_required' ? 'border-rose-600 ring-1 ring-rose-600' : 'border-zinc-200/90 hover:border-zinc-300'
            }`}
          >
            <div className="flex items-center justify-between text-rose-700">
              <span className="font-semibold uppercase tracking-wider text-[10px]">Correction Needed</span>
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
            <div className="text-xl font-bold text-rose-800 mt-1">{counts.corrections}</div>
          </div>
        </div>

        {/* ── FILTERS BAR ── */}
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white p-3.5 rounded-md border border-zinc-200/90 shadow-card text-xs">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search store, owner, FSSAI..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-9 pr-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg text-xs text-zinc-800 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Under Review</option>
              <option value="approved">Approved</option>
              <option value="correction_required">Correction Required</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>

        {/* ── TABLE / EMPTY STATE ── */}
        {isLoading ? (
          <LoadingState message="Loading seller application queue..." />
        ) : error ? (
          <ErrorState title="Failed to load applications" message={error} onRetry={fetchApplications} />
        ) : filteredData.length === 0 ? (
          <div className="bg-white rounded-md border border-zinc-200/90 shadow-card p-12 text-center">
            <Store className="w-12 h-12 text-zinc-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-zinc-900">No Seller Applications Found</h3>
            <p className="text-xs text-zinc-500 max-w-md mx-auto mt-1 leading-relaxed">
              {searchQuery || statusFilter !== 'all'
                ? 'No seller applications match your current filters. Try resetting search criteria.'
                : 'There are currently zero seller applications lodged on the platform.'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-md border border-zinc-200/90 shadow-card overflow-hidden text-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-zinc-600">
                <thead className="bg-zinc-50/80 text-[11px] font-bold text-zinc-500 uppercase tracking-wider border-b border-zinc-200">
                  <tr>
                    <th className="px-5 py-3.5">Store / Entity</th>
                    <th className="px-5 py-3.5">Owner / Contact</th>
                    <th className="px-5 py-3.5">Regulatory Compliance</th>
                    <th className="px-5 py-3.5">Categories</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {paginatedData.map((row) => {
                    const owner = row.owner || {};
                    const docs = row.documents_status || {};
                    const docCount = Object.keys(docs).length;
                    const approvedDocs = Object.values(docs).filter((d) => d.status === 'approved').length;
                    const cats = row.categories_status || [];

                    return (
                      <tr
                        key={row.id}
                        onClick={() => navigate(`/workforce/admin/seller-applications/${row.id}`)}
                        className="hover:bg-zinc-50/80 transition-colors cursor-pointer"
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-800 border border-zinc-200 flex items-center justify-center font-bold text-xs shrink-0">
                              <Store className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="font-bold text-zinc-950 flex items-center gap-1.5">
                                <span>{row.store_name}</span>
                                <span className="font-mono text-[10px] text-zinc-400 font-normal">#SEL-{row.id}</span>
                              </div>
                              <div className="text-[11px] text-zinc-500 flex items-center gap-1">
                                <Building2 className="w-3 h-3 text-zinc-400 shrink-0" />
                                <span>{row.company_name}</span>
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <div className="font-semibold text-zinc-900 flex items-center gap-1.5">
                            <User className="w-3.5 h-3.5 text-zinc-400" />
                            <span>{owner.first_name ? `${owner.first_name} ${owner.last_name || ''}` : 'Store Manager'}</span>
                          </div>
                          <div className="text-[11px] text-zinc-500 flex items-center gap-1 mt-0.5">
                            <Phone className="w-3 h-3 text-zinc-400" />
                            <span>{owner.mobile_number || 'No phone'}</span>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1 text-zinc-700">
                              <ShieldCheck className="w-3.5 h-3.5 text-zinc-500" />
                              <span className="font-mono text-[11px] font-semibold">
                                FSSAI: {row.fssai_license_number || 'Pending'}
                              </span>
                            </div>
                            <div className="text-[10px] text-zinc-500 flex items-center gap-1">
                              <FileText className="w-3 h-3 text-zinc-400" />
                              <span>{docCount > 0 ? `${approvedDocs}/${docCount} Docs Approved` : 'No files lodged'}</span>
                            </div>
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          {cats.length > 0 ? (
                            <div className="flex flex-wrap gap-1 max-w-[180px]">
                              {cats.slice(0, 2).map((c, i) => (
                                <span
                                  key={i}
                                  className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-100 text-zinc-700 border border-zinc-200"
                                >
                                  {c.name || c.id}
                                </span>
                              ))}
                              {cats.length > 2 && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-zinc-100 text-zinc-500">
                                  +{cats.length - 2}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-zinc-400 text-[11px]">General</span>
                          )}
                        </td>

                        <td className="px-5 py-4">
                          <StatusBadge status={row.registration_status || 'not_started'} />
                        </td>

                        <td className="px-5 py-4 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/workforce/admin/seller-applications/${row.id}`);
                            }}
                            className="px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-900 font-bold text-xs shadow-xs transition-all cursor-pointer"
                          >
                            Review
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3.5 border-t border-zinc-200 bg-zinc-50/50">
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={setCurrentPage}
                totalItems={filteredData.length}
                pageSize={pageSize}
              />
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default AdminSellerApplicationsPage;
