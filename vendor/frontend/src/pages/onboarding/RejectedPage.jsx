import React, { useEffect, useState } from 'react';
import { XCircle } from 'lucide-react';
import { apiGetOnboardingProfile } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';

export function RejectedPage() {
  const [rejectionReason, setRejectionReason] = useState('');
  const [supportContact, setSupportContact] = useState(null);
  // The failure was swallowed, which on this page means the applicant is told
  // they were declined and shown no reason -- indistinguishable from an
  // admin who gave none. Worth saying which of the two it is.
  const [loadFailed, setLoadFailed] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  const load = async () => {
    setIsRetrying(true);
    try {
      const data = await apiGetOnboardingProfile();
      setRejectionReason(data?.onboarding_data?.rejection_reason || data?.rejection_reason || '');
      // Load support contact from profile/company data if available
      const contact = data?.company_support_contact || data?.support_contact || null;
      setSupportContact(contact);
      setLoadFailed(false);
    } catch (_) {
      setLoadFailed(true);
    } finally {
      setIsRetrying(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <AppShell breadcrumbs={[{ label: 'Application Decision' }]}>
      <div className="max-w-md mx-auto py-12 text-center">
        <div className="bg-white border border-zinc-200/90 rounded-md p-6 sm:p-8 shadow-card space-y-5">
          <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center mx-auto shadow-xs">
            <XCircle className="w-6 h-6" />
          </div>

          <div>
            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-900 border border-rose-200 uppercase tracking-wider">
              Application Declined
            </span>
            <h1 className="text-lg font-bold text-zinc-950 mt-2 tracking-tight">
              Registration Not Approved
            </h1>
          </div>

          {loadFailed && !rejectionReason && (
            <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-left text-xs flex items-start gap-2">
              <p className="flex-1 text-amber-900 leading-relaxed">
                We could not load the reason for this decision. It may still be available.
              </p>
              <button
                type="button"
                onClick={load}
                disabled={isRetrying}
                className="shrink-0 rounded-md border border-amber-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
              >
                {isRetrying ? 'Retrying' : 'Try again'}
              </button>
            </div>
          )}

          {rejectionReason ? (
            <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-lg text-left text-xs">
              <span className="font-bold text-zinc-800 block mb-1">Reason provided by Admin:</span>
              <p className="text-zinc-600 leading-relaxed font-medium">
                "{rejectionReason}"
              </p>
            </div>
          ) : (
            <div className="p-4 bg-zinc-50 border border-zinc-200 rounded-lg text-left text-xs">
              <p className="text-zinc-500 italic">No specific reason was recorded. Please contact the operations desk for details.</p>
            </div>
          )}

          <p className="text-xs text-zinc-500 leading-relaxed">
            If you wish to dispute this evaluation or provide supplementary trade credentials, please contact your Workforce Operations desk directly.
          </p>

          {supportContact && (
            <div className="pt-3.5 border-t border-zinc-100 text-xs font-semibold text-zinc-700">
              <p>Support Contact: <span className="text-zinc-950 font-bold">{supportContact}</span></p>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

export default RejectedPage;

