import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { AppShell } from '../../components/common/AppShell.jsx';

import {
  apiGetOnboardingProfile,
  apiSaveOnboardingDraft,
  apiUploadDocument,
  apiSubmitOnboarding,
  apiGetCatalog,
} from '../../api/workforceService.js';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import {
  User,
  MapPin,
  Wrench,
  Award,
  FileText,
  CreditCard,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Upload,
  AlertCircle,
  HelpCircle,
  Lock,
  Eye,
  EyeOff,
} from 'lucide-react';


const STEPS = [
  { id: 1, label: 'Personal', icon: User },
  { id: 2, label: 'Address', icon: MapPin },
  { id: 3, label: 'Services', icon: Wrench },
  { id: 4, label: 'Skills & Tools', icon: Award },
  { id: 5, label: 'Documents', icon: FileText },
  { id: 6, label: 'Bank Details', icon: CreditCard },
  { id: 7, label: 'Review & Submit', icon: CheckCircle2 },
];

export function OnboardingWizardPage() {
  const { user, registrationStatus, refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [fieldErrors, setFieldErrors] = useState({});
  const [catalog, setCatalog] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const [showAccountNumber, setShowAccountNumber] = useState(false);
  const [showConfirmAccountNumber, setShowConfirmAccountNumber] = useState(false);

  const clearBankFieldError = (fieldKey) => {
    setFieldErrors((prev) => {
      if (!prev[fieldKey] && !prev[`bank.${fieldKey}`]) return prev;
      const next = { ...prev };
      delete next[fieldKey];
      delete next[`bank.${fieldKey}`];
      return next;
    });
  };

  const isLocked = ['approved', 'submitted', 'under_review'].includes(registrationStatus);

  // Form State
  const [formData, setFormData] = useState({
    personal: {
      dob: '',
      gender: '',
      emergencyName: '',
      emergencyPhone: '',
      emergencyRelation: '',
    },
    address: {
      street: '',
      city: '',
      state: '',
      pincode: '',
    },
    services: [],
    skills: {
      experienceYears: '',
      tools: [],
      languages: [],
      vehicleType: 'two_wheeler',
      licenseNumber: '',
    },
    documents: {},
    bank: {
      accountHolder: '',
      accountNumber: '',
      confirmAccountNumber: '',
      ifsc: '',
      bankName: '',
      upiId: '',
    },
    declarationAccepted: false,
  });

  // Load profile and catalog
  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [profile, catData] = await Promise.all([
          apiGetOnboardingProfile().catch(() => null),
          apiGetCatalog().catch(() => []),
        ]);

        if (catData && catData.length > 0) {
          setCatalog(catData);
        }

        if (profile && profile.onboarding_data) {
          const ob = profile.onboarding_data;
          const draft = ob.draft || {};

          setFormData((prev) => ({
            ...prev,
            personal: { ...prev.personal, ...(draft.personal || {}) },
            address: { ...prev.address, ...(draft.address || {}) },
            services: draft.services || prev.services,
            skills: { ...prev.skills, ...(draft.skills || {}) },
            documents: ob.documents || draft.documents || {},
            bank: {
              ...prev.bank,
              ...(draft.bank || {}),
              confirmAccountNumber: (draft.bank && draft.bank.accountNumber) ? draft.bank.accountNumber : prev.bank.confirmAccountNumber,
            },
          }));

          if (Array.isArray(ob.completed_steps)) {
            setCompletedSteps(ob.completed_steps);
          }

          if (ob.step && ob.step >= 1 && ob.step <= 7) {
            setCurrentStep(ob.step);
          }
        }
      } catch (_) {
        setError('Failed to load onboarding profile.');
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const getMaxDob = () => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 18);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const getMinDob = () => {
    const d = new Date();
    d.setFullYear(d.getFullYear() - 100);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  const canNavigateToStep = (targetStep) => {
    if (isLocked) return true;
    if (targetStep === currentStep) return true;
    // Backward navigation is always allowed for editable applications
    if (targetStep < currentStep) return true;
    // Forward navigation requires all steps up to targetStep - 1 to be validated & completed
    for (let s = 1; s < targetStep; s++) {
      if (!completedSteps.includes(s)) {
        return false;
      }
    }
    return true;
  };

  const getDraftDataForStep = (step) => {
    switch (step) {
      case 1:
        return { personal: formData.personal };
      case 2:
        return { address: formData.address };
      case 3:
        return { services: formData.services };
      case 4:
        return { skills: formData.skills };
      case 5:
        return { documents: formData.documents };
      case 6:
        return { bank: formData.bank };
      default:
        return { personal: formData.personal };
    }
  };

  const extractOnboardingError = (err) => {
    const data = err?.data || {};
    const fields = err?.fields || data.fields || {};

    const fieldMsgs = [];
    if (fields && typeof fields === 'object') {
      for (const val of Object.values(fields)) {
        if (Array.isArray(val)) {
          val.forEach((m) => { if (m) fieldMsgs.push(String(m)); });
        } else if (typeof val === 'string' && val.trim()) {
          fieldMsgs.push(val.trim());
        }
      }
    }

    let msg = '';
    if (fieldMsgs.length > 0) {
      msg = fieldMsgs.join(' • ');
    } else if (data.message && data.message !== 'Please correct the highlighted fields.' && !data.message.includes('ONBOARDING_VALIDATION_FAILED')) {
      msg = data.message;
    } else if (err?.message && !err.message.includes('ONBOARDING_VALIDATION_FAILED') && !err.message.includes('ONBOARDING_STEP_SKIPPED')) {
      msg = err.message;
    } else if (data.message) {
      msg = data.message;
    } else {
      msg = 'Validation failed. Please review your entries and try again.';
    }

    return { message: msg, fields: fields && typeof fields === 'object' ? fields : {} };
  };

  const saveCurrentDraft = async (targetStep = null) => {
    if (isLocked) {
      if (targetStep) setCurrentStep(targetStep);
      return true;
    }
    try {
      setIsSaving(true);
      setError('');
      setFieldErrors({});
      const stepToSave = targetStep !== null ? targetStep : currentStep;
      // Only send the active step's data so subsequent empty steps are not prematurely validated
      const payload = getDraftDataForStep(currentStep);
      const res = await apiSaveOnboardingDraft(stepToSave, payload);

      if (res && res.onboarding_data && Array.isArray(res.onboarding_data.completed_steps)) {
        setCompletedSteps(res.onboarding_data.completed_steps);
      }
      if (targetStep !== null) {
        setCurrentStep(targetStep);
      }
      return true;
    } catch (err) {
      const { message: errMsg, fields } = extractOnboardingError(err);
      setError(errMsg);
      if (fields && typeof fields === 'object') {
        setFieldErrors(fields);
      }
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const handleNext = async () => {
    if (isLocked) {
      if (currentStep < 7) setCurrentStep(currentStep + 1);
      return;
    }
    // Step UX validations before hitting server
    if (currentStep === 1) {
      if (!formData.personal.dob) {
        setError('Please enter your date of birth.');
        setFieldErrors({ dob: 'Date of birth is required.' });
        return;
      }
      const dobDate = new Date(formData.personal.dob);
      const today = new Date();
      let age = today.getFullYear() - dobDate.getFullYear();
      const m = today.getMonth() - dobDate.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < dobDate.getDate())) {
        age--;
      }
      if (isNaN(dobDate.getTime()) || dobDate > today) {
        setError('Date of birth cannot be in the future.');
        setFieldErrors({ dob: 'Date of birth cannot be in the future.' });
        return;
      }
      if (age < 18) {
        setError('Technician candidates must be at least 18 years of age.');
        setFieldErrors({ dob: 'Must be at least 18 years old.' });
        return;
      }
      if (formData.personal.emergencyPhone) {
        const cleanPhone = String(formData.personal.emergencyPhone).replace(/\D/g, '');
        if (cleanPhone.length < 10) {
          setError('Emergency contact phone must be at least 10 digits.');
          setFieldErrors({ emergencyPhone: 'Must be at least 10 digits.' });
          return;
        }
      }
    } else if (currentStep === 2) {
      if (!formData.address.street || !formData.address.city || !formData.address.pincode) {
        setError('Please complete your address details (street, city, and pincode).');
        return;
      }
      const cleanPin = String(formData.address.pincode).replace(/\D/g, '');
      if (cleanPin.length !== 6) {
        setError('Pincode must be exactly 6 digits.');
        setFieldErrors({ pincode: 'Pincode must be exactly 6 digits.' });
        return;
      }
    } else if (currentStep === 3) {
      if (!formData.services || formData.services.length === 0) {
        setError('Please select at least ONE service you provide.');
        return;
      }
    } else if (currentStep === 4) {
      if (formData.skills.experienceYears === '' || formData.skills.experienceYears === undefined || isNaN(formData.skills.experienceYears)) {
        setError('Please enter your years of experience (0 to 50).');
        setFieldErrors({ experienceYears: 'Years of experience is required.' });
        return;
      }
      const exp = parseFloat(formData.skills.experienceYears);
      if (exp < 0 || exp > 50) {
        setError('Years of experience must be between 0 and 50.');
        setFieldErrors({ experienceYears: 'Must be between 0 and 50.' });
        return;
      }
      if (['two_wheeler', 'four_wheeler'].includes(formData.skills.vehicleType)) {
        if (!formData.skills.licenseNumber || !formData.skills.licenseNumber.trim()) {
          setError('Driver license number is required for motorized vehicles.');
          setFieldErrors({ licenseNumber: 'License number is required.' });
          return;
        }
      }
    } else if (currentStep === 5) {
      const docs = formData.documents || {};
      const missing = [];
      if (!docs.aadhaar) missing.push('Aadhaar Card');
      if (!docs.address_proof) missing.push('Address Proof');
      if (!docs.bank_proof) missing.push('Bank Proof');
      if (missing.length > 0) {
        setError(`Please upload required documents: ${missing.join(', ')}.`);
        return;
      }
    } else if (currentStep === 6) {
      // Validate in exact order:
      // 1. Account Holder Name
      // 2. IFSC format
      // 3. Account Number format/length
      // 4. Confirm Account Number format/length
      // 5. Account Number match

      // 1. Account Holder Name
      const rawHolder = (formData.bank.accountHolder || '').replace(/\s+/g, ' ').trim();
      if (!rawHolder) {
        setError('Account holder name is required.');
        setFieldErrors({ accountHolder: 'Account holder name is required.' });
        document.getElementById('bank-account-holder')?.focus();
        return;
      }
      if (rawHolder.length < 2) {
        setError('Account holder name must be at least 2 characters.');
        setFieldErrors({ accountHolder: 'Account holder name must be at least 2 characters.' });
        document.getElementById('bank-account-holder')?.focus();
        return;
      }
      if (rawHolder.length > 100) {
        setError('Account holder name cannot exceed 100 characters.');
        setFieldErrors({ accountHolder: 'Account holder name cannot exceed 100 characters.' });
        document.getElementById('bank-account-holder')?.focus();
        return;
      }
      const holderRegex = /^[A-Za-z][A-Za-z\s.'-]*[A-Za-z.]$/;
      const alphaCount = (rawHolder.match(/[A-Za-z]/g) || []).length;
      const hasBadPunctuation = /\.\.|--|''|\.-|-\./.test(rawHolder);
      if (!holderRegex.test(rawHolder) || alphaCount < 2 || hasBadPunctuation) {
        setError('Enter a valid account holder name using English letters and standard punctuation only.');
        setFieldErrors({ accountHolder: 'Enter a valid account holder name (English letters only).' });
        document.getElementById('bank-account-holder')?.focus();
        return;
      }

      // 2. IFSC Code
      const rawIfsc = (formData.bank.ifsc || '').trim().toUpperCase();
      const ifscRegex = /^[A-Z]{4}0[A-Z0-9]{6}$/;
      if (!rawIfsc) {
        setError('IFSC code is required.');
        setFieldErrors({ ifsc: 'IFSC code is required.' });
        document.getElementById('bank-ifsc')?.focus();
        return;
      }
      if (rawIfsc.length !== 11 || !ifscRegex.test(rawIfsc)) {
        setError('Enter a valid 11-character IFSC code, e.g. SBIN0001234.');
        setFieldErrors({ ifsc: 'Enter a valid 11-character IFSC code, e.g. SBIN0001234.' });
        document.getElementById('bank-ifsc')?.focus();
        return;
      }

      // 3. Account Number format/length
      const rawAcc = (formData.bank.accountNumber || '').trim();
      const accRegex = /^\d{9,18}$/;
      if (!rawAcc) {
        setError('Account number is required.');
        setFieldErrors({ accountNumber: 'Account number is required.' });
        document.getElementById('bank-account-number')?.focus();
        return;
      }
      if (!accRegex.test(rawAcc)) {
        setError('Account number must be between 9 and 18 digits (numbers only).');
        setFieldErrors({ accountNumber: 'Account number must be between 9 and 18 digits.' });
        document.getElementById('bank-account-number')?.focus();
        return;
      }

      // 4. Confirm Account Number format/length
      const rawConfirm = (formData.bank.confirmAccountNumber || '').trim();
      if (!rawConfirm) {
        setError('Please confirm your account number.');
        setFieldErrors({ confirmAccountNumber: 'Please confirm your account number.' });
        document.getElementById('bank-confirm-account-number')?.focus();
        return;
      }
      if (!accRegex.test(rawConfirm)) {
        setError('Confirm account number must be between 9 and 18 digits (numbers only).');
        setFieldErrors({ confirmAccountNumber: 'Confirm account number must be between 9 and 18 digits.' });
        document.getElementById('bank-confirm-account-number')?.focus();
        return;
      }

      // 5. Account Number match
      if (rawAcc !== rawConfirm) {
        setError('Account numbers do not match.');
        setFieldErrors({ confirmAccountNumber: 'Account numbers do not match.' });
        document.getElementById('bank-confirm-account-number')?.focus();
        return;
      }
    }

    setError('');
    setFieldErrors({});
    const next = currentStep + 1;
    // Await server-side validation & persistence. Only advance if server verifies validity!
    await saveCurrentDraft(next);
  };

  const handleBack = () => {
    setError('');
    setFieldErrors({});
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };


  const handleFileUpload = async (category, file, title = '') => {
    try {
      setIsSaving(true);
      setError('');
      const res = await apiUploadDocument(category, file, title);
      setFormData((prev) => ({
        ...prev,
        documents: {
          ...prev.documents,
          [category]: res.document,
        },
      }));
      setSuccessMsg(`Document ${category} uploaded!`);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleToggleService = (svc) => {
    const exists = formData.services.some((s) => s.id === svc.id);
    let updated;
    if (exists) {
      updated = formData.services.filter((s) => s.id !== svc.id);
    } else {
      updated = [...formData.services, { id: svc.id, name: svc.name, category: svc.category_name || '' }];
    }
    setFormData((prev) => ({ ...prev, services: updated }));
  };

  const handleToggleCategoryAll = (cat) => {
    if (!cat?.services || cat.services.length === 0) return;
    const catSvcIds = new Set(cat.services.map((s) => s.id));
    const allSelected = cat.services.every((s) => formData.services.some((sel) => sel.id === s.id));

    let updated;
    if (allSelected) {
      // Deselect all services in this category
      updated = formData.services.filter((s) => !catSvcIds.has(s.id));
    } else {
      // Select all services in this category
      const otherServices = formData.services.filter((s) => !catSvcIds.has(s.id));
      const newCatServices = cat.services.map((svc) => ({
        id: svc.id,
        name: svc.name,
        category: cat.name || svc.category_name || '',
      }));
      updated = [...otherServices, ...newCatServices];
    }
    setFormData((prev) => ({ ...prev, services: updated }));
  };

  const handleToggleAllServices = () => {
    const allServices = (catalog || []).flatMap((cat) =>
      (cat.services || []).map((s) => ({
        id: s.id,
        name: s.name,
        category: cat.name || '',
      }))
    );
    const isAllGlobalSelected =
      allServices.length > 0 &&
      allServices.every((s) => formData.services.some((sel) => sel.id === s.id));

    if (isAllGlobalSelected) {
      setFormData((prev) => ({ ...prev, services: [] }));
    } else {
      setFormData((prev) => ({ ...prev, services: allServices }));
    }
  };

  const handleSubmitApplication = async () => {
    if (!formData.declarationAccepted) {
      setError('Please accept the declaration to submit your application.');
      return;
    }

    try {
      setIsSaving(true);
      setError('');
      setFieldErrors({});

      try {
        await apiSubmitOnboarding({ declaration_accepted: true });
      } catch (submitErr) {
        // If already submitted (409 Conflict or ALREADY_SUBMITTED), proceed gracefully
        const errData = submitErr?.data || {};
        if (
          submitErr?.status === 409 ||
          errData?.error === 'ALREADY_SUBMITTED' ||
          errData?.code === 'ALREADY_SUBMITTED' ||
          errData?.status === 'submitted' ||
          errData?.status === 'under_review'
        ) {
          // Already submitted on server
        } else {
          throw submitErr;
        }
      }

      await refreshProfile(true);
      navigate('/workforce/onboarding/pending-review', { replace: true });
    } catch (err) {
      const { message: errMsg, fields } = extractOnboardingError(err);
      setError(errMsg);
      if (fields && typeof fields === 'object') {
        setFieldErrors(fields);
      }
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Registration' }]}>
        <LoadingState message="Loading registration wizard..." />
      </AppShell>
    );
  }

  return (
    <AppShell breadcrumbs={[{ label: 'Registration Wizard' }]}>
      <div className="max-w-3xl mx-auto space-y-4">
        {/* Status Banner when Locked */}
        {isLocked && (
          <div className="bg-white border border-slate-200 rounded p-3.5 shadow-sm flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className={`p-1.5 rounded border ${registrationStatus === 'approved' ? 'bg-emerald-50 border-emerald-200 text-emerald-600' : 'bg-amber-50 border-amber-200 text-amber-600'}`}>
                <Lock className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                    Employee Registration Status
                  </h2>
                  <StatusBadge status={registrationStatus} />
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {registrationStatus === 'approved'
                    ? 'Your registration application is fully approved. All identity, trade, and bank details are verified and active.'
                    : 'Your registration application is lodged and pending Admin verification.'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Step Indicator Bar (Desktop & Mobile) */}
        <div className="bg-white border border-slate-200 rounded p-3 shadow-sm">
          <div className="flex items-center justify-between sm:hidden mb-2">
            <span className="font-bold text-slate-800 text-xs">
              Step {currentStep} of 7: {STEPS[currentStep - 1]?.label}
            </span>
            <span className="text-[11px] text-slate-500 font-medium">
              {Math.round((currentStep / 7) * 100)}% Complete
            </span>
          </div>

          <div className="hidden sm:flex items-center justify-between gap-1">
            {STEPS.map((s) => {
              const Icon = s.icon;
              const isDone = completedSteps.includes(s.id);
              const isCurrent = s.id === currentStep;
              const canAccess = canNavigateToStep(s.id);

              return (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => {
                    if (canAccess) setCurrentStep(s.id);
                  }}
                  disabled={!canAccess}
                  className={`flex-1 py-1 px-2 border-b-2 flex items-center justify-center gap-1.5 transition-colors ${
                    isCurrent
                      ? 'border-blue-600 text-blue-700 font-bold'
                      : isDone
                      ? 'border-emerald-600 text-emerald-700 font-medium hover:bg-slate-50'
                      : canAccess
                      ? 'border-slate-300 text-slate-600 hover:bg-slate-50'
                      : 'border-transparent text-slate-400 opacity-50 cursor-not-allowed'
                  }`}
                >
                  <span
                    className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      isCurrent
                        ? 'bg-blue-600 text-white'
                        : isDone
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-200 text-slate-600'
                    }`}
                  >
                    {isDone ? '✓' : s.id}
                  </span>
                  <span className="text-[11px] whitespace-nowrap">{s.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Main Step Form Card */}
        <div className="bg-white border border-slate-200 rounded p-5 sm:p-6 shadow-sm space-y-4">
          {error && (
            <div className="space-y-1">
              <ErrorState message={error} onDismiss={() => { setError(''); setFieldErrors({}); }} />
              {Object.keys(fieldErrors).length > 0 && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-[11px] text-rose-800">
                  <span className="font-bold">Required Corrections:</span>
                  <ul className="list-disc list-inside mt-1 space-y-0.5">
                    {Object.entries(fieldErrors).map(([field, msg]) => (
                      <li key={field}>
                        <span className="font-semibold capitalize">{field.replace(/_/g, ' ').replace(/^.*\./, '')}:</span>{' '}
                        {Array.isArray(msg) ? msg.join(', ') : String(msg)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          {successMsg && (
            <div className="p-3 rounded border border-emerald-200 bg-emerald-50 text-emerald-800 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* ── STEP 1: PERSONAL ── */}
          {currentStep === 1 && (
            <div className="space-y-3 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <User className="w-4 h-4 text-blue-600" />
                  1. Personal Information
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Provide your date of birth, gender, and emergency contact.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Date of Birth <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="date"
                    max={getMaxDob()}
                    min={getMinDob()}
                    value={formData.personal.dob}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        personal: { ...formData.personal, dob: e.target.value },
                      });
                      if (fieldErrors.dob || fieldErrors['personal.dob']) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.dob;
                          delete next['personal.dob'];
                          return next;
                        });
                      }
                    }}
                    className={`w-full p-2 rounded border text-xs ${
                      fieldErrors.dob || fieldErrors['personal.dob']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                    required
                  />
                  {(fieldErrors.dob || fieldErrors['personal.dob']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {fieldErrors.dob || fieldErrors['personal.dob']}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">Gender</label>
                  <select
                    value={formData.personal.gender}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        personal: { ...formData.personal, gender: e.target.value },
                      })
                    }
                    className="w-full p-2"
                  >
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Emergency Contact Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Priya (Spouse / Parent)"
                    value={formData.personal.emergencyName}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        personal: { ...formData.personal, emergencyName: e.target.value },
                      })
                    }
                    className="w-full p-2"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Emergency Contact Phone
                  </label>
                  <input
                    type="tel"
                    placeholder="9876543211"
                    value={formData.personal.emergencyPhone}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        personal: { ...formData.personal, emergencyPhone: e.target.value },
                      })
                    }
                    className="w-full p-2"
                  />
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 2: ADDRESS ── */}
          {currentStep === 2 && (
            <div className="space-y-3 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-blue-600" />
                  2. Residential Address
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Set your base residential address for operational records.
                </p>
              </div>

              <div className="space-y-3 pt-2">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Street Address <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={2}
                    placeholder="House/Flat No, Street, Landmark"
                    value={formData.address.street}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        address: { ...formData.address, street: e.target.value },
                      });
                      if (fieldErrors.street || fieldErrors['address.street']) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.street;
                          delete next['address.street'];
                          return next;
                        });
                      }
                    }}
                    className={`w-full p-2 rounded border text-xs ${
                      fieldErrors.street || fieldErrors['address.street']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                    required
                  />
                  {(fieldErrors.street || fieldErrors['address.street']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.street || fieldErrors['address.street'])
                        ? (fieldErrors.street || fieldErrors['address.street']).join(', ')
                        : String(fieldErrors.street || fieldErrors['address.street'])}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      City <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.address.city}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          address: { ...formData.address, city: e.target.value },
                        });
                        if (fieldErrors.city || fieldErrors['address.city']) {
                          setFieldErrors((prev) => {
                            const next = { ...prev };
                            delete next.city;
                            delete next['address.city'];
                            return next;
                          });
                        }
                      }}
                      className={`w-full p-2 rounded border text-xs ${
                        fieldErrors.city || fieldErrors['address.city']
                          ? 'border-rose-500 bg-rose-50'
                          : 'border-slate-300'
                      }`}
                      required
                    />
                    {(fieldErrors.city || fieldErrors['address.city']) && (
                      <p className="text-[11px] text-rose-500 mt-1">
                        {Array.isArray(fieldErrors.city || fieldErrors['address.city'])
                          ? (fieldErrors.city || fieldErrors['address.city']).join(', ')
                          : String(fieldErrors.city || fieldErrors['address.city'])}
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">State</label>
                    <input
                      type="text"
                      value={formData.address.state}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          address: { ...formData.address, state: e.target.value },
                        })
                      }
                      className="w-full p-2 rounded border border-slate-300 text-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-bold text-slate-700 mb-1">
                      Pincode <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="500001"
                      value={formData.address.pincode}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          address: { ...formData.address, pincode: e.target.value },
                        });
                        if (fieldErrors.pincode || fieldErrors['address.pincode']) {
                          setFieldErrors((prev) => {
                            const next = { ...prev };
                            delete next.pincode;
                            delete next['address.pincode'];
                            return next;
                          });
                        }
                      }}
                      className={`w-full p-2 rounded border text-xs ${
                        fieldErrors.pincode || fieldErrors['address.pincode']
                          ? 'border-rose-500 bg-rose-50'
                          : 'border-slate-300'
                      }`}
                      required
                    />
                    {(fieldErrors.pincode || fieldErrors['address.pincode']) && (
                      <p className="text-[11px] text-rose-500 mt-1">
                        {Array.isArray(fieldErrors.pincode || fieldErrors['address.pincode'])
                          ? (fieldErrors.pincode || fieldErrors['address.pincode']).join(', ')
                          : String(fieldErrors.pincode || fieldErrors['address.pincode'])}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 3: SERVICES ── */}
          {currentStep === 3 && (
            <div className="space-y-3 text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-2.5">
                <div>
                  <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                    <Wrench className="w-4 h-4 text-blue-600" />
                    3. Select Services You Provide
                  </h2>
                  <p className="text-slate-500 text-[11px] mt-0.5">
                    Select the services you are qualified to perform ({formData.services.length} selected). Each requested service will be reviewed for Admin authorization.
                  </p>
                </div>
                {catalog && catalog.length > 0 && (
                  <button
                    type="button"
                    onClick={handleToggleAllServices}
                    className="self-start sm:self-auto text-xs font-bold px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors shadow-xs"
                  >
                    {catalog.flatMap((c) => c.services || []).length > 0 &&
                    catalog.flatMap((c) => c.services || []).every((s) => formData.services.some((sel) => sel.id === s.id))
                      ? 'Deselect All Services'
                      : 'Select All Services'}
                  </button>
                )}
              </div>

              {(fieldErrors.services || fieldErrors['services']) && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-[11px] text-rose-700">
                  {Array.isArray(fieldErrors.services || fieldErrors['services'])
                    ? (fieldErrors.services || fieldErrors['services']).join(' • ')
                    : String(fieldErrors.services || fieldErrors['services'])}
                </div>
              )}

              <div className="space-y-3 pt-1 max-h-[420px] overflow-y-auto pr-1">
                {catalog && catalog.length > 0 ? (
                  catalog.map((cat) => {
                    const catServices = cat.services || [];
                    const selectedCount = catServices.filter((s) => formData.services.some((sel) => sel.id === s.id)).length;
                    const allCatSelected = catServices.length > 0 && selectedCount === catServices.length;

                    return (
                      <div key={cat.id} className="border border-slate-200 rounded-lg p-3 bg-slate-50/50 shadow-xs">
                        <div className="flex items-center justify-between gap-2 mb-2.5 border-b border-slate-200/80 pb-2">
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                              {cat.name} ({catServices.length})
                            </h3>
                            {selectedCount > 0 && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                                {selectedCount}/{catServices.length} Selected
                              </span>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleToggleCategoryAll(cat)}
                            className={`text-[11px] font-bold px-2.5 py-1 rounded transition-all flex items-center gap-1 border shadow-xs active:scale-95 ${
                              allCatSelected
                                ? 'bg-blue-600 border-blue-600 text-white hover:bg-blue-700'
                                : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-100 hover:border-slate-400'
                            }`}
                          >
                            <span>{allCatSelected ? '✓ Deselect All' : 'Select All'}</span>
                          </button>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {catServices.map((svc) => {
                            const isSelected = formData.services.some((s) => s.id === svc.id);
                            return (
                              <label
                                key={svc.id}
                                className={`p-2.5 rounded-lg border text-left flex items-start gap-2.5 cursor-pointer transition-all ${
                                  isSelected
                                    ? 'bg-blue-50/90 border-blue-300 text-blue-900 font-semibold shadow-xs'
                                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
                                }`}
                              >
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => handleToggleService({ ...svc, category_name: cat.name })}
                                  className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 w-4 h-4 cursor-pointer"
                                />
                                <div className="min-w-0 flex-1">
                                  <p className="text-xs leading-tight">{svc.name}</p>
                                </div>
                              </label>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-slate-500 text-center py-6">Loading service catalog...</p>
                )}
              </div>
            </div>
          )}

          {/* ── STEP 4: SKILLS & TOOLS ── */}
          {currentStep === 4 && (
            <div className="space-y-3 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-blue-600" />
                  4. Professional Experience & Equipment
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Provide your hands-on trade background and transportation mode.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Years of Experience <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="50"
                    placeholder="e.g. 3"
                    value={formData.skills.experienceYears}
                    onChange={(e) => {
                      const val = e.target.value === '' ? '' : parseFloat(e.target.value);
                      setFormData({
                        ...formData,
                        skills: { ...formData.skills, experienceYears: val },
                      });
                      if (fieldErrors.experienceYears || fieldErrors['skills.experienceYears']) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.experienceYears;
                          delete next['skills.experienceYears'];
                          return next;
                        });
                      }
                    }}
                    className={`w-full p-2 rounded border text-xs ${
                      fieldErrors.experienceYears || fieldErrors['skills.experienceYears']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                    required
                  />
                  {(fieldErrors.experienceYears || fieldErrors['skills.experienceYears']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.experienceYears || fieldErrors['skills.experienceYears'])
                        ? (fieldErrors.experienceYears || fieldErrors['skills.experienceYears']).join(', ')
                        : String(fieldErrors.experienceYears || fieldErrors['skills.experienceYears'])}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Vehicle Type
                  </label>
                  <select
                    value={formData.skills.vehicleType || 'two_wheeler'}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        skills: { ...formData.skills, vehicleType: e.target.value },
                      })
                    }
                    className="w-full p-2 rounded border border-slate-300 text-xs"
                  >
                    <option value="two_wheeler">Two Wheeler (Motorcycle/Scooter)</option>
                    <option value="four_wheeler">Four Wheeler / Van</option>
                    <option value="bicycle">Bicycle</option>
                    <option value="public_transit">Public Transit</option>
                    <option value="none">No vehicle / Walking</option>
                  </select>
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-[11px] font-bold text-slate-700 mb-1">
                    Driving License Number {['two_wheeler', 'four_wheeler'].includes(formData.skills.vehicleType) ? <span className="text-rose-500">*</span> : '(If applicable)'}
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. DL-0420110012345"
                    value={formData.skills.licenseNumber}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        skills: { ...formData.skills, licenseNumber: e.target.value },
                      });
                      if (fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber']) {
                        setFieldErrors((prev) => {
                          const next = { ...prev };
                          delete next.licenseNumber;
                          delete next['skills.licenseNumber'];
                          return next;
                        });
                      }
                    }}
                    className={`w-full p-2 rounded border text-xs ${
                      fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                  />
                  {(fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber'])
                        ? (fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber']).join(', ')
                        : String(fieldErrors.licenseNumber || fieldErrors['skills.licenseNumber'])}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 5: DOCUMENTS ── */}
          {currentStep === 5 && (
            <div className="space-y-3 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <FileText className="w-4 h-4 text-blue-600" />
                  5. Required Verification Documents
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Upload official identification files and trade certificates for compliance auditing.
                </p>
              </div>

              <div className="space-y-2.5 pt-2">
                {[
                  { key: 'aadhaar', title: 'Aadhaar / National ID Card', required: true },
                  { key: 'address_proof', title: 'Address Proof (Electricity Bill / Rent Agreement)', required: true },
                  { key: 'trade_cert', title: 'Trade / Vocational Certificate', required: false },
                  { key: 'bank_proof', title: 'Bank Proof (Cancelled Cheque / Passbook)', required: true },
                ].map((doc) => {
                  const uploaded = formData.documents[doc.key];
                  return (
                    <div
                      key={doc.key}
                      className="p-3 bg-slate-50 border border-slate-200 rounded flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                    >
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-800">{doc.title}</span>
                          {doc.required && <span className="text-rose-500 font-bold text-[10px]">*Required</span>}
                        </div>
                        {uploaded ? (
                          <p className="text-[11px] text-emerald-700 font-semibold mt-0.5 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Uploaded ({uploaded.status || 'Pending Verification'})</span>
                          </p>
                        ) : (
                          <p className="text-[11px] text-slate-400 mt-0.5">No file uploaded yet</p>
                        )}
                      </div>

                      <div>
                        <label className="cursor-pointer px-2.5 py-1 rounded bg-white hover:bg-slate-100 border border-slate-300 text-slate-700 font-semibold text-xs inline-flex items-center gap-1 transition-colors">
                          <Upload className="w-3.5 h-3.5 text-blue-600" />
                          <span>{uploaded ? 'Replace' : 'Upload'}</span>
                          <input
                            type="file"
                            accept="image/*,application/pdf"
                            className="hidden"
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleFileUpload(doc.key, e.target.files[0], doc.title);
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
          )}

          {/* ── STEP 6: BANK DETAILS ── */}
          {currentStep === 6 && (
            <div className="space-y-3 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <CreditCard className="w-4 h-4 text-blue-600" />
                  6. Direct Deposit & Bank Information
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Account credentials for weekly service payouts and bonus disbursements.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                <div>
                  <label htmlFor="bank-account-holder" className="block text-[11px] font-bold text-slate-700 mb-1">
                    Account Holder Name <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="bank-account-holder"
                    name="caltrack_account_holder"
                    type="text"
                    autoComplete="name"
                    maxLength={100}
                    placeholder="As printed on bank passbook"
                    value={formData.bank.accountHolder}
                    onChange={(e) => {
                      setFormData({
                        ...formData,
                        bank: { ...formData.bank, accountHolder: e.target.value },
                      });
                      clearBankFieldError('accountHolder');
                    }}
                    className={`w-full p-2 rounded border text-xs ${
                      fieldErrors.accountHolder || fieldErrors['bank.accountHolder']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                    required
                  />
                  {(fieldErrors.accountHolder || fieldErrors['bank.accountHolder']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.accountHolder || fieldErrors['bank.accountHolder'])
                        ? (fieldErrors.accountHolder || fieldErrors['bank.accountHolder']).join(', ')
                        : String(fieldErrors.accountHolder || fieldErrors['bank.accountHolder'])}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="bank-ifsc" className="block text-[11px] font-bold text-slate-700 mb-1">
                    IFSC / Routing Code <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="bank-ifsc"
                    name="caltrack_bank_ifsc"
                    type="text"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    placeholder="e.g. SBIN0001234"
                    maxLength={11}
                    value={formData.bank.ifsc}
                    onChange={(e) => {
                      const val = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 11);
                      setFormData({
                        ...formData,
                        bank: { ...formData.bank, ifsc: val },
                      });
                      clearBankFieldError('ifsc');
                    }}
                    className={`w-full p-2 uppercase rounded border text-xs font-mono tracking-wider ${
                      fieldErrors.ifsc || fieldErrors['bank.ifsc']
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-slate-300'
                    }`}
                    required
                  />
                  {(fieldErrors.ifsc || fieldErrors['bank.ifsc']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.ifsc || fieldErrors['bank.ifsc'])
                        ? (fieldErrors.ifsc || fieldErrors['bank.ifsc']).join(', ')
                        : String(fieldErrors.ifsc || fieldErrors['bank.ifsc'])}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="bank-account-number" className="block text-[11px] font-bold text-slate-700 mb-1">
                    Account Number <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="bank-account-number"
                      name="caltrack_acct_num"
                      type={showAccountNumber ? "text" : "password"}
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={18}
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      placeholder={showAccountNumber ? "Enter 9-18 digits" : "••••••••••••"}
                      value={formData.bank.accountNumber}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, '').slice(0, 18);
                        setFormData({
                          ...formData,
                          bank: { ...formData.bank, accountNumber: val },
                        });
                        clearBankFieldError('accountNumber');
                      }}
                      className={`w-full p-2 pr-10 rounded border text-xs font-mono ${
                        fieldErrors.accountNumber || fieldErrors['bank.accountNumber']
                          ? 'border-rose-500 bg-rose-50'
                          : 'border-slate-300'
                      }`}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showAccountNumber ? "Hide account number" : "Show account number"}
                      onClick={() => setShowAccountNumber((prev) => !prev)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none p-1 rounded hover:bg-slate-100"
                    >
                      {showAccountNumber ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  {(fieldErrors.accountNumber || fieldErrors['bank.accountNumber']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.accountNumber || fieldErrors['bank.accountNumber'])
                        ? (fieldErrors.accountNumber || fieldErrors['bank.accountNumber']).join(', ')
                        : String(fieldErrors.accountNumber || fieldErrors['bank.accountNumber'])}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="bank-confirm-account-number" className="block text-[11px] font-bold text-slate-700 mb-1">
                    Confirm Account Number <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      id="bank-confirm-account-number"
                      name="caltrack_confirm_acct_num"
                      type={showConfirmAccountNumber ? "text" : "password"}
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={18}
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      placeholder={showConfirmAccountNumber ? "Re-enter 9-18 digits" : "••••••••••••"}
                      value={formData.bank.confirmAccountNumber}
                      onChange={(e) => {
                        const val = e.target.value.replace(/\D/g, '').slice(0, 18);
                        setFormData({
                          ...formData,
                          bank: { ...formData.bank, confirmAccountNumber: val },
                        });
                        clearBankFieldError('confirmAccountNumber');
                      }}
                      className={`w-full p-2 pr-10 rounded border text-xs font-mono ${
                        fieldErrors.confirmAccountNumber || fieldErrors['bank.confirmAccountNumber']
                          ? 'border-rose-500 bg-rose-50'
                          : 'border-slate-300'
                      }`}
                      required
                    />
                    <button
                      type="button"
                      aria-label={showConfirmAccountNumber ? "Hide confirm account number" : "Show confirm account number"}
                      onClick={() => setShowConfirmAccountNumber((prev) => !prev)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none p-1 rounded hover:bg-slate-100"
                    >
                      {showConfirmAccountNumber ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                  {(fieldErrors.confirmAccountNumber || fieldErrors['bank.confirmAccountNumber']) && (
                    <p className="text-[11px] text-rose-500 mt-1">
                      {Array.isArray(fieldErrors.confirmAccountNumber || fieldErrors['bank.confirmAccountNumber'])
                        ? (fieldErrors.confirmAccountNumber || fieldErrors['bank.confirmAccountNumber']).join(', ')
                        : String(fieldErrors.confirmAccountNumber || fieldErrors['bank.confirmAccountNumber'])}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ── STEP 7: REVIEW & SUBMIT ── */}
          {currentStep === 7 && (
            <div className="space-y-4 text-xs">
              <div>
                <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-blue-600" />
                  7. Review & Submit Application
                </h2>
                <p className="text-slate-500 text-[11px]">
                  Confirm your application details before lodging with the Workforce Verification desk.
                </p>
              </div>

              <div className="border border-slate-200 rounded p-4 bg-slate-50/50 space-y-2">
                <div className="flex justify-between border-b border-slate-200 pb-1">
                  <span className="text-slate-500">City / Location:</span>
                  <span className="font-bold text-slate-800">{formData.address.city}{formData.address.state ? `, ${formData.address.state}` : ''} {formData.address.pincode ? `(${formData.address.pincode})` : ''}</span>
                </div>
                <div className="flex justify-between border-b border-slate-200 pb-1">
                  <span className="text-slate-500">Requested Services ({formData.services.length}):</span>
                  <span className="font-bold text-slate-800 text-right truncate max-w-xs">
                    {formData.services.map((s) => s.name).join(', ') || 'None selected'}
                  </span>
                </div>
                <div className="flex justify-between border-b border-slate-200 pb-1">
                  <span className="text-slate-500">Experience:</span>
                  <span className="font-bold text-slate-800">{formData.skills.experienceYears} Years</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Documents Uploaded:</span>
                  <span className="font-bold text-blue-700">{Object.keys(formData.documents).length} Files</span>
                </div>
              </div>

              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.declarationAccepted}
                    onChange={(e) => setFormData({ ...formData, declarationAccepted: e.target.checked })}
                    className="mt-0.5 rounded border-slate-300 text-blue-600"
                  />
                  <span className="text-[11px] text-slate-700 leading-relaxed">
                    I declare that the information and documents provided are accurate and genuine. I acknowledge that I will only receive job dispatches after formal Admin verification.
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Stepper Footer Controls */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-200">
            {currentStep > 1 ? (
              <button
                type="button"
                onClick={handleBack}
                disabled={isSaving}
                className="px-3.5 py-1.5 rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
            ) : (
              <div />
            )}

            {currentStep < 7 ? (
              <button
                type="button"
                onClick={handleNext}
                disabled={isSaving}
                className="px-4 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-sm inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                <span>{isSaving ? 'Saving...' : 'Save & Continue'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmitApplication}
                disabled={isSaving || !formData.declarationAccepted}
                className="px-5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                {isSaving ? 'Submitting...' : 'Submit Application'}
                <CheckCircle2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default OnboardingWizardPage;
