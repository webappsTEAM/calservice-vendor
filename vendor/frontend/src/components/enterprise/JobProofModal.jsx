import React, { useEffect, useState } from 'react';
import { Modal } from './Modal.jsx';
import { apiGetJobProof, apiTransitionJob } from '../../api/workforceService.js';
import { CheckCircle2, AlertCircle, Camera, User, MapPin, CreditCard, ShieldCheck, Clock, FileText, Check, Loader2, ExternalLink } from 'lucide-react';
import { StatusBadge } from './StatusBadge.jsx';

export function JobProofModal({
  job = null,
  isOpen = false,
  onClose = () => {},
  onSuccess = () => {},
}) {
  const [proof, setProof] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isApproving, setIsApproving] = useState(false);
  const [error, setError] = useState('');
  const [previewImage, setPreviewImage] = useState(null);

  const jobId = job?.id;

  useEffect(() => {
    if (!isOpen || !jobId) return;

    let isMounted = true;
    setIsLoading(true);
    setError('');

    apiGetJobProof(jobId)
      .then((data) => {
        if (isMounted) {
          setProof(data);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || 'Failed to load proof details.');
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, jobId]);

  const handleApprove = async () => {
    if (!jobId || isApproving) return;
    try {
      setIsApproving(true);
      setError('');
      await apiTransitionJob(jobId, 'completed');
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      setError(err?.message || 'Failed to approve proof and complete job.');
      setIsApproving(false);
    }
  };

  if (!isOpen) return null;

  const reqId = proof?.request_id || job?.request_id || `SR-${jobId}`;
  const isPaid = (proof?.payment_status || job?.payment_status || '').toLowerCase() === 'paid';
  const isCompleted = (proof?.status || job?.status || '').toLowerCase() === 'completed';

  return (
    <>
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        maxWidth="max-w-2xl"
        icon={Camera}
        title={`Service Proof Review — ${reqId}`}
        subtitle="Verify technician completion photos & notes before completing the work order"
        footer={
          <div className="flex items-center justify-between w-full">
            <div className="text-[11px] text-zinc-500 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Cryptographically verified geostamp & timestamps on file</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isApproving}
                className="px-3.5 py-1.5 rounded-lg border border-zinc-300 hover:bg-zinc-100 text-zinc-700 text-xs font-semibold transition-colors"
              >
                Close
              </button>
              {!isCompleted && (
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={isApproving || isLoading}
                  className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white text-xs font-bold shadow-sm inline-flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer"
                >
                  {isApproving ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Completing Job...</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Approve Proof & Complete Job</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2 text-xs text-red-800">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-500">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-700" />
              <p className="text-xs">Loading submission proof & photos...</p>
            </div>
          ) : (
            <>
              {/* Job & Customer Summary Card */}
              <div className="p-3.5 bg-zinc-50 border border-zinc-200 rounded-xl space-y-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <h4 className="text-xs font-bold text-zinc-950">
                      {proof?.service_title || job?.service_title || 'Service Work Order'}
                    </h4>
                    <p className="text-[11px] text-zinc-500 mt-0.5">
                      Customer: <strong className="text-zinc-800">{proof?.customer_name || job?.customer_display_name || 'Customer'}</strong>
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={proof?.status || job?.status} size="xs" />
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-extrabold uppercase border ${
                      isPaid ? 'bg-emerald-50 text-emerald-800 border-emerald-200' : 'bg-amber-50 text-amber-900 border-amber-200'
                    }`}>
                      {isPaid ? 'PAID (ONLINE)' : `₹${proof?.total_amount || job?.total_amount || 0} COD`}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-zinc-200/80 text-[11px] text-zinc-600">
                  <div className="flex items-center gap-1.5 truncate">
                    <User className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                    <span>Tech: <strong>{proof?.assigned_employee?.name || 'Assigned Technician'}</strong> ({proof?.assigned_employee?.employee_id || 'ID'})</span>
                  </div>
                  <div className="flex items-center gap-1.5 truncate">
                    <Clock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                    <span>Submitted: {proof?.submitted_at ? new Date(proof.submitted_at).toLocaleString() : 'Just now'}</span>
                  </div>
                </div>
              </div>

              {/* Photos Grid */}
              <div>
                <h5 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Camera className="w-3.5 h-3.5 text-zinc-700" />
                  <span>Completion Proof Photos</span>
                </h5>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Photo 1: Presence Selfie */}
                  <div className="border border-zinc-200 rounded-xl p-2 bg-white flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-zinc-700 mb-1.5 block">
                      1. Technician Presence / Selfie
                    </span>
                    {proof?.after_presence_photo ? (
                      <div
                        onClick={() => setPreviewImage(proof.after_presence_photo)}
                        className="w-full h-36 rounded-lg overflow-hidden bg-zinc-100 cursor-pointer group relative border border-zinc-200"
                      >
                        <img
                          src={proof.after_presence_photo}
                          alt="Technician Presence"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                        <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-[11px] font-bold gap-1">
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Enlarge</span>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full h-36 rounded-lg bg-zinc-100 border border-dashed border-zinc-300 flex flex-col items-center justify-center text-zinc-400 text-[11px]">
                        <Camera className="w-6 h-6 mb-1 opacity-50" />
                        <span>No Selfie Uploaded</span>
                      </div>
                    )}
                  </div>

                  {/* Photo 2: Finished Appliance / Work */}
                  <div className="border border-zinc-200 rounded-xl p-2 bg-white flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-zinc-700 mb-1.5 block">
                      2. Completed Service Work
                    </span>
                    {proof?.after_appliance_photo ? (
                      <div
                        onClick={() => setPreviewImage(proof.after_appliance_photo)}
                        className="w-full h-36 rounded-lg overflow-hidden bg-zinc-100 cursor-pointer group relative border border-zinc-200"
                      >
                        <img
                          src={proof.after_appliance_photo}
                          alt="Completed Work"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                        <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-[11px] font-bold gap-1">
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Enlarge</span>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full h-36 rounded-lg bg-zinc-100 border border-dashed border-zinc-300 flex flex-col items-center justify-center text-zinc-400 text-[11px]">
                        <Camera className="w-6 h-6 mb-1 opacity-50" />
                        <span>Optional Work Photo</span>
                      </div>
                    )}
                  </div>

                  {/* Photo 3: Clean Work Area */}
                  <div className="border border-zinc-200 rounded-xl p-2 bg-white flex flex-col items-center text-center">
                    <span className="text-[10px] font-bold text-zinc-700 mb-1.5 block">
                      3. Clean Site / Work Area
                    </span>
                    {proof?.after_work_area_photo ? (
                      <div
                        onClick={() => setPreviewImage(proof.after_work_area_photo)}
                        className="w-full h-36 rounded-lg overflow-hidden bg-zinc-100 cursor-pointer group relative border border-zinc-200"
                      >
                        <img
                          src={proof.after_work_area_photo}
                          alt="Clean Work Area"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                        />
                        <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-[11px] font-bold gap-1">
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span>Enlarge</span>
                        </div>
                      </div>
                    ) : (
                      <div className="w-full h-36 rounded-lg bg-zinc-100 border border-dashed border-zinc-300 flex flex-col items-center justify-center text-zinc-400 text-[11px]">
                        <Camera className="w-6 h-6 mb-1 opacity-50" />
                        <span>Optional Site Photo</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Technician Notes Box */}
              <div>
                <h5 className="text-xs font-bold text-zinc-900 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-zinc-700" />
                  <span>Technician Completion Notes</span>
                </h5>
                <div className="p-3 bg-zinc-50 border border-zinc-200 rounded-lg text-xs text-zinc-800 leading-relaxed min-h-[50px]">
                  {proof?.completion_notes ? (
                    <p className="whitespace-pre-line">{proof.completion_notes}</p>
                  ) : (
                    <span className="text-zinc-400 italic">No additional notes provided by technician.</span>
                  )}
                </div>
              </div>

              {/* Status Note */}
              {isCompleted ? (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-xs text-emerald-900 font-medium">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>This job order is already finalized and COMPLETED. Technician wallet has been settled.</span>
                </div>
              ) : (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-2 text-xs text-blue-900">
                  <Check className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>
                    Approving this proof will mark the job as <strong>COMPLETED</strong>, release the technician back to <strong>ONLINE / Available</strong>, and credit their wallet.
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </Modal>

      {/* Lightbox Modal for Full-Size Image Preview */}
      {previewImage && (
        <div
          className="fixed inset-0 z-[60] bg-black/80 backdrop-blur-xs flex items-center justify-center p-4 cursor-pointer"
          onClick={() => setPreviewImage(null)}
        >
          <div className="relative max-w-3xl max-h-[85vh] bg-zinc-950 p-2 rounded-xl overflow-hidden shadow-2xl">
            <img
              src={previewImage}
              alt="Full Preview"
              className="max-h-[80vh] w-auto max-w-full object-contain mx-auto rounded-lg"
            />
            <p className="text-center text-xs text-zinc-400 mt-2 font-medium">
              Click anywhere to close full preview
            </p>
          </div>
        </div>
      )}
    </>
  );
}

export default JobProofModal;
