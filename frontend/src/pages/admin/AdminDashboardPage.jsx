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
      count: pendingApps.length,
      description: 'Dossiers awaiting verification & service authorization',
      to: '/workforce/admin/applications?status=submitted',
      badgeClass: 'bg-amber-100 text-amber-900',
    },
    {
      title: 'Documents to Verify',
      count: docsToVerifyCount > 0 ? docsToVerifyCount : pendingApps.length,
      description: 'Identification & certification files in queue',
      to: '/workforce/admin/applications',
      badgeClass: 'bg-blue-100 text-blue-900',
    },
    {
      title: 'Active Operations',
      count: jobs.length,
      description: 'Assigned and pending customer service requests',
      to: '/workforce/admin/jobs',
      badgeClass: 'bg-emerald-100 text-emerald-900',
    },
  ];

  if (isSuperadmin) {
    actionItems.push({
      title: 'Service Providers',
      count: providers.length,
      description: 'Partner organizations registered across platform',
      to: '/workforce/admin/service-providers',
      badgeClass: 'bg-purple-100 text-purple-900',
    });
  }

  const recentJobsColumns = [
    {
      key: 'request_id',
      header: 'Job ID',
      render: (val, row) => (
        <span className="font-mono font-bold text-blue-600">{val || `SR-${row.id}`}</span>
      ),
    },
    {
      key: 'customer_display_name',
      header: 'Customer',
      render: (val) => <span className="font-medium text-slate-800">{val || '—'}</span>,
    },
    {
      key: 'service_category',
      header: 'Service',
      render: (val, row) => (
        <span className="text-slate-700">{row.service_title || val || '—'}</span>
      ),
    },
    {
      key: 'address',
      header: 'Location',
      render: (val) => <span className="text-slate-500 truncate max-w-xs block">{val || '—'}</span>,
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
        <span className="text-slate-500 font-mono text-[11px]">
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
          <div className="flex items-center gap-2 shrink-0">
            {isSuperadmin && (
              <Link
                to="/workforce/admin/service-providers"
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>Service Providers</span>
              </Link>
            )}
            <Link
              to="/workforce/admin/employees"
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-900 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
            >
              <Users className="w-3.5 h-3.5" />
              <span>Technician Roster</span>
            </Link>
          </div>
        </div>

        {/* Action Center */}
        <ActionCenter items={actionItems} />

        {/* Workforce Overview Metric Strip */}
        <div>
          <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-blue-600" />
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
                      iconColor: 'text-purple-600',
                      valueColor: 'text-purple-700',
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
                iconColor: 'text-emerald-600',
                valueColor: 'text-emerald-700',
                subtext: 'Authorized for dispatch',
              },
              {
                label: 'Online (Ready)',
                value: onlineTechs.length,
                icon: CheckCircle2,
                iconColor: 'text-blue-600',
                valueColor: 'text-blue-700',
                subtext: 'Available for field jobs',
              },
              {
                label: 'Pending Review',
                value: pendingApps.length,
                icon: Clock,
                iconColor: 'text-orange-600',
                valueColor: 'text-orange-700',
                subtext: 'Awaiting dossier check',
              },
            ]}
          />
        </div>

        {/* Operations Table */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Briefcase className="w-3.5 h-3.5 text-blue-600" />
              <span>Operations Queue ({jobs.length})</span>
            </h2>
            <Link
              to="/workforce/admin/jobs"
              className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
            >
              <span>View All Jobs</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <DataTable
            columns={recentJobsColumns}
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
