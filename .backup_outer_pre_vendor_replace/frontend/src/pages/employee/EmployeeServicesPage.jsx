import React, { useEffect, useState, useMemo } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetMySkills,
  apiGetOnboardingProfile,
  apiGetCatalog,
  apiRequestService,
  apiBulkRequestServices,
  apiRemoveService,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import {
  Wrench,
  Plus,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  Search,
  RotateCcw,
  Sparkles,
  Layers,
  Award,
  X,
} from 'lucide-react';

export function EmployeeServicesPage() {
  const { user, refreshProfile } = useAuth();
  const [skills, setSkills] = useState([]);
  const [profile, setProfile] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Add Service Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [selectedServiceIds, setSelectedServiceIds] = useState([]);
  const [catalogSearch, setCatalogSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionId, setActionId] = useState(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError('');
      const [skillsData, profData, catData] = await Promise.all([
        apiGetMySkills().catch(() => []),
        apiGetOnboardingProfile().catch(() => null),
        apiGetCatalog().catch(() => []),
      ]);
      setSkills(skillsData || []);
      setProfile(profData);
      setCatalog(catData || []);
    } catch (err) {
      setError(err.message || 'Failed to load your services & skills.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const requestedServices = useMemo(() => {
    return profile?.onboarding_data?.services || profile?.services || [];
  }, [profile]);

  // Combined list of approved skills and requested services
  const myServiceList = useMemo(() => {
    const map = new Map();

    // From skills
    skills.forEach((sk) => {
      map.set(sk.id || sk.name, {
        id: sk.id,
        name: sk.name || sk.skill_name,
        category: sk.category || 'General',
        status: sk.status || 'APPROVED',
        proficiency: sk.proficiency_level || 'INTERMEDIATE',
        isSkill: true,
      });
    });

    // From requested services
    requestedServices.forEach((svc) => {
      const key = svc.id || svc.name || svc.service_id;
      if (!map.has(key)) {
        map.set(key, {
          id: svc.id || svc.service_id,
          name: svc.name || svc.title,
          category: svc.category || 'General',
          status: svc.status || 'APPROVED',
          price: svc.base_price || svc.price,
          isSkill: false,
        });
      }
    });

    return Array.from(map.values());
  }, [skills, requestedServices]);

  // Catalog categories
  const categories = useMemo(() => {
    const set = new Set();
    catalog.forEach((item) => {
      if (item.category) set.add(item.category);
    });
    return ['ALL', ...Array.from(set)];
  }, [catalog]);

  const filteredCatalog = useMemo(() => {
    const existingNames = new Set(myServiceList.map((s) => s.name?.toLowerCase()));
    return catalog.filter((item) => {
      // Don't show already approved/requested services
      if (existingNames.has((item.name || item.title || '').toLowerCase())) return false;

      // Category filter
      if (selectedCategory !== 'ALL' && item.category !== selectedCategory) return false;

      // Search term
      const term = catalogSearch.toLowerCase().trim();
      if (
        term &&
        !(item.name || item.title || '').toLowerCase().includes(term) &&
        !(item.category || '').toLowerCase().includes(term)
      ) {
        return false;
      }

      return true;
    });
  }, [catalog, myServiceList, selectedCategory, catalogSearch]);

  const handleRequestSubmit = async (e) => {
    e.preventDefault();
    if (selectedServiceIds.length === 0) return;
    try {
      setIsSubmitting(true);
      setError('');
      await apiBulkRequestServices(selectedServiceIds);
      setSuccessMsg('Service request submitted to operations team for approval.');
      setShowAddModal(false);
      setSelectedServiceIds([]);
      await loadData();
      await refreshProfile();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to submit service request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRemoveService = async (serviceId, name) => {
    if (!window.confirm(`Are you sure you want to remove ${name} from your profile?`)) return;
    try {
      setActionId(serviceId);
      setError('');
      await apiRemoveService(serviceId);
      setSuccessMsg(`Removed ${name}.`);
      await loadData();
      await refreshProfile();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to remove service.');
    } finally {
      setActionId(null);
    }
  };

  const toggleCatalogSelect = (id) => {
    setSelectedServiceIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/employee/dashboard' }, { label: 'Services & Skills' }]}>
      <div className="space-y-5 max-w-5xl mx-auto">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Services & Skills"
            subtitle="Manage your authorized trade services, skills portfolio, and request new service categories"
          />
          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              type="button"
              onClick={loadData}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-3.5 py-2 min-h-[38px] bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-800 border border-slate-300 rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer"
            >
              <RotateCcw className={`w-3.5 h-3.5 text-slate-600 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setShowAddModal(true);
                setSelectedServiceIds([]);
                setCatalogSearch('');
                setSelectedCategory('ALL');
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 min-h-[38px] bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white rounded-lg text-xs font-bold shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4 text-slate-200" />
              <span>Request New Service</span>
            </button>
          </div>
        </div>

        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {successMsg && (
          <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-900 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Summary Card */}
        <div className="bg-white border border-slate-200/90 rounded-md p-5 shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-slate-100 border border-slate-200 text-slate-900 flex items-center justify-center shrink-0">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-950">Active Trade Qualifications</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                You are currently authorized to accept customer service requests for {myServiceList.length} trades.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs font-medium text-slate-600 shrink-0">
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-center min-w-[90px]">
              <span className="text-[10px] text-slate-500 block">Total Services</span>
              <strong className="text-sm font-bold text-slate-950 font-mono">{myServiceList.length}</strong>
            </div>
          </div>
        </div>

        {/* Services List */}
        {isLoading ? (
          <div className="bg-white border border-zinc-200/90 rounded-md p-12 shadow-card">
            <LoadingState message="Loading your service authorizations..." />
          </div>
        ) : myServiceList.length === 0 ? (
          <div className="bg-white border border-zinc-200/90 rounded-md p-12 text-center shadow-card space-y-3">
            <div className="w-12 h-12 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto text-zinc-400">
              <Wrench className="w-6 h-6" />
            </div>
            <h3 className="text-sm font-bold text-zinc-900">No Services Added</h3>
            <p className="text-xs text-zinc-500 max-w-sm mx-auto">
              You do not have any services approved on your roster profile yet. Request a service from the catalog to begin receiving dispatch jobs.
            </p>
            <button
              type="button"
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 min-h-[38px] bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg text-xs font-bold shadow-xs transition-all cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Browse Catalog</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {myServiceList.map((svc) => (
              <div
                key={svc.id || svc.name}
                className="bg-white border border-zinc-200/90 rounded-md p-4 shadow-card hover:border-zinc-300 transition-all flex flex-col justify-between space-y-3"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider bg-zinc-100 px-2 py-0.5 rounded">
                      {svc.category || 'General'}
                    </span>
                    <StatusBadge status={svc.status} />
                  </div>
                  <h4 className="text-sm font-bold text-zinc-950 mt-2 line-clamp-1">{svc.name}</h4>
                  {svc.proficiency && (
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      Proficiency: <span className="font-semibold text-zinc-800">{svc.proficiency}</span>
                    </p>
                  )}
                  {svc.price && (
                    <p className="text-xs font-mono font-bold text-zinc-950 mt-1">
                      Base: ₹{Number(svc.price).toLocaleString('en-IN')}
                    </p>
                  )}
                </div>

                <div className="pt-2 border-t border-zinc-100 flex items-center justify-between text-xs">
                  <span className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Eligible for Dispatch</span>
                  </span>
                  {svc.id && (
                    <button
                      type="button"
                      onClick={() => handleRemoveService(svc.id, svc.name)}
                      disabled={actionId === svc.id}
                      className="p-1 text-zinc-400 hover:text-rose-600 transition-colors cursor-pointer"
                      title="Remove service"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Request New Service Modal */}
        {showAddModal && (
          <div className="fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-white rounded-md shadow-modal max-w-2xl w-full p-6 space-y-4 border border-zinc-200/90 max-h-[90vh] flex flex-col">
              <div className="flex items-center justify-between border-b border-zinc-100 pb-3">
                <h3 className="text-sm font-bold text-zinc-950 flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-zinc-800" />
                  <span>Request New Services from Catalog</span>
                </h3>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="text-zinc-400 hover:text-zinc-700 p-1 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Filters */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <div className="relative flex-1 w-full">
                  <Search className="w-4 h-4 text-zinc-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={catalogSearch}
                    onChange={(e) => setCatalogSearch(e.target.value)}
                    placeholder="Search available trade catalog..."
                    className="w-full pl-9 pr-3 py-1.5 bg-zinc-50 border border-zinc-300 rounded-lg text-xs outline-none focus:bg-white focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                  />
                </div>
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="w-full sm:w-44 px-3 py-1.5 bg-zinc-50 border border-zinc-300 rounded-lg text-xs outline-none focus:bg-white focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                >
                  {categories.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat === 'ALL' ? 'All Categories' : cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Catalog Items Grid */}
              <div className="overflow-y-auto flex-1 pr-1 space-y-2 max-h-72">
                {filteredCatalog.length === 0 ? (
                  <div className="p-8 text-center text-xs text-zinc-500">
                    No new services found matching your filter criteria.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {filteredCatalog.map((item) => {
                      const isSelected = selectedServiceIds.includes(item.id);
                      return (
                        <div
                          key={item.id}
                          onClick={() => toggleCatalogSelect(item.id)}
                          className={`p-3 rounded-lg border text-xs cursor-pointer transition-all flex items-start justify-between gap-3 ${
                            isSelected
                              ? 'bg-zinc-900 text-white border-zinc-950 shadow-xs'
                              : 'bg-zinc-50 hover:bg-zinc-100 border-zinc-200 text-zinc-800'
                          }`}
                        >
                          <div className="space-y-0.5">
                            <span
                              className={`text-[9px] font-bold uppercase ${
                                isSelected ? 'text-zinc-300' : 'text-zinc-500'
                              }`}
                            >
                              {item.category || 'General'}
                            </span>
                            <h5 className="font-bold line-clamp-1">{item.name || item.title}</h5>
                            {item.base_price && (
                              <p className="font-mono text-[11px] opacity-90">
                                ₹{Number(item.base_price).toLocaleString('en-IN')}
                              </p>
                            )}
                          </div>
                          <div
                            className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 ${
                              isSelected
                                ? 'bg-white text-zinc-950 border-white'
                                : 'border-zinc-300 bg-white text-transparent'
                            }`}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5 fill-current" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="pt-3 border-t border-zinc-100 flex items-center justify-between">
                <span className="text-xs text-zinc-500 font-medium">
                  {selectedServiceIds.length} service(s) selected
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-4 py-2 min-h-[38px] border border-zinc-300 text-zinc-700 font-bold rounded-lg hover:bg-zinc-50 transition-all cursor-pointer shadow-xs text-xs"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={isSubmitting || selectedServiceIds.length === 0}
                    onClick={handleRequestSubmit}
                    className="px-4 py-2 min-h-[38px] bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white font-bold rounded-lg shadow-xs transition-all cursor-pointer disabled:opacity-50 text-xs flex items-center gap-2"
                  >
                    {isSubmitting && <RotateCcw className="w-3.5 h-3.5 animate-spin" />}
                    <span>Submit Request</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default EmployeeServicesPage;
