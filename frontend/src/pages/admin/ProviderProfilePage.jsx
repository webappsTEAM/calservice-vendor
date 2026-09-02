import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { apiGetProviderProfile } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  Building2,
  ShieldCheck,
  Mail,
  Phone,
  MapPin,
  Globe,
  Users,
  Calendar,
  Briefcase,
  ExternalLink,
  ArrowRight,
  Shield,
  Layers,
} from 'lucide-react';

export function ProviderProfilePage() {
  const { user, isSuperadmin, isServiceProviderAdmin } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isCancelled = false;
    const loadProfile = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await apiGetProviderProfile();
        if (!isCancelled) {
          setProfile(data);
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err.message || 'Failed to load provider profile.');
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    };
    loadProfile();
    return () => {
      isCancelled = true;
    };
  }, []);

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Provider Profile' }]}>
        <LoadingState message="Loading organization profile..." />
      </AppShell>
    );
  }

  if (isSuperadmin && (!profile || profile.is_superadmin)) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Platform Scope' }]}>
        <div className="p-6 max-w-4xl mx-auto space-y-6">
          <PageHeader
            title="Platform Administration Scope"
            subtitle="You are operating with Superadmin cross-tenant platform authority."
          />
          <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
              <Shield className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Platform Superadministrator</h3>
            <p className="text-sm text-slate-600 max-w-md mx-auto">
              As a Superadmin, your authority is platform-wide across all partner organizations, provider admins, and independent technicians.
            </p>
            <div className="pt-4 flex items-center justify-center gap-3">
              <Link
                to="/workforce/admin/service-providers"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors"
              >
                <Building2 className="w-4 h-4" />
                <span>Manage Service Providers</span>
              </Link>
              <Link
                to="/workforce/admin/employees"
                className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg transition-colors"
              >
                <Users className="w-4 h-4" />
                <span>View All Technicians</span>
              </Link>
            </div>
          </div>
        </div>
      </AppShell>
    );
  }

  if (error || !profile) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Provider Profile' }]}>
        <div className="p-6 max-w-4xl mx-auto">
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-center space-y-3">
            <Building2 className="w-10 h-10 text-rose-500 mx-auto" />
            <h3 className="text-base font-bold text-rose-900">Unable to load Organization Profile</h3>
            <p className="text-xs text-rose-700">{error || 'Provider organization context not found.'}</p>
          </div>
        </div>
      </AppShell>
    );
  }

  const admin = profile.primary_admin;

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Provider Profile' }]}>
      <div className="p-6 max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title={profile.company_name || 'Organization Profile'}
            subtitle={`Provider Code: ${profile.display_id || `ID: ${profile.id}`}`}
          />
          <div className="flex items-center gap-2">
            <StatusBadge status={profile.is_active ? 'active' : 'inactive'} />
            <Link
              to="/workforce/admin/employees"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg text-xs font-semibold transition-colors"
            >
              <Users className="w-3.5 h-3.5" />
              <span>{profile.employee_count ?? 0} Technicians</span>
            </Link>
          </div>
        </div>

        {/* Dossier Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Main Info */}
          <div className="md:col-span-2 space-y-6">
            {/* Organization Card */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-5">
              <h3 className="text-xs font-bold text-blue-600 uppercase tracking-wider flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                <span>Organization Identity</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block mb-1">Company Name</span>
                  <span className="font-semibold text-slate-900 text-sm">{profile.company_name}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Display Identifier</span>
                  <span className="font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-semibold">
                    {profile.display_id || `ID: ${profile.id}`}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Industry / Specialization</span>
                  <span className="font-medium text-slate-800">{profile.industry || 'General Workforce Services'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block mb-1">Primary Region</span>
                  <span className="font-medium text-slate-800">{profile.primary_country || 'Default'}</span>
                </div>
                <div className="sm:col-span-2">
                  <span className="text-slate-400 block mb-1">Registered Address</span>
                  <p className="font-medium text-slate-800 flex items-start gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                    <span>{profile.address || 'Address not registered'}</span>
                  </p>
                </div>
                {profile.website && (
                  <div className="sm:col-span-2">
                    <span className="text-slate-400 block mb-1">Website</span>
                    <a
                      href={profile.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline flex items-center gap-1 font-medium"
                    >
                      <Globe className="w-3.5 h-3.5" />
                      <span>{profile.website}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-slate-50 rounded-2xl border border-slate-200 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Manage Provider Technicians</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Review active roster, invite new technicians, and approve service qualifications.
                </p>
              </div>
              <Link
                to="/workforce/admin/employees"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors shrink-0"
              >
                <span>Open Technician Roster</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Primary Administrator Sidebar */}
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
              <h3 className="text-xs font-bold text-blue-600 uppercase tracking-wider flex items-center gap-2">
                <ShieldCheck className="w-4 h-4" />
                <span>Primary Administrator</span>
              </h3>
              {admin ? (
                <div className="space-y-3 text-xs">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold text-sm">
                      {admin.first_name ? admin.first_name[0].toUpperCase() : 'A'}
                    </div>
                    <div>
                      <div className="font-bold text-slate-900">{admin.full_name || admin.username}</div>
                      <div className="text-[11px] text-slate-400 font-mono">@{admin.username}</div>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-slate-100 space-y-2">
                    <div className="flex items-center gap-2 text-slate-700">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      <span className="truncate">{admin.email || 'No email registered'}</span>
                    </div>
                    {admin.phone && (
                      <div className="flex items-center gap-2 text-slate-700">
                        <Phone className="w-3.5 h-3.5 text-slate-400" />
                        <span>{admin.phone}</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No primary administrator record associated.</p>
              )}
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-3 text-xs">
              <h4 className="font-bold text-slate-900 flex items-center gap-2">
                <Layers className="w-4 h-4 text-blue-600" />
                <span>Operational Governance</span>
              </h4>
              <p className="text-slate-500 leading-relaxed">
                All operations and technicians managed within this dashboard are strictly scoped to {profile.company_name}.
              </p>
              <div className="pt-2 border-t border-slate-100 flex items-center gap-1.5 text-slate-400 text-[11px]">
                <Calendar className="w-3.5 h-3.5" />
                <span>Registered: {profile.created_at ? new Date(profile.created_at).toLocaleDateString() : '—'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default ProviderProfilePage;
