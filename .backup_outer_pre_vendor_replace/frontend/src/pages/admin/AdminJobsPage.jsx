import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { apiGetWorkforceJobs } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { Toolbar } from '../../components/enterprise/Toolbar.jsx';
import { DataTable } from '../../components/enterprise/DataTable.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Pagination } from '../../components/enterprise/Pagination.jsx';
import { CustomerLiveTrackingModal } from '../../components/common/CustomerLiveTrackingModal.jsx';
import { Briefcase, ArrowRight, User, Send, MapPin, Calendar, Navigation } from 'lucide-react';

export function AdminJobsPage() {
  const [jobs, setJobs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(12);
  const [isLoading, setIsLoading] = useState(true);
  const [liveTrackingJobId, setLiveTrackingJobId] = useState(null);

  const loadJobs = async () => {
    try {
      setIsLoading(true);
      const data = await apiGetWorkforceJobs();
      setJobs(data || []);
    } catch (_) {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const filteredData = useMemo(() => {
    return jobs.filter((job) => {
      const term = searchTerm.toLowerCase().trim();
      const reqId = (job.request_id || `SR-${job.id}`).toLowerCase();
      const cust = (job.customer_display_name || '').toLowerCase();
      const svc = (job.service_title || job.service_category || '').toLowerCase();
      const addr = (job.address || '').toLowerCase();
      const matchesSearch = !term || reqId.includes(term) || cust.includes(term) || svc.includes(term) || addr.includes(term);

      const matchesStatus = statusFilter === 'ALL' || (job.status || '').toLowerCase() === statusFilter.toLowerCase();

      return matchesSearch && matchesStatus;
    });
  }, [jobs, searchTerm, statusFilter]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  const columns = [
    {
      key: 'request_id',
      header: 'Job ID',
      render: (val, row) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="font-mono font-bold text-zinc-950">{val || `SR-${row.id}`}</span>
          {row.job_type === 'ESTIMATION' ? (
            <span className="px-1.5 py-0.5 text-[10px] font-extrabold uppercase bg-amber-100 text-amber-900 border border-amber-300 rounded-md">
              Estimation
            </span>
          ) : (
            <span className="px-1.5 py-0.5 text-[10px] font-bold uppercase bg-blue-50 text-blue-800 border border-blue-200 rounded-md">
              Service
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'customer_display_name',
      header: 'Customer',
      render: (val) => <span className="font-medium text-zinc-800">{val || '—'}</span>,
    },
    {
      key: 'service_category',
      header: 'Service Requested',
      render: (val, row) => (
        <span className="text-zinc-900 font-bold">{row.service_title || val || '—'}</span>
      ),
    },
    {
      key: 'address',
      header: 'Location / Territory',
      render: (val) => <span className="text-zinc-500 truncate max-w-xs block">{val || '—'}</span>,
    },
    {
      key: 'status',
      header: 'Job Status',
      render: (val) => <StatusBadge status={val} />,
    },
    {
      key: 'payment_status',
      header: 'Payment Status',
      render: (val, row) => (
        <StatusBadge
          status={val === 'collected' ? 'collected' : 'pending_collection'}
          label={val === 'collected' ? 'Cash Collected' : `₹${row.total_amount || 0} COD`}
          size="xs"
        />
      ),
    },
    {
      key: 'preferred_date',
      header: 'Scheduled Date',
      render: (val, row) => (
        <span className="text-zinc-500 font-mono text-[11px]">
          {val ? `${val}${row.preferred_time ? ` ${row.preferred_time}` : ''}` : '—'}
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      align: 'right',
      render: (_, row) => {
        const isTrackable = ['assigned', 'accepted', 'on_the_way', 'arrived', 'in_progress', 'completed'].includes((row.status || '').toLowerCase());
        const isEstimation = row.job_type === 'ESTIMATION' || (row.status || '').includes('quotation') || (row.status || '').includes('inspection');
        return (
          <div className="flex items-center justify-end gap-1.5">
            {isEstimation && (
              <Link
                to="/workforce/vendor/estimations"
                className="px-2.5 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-900 font-bold text-xs border border-amber-200 transition-all shadow-xs inline-flex items-center gap-1"
                title="View in AC Estimation Workflow"
              >
                <span>Estimation</span>
              </Link>
            )}
            {isTrackable && (
              <button
                type="button"
                onClick={() => setLiveTrackingJobId(row.id)}
                className="px-2.5 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 active:bg-emerald-200 text-emerald-900 font-bold text-xs border border-emerald-200 transition-all shadow-xs inline-flex items-center gap-1.5 cursor-pointer"
                title="View Live Road Tracking"
              >
                <Navigation className="w-3.5 h-3.5 text-emerald-700" />
                <span>Track</span>
              </button>
            )}
            <Link
              to="/workforce/admin/dispatch"
              className="px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white font-bold text-xs shadow-xs transition-all inline-flex items-center gap-1.5 cursor-pointer"
            >
              <span>Dispatch</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        );
      },
    },
  ];

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Jobs' }]}>
      <div className="space-y-4">

        {/* Header */}
        <PageHeader
          title="Customer Jobs & Field Work Orders"
          subtitle="Real-time lifecycle tracking across booking, dispatch, execution, proof upload, and cash collection"
        />

        {/* Toolbar */}
        <Toolbar
          searchValue={searchTerm}
          onSearchChange={setSearchTerm}
          searchPlaceholder="Search jobs by ID, customer, address..."
          filters={[
            {
              key: 'status',
              label: 'Status',
              options: [
                { value: 'ALL', label: 'All Statuses' },
                { value: 'assigned', label: 'Assigned / Queued' },
                { value: 'accepted', label: 'Accepted' },
                { value: 'on_the_way', label: 'On The Way' },
                { value: 'in_progress', label: 'In Progress' },
                { value: 'completed', label: 'Completed' },
              ],
            },
          ]}
          activeFilters={{ status: statusFilter }}
          onFilterChange={(_, val) => {
            setStatusFilter(val);
            setCurrentPage(1);
          }}
          onRefresh={loadJobs}
          isRefreshing={isLoading}
        />

        {/* Dense Table */}
        <DataTable
          columns={columns}
          data={paginatedData}
          isLoading={isLoading}
          emptyMessage="No customer job orders match the selected filters."
        />

        {/* Pagination */}
        {filteredData.length > pageSize && (
          <Pagination
            currentPage={currentPage}
            totalItems={filteredData.length}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
          />
        )}

        {/* Operational Live Tracking Modal */}
        <CustomerLiveTrackingModal
          jobId={liveTrackingJobId}
          isOpen={Boolean(liveTrackingJobId)}
          onClose={() => setLiveTrackingJobId(null)}
          viewRole="admin"
        />
      </div>
    </AppShell>
  );
}

export default AdminJobsPage;
