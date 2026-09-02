import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { AlertTriangle, Upload, CheckCircle2, FileText, ArrowRight, AlertCircle } from 'lucide-react';
import {
  apiGetOnboardingProfile,
  apiUploadDocument,
  apiSubmitOnboarding,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';

export function CorrectionRequiredPage() {
  const { refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const fetchProfile = async () => {
    try {
      const data = await apiGetOnboardingProfile();
      setProfile(data);
    } catch (_) {}
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const onboarding = profile?.onboarding_data || {};
  const correctionNotes = onboarding.correction_notes || 'Please update the highlighted documents/details.';
  const docs = onboarding.documents || {};

  const handleDocumentReplace = async (category, file, title) => {
    try {
      setError('');
      await apiUploadDocument(category, file, title);
      setSuccessMsg(`Replacement for ${title || category} uploaded!`);
      await fetchProfile();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to upload document.');
    }
  };

  const handleResubmit = async () => {
    try {
      setIsSubmitting(true);
      setError('');
      await apiSubmitOnboarding();
      await refreshProfile();
      navigate('/workforce/onboarding/pending-review');
    } catch (err) {
      setError(err.message || 'Resubmission failed. Please verify documents.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppShell breadcrumbs={[{ label: 'Correction Action Required' }]}>
      <div className="max-w-2xl mx-auto space-y-4 py-6">
        <div className="bg-white border border-zinc-200/90 rounded-md p-6 sm:p-8 shadow-card space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 flex items-center justify-center shadow-xs">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200 uppercase tracking-wider">
                Action Required
              </span>
              <h1 className="text-lg font-bold text-zinc-950 mt-1 tracking-tight">
                Application Correction Requested
              </h1>
            </div>
          </div>

          {/* Admin Feedback Box */}
          <div className="p-4 bg-amber-50/80 border border-amber-200 rounded-lg text-xs">
            <p className="font-bold text-amber-950 uppercase tracking-wider text-[11px] mb-1">
              Admin Review Notes:
            </p>
            <p className="text-zinc-800 leading-relaxed font-medium">
              "{correctionNotes}"
            </p>
          </div>

          {error && <ErrorState message={error} onDismiss={() => setError('')} />}
          {successMsg && (
            <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-900 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Document list */}
          <div className="space-y-2.5">
            <h3 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">
              Documents to Review
            </h3>

            <div className="border border-zinc-200 rounded-lg divide-y divide-zinc-100 overflow-hidden">
              {Object.entries(docs).map(([key, doc]) => {
                const isRejected = doc.status === 'rejected';
                return (
                  <div
                    key={key}
                    className={`p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
                      isRejected ? 'bg-rose-50/40' : 'bg-white'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2.5">
                        <FileText className="w-4 h-4 text-zinc-500" />
                        <span className="font-bold text-zinc-950">{doc.title || key}</span>
                        <StatusBadge status={doc.status} size="xs" />
                      </div>
                      {doc.rejection_reason && (
                        <p className="text-rose-700 font-medium text-[11px] mt-1">
                          Flag: {doc.rejection_reason}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="cursor-pointer px-3 py-1.5 rounded-lg bg-white hover:bg-zinc-50 active:bg-zinc-100 border border-zinc-300 text-zinc-800 font-semibold text-xs inline-flex items-center gap-1.5 transition-all shadow-xs min-h-[34px]">
                        <Upload className="w-3.5 h-3.5 text-zinc-700" />
                        <span>Upload Replacement</span>
                        <input
                          type="file"
                          accept="image/*,application/pdf"
                          className="hidden"
                          onChange={(e) => {
                            if (e.target.files && e.target.files[0]) {
                              handleDocumentReplace(key, e.target.files[0], doc.title);
                            }
                          }}
                        />
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3.5 border-t border-zinc-100">
            <p className="text-[11px] text-zinc-500 leading-relaxed">
              Once replacements are uploaded, resubmit for Admin re-evaluation.
            </p>
            <button
              type="button"
              onClick={handleResubmit}
              disabled={isSubmitting}
              className="px-4 py-2 min-h-[38px] rounded-lg bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white text-xs font-bold shadow-xs inline-flex items-center justify-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
            >
              <span>{isSubmitting ? 'Resubmitting...' : 'Resubmit Application'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default CorrectionRequiredPage;

