import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { useTheme } from '../../context/ThemeContext.jsx';
import {
  Home,
  Users,
  ClipboardList,
  Wrench,
  Award,
  FileText,
  Briefcase,
  Send,
  Navigation,
  BarChart3,
  Settings,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  User,
  Star,
  MapPin,
  Wallet,
  ArrowDownCircle,
  CreditCard,
  ReceiptText,
  Activity,
  Calculator,
  Building2,
  Sparkles,
  Wind,
} from 'lucide-react';

export function Sidebar({ onCloseMobile = () => {} }) {
  const { user, isAdmin, isEmployee, registrationStatus } = useAuth();
  const { accent } = useTheme();
  const location = useLocation();

  // Collapsible sections state
  const [collapsed, setCollapsed] = useState({
    workforce: false,
    operations: false,
    finance: false,
    monitoring: false,
    myWork: false,
    profile: false,
    earnings: false,
  });

  const toggleSection = (section) => {
    setCollapsed((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const renderNavLink = (to, icon, label, badge = null, end = false) => {
    const Icon = icon;
    return (
      <NavLink
        key={to}
        to={to}
        end={end}
        onClick={onCloseMobile}
        className={({ isActive }) =>
          `group relative flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold transition-all select-none cursor-pointer ${
            isActive
              ? 'bg-slate-100/90 text-slate-900 font-bold shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
          }`
        }
      >
        {({ isActive }) => (
          <>
            <div className="flex items-center gap-2.5 min-w-0">
              <div
                className={`w-7 h-7 rounded-md flex items-center justify-center transition-all shrink-0 ${
                  isActive
                    ? 'bg-white shadow-xs border border-slate-200/90'
                    : 'text-slate-500 group-hover:text-slate-900 group-hover:bg-slate-100/80'
                }`}
                style={isActive ? { color: 'var(--accent-primary)' } : {}}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span className="truncate">{label}</span>
            </div>
            {isActive && (
              <span
                className="w-1.5 h-4 rounded-full shrink-0"
                style={{ backgroundColor: 'var(--accent-primary)' }}
              />
            )}
            {badge && !isActive && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-slate-100 text-slate-600 border border-slate-200">
                {badge}
              </span>
            )}
          </>
        )}
      </NavLink>
    );
  };

  // ── ADMIN SIDEBAR ──
  if (isAdmin) {
    return (
      <aside className="w-60 bg-white border-r border-slate-200/90 h-full flex flex-col justify-between overflow-y-auto text-xs select-none shadow-xs">
        <div className="p-3.5 space-y-4">
          {/* Top Home Link */}
          <div>
            {renderNavLink('/workforce/admin', Home, 'Overview', null, true)}
          </div>

          {/* Group 1: WORKFORCE */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => toggleSection('workforce')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-zinc-400 uppercase tracking-widest hover:text-zinc-700 transition-colors"
            >
              <span>Workforce</span>
              {collapsed.workforce ? (
                <ChevronRight className="w-3 h-3 text-zinc-400" />
              ) : (
                <ChevronDown className="w-3 h-3 text-zinc-400" />
              )}
            </button>
            {!collapsed.workforce && (
              <div className="space-y-0.5">
                {user?.isSuperadmin &&
                  renderNavLink('/workforce/admin/service-providers', Building2, 'Service Providers')}
                {user?.isServiceProviderAdmin &&
                  renderNavLink('/workforce/admin/provider-profile', Building2, 'Company Profile')}
                {renderNavLink('/workforce/admin/applications', ClipboardList, 'Applications')}
                {renderNavLink('/workforce/admin/employees', Users, 'Employees')}
                {renderNavLink('/workforce/admin/skills', Award, 'Skills & Trades')}
              </div>
            )}
          </div>

          {/* Group 2: OPERATIONS */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => toggleSection('operations')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-zinc-400 uppercase tracking-widest hover:text-zinc-700 transition-colors"
            >
              <span>Operations</span>
              {collapsed.operations ? (
                <ChevronRight className="w-3 h-3 text-zinc-400" />
              ) : (
                <ChevronDown className="w-3 h-3 text-zinc-400" />
              )}
            </button>
            {!collapsed.operations && (
              <div className="space-y-0.5">
                {renderNavLink('/workforce/admin/estimations', Wind, 'AC Estimations')}
                {renderNavLink('/workforce/admin/jobs', Briefcase, 'Field Jobs')}
                {renderNavLink('/workforce/admin/dispatch', Send, 'Dispatch Radar')}
              </div>
            )}
          </div>

          {/* Group 3: FINANCE & WALLET */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => toggleSection('finance')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-zinc-400 uppercase tracking-widest hover:text-zinc-700 transition-colors"
            >
              <span>Finance & Ledger</span>
              {collapsed.finance ? (
                <ChevronRight className="w-3 h-3 text-zinc-400" />
              ) : (
                <ChevronDown className="w-3 h-3 text-zinc-400" />
              )}
            </button>
            {!collapsed.finance && (
              <div className="space-y-0.5">
                {renderNavLink('/workforce/admin/wallet', Wallet, 'Wallet Governance')}
                {renderNavLink('/workforce/admin/wallet/transactions', ReceiptText, 'Transactions')}
                {renderNavLink('/workforce/admin/wallet/withdrawals', ArrowDownCircle, 'Withdrawals')}
                {renderNavLink('/workforce/admin/wallet/payout-accounts', CreditCard, 'Payout Accounts')}
              </div>
            )}
          </div>

          {/* Group 4: MONITORING & REPORTS */}
          <div className="space-y-1">
            <button
              type="button"
              onClick={() => toggleSection('monitoring')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-zinc-400 uppercase tracking-widest hover:text-zinc-700 transition-colors"
            >
              <span>Telemetry</span>
              {collapsed.monitoring ? (
                <ChevronRight className="w-3 h-3 text-zinc-400" />
              ) : (
                <ChevronDown className="w-3 h-3 text-zinc-400" />
              )}
            </button>
            {!collapsed.monitoring && (
              <div className="space-y-0.5">
                {renderNavLink('/workforce/admin/monitoring/database-egress', Activity, 'Database & Egress')}
                {renderNavLink('/workforce/admin/reports', BarChart3, 'Reports & Audits')}
              </div>
            )}
          </div>
        </div>

        {/* Admin Footer Settings */}
        <div className="p-3 border-t border-zinc-100">
          {renderNavLink('/workforce/admin/settings', Settings, 'System Settings')}
        </div>
      </aside>
    );
  }

  // ── ONBOARDING EMPLOYEE SIDEBAR ──
  const isApproved = registrationStatus === 'approved';

  if (!isApproved) {
    let statusText = 'Registration Wizard';
    let statusBadgeColor = 'bg-amber-50 text-amber-900 border-amber-200/90';
    let statusRoute = '/workforce/onboarding/wizard';

    if (registrationStatus === 'submitted' || registrationStatus === 'under_review') {
      statusText = 'Under Review';
      statusBadgeColor = 'bg-zinc-100 text-zinc-900 border-zinc-300';
      statusRoute = '/workforce/onboarding/pending-review';
    } else if (registrationStatus === 'correction_required') {
      statusText = 'Action Required';
      statusBadgeColor = 'bg-amber-50 text-amber-900 border-amber-300';
      statusRoute = '/workforce/onboarding/corrections';
    } else if (registrationStatus === 'rejected') {
      statusText = 'Application Declined';
      statusBadgeColor = 'bg-rose-50 text-rose-900 border-rose-200/90';
      statusRoute = '/workforce/onboarding/rejected';
    }

    return (
      <aside className="w-60 bg-white border-r border-slate-200/90 h-full flex flex-col justify-between overflow-y-auto text-xs select-none shadow-xs">
        <div className="p-3.5 space-y-4">
          {/* Status Banner */}
          <div className={`p-3.5 rounded-lg border text-[11px] font-medium space-y-1.5 ${statusBadgeColor}`}>
            <p className="font-bold flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 shrink-0" />
              <span>{statusText}</span>
            </p>
            <p className="text-[10px] opacity-80 leading-relaxed">
              Operational modules unlock once Admin verifies your credentials.
            </p>
          </div>

          {/* Onboarding Navigation */}
          <div className="space-y-1">
            <div className="px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Application
            </div>
            <div className="space-y-0.5">
              {renderNavLink(statusRoute, FileText, statusText)}
              {renderNavLink('/workforce/employee/profile', User, 'My Profile')}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-100">
          {renderNavLink('/workforce/employee/settings', Settings, 'Settings')}
        </div>
      </aside>
    );
  }

  // ── APPROVED TECHNICIAN EMPLOYEE SIDEBAR ──
  return (
    <aside className="w-60 bg-white border-r border-slate-200/90 h-full flex flex-col justify-between overflow-y-auto text-xs select-none shadow-xs">
      <div className="p-3.5 space-y-4">
        {/* Dashboard Link */}
        <div>
          {renderNavLink('/workforce/employee/dashboard', Home, 'Dashboard', null, true)}
        </div>

        {/* Group 1: MY WORK */}
        <div className="space-y-1">
          <button
            type="button"
            onClick={() => toggleSection('myWork')}
            className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-700 transition-colors"
          >
            <span>My Work</span>
            {collapsed.myWork ? (
              <ChevronRight className="w-3 h-3 text-zinc-400" />
            ) : (
              <ChevronDown className="w-3 h-3 text-zinc-400" />
            )}
          </button>
          {!collapsed.myWork && (
            <div className="space-y-0.5">
              {renderNavLink('/workforce/employee/jobs', Briefcase, 'Jobs')}
              {renderNavLink('/workforce/employee/estimates', Calculator, 'Estimates')}
              {renderNavLink('/workforce/employee/performance', Star, 'Performance')}
            </div>
          )}
        </div>

        {/* Group 2: PROFILE & CREDENTIALS */}
        <div className="space-y-1">
          <button
            type="button"
            onClick={() => toggleSection('profile')}
            className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-700 transition-colors"
          >
            <span>Credentials</span>
            {collapsed.profile ? (
              <ChevronRight className="w-3 h-3 text-slate-400" />
            ) : (
              <ChevronDown className="w-3 h-3 text-slate-400" />
            )}
          </button>
          {!collapsed.profile && (
            <div className="space-y-0.5">
              {renderNavLink('/workforce/employee/profile', User, 'My Profile')}
              {renderNavLink('/workforce/employee/documents', ShieldCheck, 'Documents')}
              {renderNavLink('/workforce/employee/services', Wrench, 'Services & Skills')}
              {renderNavLink('/workforce/employee/location', MapPin, 'Locations')}
            </div>
          )}
        </div>

        {/* Group 3: EARNINGS & WALLET */}
        <div className="space-y-1">
          <button
            type="button"
            onClick={() => toggleSection('earnings')}
            className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-700 transition-colors"
          >
            <span>Earnings & Wallet</span>
            {collapsed.earnings ? (
              <ChevronRight className="w-3 h-3 text-slate-400" />
            ) : (
              <ChevronDown className="w-3 h-3 text-slate-400" />
            )}
          </button>
          {!collapsed.earnings && (
            <div className="space-y-0.5">
              {renderNavLink('/workforce/employee/wallet', Wallet, 'Wallet')}
              {renderNavLink('/workforce/employee/wallet/transactions', ReceiptText, 'Transactions')}
              {renderNavLink('/workforce/employee/wallet/withdrawals', ArrowDownCircle, 'Withdrawals')}
              {renderNavLink('/workforce/employee/wallet/payout-accounts', CreditCard, 'Bank Accounts')}
            </div>
          )}
        </div>
      </div>

      {/* Footer Settings */}
      <div className="p-3 border-t border-slate-100">
        {renderNavLink('/workforce/employee/settings', Settings, 'Settings')}
      </div>
    </aside>
  );
}

export default Sidebar;
