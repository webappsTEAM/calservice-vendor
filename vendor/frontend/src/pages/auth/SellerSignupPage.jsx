import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Store,
  Building2,
  User,
  MapPin,
  ShieldCheck,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowRight,
  Clock,
} from 'lucide-react';
import { apiGrocerySellerSignup } from '../../api/workforceService.js';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LegalComplianceModal } from '../../components/common/LegalComplianceModal.jsx';

export function SellerSignupPage() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    businessName: '',
    storeName: '',
    contactFirstName: '',
    contactLastName: '',
    mobileNumber: '',
    email: '',
    password: '',
    confirmPassword: '',
    address: '',
    city: 'Hosur',
    fssaiLicenseNumber: '',
    gstNumber: '',
    fssaiCertUrl: '',
    gstCertUrl: '',
    storePhotoUrl: '',
    panCardUrl: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedResult, setSubmittedResult] = useState(null);

  // Legal Modal
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState('contact');

  const openLegalModal = (tab = 'contact') => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (
      !formData.businessName.trim() ||
      !formData.contactFirstName.trim() ||
      !formData.mobileNumber.trim() ||
      !formData.email.trim() ||
      !formData.password
    ) {
      setError('Please fill in all mandatory contact and business fields.');
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

      const documents = {};
      if (formData.fssaiCertUrl.trim()) {
        documents.fssai_certificate = {
          title: 'FSSAI License Certificate',
          file_url: formData.fssaiCertUrl.trim(),
          document_number: formData.fssaiLicenseNumber.trim(),
        };
      }
      if (formData.gstCertUrl.trim()) {
        documents.gst_certificate = {
          title: 'GST Registration Certificate',
          file_url: formData.gstCertUrl.trim(),
          document_number: formData.gstNumber.trim(),
        };
      }
      if (formData.storePhotoUrl.trim()) {
        documents.store_photo = {
          title: 'Store Front & Signage Photo',
          file_url: formData.storePhotoUrl.trim(),
        };
      }
      if (formData.panCardUrl.trim()) {
        documents.pan_card = {
          title: 'Business / Proprietor PAN Card',
          file_url: formData.panCardUrl.trim(),
        };
      }

      const payload = {
        business_name: formData.businessName.trim(),
        store_name: formData.storeName.trim() || formData.businessName.trim(),
        contact_first_name: formData.contactFirstName.trim(),
        contact_last_name: formData.contactLastName.trim(),
        mobile_number: formData.mobileNumber.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        address: formData.address.trim(),
        city: formData.city.trim(),
        fssai_license_number: formData.fssaiLicenseNumber.trim(),
        gst_number: formData.gstNumber.trim(),
        documents: documents,
      };

      const res = await apiGrocerySellerSignup(payload);
      setSubmittedResult(res);
    } catch (err) {
      setError(err.message || 'Failed to submit grocery seller application.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // ── SUBMITTED / PENDING REVIEW CONFIRMATION STATE ──
  if (submittedResult) {
    return (
      <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans text-slate-900">
        <div className="sm:mx-auto sm:w-full sm:max-w-lg">
          <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-4 text-center">
            <div className="inline-flex w-10 h-10 rounded bg-amber-500 items-center justify-center text-white font-bold mx-auto shadow-sm">
              <Clock className="w-5 h-5" />
            </div>

            <div>
              <div className="inline-block mb-1">
                <StatusBadge status="under_review" />
              </div>
              <h1 className="text-lg font-bold text-slate-900">
                Seller Application Submitted
              </h1>
              <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                Thank you for registering <strong className="text-slate-800">{submittedResult.store_name || formData.businessName}</strong> with Sevo Seller Hub.
              </p>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded p-3.5 text-left space-y-2 text-xs">
              <div className="flex justify-between border-b border-slate-200/80 pb-2">
                <span className="text-slate-500">Application ID:</span>
                <span className="font-mono font-bold text-slate-800">#SEL-{submittedResult.application_id}</span>
              </div>
              <div className="flex justify-between border-b border-slate-200/80 py-2">
                <span className="text-slate-500">Store Name:</span>
                <span className="font-semibold text-slate-800">{submittedResult.store_name}</span>
              </div>
              <div className="flex justify-between border-b border-slate-200/80 py-2">
                <span className="text-slate-500">Review Pipeline:</span>
                <span className="font-medium text-emerald-700 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                  Admin Review Queue
                </span>
              </div>
              <div className="flex justify-between pt-1">
                <span className="text-slate-500">Status:</span>
                <span className="font-semibold text-amber-700 uppercase text-[11px]">
                  Under Verification
                </span>
              </div>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200/80 rounded text-left text-xs text-blue-800 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
              <p className="text-[11px] leading-relaxed">
                Our verification team is reviewing your regulatory credentials (FSSAI/GST). You will be able to access your store portal once your application is approved.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={() => navigate('/workforce/login')}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700 transition-colors cursor-pointer"
              >
                Return to Sign In
              </button>
              <button
                type="button"
                onClick={() => navigate('/workforce/create-account')}
                className="w-full px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs font-semibold border border-slate-300 transition-colors cursor-pointer"
              >
                Account Hub
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans text-slate-900">
      {/* ── LEGAL & COMPLIANCE MODAL ── */}
      <LegalComplianceModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />

      <div className="sm:mx-auto sm:w-full sm:max-w-lg text-center">
        <div className="inline-flex w-10 h-10 rounded bg-emerald-600 items-center justify-center text-white font-bold mb-2 shadow-sm">
          <Store className="w-5 h-5" />
        </div>
        <h1 className="text-xl font-bold text-slate-900 tracking-tight">
          Register on Sevo Seller Hub
        </h1>
        <p className="text-xs text-slate-500 mt-0.5">
          For grocery stores, supermarkets, and essential goods retailers
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-lg">
        <div className="bg-white border border-slate-200 rounded p-6 shadow-sm space-y-4">
          {error && <ErrorState message={error} onDismiss={() => setError('')} />}

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {/* ── SECTION 1: BUSINESS & STORE DETAILS ── */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5 pb-1 border-b border-slate-100">
                <Building2 className="w-3.5 h-3.5 text-slate-500" />
                <span>1. Business & Storefront Information</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Business / Legal Entity Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="businessName"
                    value={formData.businessName}
                    onChange={handleChange}
                    placeholder="e.g. Sri Krishna Traders Pvt Ltd"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Storefront Display Name
                  </label>
                  <input
                    type="text"
                    name="storeName"
                    value={formData.storeName}
                    onChange={handleChange}
                    placeholder="e.g. Krishna Supermarket"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* ── SECTION 2: CONTACT PERSON & CREDENTIALS ── */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5 pb-1 border-b border-slate-100">
                <User className="w-3.5 h-3.5 text-slate-500" />
                <span>2. Store Owner / Manager Contact</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    First Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    name="contactFirstName"
                    value={formData.contactFirstName}
                    onChange={handleChange}
                    placeholder="First name"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Last Name
                  </label>
                  <input
                    type="text"
                    name="contactLastName"
                    value={formData.contactLastName}
                    onChange={handleChange}
                    placeholder="Last name"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
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
                    placeholder="10-digit mobile number"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Official Email <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="seller@example.com"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

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
                      placeholder="Min 6 characters"
                      required
                      className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 pr-8"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 cursor-pointer"
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
                    placeholder="Re-enter password"
                    required
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* ── SECTION 3: LOCATION & COMPLIANCE ── */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5 pb-1 border-b border-slate-100">
                <MapPin className="w-3.5 h-3.5 text-slate-500" />
                <span>3. Location & Regulatory Compliance</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Store Street Address
                  </label>
                  <input
                    type="text"
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    placeholder="Shop No., Street, Landmark, Area"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    City / Operating Region
                  </label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    placeholder="Hosur"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    FSSAI License Number (14 digits)
                  </label>
                  <input
                    type="text"
                    name="fssaiLicenseNumber"
                    value={formData.fssaiLicenseNumber}
                    onChange={handleChange}
                    placeholder="e.g. 12421008000123"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    GST Number (GSTIN - Optional)
                  </label>
                  <input
                    type="text"
                    name="gstNumber"
                    value={formData.gstNumber}
                    onChange={handleChange}
                    placeholder="33AAAAA0000A1Z5"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500 uppercase font-mono"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    FSSAI Certificate File URL
                  </label>
                  <input
                    type="url"
                    name="fssaiCertUrl"
                    value={formData.fssaiCertUrl}
                    onChange={handleChange}
                    placeholder="https://... certificate URL"
                    className="w-full px-3 py-2 border border-slate-300 rounded text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* ── SUBMIT BUTTON ── */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded text-xs font-bold shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? (
                  <span>Submitting Application...</span>
                ) : (
                  <>
                    <span>Submit Seller Application for Review</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Cross-linking footer */}
          <div className="mt-4 pt-3 border-t border-slate-200 text-center space-y-1 text-xs text-slate-500">
            <p>
              Already registered?{' '}
              <Link to="/workforce/login" className="text-blue-600 font-bold hover:underline">
                Sign In
              </Link>
            </p>
            <p className="text-[11px]">
              Looking to register a service provider or technician?{' '}
              <Link to="/workforce/create-account" className="text-blue-600 font-semibold hover:underline">
                Account Selector
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SellerSignupPage;
