import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetAdminApplications,
  apiGetWorkforceJobs,
  apiGetSuperadminServiceProviders,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { MetricStrip } from '../../components/enterprise/MetricStrip.jsx';
import { ActionCenter } from '../../components/enterprise/ActionCenter.jsx';
import { DataTable } from '../../components/enterprise/DataTable.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  Users,
  CheckCircle2,
  Clock,
  Briefcase,
  AlertCircle,
  ArrowRight,
  Send,
  Calendar,
  Layers,
  FileCheck,
  Activity,
  Building2,
  UserPlus,
  Shield,
  ShieldCheck,
} from 'lucide-react';

export function AdminDashboardPage() {
  const { user, isSuperadmin, isServiceProviderAdmin } = useAuth();
  const [applications, setApplications] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchedRef = React.useRef(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const promises = [
        apiGetAdminApplications().catch(() => []),
        apiGetWorkforceJobs().catch(() => []),
      ];
      if (isSuperadmin) {
        promises.push(apiGetSuperadminServiceProviders().catch(() => []));
      }
      const [appsData, jobsData, provsData] = await Promise.all(promises);
      setApplications(appsData || []);
      setJobs(jobsData || []);
      if (provsData) setProviders(provsData);
    } catch (_) {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    loadData();
  }, [isSuperadmin]);

  // Compute metrics from actual backend data (strictly zero fake/demo numbers)
  const pendingApps = applications.filter((a) =>
    ['submitted', 'under_review'].includes((a.registration_status || '').toLowerCase())
  );
  const approvedTechs = applications.filter(
    (a) => (a.registration_status || '').toLowerCase() === 'approved'
  );
  const onlineTechs = applications.filter((a) => Boolean(a.is_online));
  const activeTechs = applications.filter((a) => Boolean(a.is_active));

  let docsToVerifyCount = 0;
  applications.forEach((app) => {
    const docs = app.documents_status || (app.onboarding_data && app.onboarding_data.documents) || {};
    Object.values(docs).forEach((d) => {
      if (d.status === 'pending' || d.status === 'submitted') docsToVerifyCount++;
    });
  });

  const actionItems = [
    {
      title: 'Pending Applications',
      count: applications.filter(a => a.status === 'SUBMITTED' || a.status === 'UNDER_REVIEW').length,
      description: 'Technician registrations requiring document review',
      to: '/workforce/admin/applications',
      badgeClass: 'bg-amber-50 text-amber-900 border border-amber-200',
    },
    {
      title: 'Active Technicians',
      count: applications.filter(e => e.is_active).length,
      description: 'Approved workforce field technicians',
      to: '/workforce/admin/employees',
      badgeClass: 'bg-zinc-100 text-zinc-900 border border-zinc-200',
    },
    {
      title: 'Active Operations',
      count: jobs.length,
      description: 'Assigned and pending customer service requests',
      to: '/workforce/admin/jobs',
      badgeClass: 'bg-emerald-50 text-emerald-900 border border-emerald-200',
    },
  ];

  if (isSuperadmin) {
    actionItems.push({
      title: 'Service Providers',
      count: providers.length,
      description: 'Partner organizations registered across platform',
      to: '/workforce/admin/service-providers',
      badgeClass: 'bg-zinc-100 text-zinc-900 border border-zinc-200',
    });
  }

  const jobColumns = [
    {
      key: 'request_id',
      header: 'Job ID',
      render: (val, row) => (
        <span className="font-mono font-bold text-zinc-950">{val || `SR-${row.id}`}</span>
      ),
    },
    {
      key: 'customer_display_name',
      header: 'Customer',
      render: (val) => <span className="font-medium text-zinc-800">{val || '—'}</span>,
    },
    {
      key: 'service_category',
      header: 'Service',
      render: (val, row) => (
        <span className="text-zinc-700 font-medium">{row.service_title || val || '—'}</span>
      ),
    },
    {
      key: 'address',
      header: 'Location',
      render: (val) => <span className="text-zinc-500 truncate max-w-xs block">{val || '—'}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (val) => <StatusBadge status={val} />,
    },
    {
      key: 'preferred_date',
      header: 'Scheduled Time',
      render: (val, row) => (
        <span className="text-zinc-500 font-mono text-[11px]">
          {val ? `${val}${row.preferred_time ? ` ${row.preferred_time}` : ''}` : '—'}
        </span>
      ),
    },
  ];

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }]}>
      <div className="space-y-6">
        {/* Role-Aware Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title={
              isSuperadmin
                ? 'Platform Administration Portal'
                : `Provider Portal • ${user?.providerName || user?.companyName || 'Organization'}`
            }
            subtitle={
              isSuperadmin
                ? 'Global platform governance across all service providers, independent technicians, and field operations.'
                : 'Technician management, onboarding applications, and field operations for your organization.'
            }
          />
          <div className="flex items-center gap-2.5 shrink-0">
            {isSuperadmin && (
              <Link
                to="/workforce/admin/service-providers"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 min-h-[38px] bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
              >
                <Building2 className="w-4 h-4 text-zinc-200" />
                <span>Service Providers</span>
              </Link>
            )}
            <Link
              to="/workforce/admin/employees"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 min-h-[38px] bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-900 border border-zinc-300 rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <Users className="w-4 h-4 text-zinc-700" />
              <span>Technician Roster</span>
            </Link>
          </div>
        </div>

        {/* Action Center */}
        <ActionCenter items={actionItems} />

        {/* Workforce Overview Metric Strip */}
        <div className="space-y-3">
          <h2 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
            <Users className="w-3.5 h-3.5 text-zinc-700" />
            <span>{isSuperadmin ? 'Platform Workforce Overview' : 'Provider Workforce Overview'}</span>
          </h2>
          <MetricStrip
            columns={isSuperadmin ? 5 : 4}
            metrics={[
              ...(isSuperadmin
                ? [
                    {
                      label: 'Service Providers',
                      value: providers.length,
                      icon: Building2,
                      iconColor: 'text-zinc-800',
                      valueColor: 'text-zinc-950',
                      subtext: 'Partner organizations',
                    },
                  ]
                : []),
              {
                label: 'Total Technicians',
                value: applications.length,
                icon: Users,
                subtext: 'Technicians on roster',
              },
              {
                label: 'Approved & Active',
                value: approvedTechs.length,
                icon: CheckCircle2,
                iconColor: 'text-emerald-700',
                valueColor: 'text-emerald-950',
                subtext: 'Authorized for dispatch',
              },
              {
                label: 'Online (Ready)',
                value: onlineTechs.length,
                icon: CheckCircle2,
                iconColor: 'text-zinc-800',
                valueColor: 'text-zinc-950',
                subtext: 'Available for field jobs',
              },
              {
                label: 'Pending Review',
                value: pendingApps.length,
                icon: Clock,
                iconColor: 'text-amber-700',
                valueColor: 'text-amber-950',
                subtext: 'Awaiting dossier check',
              },
            ]}
          />
        </div>

        {/* Operations Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
              <Briefcase className="w-3.5 h-3.5 text-zinc-700" />
              <span>Operations Queue ({jobs.length})</span>
            </h2>
            <Link
              to="/workforce/admin/jobs"
              className="text-xs font-bold text-zinc-950 hover:underline flex items-center gap-1"
            >
              <span>View All Jobs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <DataTable
            columns={jobColumns}
            data={[...jobs].sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, 8)}
            isLoading={isLoading}
            emptyMessage="No active customer service operations in queue."
          />
        </div>
      </div>
    </AppShell>
  );
}

export default AdminDashboardPage;

