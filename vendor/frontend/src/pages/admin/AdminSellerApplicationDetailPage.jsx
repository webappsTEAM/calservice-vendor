import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  apiGetAdminSellerApplicationDetail,
  apiVerifySellerDocument,
  apiBulkVerifySellerDocuments,
  apiDecideSellerCategory,
  apiRequestSellerCorrection,
  apiApproveSellerApplication,
  apiRejectSellerApplication,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { Modal } from '../../components/enterprise/Modal.jsx';
import { ConfirmDialog } from '../../components/enterprise/ConfirmDialog.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { Button } from '../../components/enterprise/Button.jsx';
import {
  Store,
  ArrowLeft,
  User,
  Building2,
  Phone,
  Mail,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ExternalLink,
  FileText,
  ShoppingBag,
  Check,
  X,
} from 'lucide-react';

export function AdminSellerApplicationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [seller, setSeller] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'documents' | 'categories'
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals
  const [showCorrectionModal, setShowCorrectionModal] = useState(false);
  const [correctionNotes, setCorrectionNotes] = useState('');

  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const [showApproveConfirm, setShowApproveConfirm] = useState(false);

  // Single doc reject modal
  const [docToReject, setDocToReject] = useState(null);
  const [docRejectReason, setDocRejectReason] = useState('');

  const loadDetail = async () => {
    try {
      setIsLoading(true);
      setError('');
      const data = await apiGetAdminSellerApplicationDetail(id);
      setSeller(data);
    } catch (err) {
      setError(err.message || 'Failed to load seller application dossier.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [id]);

  useEffect(() => {
    if (successMsg) {
      const t = setTimeout(() => setSuccessMsg(''), 4000);
      return () => clearTimeout(t);
    }
  }, [successMsg]);

  const onboarding = seller?.onboarding_data || {};
  const documents = onboarding.documents || {};
  const categories = onboarding.categories || [];
  const regStatus = (seller?.registration_status || 'not_started').toLowerCase();

  const docList = useMemo(() => Object.values(documents), [documents]);
  const allDocsApproved = useMemo(() => {
    if (docList.length === 0) return false;
    return docList.every((d) => d.status === 'approved');
  }, [docList]);

  // ── DOCUMENT ACTIONS ──
  const handleVerifyDocument = async (categoryKey, action, reason = '') => {
    try {
      setActionLoading(true);
      await apiVerifySellerDocument(id, categoryKey, action, reason);
      setSuccessMsg(`Document marked as ${action}d.`);
      await loadDetail();
      setDocToReject(null);
      setDocRejectReason('');
    } catch (err) {
      setError(err.message || `Failed to ${action} document.`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkApproveDocs = async () => {
    try {
      setActionLoading(true);
      await apiBulkVerifySellerDocuments(id, null, 'approve', '', true);
      setSuccessMsg('All pending documents approved.');
      await loadDetail();
    } catch (err) {
      setError(err.message || 'Failed to bulk approve documents.');
    } finally {
      setActionLoading(false);
    }
  };

  // ── CATEGORY ACTIONS ──
  const handleDecideCategory = async (categoryId, action, reason = '') => {
    try {
      setActionLoading(true);
      await apiDecideSellerCategory(id, categoryId, action, reason);
      setSuccessMsg(`Category ${action}d.`);
      await loadDetail();
    } catch (err) {
      setError(err.message || `Failed to ${action} category.`);
    } finally {
      setActionLoading(false);
    }
  };

  // ── DOSSIER ACTIONS ──
  const handleApproveSeller = async () => {
    try {
      setActionLoading(true);
      setError('');
      await apiApproveSellerApplication(id);
      setSuccessMsg('Seller application approved. Storefront and manager account activated.');
      setShowApproveConfirm(false);
      await loadDetail();
    } catch (err) {
      setError(err.message || 'Failed to approve seller application.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectSeller = async () => {
    if (!rejectionReason.trim()) {
      setError('Please provide a reason for rejecting this application.');
      return;
    }
    try {
      setActionLoading(true);
      setError('');
      await apiRejectSellerApplication(id, rejectionReason.trim());
      setSuccessMsg('Seller application marked as rejected.');
      setShowRejectModal(false);
      setRejectionReason('');
      await loadDetail();
    } catch (err) {
      setError(err.message || 'Failed to reject application.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestCorrection = async () => {
    if (!correctionNotes.trim()) {
      setError('Please specify the required corrections.');
      return;
    }
    try {
      setActionLoading(true);
      setError('');
      await apiRequestSellerCorrection(id, correctionNotes.trim());
      setSuccessMsg('Correction request lodged with seller.');
      setShowCorrectionModal(false);
      setCorrectionNotes('');
      await loadDetail();
    } catch (err) {
      setError(err.message || 'Failed to request correction.');
    } finally {
      setActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Platform Governance' }, { label: 'Seller Applications', to: '/workforce/admin/seller-applications' }, { label: 'Dossier' }]}>
        <LoadingState message="Loading seller application dossier..." />
      </AppShell>
    );
  }

  if (!seller) {
    return (
      <AppShell breadcrumbs={[{ label: 'Platform Governance' }, { label: 'Seller Applications', to: '/workforce/admin/seller-applications' }, { label: 'Dossier' }]}>
        <ErrorState
          title="Seller Dossier Not Found"
          message={error || 'The requested seller application could not be found.'}
          onRetry={() => navigate('/workforce/admin/seller-applications')}
        />
      </AppShell>
    );
  }

  const owner = seller.owner || {};

  return (
    <AppShell breadcrumbs={[{ label: 'Platform Governance' }, { label: 'Seller Applications', to: '/workforce/admin/seller-applications' }, { label: seller.store_name }]}>
      {/* ── NOTIFICATION ALERTS ── */}
      {error && (
        <div className="mb-4 p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-md flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')} className="text-rose-500 hover:text-rose-700 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-md flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg('')} className="text-emerald-500 hover:text-emerald-700 cursor-pointer">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      <div className="space-y-5">
        {/* ── TOP HEADER & ACTIONS ── */}
        <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-zinc-100 text-zinc-800 border border-zinc-200 flex items-center justify-center font-bold text-xs shrink-0">
              <Store className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-zinc-950">{seller.store_name}</h1>
                <StatusBadge status={regStatus} />
              </div>
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500 mt-0.5">
                <span className="flex items-center gap-1">
                  <Building2 className="w-3 h-3 text-zinc-400" />
                  {seller.company_name}
                </span>
                <span>&bull;</span>
                <span className="font-mono text-zinc-600 font-semibold">#SEL-{seller.id}</span>
                <span>&bull;</span>
                <span>Lodged: {new Date(seller.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              leftIcon={AlertTriangle}
              onClick={() => setShowCorrectionModal(true)}
            >
              Request Correction
            </Button>

            <Button
              variant="dangerSubtle"
              size="sm"
              leftIcon={XCircle}
              onClick={() => setShowRejectModal(true)}
            >
              Reject
            </Button>

            <button
              type="button"
              onClick={() => setShowApproveConfirm(true)}
              disabled={regStatus === 'approved'}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold text-xs shadow-sm transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{regStatus === 'approved' ? 'Store Approved' : 'Approve Application'}</span>
            </button>
          </div>
        </div>

        {/* ── TABS NAVIGATION ── */}
        <div className="border-b border-zinc-200 flex gap-6 text-xs font-semibold text-zinc-500">
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            className={`pb-2.5 transition-colors cursor-pointer ${
              activeTab === 'overview'
                ? 'text-zinc-950 border-b-2 border-zinc-950 font-bold'
                : 'hover:text-zinc-800'
            }`}
          >
            Overview & Entity Info
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('documents')}
            className={`pb-2.5 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'documents'
                ? 'text-zinc-950 border-b-2 border-zinc-950 font-bold'
                : 'hover:text-zinc-800'
            }`}
          >
            <span>Regulatory Documents</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-100 text-zinc-700 font-bold">
              {docList.length}
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('categories')}
            className={`pb-2.5 transition-colors cursor-pointer flex items-center gap-1.5 ${
              activeTab === 'categories'
                ? 'text-zinc-950 border-b-2 border-zinc-950 font-bold'
                : 'hover:text-zinc-800'
            }`}
          >
            <span>Product Categories</span>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-zinc-100 text-zinc-700 font-bold">
              {categories.length}
            </span>
          </button>
        </div>

        {/* ── TAB 1: OVERVIEW & ENTITY DETAILS ── */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="md:col-span-2 space-y-5">
              {/* Store & Legal Details */}
              <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3.5">
                <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <Building2 className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Storefront & Corporate Entity</span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">Store Display Name</span>
                    <strong className="text-zinc-900 text-xs font-bold">{seller.store_name}</strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">Legal Entity Name</span>
                    <strong className="text-zinc-900 text-xs font-bold">{seller.company_name}</strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">FSSAI License Number</span>
                    <strong className="text-zinc-900 font-mono text-xs font-bold">
                      {seller.fssai_license_number || 'Not provided'}
                    </strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">GST Number (GSTIN)</span>
                    <strong className="text-zinc-900 font-mono text-xs font-bold">
                      {seller.gst_number || 'Not registered'}
                    </strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg sm:col-span-2">
                    <span className="text-zinc-500 text-[11px] block">Store Street Address</span>
                    <strong className="text-zinc-900 text-xs">
                      {seller.store_address || 'No physical address lodged.'}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Owner / Contact Card */}
              <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3.5">
                <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <User className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Store Owner / Primary Manager</span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">Contact Person</span>
                    <strong className="text-zinc-900 text-xs font-bold">
                      {owner.first_name ? `${owner.first_name} ${owner.last_name || ''}` : 'Not designated'}
                    </strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">Mobile Number</span>
                    <strong className="text-zinc-900 font-mono text-xs">{owner.mobile_number || 'None'}</strong>
                  </div>

                  <div className="p-3 bg-zinc-50/70 border border-zinc-100 rounded-lg">
                    <span className="text-zinc-500 text-[11px] block">Email Address</span>
                    <strong className="text-zinc-900 text-xs truncate block">{owner.email || 'None'}</strong>
                  </div>
                </div>
              </div>
            </div>

            {/* Sidebar Status Card */}
            <div className="space-y-5">
              <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-3.5">
                <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Review Audit Status</span>
                </h3>

                <div className="space-y-2 text-xs">
                  <div className="flex justify-between py-1.5 border-b border-zinc-100">
                    <span className="text-zinc-500">Registration State:</span>
                    <strong className="uppercase text-zinc-900">{regStatus}</strong>
                  </div>

                  <div className="flex justify-between py-1.5 border-b border-zinc-100">
                    <span className="text-zinc-500">Company Active:</span>
                    <strong className={seller.is_company_active ? 'text-emerald-700' : 'text-zinc-500'}>
                      {seller.is_company_active ? 'Yes' : 'Inactive'}
                    </strong>
                  </div>

                  <div className="flex justify-between py-1.5 border-b border-zinc-100">
                    <span className="text-zinc-500">Accepting Orders:</span>
                    <strong className={seller.is_accepting_orders ? 'text-emerald-700' : 'text-zinc-500'}>
                      {seller.is_accepting_orders ? 'Yes' : 'Disabled'}
                    </strong>
                  </div>

                  {onboarding.approved_at && (
                    <div className="flex justify-between py-1.5 border-b border-zinc-100">
                      <span className="text-zinc-500">Approved At:</span>
                      <span className="text-zinc-700">{new Date(onboarding.approved_at).toLocaleDateString()}</span>
                    </div>
                  )}

                  {onboarding.correction_notes && (
                    <div className="p-3 bg-amber-50 border border-amber-200/80 rounded-lg mt-2">
                      <span className="text-amber-800 font-bold block mb-1 text-[11px]">Active Correction Notes:</span>
                      <p className="text-amber-900 text-xs">{onboarding.correction_notes}</p>
                    </div>
                  )}

                  {onboarding.rejection_reason && (
                    <div className="p-3 bg-rose-50 border border-rose-200/80 rounded-lg mt-2">
                      <span className="text-rose-800 font-bold block mb-1 text-[11px]">Rejection Reason:</span>
                      <p className="text-rose-900 text-xs">{onboarding.rejection_reason}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: REGULATORY DOCUMENTS ── */}
        {activeTab === 'documents' && (
          <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                  <ShieldCheck className="w-3.5 h-3.5 text-zinc-600" />
                  <span>Lodged Compliance Documents</span>
                </h3>
                <p className="text-[11px] text-zinc-500 mt-0.5">
                  Verify FSSAI license certificates, tax registrations, and storefront verification files.
                </p>
              </div>

              {docList.length > 0 && (
                <Button
                  variant="outline"
                  size="xs"
                  leftIcon={Check}
                  onClick={handleBulkApproveDocs}
                  disabled={actionLoading}
                >
                  Bulk Approve All Pending
                </Button>
              )}
            </div>

            {docList.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-zinc-200 rounded-md space-y-1">
                <FileText className="w-6 h-6 text-zinc-400 mx-auto" />
                <p className="text-xs font-medium text-zinc-500">No documents lodged with this application.</p>
              </div>
            ) : (
              <div className="space-y-2.5">
                {Object.entries(documents).map(([key, doc]) => {
                  const isApproved = doc.status === 'approved';
                  const isRejected = doc.status === 'rejected';

                  return (
                    <div
                      key={key}
                      className="p-3.5 rounded-md border border-zinc-200/80 bg-zinc-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-white border border-zinc-200 text-zinc-700 flex items-center justify-center shrink-0 shadow-xs">
                          <FileText className="w-4 h-4 text-zinc-600" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-zinc-900">{doc.title || key}</span>
                            <StatusBadge status={doc.status || 'pending'} />
                          </div>

                          {doc.document_number && (
                            <div className="text-[11px] font-mono text-zinc-500 mt-0.5">
                              Doc #: {doc.document_number}
                            </div>
                          )}

                          {doc.file_url ? (
                            <a
                              href={doc.file_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-1 mt-1 hover:underline"
                            >
                              <span>View / Download File</span>
                              <ExternalLink className="w-3 h-3" />
                            </a>
                          ) : (
                            <span className="text-[11px] text-zinc-400 block mt-1">No file attachment</span>
                          )}

                          {doc.rejection_reason && (
                            <p className="text-[11px] text-rose-600 mt-1 font-medium">
                              Reason: {doc.rejection_reason}
                            </p>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5 self-end sm:self-center">
                        <button
                          type="button"
                          onClick={() => handleVerifyDocument(key, 'approve')}
                          disabled={actionLoading || isApproved}
                          className="px-2.5 py-1 rounded bg-white hover:bg-zinc-100 text-emerald-700 font-bold text-xs border border-zinc-300 disabled:opacity-40 transition-colors flex items-center gap-1 shadow-xs cursor-pointer"
                        >
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span>Approve</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setDocToReject(key);
                            setDocRejectReason('');
                          }}
                          disabled={actionLoading || isRejected}
                          className="px-2.5 py-1 rounded bg-white hover:bg-zinc-100 text-rose-700 font-bold text-xs border border-zinc-300 disabled:opacity-40 transition-colors flex items-center gap-1 shadow-xs cursor-pointer"
                        >
                          <X className="w-3 h-3 text-rose-600" />
                          <span>Reject</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: PRODUCT CATEGORIES ── */}
        {activeTab === 'categories' && (
          <div className="bg-white border border-zinc-200/90 rounded-md p-5 shadow-card space-y-4">
            <div>
              <h3 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                <ShoppingBag className="w-3.5 h-3.5 text-zinc-600" />
                <span>Requested Product Categories</span>
              </h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                Authorize or decline retail product segments for this store catalog.
              </p>
            </div>

            {categories.length === 0 ? (
              <div className="p-8 text-center border border-dashed border-zinc-200 rounded-md space-y-1">
                <ShoppingBag className="w-6 h-6 text-zinc-400 mx-auto" />
                <p className="text-xs font-medium text-zinc-500">No product categories requested.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {categories.map((cat) => {
                  const isApproved = cat.status === 'approved';
                  const isRejected = cat.status === 'rejected';

                  return (
                    <div
                      key={cat.id || cat.name}
                      className="p-3.5 rounded-md border border-zinc-200/80 bg-zinc-50/50 flex items-center justify-between gap-3 text-xs"
                    >
                      <div>
                        <span className="font-bold text-zinc-900 block">{cat.name || cat.id}</span>
                        <div className="mt-1">
                          <StatusBadge status={cat.status || 'pending'} />
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleDecideCategory(cat.id || cat.name, 'approve')}
                          disabled={actionLoading || isApproved}
                          className="px-2.5 py-1 rounded bg-white hover:bg-zinc-100 text-emerald-700 font-bold text-xs border border-zinc-300 disabled:opacity-40 transition-colors shadow-xs cursor-pointer"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDecideCategory(cat.id || cat.name, 'reject')}
                          disabled={actionLoading || isRejected}
                          className="px-2.5 py-1 rounded bg-white hover:bg-zinc-100 text-rose-700 font-bold text-xs border border-zinc-300 disabled:opacity-40 transition-colors shadow-xs cursor-pointer"
                        >
                          Decline
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── MODALS ── */}

      {/* Request Correction Modal */}
      <Modal
        isOpen={showCorrectionModal}
        onClose={() => setShowCorrectionModal(false)}
        title="Request Seller Correction"
      >
        <div className="space-y-3.5 text-xs">
          <p className="text-zinc-600">
            Specify the exact compliance or profile discrepancies the merchant needs to correct:
          </p>
          <div>
            <label className="block font-semibold text-zinc-800 mb-1">
              Correction Notes <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={4}
              value={correctionNotes}
              onChange={(e) => setCorrectionNotes(e.target.value)}
              placeholder="e.g. Please re-upload a clear copy of your FSSAI certificate showing the valid registration number."
              className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCorrectionModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRequestCorrection}
              disabled={actionLoading || !correctionNotes.trim()}
              isLoading={actionLoading}
            >
              Send Correction Request
            </Button>
          </div>
        </div>
      </Modal>

      {/* Reject Application Modal */}
      <Modal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        title="Reject Seller Application"
      >
        <div className="space-y-3.5 text-xs">
          <p className="text-zinc-600">
            Are you sure you want to reject this grocery seller application? This action will decline merchant onboarding.
          </p>
          <div>
            <label className="block font-semibold text-zinc-800 mb-1">
              Rejection Reason <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Reason for declining application..."
              className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowRejectModal(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleRejectSeller}
              disabled={actionLoading || !rejectionReason.trim()}
              isLoading={actionLoading}
            >
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Modal>

      {/* Approve Confirm Dialog */}
      <ConfirmDialog
        isOpen={showApproveConfirm}
        onClose={() => setShowApproveConfirm(false)}
        onConfirm={handleApproveSeller}
        title={`Approve ${seller.store_name}?`}
        message={
          !allDocsApproved
            ? 'Warning: Some uploaded compliance documents are not marked as approved yet. All documents must be verified and approved before final activation.'
            : 'This will activate the company, merchant user account, and enable order intake for this store on the customer marketplace.'
        }
        confirmText="Approve & Activate Seller"
        type="success"
        isLoading={actionLoading}
      />

      {/* Single Doc Reject Modal */}
      <Modal
        isOpen={Boolean(docToReject)}
        onClose={() => setDocToReject(null)}
        title="Reject Document"
      >
        <div className="space-y-3.5 text-xs">
          <p className="text-zinc-600">
            Specify why this document is invalid or rejected:
          </p>
          <input
            type="text"
            value={docRejectReason}
            onChange={(e) => setDocRejectReason(e.target.value)}
            placeholder="e.g. Expired FSSAI certificate, unclear image"
            className="w-full px-3 py-2 border border-zinc-300 rounded-lg text-xs text-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 shadow-xs"
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDocToReject(null)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={() => handleVerifyDocument(docToReject, 'reject', docRejectReason)}
              disabled={actionLoading}
              isLoading={actionLoading}
            >
              Confirm Rejection
            </Button>
          </div>
        </div>
      </Modal>
    </AppShell>
  );
}

export default AdminSellerApplicationDetailPage;
