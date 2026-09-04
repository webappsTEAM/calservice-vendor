import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { Building2, Eye, EyeOff } from 'lucide-react';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';

// SEVO business plan Section 2, "Existing Service Provider Model": a
// service-provider business (not an individual technician) registers
// itself here, separately from the technician SignupPage. Backed by
// POST /workforce/provider/signup/ (ProviderSignupView), which creates a
// new Company + admin User + PROVIDER_HEAD wallet all at once.
export function ProviderSignupPage() {
  const { providerSignup } = useAuth();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    businessName: '',
    contactFirstName: '',
    contactLastName: '',
    mobileNumber: '',
    email: '',
    password: '',
    confirmPassword: '',
    address: '',
    city: 'Hosur',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.businessName.trim() || !formData.contactFirstName.trim() || !formData.mobileNumber.trim() || !formData.email.trim() || !formData.password) {
      setError('Please fill in all required fields.');
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

    try {
      setIsSubmitting(true);
      setError('');
      const res = await providerSignup({
        business_name: formData.businessName.trim(),
        contact_first_name: formData.contactFirstName.trim(),
        contact_last_name: formData.contactLastName.trim(),
        mobile_number: formData.mobileNumber.trim(),
        email: formData.email.trim(),
        password: formData.password,
        address: formData.address.trim(),
        city: formData.city.trim(),
      });
      // Show the invite link/company_id once, rather than navigating
      // straight away -- the business owner needs this to bring their
      // own workers onto the platform under the same company.
      setResult(res);
    } catch (err) {
      setError(err.message || 'Failed to create provider account.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (result) {
    const company = result.company || {};
    const inviteUrl = `${window.location.origin}/workforce/signup?company_id=${company.id}`;
    return (
      <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans text-slate-900">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-4 text-center">
            <div className="inline-flex w-10 h-10 rounded bg-emerald-600 items-center justify-center text-white font-bold mx-auto">
              <Building2 className="w-5 h-5" />
            </div>
            <h1 className="text-lg font-bold text-slate-900">{company.company_name} is registered</h1>
            <p className="text-xs text-slate-500">
              Share this link with your own workers so they join your team's wallet instead of
              signing up as independent technicians:
            </p>
            <div className="bg-slate-50 border border-slate-200 rounded p-3 text-xs font-mono break-all text-slate-700">
              {inviteUrl}
            </div>
            <button
              type="button"
              onClick={() => navigate('/workforce/admin')}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans text-slate-900">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex w-10 h-10 rounded bg-emerald-600 items-center justify-center text-white font-bold mb-2 shadow-sm">
          <Building2 className="w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Register Your Service Business
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          For plumbing, electrical, carpentry and other provider businesses with their own team
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-4">
          {error && <ErrorState message={error} onDismiss={() => setError('')} />}

          <form onSubmit={handleSubmit} className="space-y-3 text-xs">
            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Business Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                name="businessName"
                value={formData.businessName}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g. Ravi Plumbing Services"
              />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Contact First Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  name="contactFirstName"
                  value={formData.contactFirstName}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">Contact Last Name</label>
                <input
                  type="text"
                  name="contactLastName"
                  value={formData.contactLastName}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Mobile Number <span className="text-rose-500">*</span>
              </label>
              <input
                type="tel"
                name="mobileNumber"
                value={formData.mobileNumber}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">
                Email <span className="text-rose-500">*</span>
              </label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

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
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-2 text-slate-400"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 mb-1">
                  Confirm Password <span className="text-rose-500">*</span>
                </label>
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-bold text-slate-700 mb-1">City</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full px-4 py-2.5 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700 disabled:opacity-50"
            >
              {isSubmitting ? 'Creating account...' : 'Register Business'}
            </button>
          </form>

          <p className="text-[11px] text-center text-slate-500">
            Signing up as an individual technician instead?{' '}
            <Link to="/workforce/signup" className="text-blue-600 font-semibold">Sign up here</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
