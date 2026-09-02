import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import { Clock, RefreshCw, FileText, Wrench, AlertCircle, CheckCircle2 } from 'lucide-react';
import { apiGetOnboardingProfile } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';

export function PendingReviewPage() {
  const { refreshProfile } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      setIsRefreshing(true);
      const updatedUser = await refreshProfile();
      if (updatedUser) {
        setProfile(updatedUser);
      }
    } catch (_) {
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const onboarding = profile?.onboarding_data || {};
  const services = onboarding.services || [];
  const docs = onboarding.documents || {};

  return (
    <AppShell breadcrumbs={[{ label: 'Application Status' }]}>
      <div className="max-w-xl mx-auto py-8">
        <div className="bg-white border border-zinc-200/90 rounded-md p-6 sm:p-8 shadow-card text-center space-y-5">
          <div className="w-12 h-12 rounded-full bg-zinc-100 border border-zinc-300 text-zinc-900 flex items-center justify-center mx-auto shadow-xs">
            <Clock className="w-6 h-6" />
          </div>

          <div>
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-50 text-amber-900 border border-amber-200 uppercase tracking-wider">
              Verification In Progress
            </span>
            <h1 className="text-xl font-bold text-zinc-950 mt-3 tracking-tight">
              Your Application is Under Review
            </h1>
            <p className="text-xs text-zinc-500 mt-1.5 max-w-md mx-auto leading-relaxed">
              Our Operations & Verification team is inspecting your identification files and trade qualifications.
            </p>
          </div>

          {/* Dossier status summary */}
          <div className="grid grid-cols-2 gap-3 text-left pt-2">
            <div className="p-3.5 bg-zinc-50 border border-zinc-200 rounded-lg text-xs">
              <span className="text-zinc-500 block text-[11px]">Requested Services:</span>
              <strong className="text-zinc-900 text-xs font-bold">{services.length} Services</strong>
            </div>
            <div className="p-3.5 bg-zinc-50 border border-zinc-200 rounded-lg text-xs">
              <span className="text-zinc-500 block text-[11px]">Documents Lodged:</span>
              <strong className="text-zinc-900 text-xs font-bold">{Object.keys(docs).length} Files</strong>
            </div>
          </div>

          {/* Provider Affiliation / Join Request Status */}
          {profile?.requested_provider_name && profile?.association_status === 'PENDING' && (
            <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-lg text-left text-xs text-amber-900 flex items-start gap-2.5">
              <Clock className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold block text-xs text-amber-950">Service Provider Join Request Pending</strong>
                <span className="text-amber-800 text-[11px] mt-0.5 block leading-relaxed">
                  Your request to join <strong>{profile.requested_provider_name}</strong> is awaiting approval from their administrator.
                </span>
              </div>
            </div>
          )}

          {profile?.provider_name && profile?.association_status === 'APPROVED' && (
            <div className="p-3.5 bg-emerald-50/70 border border-emerald-200 rounded-lg text-left text-xs text-emerald-900 flex items-start gap-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold block text-xs text-emerald-950">Organization Affiliation Approved</strong>
                <span className="text-emerald-800 text-[11px] mt-0.5 block leading-relaxed">
                  You are officially enrolled under <strong>{profile.provider_name}</strong>.
                </span>
              </div>
            </div>
          )}

          {profile?.association_status === 'REJECTED' && profile?.requested_provider_name && (
            <div className="p-3.5 bg-zinc-100 border border-zinc-200 rounded-lg text-left text-xs text-zinc-700 flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 text-zinc-500 shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold block text-xs text-zinc-900">Independent Contractor Mode</strong>
                <span className="text-zinc-600 text-[11px] mt-0.5 block leading-relaxed">
                  Your request to join {profile.requested_provider_name} was declined. You are progressing as an Independent Technician.
                </span>
              </div>
            </div>
          )}

          <div className="p-3.5 bg-zinc-100/80 border border-zinc-200 rounded-lg text-left text-xs text-zinc-800 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-zinc-600 shrink-0 mt-0.5" />
            <span className="text-xs leading-relaxed">
              You will be notified once verification is completed. You cannot receive job dispatches until your application is approved.
            </span>
          </div>

          <div className="pt-2">
            <button
              type="button"
              onClick={fetchStatus}
              disabled={isRefreshing}
              className="px-4 py-2 min-h-[38px] rounded-lg border border-zinc-300 bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-800 font-semibold text-xs inline-flex items-center gap-2 transition-all shadow-xs disabled:opacity-50 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Checking Status...' : 'Refresh Status'}</span>
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default PendingReviewPage;

