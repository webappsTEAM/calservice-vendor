import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  Wrench,
  Smartphone,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  Building2,
  CheckCircle2,
  Search,
  ArrowRight,
  Users,
  Briefcase,
  Globe,
  MapPin,
  ShieldCheck,
} from 'lucide-react';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LegalComplianceModal } from '../../components/common/LegalComplianceModal.jsx';
import { apiGetPublicServiceProviders } from '../../api/workforceService.js';

export function SignupPage() {
  const { signup, signupServiceProvider } = useAuth();
  const navigate = useNavigate();

  // 'independent' | 'provider_technician' | 'service_provider'
  const [accountType, setAccountType] = useState('independent');
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [providerSearch, setProviderSearch] = useState('');
  const [providers, setProviders] = useState([]);
  const [loadingProviders, setLoadingProviders] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // Common & Admin credentials
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    mobileNumber: '',
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
  });

  // Organization fields for Service Provider creation
  const [providerData, setProviderData] = useState({
    companyName: '',
    industry: '',
    companyPhone: '',
    companyEmail: '',
    address: '',
    city: '',
    state: '',
    country: 'US',
    website: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Legal Modal Popup
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState('contact');

  const openLegalModal = (tab = 'contact') => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  useEffect(() => {
    if (accountType === 'provider_technician') {
      fetchProviders();
    }
  }, [accountType]);

  const fetchProviders = async (search = '') => {
    try {
      setLoadingProviders(true);
      const data = await apiGetPublicServiceProviders({ search });
      setProviders(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load service providers:', err);
    } finally {
      setLoadingProviders(false);
    }
  };

  const handleProviderSearchChange = (e) => {
    const val = e.target.value;
    setProviderSearch(val);
    fetchProviders(val);
  };

  const handleFormChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleProviderChange = (e) => {
    setProviderData({ ...providerData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Shared credentials check
    if (!formData.firstName.trim() || !formData.mobileNumber.trim() || !formData.email.trim() || !formData.password) {
      setError('Please fill in all required personal credentials.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    // Branch 1: Service Provider Organization Creation
    if (accountType === 'service_provider') {
      if (!providerData.companyName.trim()) {
        setError('Service Provider Organization Name is required.');
        return;
      }

      try {
        setIsSubmitting(true);
        let website = providerData.website.trim();
        if (website && !website.startsWith('http://') && !website.startsWith('https://')) {
          website = 'https://' + website;
        }

        await signupServiceProvider({
          company_name: providerData.companyName.trim(),
          industry: providerData.industry.trim(),
          phone: providerData.companyPhone.trim() || formData.mobileNumber.trim(),
          email: providerData.companyEmail.trim() || formData.email.trim(),
          address: providerData.address.trim(),
          city: providerData.city.trim(),
          state: providerData.state.trim(),
          country: providerData.country || 'US',
          website: website,
          first_name: formData.firstName.trim(),
          last_name: formData.lastName.trim(),
          admin_email: formData.email.trim(),
          admin_phone: formData.mobileNumber.trim(),
          username: formData.username.trim() || undefined,
          password: formData.password,
          confirm_password: formData.confirmPassword,
        });

        navigate('/workforce/admin');
      } catch (err) {
        let msg = err.message || 'Failed to create Service Provider organization.';
        if (err.data?.error) {
          msg = err.data.error;
        } else if (err.data?.details && typeof err.data.details === 'object') {
          const entries = Object.entries(err.data.details);
          if (entries.length > 0) {
            const [field, fieldErrs] = entries[0];
            const cleanField = field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
            const firstDetail = Array.isArray(fieldErrs) ? fieldErrs[0] : fieldErrs;
            msg = `${cleanField}: ${firstDetail}`;
          }
        }
        setError(msg);
      } finally {
        setIsSubmitting(false);
      }
      return;
    }


    // Branch 2: Join an existing Service Provider as Technician
    if (accountType === 'provider_technician') {
      if (!selectedProvider) {
        setError('Please select an active Service Provider to join.');
        return;
      }

      try {
        setIsSubmitting(true);
        await signup({
          first_name: formData.firstName.trim(),
          last_name: formData.lastName.trim(),
          mobile_number: formData.mobileNumber.trim(),
          email: formData.email.trim(),
          password: formData.password,
          account_type: 'provider_technician',
          provider_id: selectedProvider.id,
        });

        navigate('/workforce/onboarding/wizard');
      } catch (err) {
        setError(err.message || 'Failed to submit provider join request.');
      } finally {
        setIsSubmitting(false);
      }
      return;
    }

    // Branch 3: Individual Independent Technician
    try {
      setIsSubmitting(true);
      await signup({
        first_name: formData.firstName.trim(),
        last_name: formData.lastName.trim(),
        mobile_number: formData.mobileNumber.trim(),
        email: formData.email.trim(),
        password: formData.password,
        account_type: 'independent',
        provider_id: null,
      });

      navigate('/workforce/onboarding/wizard');
    } catch (err) {
      setError(err.message || 'Failed to create workforce account.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-100/90 flex flex-col justify-center py-10 px-4 sm:px-6 lg:px-8 font-sans text-zinc-900 antialiased select-none">
      {/* ── LEGAL & COMPLIANCE POPUP MODAL ── */}
      <LegalComplianceModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex w-11 h-11 rounded-lg bg-zinc-950 items-center justify-center text-white font-bold mb-3 shadow-xs border border-zinc-800">
          <Wrench className="w-5 h-5 text-zinc-200" />
        </div>
        <h1 className="text-xl sm:text-2xl font-bold text-zinc-950 tracking-tight">
          Join the Workforce Platform
        </h1>
        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
          Select your account type and start workforce onboarding
        </p>
      </div>

      <div className={`mt-6 sm:mx-auto sm:w-full transition-all ${accountType === 'service_provider' ? 'sm:max-w-2xl' : 'sm:max-w-lg'}`}>
        <div className="bg-white border border-zinc-200/90 rounded-md p-6 sm:p-8 shadow-card space-y-5">
          {error && <ErrorState message={error} onDismiss={() => setError('')} />}

          {/* ── 3-WAY ACCOUNT TYPE SELECTION ── */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-zinc-800 tracking-tight">
              How will you work? <span className="text-rose-500 font-bold">*</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Option 1: Individual Technician */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('independent');
                  setSelectedProvider(null);
                  setError('');
                }}
                className={`p-3.5 rounded-lg border text-left transition-all cursor-pointer shadow-xs ${
                  accountType === 'independent'
                    ? 'border-slate-800 bg-slate-50 ring-1 ring-slate-800'
                    : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className={`p-1.5 rounded-md ${accountType === 'independent' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'}`}>
                    <User className="w-3.5 h-3.5" />
                  </div>
                  {accountType === 'independent' && (
                    <CheckCircle2 className="w-4 h-4 text-slate-900 stroke-[2.5]" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-900">Independent</div>
                <div className="text-[10px] text-slate-500 mt-0.5 leading-tight">Work independently & receive direct jobs</div>
              </button>

              {/* Option 2: Join a Service Provider */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('provider_technician');
                  setError('');
                }}
                className={`p-3.5 rounded-lg border text-left transition-all cursor-pointer shadow-xs ${
                  accountType === 'provider_technician'
                    ? 'border-slate-800 bg-slate-50 ring-1 ring-slate-800'
                    : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className={`p-1.5 rounded-md ${accountType === 'provider_technician' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'}`}>
                    <Users className="w-3.5 h-3.5" />
                  </div>
                  {accountType === 'provider_technician' && (
                    <CheckCircle2 className="w-4 h-4 text-slate-900 stroke-[2.5]" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-900">Join Provider</div>
                <div className="text-[10px] text-slate-500 mt-0.5 leading-tight">Work under an established provider</div>
              </button>

              {/* Option 3: Service Provider */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('service_provider');
                  setSelectedProvider(null);
                  setError('');
                }}
                className={`p-3.5 rounded-lg border text-left transition-all cursor-pointer shadow-xs ${
                  accountType === 'service_provider'
                    ? 'border-slate-800 bg-slate-50 ring-1 ring-slate-800'
                    : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/50'
                }`}
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className={`p-1.5 rounded-md ${accountType === 'service_provider' ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600'}`}>
                    <Building2 className="w-3.5 h-3.5" />
                  </div>
                  {accountType === 'service_provider' && (
                    <CheckCircle2 className="w-4 h-4 text-slate-900 stroke-[2.5]" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-900">Service Provider</div>
                <div className="text-[10px] text-slate-500 mt-0.5 leading-tight">Register provider company & roster</div>
              </button>
            </div>
          </div>

          {/* ── SERVICE PROVIDER SELECTOR (JOIN REQUEST) ── */}
          {accountType === 'provider_technician' && (
            <div className="p-4 bg-zinc-50 rounded-lg border border-zinc-200 space-y-2.5">
              <label className="block text-xs font-semibold text-zinc-800 tracking-tight">
                Select Service Provider Organization <span className="text-rose-500 font-bold">*</span>
              </label>

              {selectedProvider ? (
                <div className="flex items-center justify-between p-3 bg-white rounded-lg border border-zinc-300 shadow-xs">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-zinc-100 text-zinc-800 flex items-center justify-center font-bold text-xs">
                      <Building2 className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-zinc-900">{selectedProvider.company_name}</div>
                      <div className="text-[10px] text-zinc-500 flex items-center gap-1.5 mt-0.5">
                        <span className="font-mono bg-zinc-100 px-1 rounded text-zinc-700">{selectedProvider.display_id}</span>
                        {selectedProvider.industry && <span>&bull; {selectedProvider.industry}</span>}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedProvider(null);
                      setIsDropdownOpen(true);
                    }}
                    className="text-[11px] text-zinc-950 font-bold hover:underline cursor-pointer px-2.5 py-1 rounded-md hover:bg-zinc-100 transition-colors"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <div className="relative">
                    <input
                      type="text"
                      value={providerSearch}
                      onChange={handleProviderSearchChange}
                      onFocus={() => setIsDropdownOpen(true)}
                      placeholder="Search active providers by name or code..."
                      className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs bg-white border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
                    />
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>

                  {isDropdownOpen && (
                    <div className="absolute z-20 left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-zinc-200 rounded-lg shadow-modal divide-y divide-zinc-100 text-xs animate-in zoom-in-95 duration-100">
                      {loadingProviders ? (
                        <div className="p-4 text-center text-zinc-400 text-[11px]">Loading active providers...</div>
                      ) : providers.length === 0 ? (
                        <div className="p-4 text-center text-zinc-500 text-[11px]">No active service providers found.</div>
                      ) : (
                        providers.map((p) => (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => {
                              setSelectedProvider(p);
                              setIsDropdownOpen(false);
                              setProviderSearch('');
                              setError('');
                            }}
                            className="w-full p-3 text-left hover:bg-zinc-50 transition-colors flex items-center justify-between cursor-pointer"
                          >
                            <div>
                              <div className="font-bold text-zinc-900">{p.company_name}</div>
                              <div className="text-[10px] text-zinc-500 font-mono mt-0.5">{p.display_id} {p.industry ? `• ${p.industry}` : ''}</div>
                            </div>
                            <ArrowRight className="w-3.5 h-3.5 text-zinc-400" />
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              <p className="text-[10px] text-zinc-500 leading-relaxed">
                Note: Selecting a provider submits a join request. You will be officially affiliated once authorized by their administrator.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* ── ORGANIZATION DETAILS (ONLY FOR SERVICE PROVIDER ACCOUNT TYPE) ── */}
            {accountType === 'service_provider' && (
              <div className="p-4 bg-zinc-50 rounded-lg border border-zinc-200 space-y-3.5">
                <div className="flex items-center gap-2 text-zinc-950 font-bold text-xs pb-2 border-b border-zinc-200">
                  <Building2 className="w-4 h-4 text-zinc-700" />
                  <span>Company / Organization Details</span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    Service Provider Company Name <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <input
                    type="text"
                    name="companyName"
                    value={providerData.companyName}
                    onChange={handleProviderChange}
                    placeholder="e.g. Apex Engineering Services LLC"
                    className="w-full px-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                      Industry / Category
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        name="industry"
                        value={providerData.industry}
                        onChange={handleProviderChange}
                        placeholder="e.g. Electrical & HVAC"
                        className="w-full pl-9 pr-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                      />
                      <Briefcase className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                      Website URL
                    </label>
                    <div className="relative">
                      <input
                        type="url"
                        name="website"
                        value={providerData.website}
                        onChange={handleProviderChange}
                        placeholder="https://example.com"
                        className="w-full pl-9 pr-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                      />
                      <Globe className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="sm:col-span-1">
                    <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                      Street Address
                    </label>
                    <input
                      type="text"
                      name="address"
                      value={providerData.address}
                      onChange={handleProviderChange}
                      placeholder="123 Tech Blvd"
                      className="w-full px-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                      City
                    </label>
                    <input
                      type="text"
                      name="city"
                      value={providerData.city}
                      onChange={handleProviderChange}
                      placeholder="City"
                      className="w-full px-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                      State / Province
                    </label>
                    <input
                      type="text"
                      name="state"
                      value={providerData.state}
                      onChange={handleProviderChange}
                      placeholder="State"
                      className="w-full px-3 py-2 min-h-[38px] bg-white border border-zinc-300 rounded-lg text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ── ACCOUNT CREDENTIALS ── */}
            <div className="space-y-3.5">
              {accountType === 'service_provider' && (
                <div className="flex items-center gap-2 text-zinc-950 font-bold text-xs pt-1 border-b border-zinc-100 pb-2">
                  <ShieldCheck className="w-4 h-4 text-zinc-700" />
                  <span>Primary Administrator Credentials</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    First Name <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="firstName"
                      value={formData.firstName}
                      onChange={handleFormChange}
                      placeholder="John"
                      className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400"
                      required
                    />
                    <User className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    Last Name
                  </label>
                  <input
                    type="text"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleFormChange}
                    placeholder="Doe"
                    className="w-full px-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    {accountType === 'service_provider' ? 'Admin Phone' : 'Mobile Number'} <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="tel"
                      name="mobileNumber"
                      value={formData.mobileNumber}
                      onChange={handleFormChange}
                      placeholder="9876543210"
                      className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400"
                      required
                    />
                    <Smartphone className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    {accountType === 'service_provider' ? 'Admin Email' : 'Email Address'} <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleFormChange}
                      placeholder="admin@example.com"
                      className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400"
                      required
                    />
                    <Mail className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              {accountType === 'service_provider' && (
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    Admin Username (optional)
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleFormChange}
                      placeholder="e.g. john_admin (defaults to email prefix)"
                      className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400"
                    />
                    <User className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    Password <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      value={formData.password}
                      onChange={handleFormChange}
                      placeholder="••••••••"
                      className="w-full pl-9 pr-8 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900"
                      required
                    />
                    <Lock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 focus:outline-none p-0.5"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? (
                        <EyeOff className="w-3.5 h-3.5" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-800 mb-1 tracking-tight">
                    Confirm Password <span className="text-rose-500 font-bold">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleFormChange}
                      placeholder="••••••••"
                      className="w-full pl-9 pr-8 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900"
                      required
                    />
                    <Lock className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 focus:outline-none p-0.5"
                      aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="w-3.5 h-3.5" />
                      ) : (
                        <Eye className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-4 py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white font-bold text-xs shadow-xs transition-all disabled:opacity-50 cursor-pointer min-h-[40px]"
            >
              {isSubmitting
                ? 'Registering Account...'
                : accountType === 'service_provider'
                ? 'Create Service Provider & Enter Portal'
                : accountType === 'provider_technician'
                ? 'Submit Join Request & Start Onboarding'
                : 'Create Account & Start Onboarding'}
            </button>
          </form>

          <div className="pt-3.5 border-t border-zinc-100 text-center">
            <p className="text-xs text-zinc-500">
              Already have an account?{' '}
              <Link to="/workforce/login" className="text-zinc-950 font-bold hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>

        {/* ── FOOTER: PRIVACY, TERMS, SUPPORT & COMPLIANCE ── */}
        <footer className="w-full max-w-md mx-auto pt-6 pb-2 text-center">
          <div className="flex flex-wrap justify-center items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500 font-medium">
            <button
              type="button"
              onClick={() => openLegalModal('privacy')}
              className="hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('terms')}
              className="hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Terms of Service
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('contact')}
              className="hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Support & Contact
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('refunds')}
              className="hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Cancellation & Refunds
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('shipping')}
              className="hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Service Delivery
            </button>
          </div>
          <p className="text-[10px] text-zinc-400 mt-2">
            &copy; {new Date().getFullYear()} CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default SignupPage;

