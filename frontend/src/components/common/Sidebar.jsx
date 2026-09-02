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
  Landmark,
  Building2,
  Mail,
  UserPlus,
  Clock,
  Radio,
  Layers,
  Crown,
  UserCheck,
} from 'lucide-react';

export function Sidebar({ onCloseMobile = () => {} }) {
  const { user, isAdmin, isPlatformAdmin, isVendorAdmin, isEmployee, isTiedWorker, isSoloWorker, registrationStatus } = useAuth();
  const location = useLocation();

  // Collapsible sections state
  const [collapsed, setCollapsed] = useState({
    governance: false,
    workforce: false,
    operations: false,
    myWork: false,
    profile: false,
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

  // ─── 1. SEVO Platform Superadmin Sidebar ─────────────────────────────────────
  if (isPlatformAdmin) {
    return (
      <aside className="w-56 bg-white border-r border-slate-200 h-full flex flex-col overflow-y-auto text-xs select-none">
        <div className="p-3 space-y-4">
          {/* Platform Admin Badge */}
          <div className="p-2.5 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-900 flex items-center gap-2">
            <Crown className="w-4 h-4 text-indigo-600 shrink-0" />
            <div>
              <span className="font-bold text-[11px] block leading-tight">SEVO Platform Admin</span>
              <span className="text-[10px] text-indigo-600">Cross-Tenant Authority</span>
            </div>
          </div>

          {/* Home */}
          <div>
            <NavLink
              to="/workforce/admin"
              end
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <Home className="w-4 h-4 text-slate-500" />
              <span>Platform Dashboard</span>
            </NavLink>
          </div>

          {/* Group 1: PLATFORM GOVERNANCE */}
          <div>
            <button
              type="button"
              onClick={() => toggleSection('governance')}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider hover:text-slate-600 transition-colors"
            >
              <span>Platform Governance</span>
              {collapsed.governance ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {!collapsed.governance && (
              <div className="mt-1 space-y-0.5 pl-1">
                <NavLink
                  to="/workforce/platform/vendors"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Building2 className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Vendor Companies</span>
                </NavLink>
                <NavLink
                  to="/workforce/platform/workforce"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Users className="w-3.5 h-3.5 text-blue-600" />
                  <span>All Workforce (Solo/Tied)</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/applications"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <ClipboardList className="w-3.5 h-3.5 text-slate-400" />
                  <span>Application Approvals</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Group 2: GLOBAL OPERATIONS */}
          <div>
            <button
              type="button"
              onClick={() => toggleSection('operations')}
              className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-zinc-400 uppercase tracking-widest hover:text-zinc-700 transition-colors"
            >
              <span>Global Operations</span>
              {collapsed.operations ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {!collapsed.operations && (
              <div className="mt-1 space-y-0.5 pl-1">
                <NavLink
                  to="/workforce/admin/jobs"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                  <span>All Jobs</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/dispatch"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Send className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Global Dispatch</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/operations"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Navigation className="w-3.5 h-3.5 text-slate-400" />
                  <span>Live Fleet Tracking</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/services"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Wrench className="w-3.5 h-3.5 text-slate-400" />
                  <span>Service Catalog</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/skills"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Award className="w-3.5 h-3.5 text-slate-400" />
                  <span>Skills Master</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/wallet"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Wallet className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Platform Treasury</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/scorecards"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Award className="w-3.5 h-3.5 text-amber-500" />
                  <span>Scorecards</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/social-security"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Landmark className="w-3.5 h-3.5 text-blue-500" />
                  <span>Social Security</span>
                </NavLink>
              </div>
            )}
          </div>
        </div>

          {/* Reports & Settings */}
          <div className="space-y-0.5 pt-2 border-t border-slate-100">
            <NavLink
              to="/workforce/admin/reports"
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span>Platform Reports</span>
            </NavLink>
            <NavLink
              to="/workforce/admin/settings"
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <Settings className="w-3.5 h-3.5 text-slate-400" />
              <span>Settings</span>
            </NavLink>
          </div>
        </div>
      </aside>
    );
  }

  // ─── 2. Vendor Workspace Sidebar (Service Provider Business) ─────────────────
  if (isAdmin || isVendorAdmin) {
    return (
      <aside className="w-56 bg-white border-r border-slate-200 h-full flex flex-col overflow-y-auto text-xs select-none">
        <div className="p-3 space-y-4">
          {/* Vendor Company Header */}
          <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-blue-900 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-600 shrink-0" />
            <div className="overflow-hidden">
              <span className="font-bold text-[11px] block truncate">{user?.companyName || 'Vendor Business'}</span>
              <span className="text-[10px] text-blue-600">Company Portal</span>
            </div>
          </div>

          {/* Home */}
          <div>
            <NavLink
              to="/workforce/admin"
              end
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <Home className="w-4 h-4 text-slate-500" />
              <span>Company Home</span>
            </NavLink>
          </div>

          {/* Group 1: MY WORKFORCE */}
          <div>
            <button
              type="button"
              onClick={() => toggleSection('workforce')}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider hover:text-slate-600 transition-colors"
            >
              <span>My Workforce</span>
              {collapsed.workforce ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {!collapsed.workforce && (
              <div className="mt-1 space-y-0.5 pl-1">
                <NavLink
                  to="/workforce/admin/technician-network"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Users className="w-3.5 h-3.5 text-blue-600" />
                  <span>My Tied Technicians</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/vendor-invitations"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span>Send Invitations</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/employees"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                  <span>Employee Roster</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Group 2: COMPANY OPERATIONS */}
          <div>
            <button
              type="button"
              onClick={() => toggleSection('operations')}
              className="w-full flex items-center justify-between px-2 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider hover:text-slate-600 transition-colors"
            >
              <span>Operations</span>
              {collapsed.operations ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            {!collapsed.operations && (
              <div className="mt-1 space-y-0.5 pl-1">
                <NavLink
                  to="/workforce/admin/jobs"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                  <span>Company Jobs</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/dispatch"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Send className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Dispatch Technicians</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/operations"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Navigation className="w-3.5 h-3.5 text-slate-400" />
                  <span>Live Workforce</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/wallet"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Wallet className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Company Wallet</span>
                </NavLink>
                <NavLink
                  to="/workforce/admin/scorecards"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Award className="w-3.5 h-3.5 text-amber-500" />
                  <span>Performance Scorecards</span>
                </NavLink>
              </div>
            )}
          </div>

          {/* Reports & Settings */}
          <div className="space-y-0.5 pt-2 border-t border-slate-100">
            <NavLink
              to="/workforce/admin/reports"
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <BarChart3 className="w-3.5 h-3.5 text-slate-400" />
              <span>Company Reports</span>
            </NavLink>
            <NavLink
              to="/workforce/admin/settings"
              onClick={onCloseMobile}
              className={navItemClass}
            >
              <Settings className="w-3.5 h-3.5 text-slate-400" />
              <span>Company Settings</span>
            </NavLink>
          </div>
        </div>
      </aside>
    );
  }

  // ─── 3. Technician Sidebar (Field Worker / Employee) ─────────────────────────
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
            <p className="text-[10px] opacity-90 leading-tight">
              Operational modules unlock once approved.
            </p>
          </div>

          {/* Onboarding Navigation */}
          <div className="space-y-1">
            <div className="px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Application
            </div>
            <div className="mt-1 space-y-0.5 pl-1">
              <NavLink
                to={statusRoute}
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span>Registration Wizard</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/profile"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span>My Profile</span>
              </NavLink>
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

  // Approved Technician
  return (
    <aside className="w-60 bg-white border-r border-slate-200/90 h-full flex flex-col justify-between overflow-y-auto text-xs select-none shadow-xs">
      <div className="p-3.5 space-y-4">
        {/* Dashboard Link */}
        <div>
          <NavLink
            to="/workforce/employee/dashboard"
            end
            onClick={onCloseMobile}
            className={navItemClass}
          >
            <Home className="w-4 h-4 text-slate-500" />
            <span>Dashboard</span>
          </NavLink>
        </div>

        {/* Group 1: MY WORK */}
        <div>
          <button
            type="button"
            onClick={() => toggleSection('myWork')}
            className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-700 transition-colors"
          >
            <span>My Work</span>
            {collapsed.myWork ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {!collapsed.myWork && (
            <div className="mt-1 space-y-0.5 pl-1">
              <NavLink
                to="/workforce/employee/jobs"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Briefcase className="w-3.5 h-3.5 text-slate-400" />
                <span>My Jobs</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/vendor-network"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Building2 className="w-3.5 h-3.5 text-blue-600" />
                <span>My Vendor Assignment</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/invitations"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Mail className="w-3.5 h-3.5 text-indigo-500" />
                <span>Vendor Invitations</span>
              </NavLink>
              {isSoloWorker && (
                <NavLink
                  to="/workforce/employee/wallet"
                  onClick={onCloseMobile}
                  className={navItemClass}
                >
                  <Wallet className="w-3.5 h-3.5 text-emerald-500" />
                  <span>My Wallet (Solo)</span>
                </NavLink>
              )}
              <NavLink
                to="/workforce/employee/attendance"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Attendance & Time</span>
              </NavLink>
            </div>
          )}
        </div>

        {/* Group 2: PROFILE & SKILLS */}
        <div>
          <button
            type="button"
            onClick={() => toggleSection('profile')}
            className="w-full flex items-center justify-between px-2.5 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-700 transition-colors"
          >
            <span>Profile & Skills</span>
            {collapsed.profile ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
          {!collapsed.profile && (
            <div className="mt-1 space-y-0.5 pl-1">
              <NavLink
                to="/workforce/employee/profile"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span>My Profile</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/services"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Wrench className="w-3.5 h-3.5 text-slate-400" />
                <span>My Services</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/performance"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <Star className="w-3.5 h-3.5 text-amber-500" />
                <span>My Performance</span>
              </NavLink>
              <NavLink
                to="/workforce/employee/saved-locations"
                onClick={onCloseMobile}
                className={navItemClass}
              >
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>Saved Locations</span>
              </NavLink>
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
