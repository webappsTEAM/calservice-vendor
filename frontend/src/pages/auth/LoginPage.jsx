import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { Lock, User, Eye, EyeOff, HelpCircle, Power, CheckCircle2 } from 'lucide-react';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LegalComplianceModal } from '../../components/common/LegalComplianceModal.jsx';

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [logoutNotice, setLogoutNotice] = useState(() => {
    try {
      if (typeof sessionStorage !== 'undefined') {
        const raw = sessionStorage.getItem('wf_logout_notification');
        if (raw) {
          sessionStorage.removeItem('wf_logout_notification');
          const parsed = JSON.parse(raw);
          return parsed.message || 'Signed out successfully. Technician presence set to OFFLINE.';
        }
      }
    } catch (_) {}
    return '';
  });

  // Legal & Corporate Information Modal Popup
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState('contact');

  const openLegalModal = (tab = 'contact') => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setError('Please enter both username/email and password.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const user = await login(identifier.trim(), password);

      if (!user) {
        throw new Error('Authentication failed. Please check credentials.');
      }

      if (user.isAdmin) {
        navigate('/workforce/admin');
      } else {
        const regStatus = user.registrationStatus || 'not_started';
        if (regStatus === 'approved') {
          navigate('/workforce/employee/dashboard');
        } else if (regStatus === 'submitted' || regStatus === 'under_review') {
          navigate('/workforce/onboarding/pending-review');
        } else if (regStatus === 'correction_required') {
          navigate('/workforce/onboarding/corrections');
        } else if (regStatus === 'rejected') {
          navigate('/workforce/onboarding/rejected');
        } else {
          navigate('/workforce/onboarding/wizard');
        }
      }
    } catch (err) {
      if (typeof console !== 'undefined' && console.info) {
        console.info('[AUTH CLIENT]', {
          status: err.status,
          code: err.code,
          message: err.message,
        });
      }
      const serverMsg = err.data?.error || err.message;
      if (err.status === 401) {
        setError(serverMsg || 'Invalid credentials. Please verify your email/username and password.');
      } else if (err.status === 403 || err.code === 'ACCOUNT_INACTIVE') {
        setError(serverMsg || 'Account is inactive or deactivated. Please contact your administrator.');
      } else if (err.status === 503 || err.code === 'DB_UNAVAILABLE') {
        setError(serverMsg || 'Database service temporarily unavailable. Please retry shortly.');
      } else if (err.code === 'CREDENTIALS_REQUIRED') {
        setError(serverMsg || 'Identifier and password required.');
      } else if (err.code === 'NETWORK_ERROR') {
        setError('Network error. Please check your internet connection.');
      } else {
        setError(serverMsg || 'Unable to complete sign-in. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex bg-zinc-950 font-sans text-zinc-900 antialiased select-none">
      {/* ── LEGAL & COMPLIANCE POPUP MODAL ── */}
      <LegalComplianceModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />

      {/* ── LEFT: BRAND PANEL (Desktop Only) ── */}
      <div className="hidden lg:flex lg:w-5/12 xl:w-[42%] flex-col justify-between bg-zinc-950 text-white p-10 xl:p-14 border-r border-zinc-800">
        <div>
          <div className="text-sm font-bold tracking-widest text-zinc-200 uppercase">
            CAL SERVICES
          </div>
          <div className="text-xs text-zinc-400 font-semibold tracking-wide mt-0.5">
            Workforce Field Operations
          </div>
        </div>

        <div className="space-y-3">
          <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center text-white mb-4">
            <Lock className="w-5 h-5 text-zinc-300" />
          </div>
          <h1 className="text-2xl xl:text-3xl font-bold text-white tracking-tight">
            Field Operations & Engineering Network
          </h1>
          <p className="text-xs text-zinc-400 max-w-sm leading-relaxed">
            Enterprise dispatching, real-time spatial telemetry, and verified precision service delivery.
          </p>
        </div>

        {/* Desktop Left Brand Footer */}
        <div className="space-y-2 pt-6 border-t border-zinc-800/80">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-zinc-400">
            <button
              type="button"
              onClick={() => openLegalModal('terms')}
              className="hover:text-white transition-colors cursor-pointer"
            >
              Terms
            </button>
            <span className="text-zinc-600">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('privacy')}
              className="hover:text-white transition-colors cursor-pointer"
            >
              Privacy
            </button>
            <span className="text-zinc-600">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('contact')}
              className="hover:text-white transition-colors cursor-pointer"
            >
              Contact & Support
            </button>
            <span className="text-zinc-600">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('refunds')}
              className="hover:text-white transition-colors cursor-pointer"
            >
              Refunds
            </button>
            <span className="text-zinc-600">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('shipping')}
              className="hover:text-white transition-colors cursor-pointer"
            >
              Fulfillment
            </button>
          </div>
          <div className="text-[10px] text-zinc-500 font-normal">
            &copy; {new Date().getFullYear()} CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.
          </div>
        </div>
      </div>

      {/* ── RIGHT: LOGIN AREA WITH FOOTER ── */}
      <div className="flex-1 flex flex-col justify-between items-center p-4 sm:p-8 lg:p-12 bg-zinc-50/70 min-h-screen overflow-y-auto">
        {/* Top Spacer / Mobile Brand Badge */}
        <div className="w-full flex justify-between items-center lg:justify-end">
          <div className="lg:hidden text-xs font-bold text-zinc-900 uppercase tracking-wider">
            CAL SERVICES
          </div>
          <button
            type="button"
            onClick={() => openLegalModal('contact')}
            className="text-[11px] font-semibold text-zinc-600 hover:text-zinc-950 transition-colors flex items-center gap-1.5 cursor-pointer py-1 px-2.5 rounded-lg hover:bg-zinc-200/50"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Need Help? Contact Us</span>
          </button>
        </div>

        {/* Center Login Form Card - Medium sharp edge container */}
        <div className="w-full max-w-[400px] my-auto py-6">
          <div className="bg-white border border-zinc-200/90 rounded-md p-6 sm:p-8 shadow-card space-y-6">
            {/* Header */}
            <div>
              <div className="text-[11px] font-bold text-zinc-400 uppercase tracking-wider mb-1">
                Workforce Portal
              </div>
              <h2 className="text-xl font-bold text-zinc-950 tracking-tight">
                Employee Sign In
              </h2>
              <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
                Sign in to access your dispatch operations and assignments.
              </p>
            </div>

            {/* Logout Notification Banner */}
            {logoutNotice && (
              <div className="p-3 rounded-lg border border-zinc-300 bg-zinc-100 text-zinc-900 text-xs flex items-start gap-2.5 shadow-xs">
                <Power className="w-4 h-4 text-zinc-700 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-bold text-[11px] uppercase tracking-wide text-zinc-900">Status: OFFLINE</p>
                  <p className="text-[11px] text-zinc-700 mt-0.5">{logoutNotice}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setLogoutNotice('')}
                  className="text-zinc-400 hover:text-zinc-900 text-base font-bold leading-none ml-1 cursor-pointer"
                  aria-label="Dismiss"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Error Message */}
            {error && <ErrorState message={error} onDismiss={() => setError('')} />}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-xs font-semibold text-zinc-800 mb-1.5 tracking-tight">
                  Email, Username or Employee ID
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    placeholder="Enter your email, username, or ID"
                    className="w-full pl-9 pr-3 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
                    required
                    autoComplete="username"
                  />
                  <User className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-800 mb-1.5 tracking-tight">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full pl-9 pr-9 py-2 min-h-[38px] text-xs rounded-lg border border-zinc-300 text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs transition-all"
                    required
                    autoComplete="current-password"
                  />
                  <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none" />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 focus:outline-none p-0.5"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white font-semibold text-xs shadow-xs transition-all flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer min-h-[40px]"
              >
                {isSubmitting ? 'Signing In...' : 'Sign In'}
              </button>
            </form>

            {/* Footer Registration Link */}
            <div className="pt-4 border-t border-zinc-100 text-center">
              <p className="text-xs text-zinc-500">
                New technician?{' '}
                <Link
                  to="/workforce/signup"
                  className="text-zinc-950 font-bold hover:underline"
                >
                  Create Account
                </Link>
              </p>
            </div>
          </div>
        </div>

        {/* ── FOOTER: PRIVACY, TERMS, SUPPORT & COMPLIANCE ── */}
        <footer className="w-full pt-6 pb-2 text-center">
          <div className="flex flex-wrap justify-center items-center gap-x-3.5 gap-y-1.5 text-[11px] text-zinc-500 font-medium">
            <button
              type="button"
              onClick={() => openLegalModal('privacy')}
              className="text-zinc-500 hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Privacy Policy
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('terms')}
              className="text-zinc-500 hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Terms of Service
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('contact')}
              className="text-zinc-500 hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Support & Contact
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('refunds')}
              className="text-zinc-500 hover:text-zinc-900 transition-colors cursor-pointer"
            >
              Cancellation & Refunds
            </button>
            <span className="text-zinc-300 select-none">&bull;</span>
            <button
              type="button"
              onClick={() => openLegalModal('shipping')}
              className="text-zinc-500 hover:text-zinc-900 transition-colors cursor-pointer"
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

export default LoginPage;

