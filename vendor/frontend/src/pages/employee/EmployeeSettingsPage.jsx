import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import { useTheme, ACCENT_PALETTES } from '../../context/ThemeContext.jsx';
import {
  apiGetPreferences,
  apiSavePreferences,
  apiGetNotificationPreferences,
  apiSaveNotificationPreferences,
  apiChangePassword,
  apiChangeEmail,
  apiGet2FAStatus,
  apiToggle2FA,
  apiGetActiveSessions,
  apiGetLoginHistory,
  apiExportMyData,
  apiDeactivateAccount,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Modal } from '../../components/enterprise/Modal.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  Settings,
  Lock,
  Key,
  Shield,
  Palette,
  Bell,
  Download,
  AlertTriangle,
  CheckCircle2,
  Save,
  Laptop,
  Smartphone,
  History,
  Mail,
  Trash2,
  Eye,
  EyeOff,
  UserCheck,
  Moon,
  Sun,
  Layout,
  Type,
  Sparkles,
} from 'lucide-react';

export function EmployeeSettingsPage() {
  const { user, logout } = useAuth();
  const {
    accentColor,
    setAccentColor,
    themeMode,
    setThemeMode,
    density,
    setDensity,
    availablePalettes,
  } = useTheme();

  const [activeTab, setActiveTab] = useState('security');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // 1. Security States
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [emailCurrentPassword, setEmailCurrentPassword] = useState('');
  const [twoFaEnabled, setTwoFaEnabled] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [loginHistory, setLoginHistory] = useState([]);

  // 2. Appearance States
  const [appearance, setAppearance] = useState({
    theme: 'light',
    accent_color: 'blue',
    layout_density: 'comfortable',
    font_size: 'medium',
    high_contrast: false,
    reduced_motion: false,
  });

  // 3. Notification Preferences States
  const [notifications, setNotifications] = useState({
    security_alerts: true,
    login_alerts: true,
    job_assignments: true,
    weekly_digest: true,
    product_updates: false,
    workspace_announcements: true,
    channel_email: true,
    channel_in_app: true,
    channel_sms: false,
  });

  // 4. Privacy & Deactivation States
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);
  const [deactivatePassword, setDeactivatePassword] = useState('');
  const [deactivateReason, setDeactivateReason] = useState('');
  const [isDeactivating, setIsDeactivating] = useState(false);

  const loadSettingsData = async () => {
    try {
      setIsLoading(true);
      setError('');
      const [prefData, notifData, twoFaData, sessData, histData] = await Promise.all([
        apiGetPreferences().catch(() => null),
        apiGetNotificationPreferences().catch(() => null),
        apiGet2FAStatus().catch(() => ({ two_fa_enabled: false })),
        apiGetActiveSessions().catch(() => []),
        apiGetLoginHistory().catch(() => []),
      ]);

      if (prefData) {
        setAppearance({
          theme: prefData.theme || 'light',
          accent_color: prefData.accent_color || 'blue',
          layout_density: prefData.layout_density || 'comfortable',
          font_size: prefData.font_size || 'medium',
          high_contrast: Boolean(prefData.high_contrast),
          reduced_motion: Boolean(prefData.reduced_motion),
        });
      }

      if (notifData) {
        setNotifications((prev) => ({ ...prev, ...notifData }));
      }

      setTwoFaEnabled(Boolean(twoFaData?.two_fa_enabled));
      setSessions(sessData || []);
      setLoginHistory(histData || []);
    } catch (err) {
      setError('Failed to load settings from server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSettingsData();
  }, []);

  // Handlers
  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }

    try {
      setIsSaving(true);
      setError('');
      const res = await apiChangePassword(currentPassword, newPassword, confirmPassword);
      setSuccessMsg(res.message || 'Password updated successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update password.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleEmailChange = async (e) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError('');
      const res = await apiChangeEmail(emailCurrentPassword, newEmail);
      setSuccessMsg(res.message || 'Email address updated successfully.');
      setEmailCurrentPassword('');
      setNewEmail('');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update email address.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggle2FA = async () => {
    try {
      setIsSaving(true);
      setError('');
      const res = await apiToggle2FA();
      setTwoFaEnabled(res.two_fa_enabled);
      setSuccessMsg(res.message || 'Two-Factor Authentication updated.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update 2FA status.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveAppearance = async (e) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError('');
      const res = await apiSavePreferences(appearance);
      setSuccessMsg(res.message || 'Appearance preferences persisted.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to save appearance preferences.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSaveNotifications = async (e) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError('');
      const res = await apiSaveNotificationPreferences(notifications);
      setSuccessMsg(res.message || 'Notification preferences persisted.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to save notification preferences.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleExportData = async () => {
    try {
      setError('');
      const data = await apiExportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `workforce-dossier-export-${user?.username || 'employee'}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccessMsg('Operational data export downloaded successfully.');
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to export operational dossier.');
    }
  };

  const handleDeactivateSubmit = async (e) => {
    e.preventDefault();
    if (!deactivatePassword) return;

    try {
      setIsDeactivating(true);
      setError('');
      await apiDeactivateAccount(deactivatePassword, deactivateReason);
      setShowDeactivateModal(false);
      alert('Your account has been deactivated. Logging out now.');
      await logout();
    } catch (err) {
      setError(err.message || 'Account deactivation failed.');
    } finally {
      setIsDeactivating(false);
    }
  };

  const tabs = [
    { id: 'security', label: 'Account & Security', icon: Lock },
    { id: 'appearance', label: 'Appearance & UI', icon: Palette },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'privacy', label: 'Privacy & Data', icon: Shield },
  ];

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Settings' }]}>
        <LoadingState message="Loading workforce employee settings..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Settings' }]}>
      <div className="space-y-4 max-w-5xl mx-auto">
        {/* Alerts */}
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}
        {successMsg && (
          <div className="p-3 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Tab Navigation Header */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-1.5 shadow-card flex items-center gap-1.5 overflow-x-auto text-xs">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-2 px-4 py-2 min-h-[36px] rounded-lg font-bold transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-zinc-900 text-white shadow-xs'
                    : 'text-zinc-600 hover:text-zinc-950 hover:bg-zinc-100'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-zinc-400'}`} />
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>

        {/* ── TAB 1: ACCOUNT & SECURITY ── */}
        {activeTab === 'security' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Change Password Card */}
              <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card flex flex-col">
                <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 font-bold text-xs text-zinc-950 flex items-center gap-2">
                  <Key className="w-4 h-4 text-zinc-800" />
                  <span>Change Account Password</span>
                </div>
                <form onSubmit={handlePasswordChange} className="p-5 space-y-4 text-xs flex-1 flex flex-col justify-between">
                  <div className="space-y-3.5">
                    <div>
                      <label className="block text-zinc-700 font-bold mb-1">Current Password</label>
                      <input
                        type="password"
                        required
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-zinc-700 font-bold mb-1">New Password (min 6 chars)</label>
                      <input
                        type="password"
                        required
                        minLength={6}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                      />
                    </div>
                    <div>
                      <label className="block text-zinc-700 font-bold mb-1">Confirm New Password</label>
                      <input
                        type="password"
                        required
                        minLength={6}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                      />
                    </div>
                  </div>
                  <div className="pt-4 border-t border-zinc-100 flex justify-end">
                    <button
                      type="submit"
                      disabled={isSaving}
                      className="px-4 py-2 min-h-[38px] bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white font-bold rounded-lg text-xs transition-all shadow-xs disabled:opacity-50 inline-flex items-center gap-2 cursor-pointer"
                    >
                      <Save className="w-3.5 h-3.5" />
                      <span>{isSaving ? 'Updating...' : 'Update Password'}</span>
                    </button>
                  </div>
                </form>
              </div>

              {/* Change Email & 2FA Card */}
              <div className="space-y-4">
                {/* Change Email */}
                <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card">
                  <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 font-bold text-xs text-zinc-950 flex items-center gap-2">
                    <Mail className="w-4 h-4 text-zinc-800" />
                    <span>Update Email Address</span>
                  </div>
                  <form onSubmit={handleEmailChange} className="p-5 space-y-4 text-xs">
                    <div>
                      <label className="block text-zinc-700 font-bold mb-1">New Email Address</label>
                      <input
                        type="email"

                        required
                        value={newEmail}
                        onChange={(e) => setNewEmail(e.target.value)}
                        placeholder="new.email@example.com"
                        className="w-full border border-slate-300 rounded px-3 py-1.5 text-slate-800 text-xs focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-700 font-semibold mb-1">Confirm With Current Password</label>
                      <input
                        type="password"
                        required
                        value={emailCurrentPassword}
                        onChange={(e) => setEmailCurrentPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full border border-slate-300 rounded px-3 py-1.5 text-slate-800 text-xs focus:ring-1 focus:ring-blue-500"
                      />
                    </div>
                    <div className="pt-2 flex justify-end">
                      <button
                        type="submit"
                        disabled={isSaving}
                        className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded text-xs transition-colors shadow-sm disabled:opacity-50"
                      >
                        Update Email
                      </button>
                    </div>
                  </form>
                </div>

                {/* Two-Factor Authentication Toggle */}
                <div className="bg-white border border-slate-200 rounded p-4 shadow-sm flex items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                      <Shield className="w-4 h-4 text-emerald-600" />
                      <span className="font-bold text-slate-900 text-xs">Two-Factor Authentication (2FA)</span>
                    </div>
                    <p className="text-[11px] text-slate-500">
                      Require OTP verification code when signing in to your workforce account.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggle2FA}
                    disabled={isSaving}
                    className={`px-3 py-1.5 rounded text-xs font-bold transition-colors border ${
                      twoFaEnabled
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-300 hover:bg-emerald-100'
                        : 'bg-slate-100 text-slate-700 border-slate-300 hover:bg-slate-200'
                    }`}
                  >
                    {twoFaEnabled ? 'ENABLED ✓' : 'ENABLE 2FA'}
                  </button>
                </div>
              </div>
            </div>

            {/* Active Sessions & Authentic Login History */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Active Sessions */}
              <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
                <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 font-bold text-xs text-slate-800 flex items-center gap-2">
                  <Laptop className="w-4 h-4 text-blue-600" />
                  <span>Active Device Sessions ({sessions.length})</span>
                </div>
                <div className="divide-y divide-slate-100 text-xs">
                  {sessions.map((sess) => (
                    <div key={sess.id} className="p-3 flex items-center justify-between gap-2">
                      <div className="space-y-0.5">
                        <p className="font-bold text-slate-900">{sess.device}</p>
                        <p className="text-[10px] text-slate-500 font-mono">
                          IP: {sess.ip_address} • {sess.browser}
                        </p>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold text-[10px]">
                        CURRENT SESSION
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Login History */}
              <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm">
                <div className="bg-slate-50 px-4 py-3 border-b border-slate-200 font-bold text-xs text-slate-800 flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-600" />
                  <span>Recent Security & Presence Logs</span>
                </div>
                <div className="divide-y divide-slate-100 text-xs max-h-48 overflow-y-auto">
                  {loginHistory.length > 0 ? (
                    loginHistory.map((h) => (
                      <div key={h.id} className="p-2.5 px-4 flex items-center justify-between text-[11px]">
                        <div>
                          <span className="font-semibold text-slate-800">{h.event}</span>
                          <span className="text-slate-400 font-mono text-[10px] ml-2">IP: {h.ip}</span>
                        </div>
                        <span className="text-slate-500 font-mono text-[10px]">
                          {new Date(h.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="p-4 text-slate-500 text-center">No recent security history found.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: APPEARANCE & PREFERENCES ── */}
        {activeTab === 'appearance' && (
          <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card p-6 space-y-6">
            <div className="border-b border-zinc-200/80 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <Palette className="w-4 h-4 text-zinc-800" />
                  <span>Display & Accent Color Customizer</span>
                </h2>
                <p className="text-[11px] text-zinc-500 mt-0.5">
                  Select your primary accent highlight color and theme density. Changes apply instantly across the entire interface.
                </p>
              </div>
            </div>

            <form onSubmit={handleSaveAppearance} className="space-y-6 text-xs">
              {/* 1. Accent Color Palette Selector */}
              <div className="space-y-3">
                <label className="block text-zinc-800 font-bold text-xs uppercase tracking-wider">
                  Select Primary Accent & Secondary Highlight Color
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                  {Object.values(availablePalettes || ACCENT_PALETTES).map((pal) => {
                    const isSelected = accentColor === pal.id;
                    return (
                      <button
                        key={pal.id}
                        type="button"
                        onClick={() => {
                          setAccentColor(pal.id);
                          setAppearance((prev) => ({ ...prev, accent_color: pal.id }));
                        }}
                        className={`p-3.5 rounded-lg border text-left transition-all flex items-center gap-3 cursor-pointer shadow-xs ${
                          isSelected
                            ? 'border-slate-800 bg-slate-50 ring-2 ring-slate-800/20'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                        }`}
                      >
                        <div
                          className="w-7 h-7 rounded-full shadow-xs shrink-0 flex items-center justify-center text-white"
                          style={{ backgroundColor: pal.primary }}
                        >
                          {isSelected && <CheckCircle2 className="w-4 h-4 fill-white text-slate-900" />}
                        </div>
                        <div className="min-w-0">
                          <div className="font-bold text-slate-950 truncate text-xs">{pal.name}</div>
                          <div className="text-[10px] text-slate-400 font-mono uppercase">{pal.id}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 2. Theme Mode & Density Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                {/* Theme Mode */}
                <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-lg space-y-2">
                  <label className="block text-slate-800 font-bold flex items-center gap-1.5">
                    <Sun className="w-3.5 h-3.5 text-slate-600" />
                    <span>Interface Theme Mode</span>
                  </label>
                  <select
                    value={themeMode}
                    onChange={(e) => {
                      setThemeMode(e.target.value);
                      setAppearance((prev) => ({ ...prev, theme: e.target.value }));
                    }}
                    className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2 min-h-[38px] text-slate-900 text-xs focus:outline-none focus:ring-2 focus:ring-slate-800/10 focus:border-slate-700 shadow-xs"
                  >
                    <option value="light">Light Mode (Clean Slate & Neutral)</option>
                    <option value="dark">Dark Mode (Deep Slate & Steel)</option>
                    <option value="system">Follow System Appearance</option>
                  </select>
                </div>

                {/* Density */}
                <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-lg space-y-2">
                  <label className="block text-slate-800 font-bold flex items-center gap-1.5">
                    <Layout className="w-3.5 h-3.5 text-slate-600" />
                    <span>Layout Density</span>
                  </label>
                  <select
                    value={density}
                    onChange={(e) => {
                      setDensity(e.target.value);
                      setAppearance((prev) => ({ ...prev, layout_density: e.target.value }));
                    }}
                    className="w-full bg-white border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                  >
                    <option value="comfortable">Comfortable (Standard Touch-Friendly Spacing)</option>
                    <option value="compact">Compact (High-Density Data Grid)</option>
                  </select>
                </div>
              </div>

              {/* 3. Live UI Component Preview Card */}
              <div className="p-4 border border-zinc-200 rounded-lg bg-white space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-100 pb-2">
                  <span className="text-[11px] font-bold text-zinc-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-zinc-500" />
                    <span>Live Accent Preview</span>
                  </span>
                  <span className="badge-accent px-2.5 py-0.5 rounded-full text-[10px] font-bold">
                    Active Palette: {availablePalettes[accentColor]?.name || accentColor}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <button
                    type="button"
                    className="btn-accent px-4 py-2 min-h-[36px] font-bold text-xs rounded-lg shadow-xs cursor-pointer"
                  >
                    Primary Button
                  </button>
                  <button
                    type="button"
                    className="bg-accent-subtle text-accent-dynamic border border-accent-dynamic px-4 py-2 min-h-[36px] font-bold text-xs rounded-lg shadow-xs cursor-pointer"
                  >
                    Secondary Pill
                  </button>
                  <div className="inline-flex items-center gap-1.5 font-bold text-xs text-accent-dynamic">
                    <CheckCircle2 className="w-4 h-4 fill-current text-white" style={{ fill: 'var(--accent-primary)' }} />
                    <span>Verified Active Telemetry</span>
                  </div>
                </div>
              </div>

              {/* Toggles */}
              <div className="pt-2 border-t border-zinc-100 space-y-2.5">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={appearance.high_contrast}
                    onChange={(e) => setAppearance({ ...appearance, high_contrast: e.target.checked })}
                    className="w-4 h-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-950/20 cursor-pointer"
                  />
                  <span className="text-zinc-800 font-bold text-xs">Enable High Contrast Mode</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={appearance.reduced_motion}
                    onChange={(e) => setAppearance({ ...appearance, reduced_motion: e.target.checked })}
                    className="w-4 h-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-950/20 cursor-pointer"
                  />
                  <span className="text-zinc-800 font-bold text-xs">Reduce Animations & Transitions</span>
                </label>
              </div>

              <div className="pt-4 border-t border-zinc-100 flex justify-end">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-5 py-2.5 min-h-[40px] bg-zinc-900 hover:bg-zinc-800 text-white font-bold rounded-lg text-xs transition-all shadow-xs inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? 'Saving...' : 'Save Appearance Preferences'}</span>
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ── TAB 3: NOTIFICATIONS ── */}
        {activeTab === 'notifications' && (
          <div className="bg-white border border-slate-200 rounded overflow-hidden shadow-sm p-5 space-y-4">
            <div className="border-b border-slate-200 pb-3">
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-2">
                <Bell className="w-4 h-4 text-blue-600" />
                Notification Alerts & Communication Channels
              </h2>
              <p className="text-[11px] text-slate-500 mt-0.5">
                Configure operational alerts and authorized delivery channels.
              </p>
            </div>

            <form onSubmit={handleSaveNotifications} className="space-y-4 text-xs">
              {/* Delivery Channels */}
              <div className="bg-slate-50 border border-slate-200 rounded p-3.5 space-y-2">
                <h3 className="font-bold text-slate-900 text-xs">Active Notification Channels</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.channel_email}
                      onChange={(e) => setNotifications({ ...notifications, channel_email: e.target.checked })}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span className="font-medium text-slate-800">Email Notifications</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.channel_in_app}
                      onChange={(e) => setNotifications({ ...notifications, channel_in_app: e.target.checked })}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span className="font-medium text-slate-800">In-App Popups & Bell</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={notifications.channel_sms}
                      onChange={(e) => setNotifications({ ...notifications, channel_sms: e.target.checked })}
                      className="rounded text-blue-600 focus:ring-blue-500"
                    />
                    <span className="font-medium text-slate-800">SMS Text Alerts</span>
                  </label>
                </div>
              </div>

              {/* Alert Types */}
              <div className="space-y-3">
                <h3 className="font-bold text-slate-900 text-xs uppercase tracking-wider">Alert Subscriptions</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { key: 'job_assignments', label: 'Field Job Offers & Automatic Assignments', desc: 'Alert immediately when new service requests match your skills' },
                    { key: 'security_alerts', label: 'Security & Critical Account Alerts', desc: 'Notices on new logins, password changes, or 2FA updates' },
                    { key: 'workspace_announcements', label: 'Company & Operations Announcements', desc: 'Broad organizational updates from your workforce administrator' },
                    { key: 'weekly_digest', label: 'Weekly Summary & Performance Digest', desc: 'Weekly roundup of completed jobs and customer CSAT metrics' },
                    { key: 'product_updates', label: 'Product & Platform Enhancements', desc: 'New feature updates and technical enhancements' },
                  ].map((item) => (
                    <div key={item.key} className="p-3 border border-slate-200 rounded flex items-start gap-2.5 bg-slate-50/40">
                      <input
                        type="checkbox"
                        checked={notifications[item.key]}
                        onChange={(e) => setNotifications({ ...notifications, [item.key]: e.target.checked })}
                        className="mt-0.5 rounded text-blue-600 focus:ring-blue-500"
                      />
                      <div>
                        <p className="font-semibold text-slate-900 text-xs">{item.label}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded text-xs transition-colors shadow-sm inline-flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? 'Saving...' : 'Save Notification Settings'}</span>
                </button>
              </div>
            </form>
          </div>
        )}

        {/* ── TAB 4: PRIVACY & DATA ── */}
        {activeTab === 'privacy' && (
          <div className="space-y-4">
            {/* Export Data Card */}
            <div className="bg-white border border-slate-200 rounded p-5 shadow-sm space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Download className="w-4 h-4 text-blue-600" />
                    <h3 className="font-bold text-slate-900 text-xs">Export My Data & Records</h3>
                  </div>
                  <p className="text-[11px] text-slate-500 max-w-xl">
                    Download a structured export of your verified profile, skills, territory locations, and completed jobs history.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleExportData}
                  className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 border border-slate-300 font-bold rounded text-xs transition-colors shadow-sm inline-flex items-center gap-1.5 shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Export JSON</span>
                </button>
              </div>
            </div>

            {/* Account Deactivation Card */}
            <div className="bg-white border border-rose-200 rounded p-5 shadow-sm space-y-3">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <h3 className="font-bold text-rose-900 text-xs">Account Deactivation</h3>
                  </div>
                  <p className="text-[11px] text-slate-600 max-w-xl">
                    Safely deactivate your workforce account. Requires completion of all in-progress service requests. In accordance with enterprise audit rules, your operational and financial history is archived safely.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setShowDeactivateModal(true)}
                  className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded text-xs transition-colors shadow-sm inline-flex items-center gap-1.5 shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Deactivate Account</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Account Deactivation Modal */}
        <Modal
          isOpen={showDeactivateModal}
          onClose={() => setShowDeactivateModal(false)}
          title="Confirm Account Deactivation"
          icon={AlertTriangle}
          maxWidth="max-w-md"
        >
          <form onSubmit={handleDeactivateSubmit} className="space-y-3 text-xs">
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-rose-900 text-[11px]">
              <p className="font-bold mb-1">Warning: Account will become inactive immediately.</p>
              <p>You will no longer receive automated dispatch offers or be able to clock in for shifts.</p>
            </div>

            <div>
              <label className="block text-slate-700 font-semibold mb-1">Confirm Account Password</label>
              <input
                type="password"
                required
                value={deactivatePassword}
                onChange={(e) => setDeactivatePassword(e.target.value)}
                placeholder="Enter your current password..."
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-slate-800 text-xs focus:ring-1 focus:ring-rose-500"
              />
            </div>

            <div>
              <label className="block text-slate-700 font-semibold mb-1">Reason for Deactivation (Optional)</label>
              <textarea
                rows={2}
                value={deactivateReason}
                onChange={(e) => setDeactivateReason(e.target.value)}
                placeholder="Reason for departing or closing account..."
                className="w-full border border-slate-300 rounded px-3 py-1.5 text-slate-800 text-xs focus:ring-1 focus:ring-rose-500 resize-none"
              />
            </div>

            <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowDeactivateModal(false)}
                className="px-3 py-1.5 rounded border border-slate-300 text-slate-700 font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isDeactivating}
                className="px-4 py-1.5 rounded bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-sm disabled:opacity-50 inline-flex items-center gap-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{isDeactivating ? 'Deactivating...' : 'Confirm Deactivation'}</span>
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
}

export default EmployeeSettingsPage;
