import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import {
  apiGetOnboardingProfile,
  apiUploadDocument,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { PageHeader } from '../../components/common/PageHeader.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import {
  ShieldCheck,
  FileText,
  Upload,
  CheckCircle2,
  AlertCircle,
  Clock,
  XCircle,
  ExternalLink,
  Eye,
  RotateCcw,
  Check,
} from 'lucide-react';

const DOCUMENT_DEFINITIONS = [
  {
    key: 'aadhaar',
    title: 'Government Identity Proof (Aadhaar / ID)',
    description: 'Government issued photo identity with full name and date of birth.',
    required: true,
  },
  {
    key: 'driving_license',
    title: 'Driving License / Vehicle RC',
    description: 'Valid motor vehicle license for field transit and customer dispatch.',
    required: true,
  },
  {
    key: 'trade_certificate',
    title: 'Trade & Technical Qualification',
    description: 'ITI, Diploma, or verified vocational trade certification in your service category.',
    required: true,
  },
  {
    key: 'police_clearance',
    title: 'Police Verification / Background Check',
    description: 'Criminal background clearance report or local police verification certificate.',
    required: false,
  },
  {
    key: 'bank_proof',
    title: 'Bank Passbook / Cancelled Cheque',
    description: 'Official document clearly showing your name, account number, and IFSC code.',
    required: true,
  },
];

export function EmployeeDocumentsPage() {
  const { user, refreshProfile } = useAuth();
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [uploadingCategory, setUploadingCategory] = useState(null);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await apiGetOnboardingProfile();
      setProfile(data);
    } catch (err) {
      setError(err.message || 'Failed to load your verification documents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (category, title, file) => {
    if (!file) return;
    try {
      setUploadingCategory(category);
      setError('');
      setSuccessMsg('');
      await apiUploadDocument(category, file, title);
      setSuccessMsg(`Uploaded ${title} successfully.`);
      await loadDocuments();
      await refreshProfile();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to upload document file.');
    } finally {
      setUploadingCategory(null);
    }
  };

  const docsMap = profile?.onboarding_data?.documents || profile?.documents || {};

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/employee/dashboard' }, { label: 'Documents' }]}>
      <div className="space-y-5 max-w-5xl mx-auto">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <PageHeader
            title="Documents & Identity"
            subtitle="Manage your identity credentials, trade certifications, and compliance verification files"
          />
          <button
            type="button"
            onClick={loadDocuments}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 min-h-[38px] bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-800 border border-zinc-300 rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer self-start sm:self-auto"
          >
            <RotateCcw className={`w-3.5 h-3.5 text-zinc-600 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {successMsg && (
          <div className="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-900 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-700 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Verification Summary Banner */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-zinc-100 border border-zinc-200 text-zinc-900 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-zinc-950">Credential Status</h3>
              <p className="text-xs text-zinc-500 mt-0.5">
                All documents are securely archived and audited against platform compliance requirements.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="text-xs font-bold text-zinc-700">Account Status:</span>
            <StatusBadge status={user?.registrationStatus || 'approved'} />
          </div>
        </div>

        {/* Documents Grid */}
        {isLoading ? (
          <div className="bg-white border border-zinc-200/90 rounded-md p-12 shadow-card">
            <LoadingState message="Loading documents..." />
          </div>
        ) : (
          <div className="space-y-4">
            {DOCUMENT_DEFINITIONS.map((def) => {
              const doc = docsMap[def.key] || {};
              const status = (doc.status || 'missing').toLowerCase();
              const isApproved = status === 'approved' || status === 'verified';
              const isPending = status === 'pending' || status === 'submitted' || status === 'under_review';
              const isCorrection = status === 'correction_required' || status === 'rejected';
              const isUploading = uploadingCategory === def.key;

              return (
                <div
                  key={def.key}
                  className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card hover:border-zinc-300 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  {/* Left: Info */}
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-bold text-zinc-950">{def.title}</h4>
                      {def.required ? (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-100 text-zinc-700 border border-zinc-200">
                          Mandatory
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold text-zinc-500">
                          Optional
                        </span>
                      )}
                      <StatusBadge status={doc.status || 'MISSING'} />
                    </div>
                    <p className="text-xs text-zinc-500 leading-relaxed max-w-xl">{def.description}</p>

                    {/* Feedback if any */}
                    {doc.rejection_reason && (
                      <div className="mt-2 p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-800 font-medium">
                        <strong>Admin Note:</strong> {doc.rejection_reason}
                      </div>
                    )}

                    {/* Existing file link */}
                    {doc.file_url && (
                      <div className="pt-1">
                        <a
                          href={doc.file_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-semibold text-zinc-700 hover:text-zinc-950 hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5 text-zinc-500" />
                          <span>View uploaded document</span>
                          <ExternalLink className="w-3 h-3 text-zinc-400" />
                        </a>
                      </div>
                    )}
                  </div>

                  {/* Right: Upload Trigger */}
                  <div className="shrink-0 flex items-center gap-2">
                    <label className="inline-flex items-center gap-1.5 px-3.5 py-2 min-h-[38px] bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-800 border border-zinc-300 rounded-lg text-xs font-bold shadow-xs transition-all cursor-pointer">
                      <Upload className={`w-3.5 h-3.5 text-zinc-600 ${isUploading ? 'animate-spin' : ''}`} />
                      <span>{doc.file_url ? 'Replace Document' : 'Upload File'}</span>
                      <input
                        type="file"
                        accept="image/*,application/pdf"
                        disabled={isUploading}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleFileUpload(def.key, def.title, file);
                        }}
                        className="hidden"
                      />
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default EmployeeDocumentsPage;
