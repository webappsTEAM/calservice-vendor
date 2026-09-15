import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetMyProfile,
  apiUpdateMyProfile,
  apiUploadAvatar,
  apiGetChangeRequests,
  apiSubmitChangeRequest,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Modal } from '../../components/enterprise/Modal.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  User,
  Camera,
  ShieldAlert,
  Lock,
  Edit3,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  Save,
  Send,
  Building,
  Calendar,
  Phone,
  Mail,
  Globe,
  Briefcase,
} from 'lucide-react';

export function EmployeeProfilePage() {
  const { user, refreshProfile } = useAuth();

  const [profile, setProfile] = useState(null);
  const [changeRequests, setChangeRequests] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Editable fields state
  const [editableForm, setEditableForm] = useState({
    phone: '',
    bio: '',
    timezone: 'UTC',
    language: 'en',
  });

  // Change request modal state
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [targetField, setTargetField] = useState('first_name');
  const [newValue, setNewValue] = useState('');
  const [changeReason, setChangeReason] = useState('');
  const [isSubmittingCR, setIsSubmittingCR] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError('');
      const [profData, crData] = await Promise.all([
        apiGetMyProfile().catch(() => null),
        apiGetChangeRequests().catch(() => []),
      ]);

      if (profData) {
        setProfile(profData);
        setEditableForm({
          phone: profData.phone || profData.mobile_number || '',
          bio: profData.bio || '',
          timezone: profData.timezone || 'UTC',
          language: profData.language || 'en',
        });
      }
      setChangeRequests(crData || []);
    } catch (err) {
      setError(err.message || 'Failed to load profile data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSavePreferences = async (e) => {
    e.preventDefault();
    try {
      setIsSaving(true);
      setError('');
      const res = await apiUpdateMyProfile(editableForm);
      setSuccessMsg(res.message || 'Profile updated successfully.');
      if (res.profile) setProfile(res.profile);
      await refreshProfile();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update profile preferences.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploadingAvatar(true);
      setError('');
      const res = await apiUploadAvatar(file);
      setSuccessMsg(res.message || 'Avatar photo updated successfully.');
      await loadData();
      await refreshProfile();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to upload profile photo.');
    } finally {
      setIsUploadingAvatar(false);
    }
  };

  const handleSubmitChangeRequest = async (e) => {
    e.preventDefault();
    if (!newValue.trim() || !changeReason.trim()) {
      setError('Please provide the new value and a valid business reason.');
      return;
    }

    try {
      setIsSubmittingCR(true);
      setError('');
      await apiSubmitChangeRequest({
        field_name: targetField,
        new_value: newValue.trim(),
        reason: changeReason.trim(),
      });
      setShowChangeModal(false);
      setNewValue('');
      setChangeReason('');
      setSuccessMsg('Employee Change Request submitted for Workforce Admin review.');
      const updatedCRs = await apiGetChangeRequests().catch(() => []);
      setChangeRequests(updatedCRs);
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to submit change request.');
    } finally {
      setIsSubmittingCR(false);
    }
  };

  const openChangeRequestModal = (fieldKey) => {
    setTargetField(fieldKey);
    setNewValue('');
    setChangeReason('');
    setShowChangeModal(true);
  };

  const isControlledLocked = Boolean(profile?.controlled_fields?.is_locked);

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'My Profile' }]}>
        <LoadingState message="Loading authentic employee profile..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'My Profile' }]}>
      <div className="space-y-4 max-w-5xl mx-auto">
        {/* Header Notification Banner */}
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}
        {successMsg && (
          <div className="p-3 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Profile Header Card */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card">
          <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
            {/* Avatar with Upload Badge */}
            <div className="relative group">
              <div className="w-20 h-20 rounded-full border-2 border-zinc-200 overflow-hidden bg-zinc-100 flex items-center justify-center text-zinc-700 font-bold text-xl shadow-xs">
                {profile?.avatar ? (
                  <img src={profile.avatar} alt="Avatar" className="w-full h-full object-cover" />
                ) : (
                  <span>{user?.firstName ? user.firstName[0].toUpperCase() : 'T'}</span>
                )}
              </div>
              <label
                htmlFor="avatar-upload"
                className="absolute bottom-0 right-0 p-1.5 bg-slate-800 hover:bg-slate-700 text-white rounded-full cursor-pointer shadow-md transition-transform transform active:scale-95"
                title="Change Photo"
              >
                <Camera className="w-3.5 h-3.5" />
                <input
                  id="avatar-upload"
                  type="file"
                  accept="image/*"
                  onChange={handleAvatarFileChange}
                  disabled={isUploadingAvatar}
                  className="hidden"
                />
              </label>
            </div>

            {/* Profile Overview */}
            <div className="flex-1 text-center sm:text-left space-y-1.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h1 className="text-lg font-bold text-zinc-950 tracking-tight">
                    {profile?.first_name} {profile?.last_name}
                  </h1>
                  <p className="text-xs text-zinc-500 font-medium">
                    {profile?.title || 'Certified Technician'} • {profile?.company_name || 'CalServices'}
                  </p>
                </div>
                <div className="flex items-center justify-center sm:justify-end gap-2">
                  <StatusBadge
                    status={profile?.registration_status || 'not_started'}
                    label={`Dossier: ${(profile?.registration_status || 'not_started').toUpperCase()}`}
                  />
                  <StatusBadge
                    status={profile?.is_online ? 'online' : 'offline'}
                    label={profile?.is_online ? 'ONLINE' : 'OFFLINE'}
                  />
                </div>
              </div>

              <div className="pt-3 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs text-zinc-600 border-t border-zinc-100 mt-2">
                <div className="flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span>ID: <strong className="text-zinc-950 font-mono">{profile?.employee_id || user?.username}</strong></span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span className="truncate">{profile?.email}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                  <span>{profile?.mobile_number || profile?.phone || '—'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left Column: Personal Preferences Form (5 cols) */}
          <div className="lg:col-span-5 bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card flex flex-col">
            <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 flex items-center justify-between">
              <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                <Edit3 className="w-4 h-4 text-zinc-800" />
                <span>Personal Preferences</span>
              </h2>
              <span className="text-[10px] text-emerald-900 font-bold bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
                Directly Editable
              </span>
            </div>

            <form onSubmit={handleSavePreferences} className="p-5 space-y-4 text-xs flex-1 flex flex-col justify-between">
              <div className="space-y-3.5">
                <div>
                  <label className="block text-zinc-700 font-bold mb-1">Contact Phone</label>
                  <input
                    type="text"
                    value={editableForm.phone}
                    onChange={(e) => setEditableForm({ ...editableForm, phone: e.target.value })}
                    placeholder="e.g. +91 9876543210"
                    className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
                  />
                  <p className="text-[10px] text-zinc-400 mt-1">Used for dispatch communications.</p>
                </div>

                <div>
                  <label className="block text-zinc-700 font-bold mb-1">Professional Bio / Notes</label>
                  <textarea
                    rows={3}
                    value={editableForm.bio}
                    onChange={(e) => setEditableForm({ ...editableForm, bio: e.target.value })}
                    placeholder="Short bio or technician specialization summary..."
                    className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs resize-none"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-zinc-700 font-bold mb-1">Timezone</label>
                    <select
                      value={editableForm.timezone}
                      onChange={(e) => setEditableForm({ ...editableForm, timezone: e.target.value })}
                      className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs bg-white"
                    >
                      <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                      <option value="UTC">UTC (Universal Time)</option>
                      <option value="America/New_York">America/New_York (EST)</option>
                      <option value="America/Los_Angeles">America/Los_Angeles (PST)</option>
                      <option value="Europe/London">Europe/London (GMT)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-zinc-700 font-bold mb-1">Language</label>
                    <select
                      value={editableForm.language}
                      onChange={(e) => setEditableForm({ ...editableForm, language: e.target.value })}
                      className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs bg-white"
                    >
                      <option value="en">English (US/UK)</option>
                      <option value="hi">Hindi (हिंदी)</option>
                      <option value="es">Spanish (Español)</option>
                      <option value="ta">Tamil (தமிழ்)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-100 flex justify-end">
                <button
                  type="submit"
                  disabled={isSaving}
                  className="px-4 py-2 min-h-[38px] bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white font-bold text-xs rounded-lg transition-all shadow-xs inline-flex items-center gap-2 disabled:opacity-50 cursor-pointer"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{isSaving ? 'Saving...' : 'Save Preferences'}</span>
                </button>
              </div>
            </form>
          </div>


          {/* Right Column: Controlled Registration Information (7 cols) */}
          <div className="lg:col-span-7 bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card flex flex-col">
            <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 flex items-center justify-between">
              <div>
                <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <Lock className="w-3.5 h-3.5 text-amber-700" />
                  <span>Verified Identity & Employment Info</span>
                </h2>
              </div>
              <span className="text-[10px] text-amber-900 font-bold bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                Admin Verified
              </span>
            </div>

            <div className="p-5 space-y-3.5 text-xs flex-1">
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-[11px] text-amber-900 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold">Verified Data Governance Policy</p>
                  <p className="text-amber-800 mt-0.5 leading-relaxed">
                    Legal identity, date of birth, company assignment, and bank details require an <strong>Employee Change Request</strong> with Admin verification before updating.
                  </p>
                </div>
              </div>

              {/* Grid of Controlled Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">Legal First Name</span>
                    <p className="font-bold text-zinc-950 text-xs">{profile?.first_name || '—'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('first_name')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>

                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">Legal Last Name</span>
                    <p className="font-bold text-zinc-950 text-xs">{profile?.last_name || '—'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('last_name')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>

                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">Date of Birth</span>
                    <p className="font-bold text-zinc-950 text-xs">{profile?.date_of_birth || '—'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('date_of_birth')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>

                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">Registered Mobile</span>
                    <p className="font-bold text-zinc-950 text-xs font-mono">{profile?.mobile_number || '—'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('mobile_number')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>

                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">Department</span>
                    <p className="font-bold text-zinc-950 text-xs">{profile?.department || 'Field Services'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('department')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>

                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-zinc-500 font-semibold uppercase">State / Territory</span>
                    <p className="font-bold text-zinc-950 text-xs">{profile?.state || 'Tamil Nadu'}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => openChangeRequestModal('state')}
                    className="text-[11px] font-bold text-zinc-900 hover:underline cursor-pointer"
                  >
                    Request Edit
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Change Requests History Table */}
        <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card">
          <div className="bg-zinc-50/80 px-5 py-4 border-b border-zinc-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
              <FileText className="w-4 h-4 text-zinc-800" />
              <span>Employee Change Requests History ({changeRequests.length})</span>
            </h2>
            <button
              type="button"
              onClick={() => openChangeRequestModal('first_name')}
              className="px-4 py-2 min-h-[36px] bg-slate-800 text-white font-bold rounded-lg text-xs hover:bg-slate-700 active:bg-slate-900 inline-flex items-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Submit New Change Request</span>
            </button>
          </div>

          <div className="p-0 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-zinc-50/60 text-zinc-600 font-bold uppercase text-[10px] tracking-wider border-b border-zinc-200">
                <tr>
                  <th className="px-5 py-3.5">Request ID</th>
                  <th className="px-5 py-3.5">Field</th>
                  <th className="px-5 py-3.5">Old Value</th>
                  <th className="px-5 py-3.5">Requested Value</th>
                  <th className="px-5 py-3.5">Reason</th>
                  <th className="px-5 py-3.5">Submitted</th>
                  <th className="px-5 py-3.5">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-medium text-zinc-800">
                {changeRequests.length > 0 ? (
                  changeRequests.map((cr) => (
                    <tr key={cr.id} className="hover:bg-zinc-50/80 transition-colors">
                      <td className="px-5 py-3.5 font-mono font-bold text-zinc-950">#{cr.id}</td>
                      <td className="px-5 py-3.5 font-bold text-zinc-900">{cr.field_label || cr.field_name}</td>
                      <td className="px-5 py-3.5 text-zinc-500 font-mono text-[11px] max-w-[120px] truncate">{cr.old_value || '—'}</td>
                      <td className="px-5 py-3.5 text-zinc-950 font-bold max-w-[120px] truncate">{cr.new_value}</td>
                      <td className="px-5 py-3.5 text-zinc-600 max-w-xs truncate" title={cr.reason}>{cr.reason}</td>
                      <td className="px-5 py-3.5 text-zinc-500 font-mono">{new Date(cr.created_at).toLocaleDateString()}</td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={cr.status.toLowerCase()} size="xs" label={cr.status} />
                        {cr.admin_notes && (
                          <p className="text-[10px] text-zinc-500 italic mt-0.5" title={cr.admin_notes}>
                            Note: {cr.admin_notes}
                          </p>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="px-5 py-10 text-center text-zinc-500">
                      No change requests submitted. All controlled records match registration dossier.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Change Request Modal */}
        <Modal
          isOpen={showChangeModal}
          onClose={() => setShowChangeModal(false)}
          title="Submit Employee Profile Change Request"
          icon={Send}
          maxWidth="max-w-md"
        >
          <form onSubmit={handleSubmitChangeRequest} className="space-y-4 text-xs">
            <div>
              <label className="block text-zinc-700 font-bold mb-1">Target Controlled Field</label>
              <select
                value={targetField}
                onChange={(e) => setTargetField(e.target.value)}
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs bg-white focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
              >
                <option value="first_name">Legal First Name</option>
                <option value="last_name">Legal Last Name</option>
                <option value="date_of_birth">Date of Birth</option>
                <option value="mobile_number">Registered Mobile Number</option>
                <option value="department">Department</option>
                <option value="state">State / Territory</option>
                <option value="bank_account">Bank Account / IFSC</option>
              </select>
            </div>

            <div>
              <label className="block text-zinc-700 font-bold mb-1">New Requested Value</label>
              <input
                type="text"
                required
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                placeholder="Enter new correct value..."
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 min-h-[38px] text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
              />
            </div>

            <div>
              <label className="block text-zinc-700 font-bold mb-1">Reason for Change & Supporting Reference</label>
              <textarea
                required
                rows={3}
                value={changeReason}
                onChange={(e) => setChangeReason(e.target.value)}
                placeholder="Explain reason for correction or update..."
                className="w-full border border-zinc-300 rounded-lg px-3 py-2 text-zinc-900 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs resize-none"
              />
            </div>

            <div className="pt-4 border-t border-zinc-100 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowChangeModal(false)}
                className="px-4 py-2 min-h-[38px] rounded-lg border border-zinc-300 text-zinc-700 font-bold hover:bg-zinc-50 transition-all cursor-pointer shadow-xs"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmittingCR}
                className="px-4 py-2 min-h-[38px] rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-900 text-white font-bold shadow-xs disabled:opacity-50 inline-flex items-center gap-2 transition-all cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSubmittingCR ? 'Submitting...' : 'Submit for Admin Review'}</span>
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
}

export default EmployeeProfilePage;
