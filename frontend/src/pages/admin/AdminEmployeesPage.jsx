import React, { useEffect, useState, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetAdminTechnicians,
  apiCreateAdminTechnician,
  apiToggleAdminTechnicianActive,
  apiGetCatalog,
  apiGetSuperadminServiceProviders,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { Toolbar } from '../../components/enterprise/Toolbar.jsx';
import { DataTable } from '../../components/enterprise/DataTable.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Drawer } from '../../components/enterprise/Drawer.jsx';
import { Pagination } from '../../components/enterprise/Pagination.jsx';
import {
  Users,
  UserPlus,
  Phone,
  Mail,
  MapPin,
  Wrench,
  ShieldCheck,
  Building2,
  ArrowRight,
  Plus,
  X,
  CheckCircle2,
  AlertCircle,
  Power,
  Lock,
} from 'lucide-react';

export function AdminEmployeesPage() {
  const { user, isSuperadmin, isServiceProviderAdmin } = useAuth();
  const [searchParams] = useSearchParams();
  const initialCompanyFilter = searchParams.get('company_id') || 'ALL';

  const [technicians, setTechnicians] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [providers, setProviders] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [availabilityFilter, setAvailabilityFilter] = useState('ALL');
  const [affiliationFilter, setAffiliationFilter] = useState(initialCompanyFilter);
  const [selectedTech, setSelectedTech] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(12);
  const [isLoading, setIsLoading] = useState(true);

  // Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    password: '',
    company_id: '',
    services: [],
  });

  const loadEmployees = async () => {
    try {
      setIsLoading(true);
      const techs = await apiGetAdminTechnicians().catch(() => []);
      setTechnicians(techs || []);
    } catch (_) {
    } finally {
      setIsLoading(false);
    }
  };

  const loadMetadata = async () => {
    try {
      const cat = await apiGetCatalog().catch(() => []);
      setCatalog(cat || []);
      if (isSuperadmin) {
        const provs = await apiGetSuperadminServiceProviders({ is_active: true }).catch(() => []);
        setProviders(provs || []);
      }
    } catch (_) {}
  };

  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;
    loadEmployees();
    loadMetadata();
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleServiceToggle = (serviceName) => {
    setFormData((prev) => {
      const exists = prev.services.includes(serviceName);
      return {
        ...prev,
        services: exists
          ? prev.services.filter((s) => s !== serviceName)
          : [...prev.services, serviceName],
      };
    });
  };

  const handleCreateTechnician = async (e) => {
    e.preventDefault();
    setFeedback(null);

    if (!formData.first_name.trim()) {
      setFeedback({ type: 'error', message: 'First Name is required.' });
      return;
    }
    if (!formData.email.trim()) {
      setFeedback({ type: 'error', message: 'Email is required.' });
      return;
    }

    try {
      setIsSubmitting(true);
      const payload = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
        email: formData.email.trim(),
        phone: formData.phone.trim(),
        password: formData.password || undefined,
        services: formData.services,
      };

      if (isSuperadmin && formData.company_id) {
        payload.company_id = parseInt(formData.company_id, 10);
      }

      const res = await apiCreateAdminTechnician(payload);
      setFeedback({
        type: 'success',
        message: res.message || 'Technician created and enrolled successfully.',
      });
      setIsAddModalOpen(false);
      setFormData({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        password: '',
        company_id: '',
        services: [],
      });
      loadEmployees();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to create technician.',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (techId, e) => {
    e.stopPropagation();
    try {
      await apiToggleAdminTechnicianActive(techId);
      loadEmployees();
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to update active status.',
      });
    }
  };

  const filteredData = useMemo(() => {
    return technicians.filter((tech) => {
      const term = searchTerm.toLowerCase().trim();
      const name = `${tech.first_name || ''} ${tech.last_name || ''}`.toLowerCase();
      const empId = (tech.employee_id || '').toLowerCase();
      const phone = (tech.mobile_number || tech.phone || '').toLowerCase();
      const coName = (tech.company_name || '').toLowerCase();
      const matchesSearch =
        !term || name.includes(term) || empId.includes(term) || phone.includes(term) || coName.includes(term);

      const reg = (tech.registration_status || '').toLowerCase();
      const matchesStatus =
        statusFilter === 'ALL' ||
        (statusFilter === 'approved' && reg === 'approved') ||
        (statusFilter === 'pending' && ['submitted', 'under_review'].includes(reg));

      const isOnline = Boolean(tech.is_online);
      const matchesAvailability =
        availabilityFilter === 'ALL' ||
        (availabilityFilter === 'online' && isOnline) ||
        (availabilityFilter === 'offline' && !isOnline);

      const matchesAffiliation =
        affiliationFilter === 'ALL' ||
        (affiliationFilter === 'independent' && !tech.company_id) ||
        (affiliationFilter === 'provider' && Boolean(tech.company_id)) ||
        String(tech.company_id) === String(affiliationFilter);

      return matchesSearch && matchesStatus && matchesAvailability && matchesAffiliation;
    });
  }, [technicians, searchTerm, statusFilter, availabilityFilter, affiliationFilter]);

  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredData.slice(start, start + pageSize);
  }, [filteredData, currentPage, pageSize]);

  const columns = [
    {
      key: 'employee',
      header: 'Technician',
      render: (_, row) => (
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center font-bold text-blue-700 text-xs shrink-0">
            {row.first_name ? row.first_name[0].toUpperCase() : 'T'}
          </div>
          <div>
            <span className="font-bold text-slate-900 block truncate">
              {row.first_name} {row.last_name}
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              {row.employee_id || 'ID Pending'}
            </span>
          </div>
        </div>
      ),
    },
    {
      key: 'affiliation',
      header: 'Organization / Affiliation',
      render: (_, row) => (
        <div className="flex items-center gap-1.5 text-xs">
          {row.company_name ? (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-medium">
              <Building2 className="w-3 h-3 text-blue-600" />
              <span>{row.company_name}</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium">
              <ShieldCheck className="w-3 h-3 text-slate-500" />
              <span>Independent Technician</span>
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'services',
      header: 'Approved Services',
      render: (_, row) => {
        const approved = row.approved_services || [];
        return (
          <div>
            <span className="font-semibold text-slate-800 text-xs">
              {approved.length} Services
            </span>
            <p className="text-[10px] text-slate-500 truncate max-w-[180px]">
              {approved.map((s) => s.name).join(', ') || 'No approved services'}
            </p>
          </div>
        );
      },
    },
    {
      key: 'is_online',
      header: 'Presence',
      render: (val) => (
        <StatusBadge
          status={val ? 'online' : 'offline'}
          label={val ? 'Online (Ready)' : 'Offline'}
        />
      ),
    },
    {
      key: 'phone',
      header: 'Contact',
      render: (_, row) => (
        <span className="font-mono text-slate-600 text-xs">{row.phone || row.mobile_number || '—'}</span>
      ),
    },
    {
      key: 'is_active',
      header: 'Roster Status',
      render: (val, row) => (
        <button
          type="button"
          onClick={(e) => handleToggleActive(row.id, e)}
          title={`Click to ${val ? 'deactivate' : 'activate'}`}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
            val
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-rose-50 hover:text-rose-700 hover:border-rose-200'
              : 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200'
          }`}
        >
          <Power className="w-3 h-3" />
          <span>{val ? 'Active' : 'Inactive'}</span>
        </button>
      ),
    },
    {
      key: 'actions',
      header: 'Action',
      align: 'right',
      render: (_, row) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedTech(row);
          }}
          className="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs transition-colors"
        >
          View Dossier
        </button>
      ),
    },
  ];

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/admin' }, { label: 'Technicians' }]}>
      <div className="space-y-4">
        {/* Header & Add Button */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Technician Roster"
            subtitle="Directory of field technicians, organization affiliations, and active dispatch credentials."
          />
          <button
            type="button"
            onClick={() => {
              setFeedback(null);
              setIsAddModalOpen(true);
            }}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors shrink-0"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Technician</span>
          </button>
        </div>

        {/* Global Feedback Banner */}
        {feedback && (
          <div
            className={`p-3 rounded-xl border flex items-start gap-3 text-xs ${
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

        {/* Toolbar */}
        <Toolbar
          searchValue={searchTerm}
          onSearchChange={setSearchTerm}
          searchPlaceholder="Search by name, ID, phone, or provider..."
          filters={[
            ...(isSuperadmin
              ? [
                  {
                    key: 'affiliation',
                    label: 'Affiliation',
                    options: [
                      { value: 'ALL', label: 'All Affiliations' },
                      { value: 'independent', label: 'Independent Technicians' },
                      { value: 'provider', label: 'All Provider Technicians' },
                      ...providers.map((p) => ({
                        value: String(p.id),
                        label: p.company_name,
                      })),
                    ],
                  },
                ]
              : []),
            {
              key: 'status',
              label: 'Status',
              options: [
                { value: 'ALL', label: 'All Statuses' },
                { value: 'approved', label: 'Approved Only' },
                { value: 'pending', label: 'Pending Only' },
              ],
            },
            {
              key: 'availability',
              label: 'Presence',
              options: [
                { value: 'ALL', label: 'All Presence' },
                { value: 'online', label: 'Online Only' },
                { value: 'offline', label: 'Offline Only' },
              ],
            },
          ]}
          activeFilters={{
            status: statusFilter,
            availability: availabilityFilter,
            affiliation: affiliationFilter,
          }}
          onFilterChange={(key, val) => {
            if (key === 'status') setStatusFilter(val);
            if (key === 'availability') setAvailabilityFilter(val);
            if (key === 'affiliation') setAffiliationFilter(val);
            setCurrentPage(1);
          }}
          onRefresh={loadEmployees}
          isRefreshing={isLoading}
        />

        {/* Dense Table */}
        <DataTable
          columns={columns}
          data={paginatedData}
          isLoading={isLoading}
          onRowClick={(row) => setSelectedTech(row)}
          emptyMessage="No technicians match the current filter parameters."
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

        {/* Modal: Add Technician */}
        {isAddModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-xl max-h-[90vh] overflow-y-auto border border-slate-200">
              <div className="p-5 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white z-10">
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    <UserPlus className="w-4 h-4 text-blue-600" />
                    <span>Add New Technician</span>
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {isServiceProviderAdmin
                      ? 'Technician will be automatically registered under your Service Provider.'
                      : 'Enroll a new technician under a Service Provider or as an Independent Technician.'}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateTechnician} className="p-5 space-y-4">
                {/* Superadmin Provider Selector */}
                {isSuperadmin && (
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Organization / Affiliation
                    </label>
                    <select
                      name="company_id"
                      value={formData.company_id}
                      onChange={handleInputChange}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    >
                      <option value="">Independent Technician (No Provider)</option>
                      {providers.map((prov) => (
                        <option key={prov.id} value={prov.id}>
                          {prov.company_name} ({prov.display_id || `ID: ${prov.id}`})
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Personal Information */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      First Name <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      name="first_name"
                      required
                      value={formData.first_name}
                      onChange={handleInputChange}
                      placeholder="e.g. John"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Last Name
                    </label>
                    <input
                      type="text"
                      name="last_name"
                      value={formData.last_name}
                      onChange={handleInputChange}
                      placeholder="e.g. Doe"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Email Address <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      placeholder="technician@example.com"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Phone Number
                    </label>
                    <input
                      type="text"
                      name="phone"
                      value={formData.phone}
                      onChange={handleInputChange}
                      placeholder="+1 555-0199"
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Initial Password (Optional — auto-generated if left blank)
                  </label>
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleInputChange}
                    placeholder="Leave blank to auto-generate"
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>

                {/* Services Checklist */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Authorized Dispatch Services
                  </label>
                  <div className="p-3 border border-slate-200 rounded-lg max-h-36 overflow-y-auto space-y-1.5 bg-slate-50">
                    {catalog.flatMap((cat) => cat.services || []).map((svc) => (
                      <label
                        key={svc.id}
                        className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer select-none"
                      >
                        <input
                          type="checkbox"
                          checked={formData.services.includes(svc.name)}
                          onChange={() => handleServiceToggle(svc.name)}
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                        />
                        <span>{svc.name}</span>
                      </label>
                    ))}
                    {catalog.length === 0 && (
                      <span className="text-xs text-slate-400 italic">No catalog services available</span>
                    )}
                  </div>
                </div>

                {/* Submit Actions */}
                <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsAddModalOpen(false)}
                    className="px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-sm transition-colors inline-flex items-center gap-1.5"
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Enrolling...</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" />
                        <span>Enroll Technician</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Quick Inspection Drawer */}
        <Drawer
          isOpen={Boolean(selectedTech)}
          onClose={() => setSelectedTech(null)}
          title={`${selectedTech?.first_name || ''} ${selectedTech?.last_name || ''}`}
          subtitle={`Employee ID: ${selectedTech?.employee_id || 'Pending'}`}
          footer={
            <Link
              to={`/workforce/admin/applications/${selectedTech?.id}`}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs inline-flex items-center gap-1"
            >
              <span>Full Dossier</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          }
        >
          {selectedTech && (
            <div className="space-y-4 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Registration Status:</span>
                  <StatusBadge status={selectedTech.registration_status} />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Live Presence:</span>
                  <StatusBadge
                    status={selectedTech.is_online ? 'online' : 'offline'}
                    label={selectedTech.is_online ? 'Online' : 'Offline'}
                  />
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Provider:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedTech.company_name || 'Independent'}
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Contact Information
                </h4>
                <div className="space-y-1 text-slate-700">
                  <p className="flex items-center gap-2">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    <span>{selectedTech.phone || selectedTech.mobile_number || '—'}</span>
                  </p>
                  <p className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{selectedTech.email || '—'}</span>
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Authorized Services
                </h4>
                <div className="space-y-1">
                  {(selectedTech.approved_services || []).map((s) => (
                    <div
                      key={s.id || s.name}
                      className="p-2 bg-white border border-slate-200 rounded flex items-center justify-between"
                    >
                      <span className="font-medium text-slate-800">{s.name}</span>
                      <StatusBadge status="approved" size="xs" />
                    </div>
                  ))}
                  {(!selectedTech.approved_services || selectedTech.approved_services.length === 0) && (
                    <span className="text-slate-400 italic">No approved services</span>
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

export default AdminEmployeesPage;
