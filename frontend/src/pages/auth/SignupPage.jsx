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
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-10 sm:px-6 lg:px-8 font-sans text-slate-900">
      {/* ── LEGAL & COMPLIANCE POPUP MODAL ── */}
      <LegalComplianceModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex w-10 h-10 rounded bg-blue-600 items-center justify-center text-white font-bold mb-2 shadow-sm">
          <Wrench className="w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Join the Workforce Platform
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Select your account type and start onboarding
        </p>
      </div>

      <div className={`mt-5 sm:mx-auto sm:w-full transition-all ${accountType === 'service_provider' ? 'sm:max-w-xl' : 'sm:max-w-md'}`}>
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-4">
          {error && <ErrorState message={error} onDismiss={() => setError('')} />}

          {/* ── 3-WAY ACCOUNT TYPE SELECTION (PHASE 2D) ── */}
          <div className="space-y-2">
            <label className="block text-[11px] font-bold text-slate-700">
              How will you work? <span className="text-rose-500">*</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {/* Option 1: Individual Technician */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('independent');
                  setSelectedProvider(null);
                  setError('');
                }}
                className={`p-3 rounded border text-left transition-all cursor-pointer ${
                  accountType === 'independent'
                    ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/40'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <User className={`w-4 h-4 ${accountType === 'independent' ? 'text-blue-600' : 'text-slate-500'}`} />
                  {accountType === 'independent' && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-800">Individual Technician</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Work independently & receive direct jobs</div>
              </button>

              {/* Option 2: Join a Service Provider */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('provider_technician');
                  setError('');
                }}
                className={`p-3 rounded border text-left transition-all cursor-pointer ${
                  accountType === 'provider_technician'
                    ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/40'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <Users className={`w-4 h-4 ${accountType === 'provider_technician' ? 'text-blue-600' : 'text-slate-500'}`} />
                  {accountType === 'provider_technician' && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-800">Join a Provider</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Work as a technician under a provider</div>
              </button>

              {/* Option 3: Service Provider */}
              <button
                type="button"
                onClick={() => {
                  setAccountType('service_provider');
                  setSelectedProvider(null);
                  setError('');
                }}
                className={`p-3 rounded border text-left transition-all cursor-pointer ${
                  accountType === 'service_provider'
                    ? 'border-blue-600 bg-blue-50/50 ring-1 ring-blue-600'
                    : 'border-slate-200 hover:border-slate-300 bg-slate-50/40'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <Building2 className={`w-4 h-4 ${accountType === 'service_provider' ? 'text-blue-600' : 'text-slate-500'}`} />
                  {accountType === 'service_provider' && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                  )}
                </div>
                <div className="text-xs font-bold text-slate-800">Service Provider</div>
                <div className="text-[10px] text-slate-500 mt-0.5">Register organization & manage roster</div>
              </button>
            </div>
          </div>

          {/* ── SERVICE PROVIDER SELECTOR (SHOWN ONLY FOR TECHNICIANS JOINING A PROVIDER) ── */}
          {accountType === 'provider_technician' && (
            <div className="p-3 bg-slate-50 rounded border border-slate-200 space-y-2">
              <label className="block text-[11px] font-bold text-slate-700">
                Select Service Provider Organization <span className="text-rose-500">*</span>
              </label>

              {selectedProvider ? (
                <div className="flex items-center justify-between p-2.5 bg-white rounded border border-blue-200 shadow-2xs">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-xs">
                      <Building2 className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">{selectedProvider.company_name}</div>
                      <div className="text-[10px] text-slate-500 flex items-center gap-1.5">
                        <span className="font-mono bg-slate-100 px-1 rounded text-slate-600">{selectedProvider.display_id}</span>
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
                    className="text-[11px] text-blue-600 font-semibold hover:underline cursor-pointer"
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
                      className="w-full pl-8 pr-2.5 py-1.5 text-xs bg-white border border-slate-300 rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                  </div>

                  {isDropdownOpen && (
                    <div className="absolute z-20 left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded shadow-lg divide-y divide-slate-100 text-xs">
                      {loadingProviders ? (
                        <div className="p-3 text-center text-slate-400 text-[11px]">Loading active providers...</div>
                      ) : providers.length === 0 ? (
                        <div className="p-3 text-center text-slate-500 text-[11px]">No active service providers found.</div>
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
                            className="w-full p-2.5 text-left hover:bg-blue-50 transition-colors flex items-center justify-between cursor-pointer"
                          >
                            <div>
                              <div className="font-semibold text-slate-800">{p.company_name}</div>
                              <div className="text-[10px] text-slate-500 font-mono">{p.display_id} {p.industry ? `• ${p.industry}` : ''}</div>
                            </div>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
                          </button>
                        ))
                      )}
                    </div>
                  )}
                </div>
              )}

              <p className="text-[10px] text-slate-500 italic">
                Note: Selecting a provider submits a join request. You will be officially affiliated once approved by their admin.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* ── ORGANIZATION DETAILS (ONLY FOR SERVICE PROVIDER ACCOUNT TYPE) ── */}
            {accountType === 'service_provider' && (
              <div className="p-3.5 bg-blue-50/40 rounded border border-blue-100 space-y-3">
                <div className="flex items-center gap-1.5 text-blue-900 font-bold text-xs pb-1 border-b border-blue-100">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  <span>Organization Information</span>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Service Provider Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="companyName"
                    value={providerData.companyName}
                    onChange={handleProviderChange}
                    placeholder="e.g. Apex Electrical Services LLC"
                    className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded"
                    required
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Industry / Category
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        name="industry"
                        value={providerData.industry}
                        onChange={handleProviderChange}
                        placeholder="e.g. Electrical & HVAC"
                        className="w-full pl-8 pr-2.5 py-1.5 bg-white border border-slate-300 rounded"
                      />
                      <Briefcase className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Website URL
                    </label>
                    <div className="relative">
                      <input
                        type="url"
                        name="website"
                        value={providerData.website}
                        onChange={handleProviderChange}
                        placeholder="https://example.com"
                        className="w-full pl-8 pr-2.5 py-1.5 bg-white border border-slate-300 rounded"
                      />
                      <Globe className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <div className="sm:col-span-1">
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Street Address
                    </label>
                    <input
                      type="text"
                      name="address"
                      value={providerData.address}
                      onChange={handleProviderChange}
                      placeholder="123 Tech Blvd"
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      City
                    </label>
                    <input
                      type="text"
                      name="city"
                      value={providerData.city}
                      onChange={handleProviderChange}
                      placeholder="City"
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      State / Province
                    </label>
                    <input
                      type="text"
                      name="state"
                      value={providerData.state}
                      onChange={handleProviderChange}
                      placeholder="State"
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-300 rounded"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ── ADMINISTRATOR OR TECHNICIAN ACCOUNT CREDENTIALS ── */}
            <div className="space-y-3">
              {accountType === 'service_provider' && (
                <div className="flex items-center gap-1.5 text-slate-800 font-bold text-xs pt-1 border-b border-slate-100 pb-1">
                  <ShieldCheck className="w-4 h-4 text-slate-600" />
                  <span>Primary Administrator Account</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    First Name <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="firstName"
                      value={formData.firstName}
                      onChange={handleFormChange}
                      placeholder="John"
                      className="w-full pl-8 pr-2.5 py-1.5"
                      required
                    />
                    <User className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                  </div>
                </div>
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Last Name
                  </label>
                  <input
                    type="text"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleFormChange}
                    placeholder="Doe"
                    className="w-full px-2.5 py-1.5"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    {accountType === 'service_provider' ? 'Admin Mobile / Phone' : 'Mobile Number'} <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="tel"
                      name="mobileNumber"
                      value={formData.mobileNumber}
                      onChange={handleFormChange}
                      placeholder="9876543210"
                      className="w-full pl-8 pr-2.5 py-1.5"
                      required
                    />
                    <Smartphone className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    {accountType === 'service_provider' ? 'Admin Email Address' : 'Email Address'} <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleFormChange}
                      placeholder="admin@example.com"
                      className="w-full pl-8 pr-2.5 py-1.5"
                      required
                    />
                    <Mail className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                  </div>
                </div>
              </div>

              {accountType === 'service_provider' && (
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Admin Username (optional)
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleFormChange}
                      placeholder="e.g. john_admin (defaults to email prefix)"
                      className="w-full pl-8 pr-2.5 py-1.5"
                    />
                    <User className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Password <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      value={formData.password}
                      onChange={handleFormChange}
                      placeholder="••••••••"
                      className="w-full pl-8 pr-7 py-1.5"
                      required
                    />
                    <Lock className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 focus:outline-none"
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
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Confirm Password <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      name="confirmPassword"
                      value={formData.confirmPassword}
                      onChange={handleFormChange}
                      placeholder="••••••••"
                      className="w-full pl-8 pr-7 py-1.5"
                      required
                    />
                    <Lock className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-2 top-2 text-slate-400 hover:text-slate-600 focus:outline-none"
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
              className="w-full mt-3 py-2 px-4 rounded bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-sm transition-colors disabled:opacity-50 cursor-pointer"
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

          <div className="pt-3 border-t border-slate-100 text-center">
            <p className="text-xs text-slate-500">
              Already have an account?{' '}
              <Link to="/workforce/login" className="text-blue-600 font-semibold hover:underline">
                Sign In
              </Link>
            </p>
          </div>
        </div>

        {/* ── FOOTER: PRIVACY, TERMS, SUPPORT & COMPLIANCE ── */}
        <footer className="w-full max-w-md mx-auto pt-6 pb-2 text-center">
          <div className="flex flex-wrap justify-center items-center gap-x-3 gap-y-1 text-[11px] text-slate-500 font-medium">
            <button
              type="button"
              onClick={() => openLegalModal('privacy')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <span className="text-slate-300">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('terms')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Terms of Service
            </button>
            <span className="text-slate-300">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('contact')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Support & Contact
            </button>
            <span className="text-slate-300">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('refunds')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Cancellation & Refunds
            </button>
            <span className="text-slate-300">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('shipping')}
              className="hover:text-blue-600 transition-colors cursor-pointer"
            >
              Service Delivery
            </button>
          </div>
          <p className="text-[10px] text-slate-400 mt-2">
            &copy; {new Date().getFullYear()} CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.
          </p>
        </footer>
      </div>
    </div>
  );
}

export default SignupPage;
