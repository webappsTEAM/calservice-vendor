import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetSuperadminServiceProviders,
  apiCreateSuperadminServiceProvider,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { Drawer } from '../../components/enterprise/Drawer.jsx';
import {
  Building2,
  Plus,
  Search,
  Users,
  ShieldCheck,
  Mail,
  Phone,
  Calendar,
  AlertCircle,
  CheckCircle2,
  X,
  Lock,
  User,
  Globe,
  MapPin,
  Briefcase,
  ArrowRight,
  ExternalLink,
} from 'lucide-react';

export function AdminServiceProvidersPage() {
  const { isSuperadmin } = useAuth();
  const [providers, setProviders] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);

  // Form State
  const [formData, setFormData] = useState({
    company_name: '',
    display_id: '',
    address: '',
    industry: '',
    website: '',
    admin_username: '',
    admin_email: '',
    admin_password: '',
    admin_first_name: '',
    admin_last_name: '',
    admin_phone: '',
  });

  const loadProviders = async () => {
    try {
      setIsLoading(true);
      const data = await apiGetSuperadminServiceProviders({
        q: searchQuery,
        is_active: statusFilter === 'all' ? undefined : statusFilter === 'active',
      });
      setProviders(data || []);
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to load service providers.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isSuperadmin) {
      loadProviders();
    }
  }, [searchQuery, statusFilter, isSuperadmin]);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateProvider = async (e) => {
    e.preventDefault();
    setFeedback(null);

    if (!formData.company_name.trim()) {
      setFeedback({ type: 'error', message: 'Company Name is required.' });
      return;
    }
    if (!formData.admin_username.trim()) {
      setFeedback({ type: 'error', message: 'Admin Username is required.' });
      return;
    }
    if (!formData.admin_email.trim()) {
      setFeedback({ type: 'error', message: 'Admin Email is required.' });
      return;
    }
    if (!formData.admin_password || formData.admin_password.length < 6) {
      setFeedback({ type: 'error', message: 'Admin Password must be at least 6 characters.' });
      return;
    }

    try {
      setIsSubmitting(true);
      const res = await apiCreateSuperadminServiceProvider(formData);
      setFeedback({
        type: 'success',
        message: res.message || 'Service Provider and Primary Admin created successfully.',
      });
      setIsModalOpen(false);
      setFormData({
        company_name: '',
        display_id: '',
        address: '',
        industry: '',
        website: '',
        admin_username: '',
        admin_email: '',
        admin_password: '',
        admin_first_name: '',
        admin_last_name: '',
        admin_phone: '',
      });
      loadProviders();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to create Service Provider.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isSuperadmin) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }]}>
        <div className="p-8 max-w-4xl mx-auto">
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
            <ShieldCheck className="w-12 h-12 text-amber-600 mx-auto mb-3" />
            <h2 className="text-lg font-bold text-amber-900 mb-1">Superadmin Access Required</h2>
            <p className="text-sm text-amber-700">
              Only platform Superadministrators have authority to manage and create Service Providers.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Service Providers' }]}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Service Providers"
            subtitle="Platform-wide governance of partner organizations and their primary administrators."
          />
          <button
            type="button"
            onClick={() => {
              setFeedback(null);
              setIsModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span>Create Service Provider</span>
          </button>
        </div>

        {/* Global Feedback Alert */}
        {feedback && (
          <div
            className={`p-3.5 rounded-xl border flex items-start gap-3 text-xs ${
              feedback.type === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-rose-50 border-rose-200 text-rose-900'
            }`}
          >
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1 font-medium">{feedback.message}</div>
            <button
              type="button"
              onClick={() => setFeedback(null)}
              className="text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white p-3.5 rounded-md border border-zinc-200/90 shadow-card text-xs">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
            <input
              type="text"
              placeholder="Search providers or display ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            />
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 min-h-[38px] border border-zinc-300 rounded-lg text-xs text-zinc-800 bg-white focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
            >
              <option value="all">All Statuses</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
            </select>
          </div>
        </div>

        {/* Providers Table */}
        {isLoading ? (
          <LoadingState message="Loading service providers..." />
        ) : providers.length === 0 ? (
          <div className="bg-white rounded-md border border-zinc-200/90 shadow-card p-12 text-center">
            <Building2 className="w-12 h-12 text-zinc-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-zinc-900">No Service Providers Found</h3>
            <p className="text-xs text-zinc-500 max-w-md mx-auto mt-1 leading-relaxed">
              {searchQuery
                ? 'No providers match your search query. Try clearing filters.'
                : 'Click "Create Service Provider" above to add the first service provider and primary admin.'}
            </p>
          </div>
        ) : (
          <div className="bg-white rounded-md border border-zinc-200/90 shadow-card overflow-hidden text-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-zinc-600">
                <thead className="bg-zinc-50/80 text-[11px] font-bold text-zinc-500 uppercase tracking-wider border-b border-zinc-200">
                  <tr>
                    <th className="px-5 py-3.5">Provider / Organization</th>
                    <th className="px-5 py-3.5">Display ID</th>
                    <th className="px-5 py-3.5">Primary Administrator</th>
                    <th className="px-5 py-3.5 text-center">Technicians</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Created</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100">
                  {providers.map((p) => {
                    const admin = p.primary_admin;
                    return (
                      <tr
                        key={p.id}
                        onClick={() => setSelectedProvider(p)}
                        className="hover:bg-zinc-50/80 transition-colors cursor-pointer"
                      >
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-800 border border-zinc-200 flex items-center justify-center font-bold text-xs shrink-0">
                              <Building2 className="w-4 h-4" />
                            </div>
                            <div>
                              <div className="font-bold text-zinc-950">{p.company_name}</div>
                              {p.industry && (
                                <div className="text-[10px] text-zinc-400 font-medium">{p.industry}</div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <span className="font-mono text-[11px] px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-800 font-bold border border-zinc-200">
                            {p.display_id || `ID: ${p.id}`}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          {admin ? (
                            <div>
                              <div className="font-bold text-zinc-900 flex items-center gap-1.5">
                                <User className="w-3.5 h-3.5 text-zinc-400" />
                                <span>{admin.full_name || admin.username}</span>
                              </div>
                              <div className="text-[11px] text-zinc-500 flex items-center gap-1.5 mt-0.5">
                                <Mail className="w-3.5 h-3.5 text-zinc-400" />
                                <span className="truncate max-w-[160px]">{admin.email || 'No email'}</span>
                              </div>
                            </div>
                          ) : (
                            <span className="text-[11px] text-zinc-400 italic">No admin assigned</span>
                          )}
                        </td>
                        <td className="px-5 py-4 text-center">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-zinc-100 text-zinc-800 font-bold text-[11px]">
                            <Users className="w-3.5 h-3.5 text-zinc-400" />
                            <span>{p.employee_count ?? 0}</span>
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <StatusBadge status={p.is_active ? 'active' : 'inactive'} />
                        </td>
                        <td className="px-5 py-4 text-zinc-500 font-mono text-[11px]">
                          {p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-5 py-4 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedProvider(p);
                            }}
                            className="px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200 text-zinc-900 font-bold text-xs shadow-xs transition-all cursor-pointer"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}


        {/* Modal: Create Service Provider */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto border border-slate-200 text-xs">
              <div className="p-5 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-blue-600" />
                    <span>Create Service Provider</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Establishes a new provider organization and provisions its primary Service Provider Admin.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateProvider} className="p-5 space-y-5">
                {/* Organization Section */}
                <div className="space-y-3">
                  <h4 className="text-[11px] font-bold text-blue-600 uppercase tracking-wider flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5" />
                    <span>Organization Information</span>
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="sm:col-span-2">
                      <label className="block font-semibold text-slate-700 mb-1">
                        Company Name <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="company_name"
                        required
                        value={formData.company_name}
                        onChange={handleInputChange}
                        placeholder="e.g. Apex Electrical Solutions"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Display Identifier / Code
                      </label>
                      <input
                        type="text"
                        name="display_id"
                        value={formData.display_id}
                        onChange={handleInputChange}
                        placeholder="e.g. APEX"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-mono"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Industry / Specialization
                      </label>
                      <input
                        type="text"
                        name="industry"
                        value={formData.industry}
                        onChange={handleInputChange}
                        placeholder="e.g. HVAC, Electrical"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block font-semibold text-slate-700 mb-1">
                        Registered Business Address
                      </label>
                      <input
                        type="text"
                        name="address"
                        value={formData.address}
                        onChange={handleInputChange}
                        placeholder="e.g. 100 Main Street, Suite 400"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block font-semibold text-slate-700 mb-1">
                        Official Website
                      </label>
                      <input
                        type="url"
                        name="website"
                        value={formData.website}
                        onChange={handleInputChange}
                        placeholder="https://example.com"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                  </div>
                </div>

                {/* Primary Admin Section */}
                <div className="space-y-3 pt-3 border-t border-slate-100">
                  <h4 className="text-[11px] font-bold text-blue-600 uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Primary Service Provider Admin Account</span>
                  </h4>
                  <p className="text-[11px] text-slate-500">
                    This user will receive <span className="font-semibold text-slate-700">Service Provider Admin</span> privileges to manage technicians under this organization.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Admin Username <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        name="admin_username"
                        required
                        value={formData.admin_username}
                        onChange={handleInputChange}
                        placeholder="e.g. apex_admin"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Admin Email <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="email"
                        name="admin_email"
                        required
                        value={formData.admin_email}
                        onChange={handleInputChange}
                        placeholder="admin@apex.com"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Initial Password <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="password"
                        name="admin_password"
                        required
                        value={formData.admin_password}
                        onChange={handleInputChange}
                        placeholder="Minimum 6 characters"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Contact Phone
                      </label>
                      <input
                        type="text"
                        name="admin_phone"
                        value={formData.admin_phone}
                        onChange={handleInputChange}
                        placeholder="+1 555-0199"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        First Name
                      </label>
                      <input
                        type="text"
                        name="admin_first_name"
                        value={formData.admin_first_name}
                        onChange={handleInputChange}
                        placeholder="John"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                    <div>
                      <label className="block font-semibold text-slate-700 mb-1">
                        Last Name
                      </label>
                      <input
                        type="text"
                        name="admin_last_name"
                        value={formData.admin_last_name}
                        onChange={handleInputChange}
                        placeholder="Doe"
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                  </div>
                </div>

                {/* Submit Buttons */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold rounded-lg shadow-sm transition-colors inline-flex items-center gap-1.5"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Creating Provider...</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" />
                        <span>Create Provider</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Provider Dossier Drawer */}
        <Drawer
          isOpen={Boolean(selectedProvider)}
          onClose={() => setSelectedProvider(null)}
          title={selectedProvider?.company_name || 'Provider Dossier'}
          subtitle={`Identifier: ${selectedProvider?.display_id || `ID: ${selectedProvider?.id}`}`}
          footer={
            <Link
              to={`/workforce/admin/employees?company_id=${selectedProvider?.id}`}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs inline-flex items-center gap-1"
            >
              <span>View Technicians ({selectedProvider?.employee_count ?? 0})</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          }
        >
          {selectedProvider && (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Status:</span>
                  <StatusBadge status={selectedProvider.is_active ? 'active' : 'inactive'} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Technician Roster:</span>
                  <span className="font-bold text-slate-800">
                    {selectedProvider.employee_count ?? 0} Technicians
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Created:</span>
                  <span className="text-slate-700 font-mono">
                    {selectedProvider.created_at ? new Date(selectedProvider.created_at).toLocaleDateString() : '—'}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Primary Administrator
                </h4>
                {selectedProvider.primary_admin ? (
                  <div className="p-3 bg-white border border-slate-200 rounded space-y-1 text-slate-700">
                    <p className="font-semibold text-slate-900">
                      {selectedProvider.primary_admin.full_name || selectedProvider.primary_admin.username}
                    </p>
                    <p className="flex items-center gap-1.5 text-slate-500">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      <span>{selectedProvider.primary_admin.email || '—'}</span>
                    </p>
                    {selectedProvider.primary_admin.phone && (
                      <p className="flex items-center gap-1.5 text-slate-500">
                        <Phone className="w-3.5 h-3.5 text-slate-400" />
                        <span>{selectedProvider.primary_admin.phone}</span>
                      </p>
                    )}
                  </div>
                ) : (
                  <span className="text-slate-400 italic">No primary administrator configured.</span>
                )}
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Organization Information
                </h4>
                <div className="space-y-1 text-slate-700">
                  <p className="flex items-start gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                    <span>{selectedProvider.address || 'Address not registered'}</span>
                  </p>
                  {selectedProvider.website && (
                    <p className="flex items-center gap-1.5">
                      <Globe className="w-3.5 h-3.5 text-slate-400" />
                      <a
                        href={selectedProvider.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline flex items-center gap-0.5"
                      >
                        <span>{selectedProvider.website}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </Drawer>
      </div>
    </AppShell>
  );
}

export default AdminServiceProvidersPage;
