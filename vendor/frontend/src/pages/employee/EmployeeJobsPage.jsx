import React, { useEffect, useState, useMemo, useContext, useCallback, useRef } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { EmployeeRuntimeContext } from '../../context/EmployeeRuntimeContext.jsx';
import { getGPSPosition } from '../../hooks/useGPSPosition.js';
import {
  apiGetWorkforceJobs,
  apiTransitionJob,
  apiAcceptJobOffer,
  apiRejectJobOffer,
  apiVerifyOTP,
  apiVerifyArrival,
} from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';

import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import { Modal } from '../../components/enterprise/Modal.jsx';
import {
  Search,
  MapPin,
  Calendar,
  Clock,
  Phone,
  Navigation,
  CheckCircle2,
  AlertCircle,
  ChevronRight,
  ArrowRight,
  ShieldCheck,
  DollarSign,
  User,
  ExternalLink,
  Sparkles,
  Play,
  RotateCcw,
  X,
  Zap,
  Wind,
  Droplets,
  KeyRound,
  Wrench,
  Layers,
  Truck,
  Eye,
  Check,
  Copy,
  Lock,
} from 'lucide-react';

/**
 * Safely parse and format error messages, cleaning DRF ErrorDetail representations
 */
function cleanErrorMessage(error) {
  if (!error) return 'An unexpected error occurred.';
  let msg = typeof error === 'string' ? error : (error?.message || error?.error || error?.detail || '');
  if (typeof msg !== 'string') {
    try {
      msg = JSON.stringify(msg);
    } catch (_) {
      msg = 'An unexpected error occurred.';
    }
  }

  // 1. Extract string from Python DRF ErrorDetail representation: [ErrorDetail(string='...', code='...')]
  const drfMatch = msg.match(/ErrorDetail\(string=['"]([^'"]+)['"]/);
  if (drfMatch && drfMatch[1]) {
    msg = drfMatch[1];
  }

  // 2. Strip bracket/quote wrappers like ["..."] or ['...']
  msg = msg.replace(/^\[['"]?|['"]?\]$/g, '').trim();

  // 3. Human-friendly geofence explanation if technical phrase was passed
  if (msg.includes('Real GPS Arrival geofence check has not passed')) {
    return 'Arrival verification requires GPS within 250m of the site.';
  }

  return msg || 'Action could not be completed.';
}

/**
 * Service Category Styling (Swiggy / Urban Company clean style)
 */
function getServiceCategoryMeta(categoryName = '', title = '') {
  const text = `${categoryName} ${title}`.toLowerCase();

  // 1. Mini Truck Delivery / Heavy Goods Transport
  if (
    text.includes('goods_transport_truck') ||
    text.includes('mini truck') ||
    text.includes('3 wheeler') ||
    text.includes('three wheeler') ||
    text.includes('truck') ||
    text.includes('pickup') ||
    text.includes('tata ace') ||
    text.includes('dost') ||
    text.includes('bolero') ||
    text.includes('general goods')
  ) {
    return {
      id: 'goods_transport_truck',
      icon: Truck,
      label: 'Mini Truck',
      tagColor: 'bg-blue-500/10 text-blue-800 border-blue-200',
      iconBg: 'bg-blue-100 text-blue-700',
    };
  }

  // 2. Two-Wheeler / Bike Courier
  if (
    text.includes('goods_transport_two_wheeler') ||
    text.includes('two_wheeler') ||
    text.includes('two wheeler') ||
    text.includes('bike') ||
    text.includes('scooter') ||
    text.includes('motorcycle') ||
    text.includes('parcel') ||
    text.includes('courier')
  ) {
    return {
      id: 'goods_transport_two_wheeler',
      icon: Truck,
      label: 'Two-Wheeler',
      tagColor: 'bg-indigo-500/10 text-indigo-800 border-indigo-200',
      iconBg: 'bg-indigo-100 text-indigo-700',
    };
  }

  // 3. Packers & Movers / Relocation
  if (
    text.includes('packers_movers') ||
    text.includes('packer') ||
    text.includes('mover') ||
    text.includes('relocation') ||
    text.includes('house shifting') ||
    text.includes('shifting')
  ) {
    return {
      id: 'packers_movers',
      icon: Layers,
      label: 'Packers & Movers',
      tagColor: 'bg-purple-500/10 text-purple-800 border-purple-200',
      iconBg: 'bg-purple-100 text-purple-700',
    };
  }

  // 4. General Goods & Transport / Logistics
  if (
    text.includes('goods_transport') ||
    text.includes('logistics') ||
    text.includes('goods & transport') ||
    text.includes('goods and transport')
  ) {
    return {
      id: 'goods_transport',
      icon: Truck,
      label: 'Goods & Transport',
      tagColor: 'bg-blue-500/10 text-blue-800 border-blue-200',
      iconBg: 'bg-blue-100 text-blue-700',
    };
  }

  // 5. Electrical & Power
  if (
    text.includes('electr') ||
    text.includes('socket') ||
    text.includes('switch') ||
    text.includes('wiring') ||
    text.includes('fan') ||
    text.includes('light') ||
    text.includes('inverter') ||
    text.includes('mcb') ||
    text.includes('fuse')
  ) {
    return {
      id: 'electrical',
      icon: Zap,
      label: 'Electrical',
      tagColor: 'bg-amber-500/10 text-amber-800 border-amber-200',
      iconBg: 'bg-amber-100 text-amber-700',
    };
  }

  // 6. AC & Appliances
  if (
    text.includes('ac') ||
    text.includes('air') ||
    text.includes('cool') ||
    text.includes('refrigerat') ||
    text.includes('appliance') ||
    text.includes('wash') ||
    text.includes('jet') ||
    text.includes('compressor')
  ) {
    return {
      id: 'ac',
      icon: Wind,
      label: 'AC & Appliance',
      tagColor: 'bg-sky-500/10 text-sky-800 border-sky-200',
      iconBg: 'bg-sky-100 text-sky-700',
    };
  }

  // 7. Plumbing & Water
  if (
    text.includes('plumb') ||
    text.includes('pipe') ||
    text.includes('tap') ||
    text.includes('leak') ||
    text.includes('geyser') ||
    text.includes('drain') ||
    text.includes('water') ||
    text.includes('flush')
  ) {
    return {
      id: 'plumbing',
      icon: Droplets,
      label: 'Plumbing',
      tagColor: 'bg-blue-500/10 text-blue-800 border-blue-200',
      iconBg: 'bg-blue-100 text-blue-700',
    };
  }

  // 8. Carpentry, Locks & Doors
  if (
    text.includes('lock') ||
    text.includes('mortise') ||
    text.includes('carpenter') ||
    text.includes('door') ||
    text.includes('wood') ||
    text.includes('furniture') ||
    text.includes('hinge')
  ) {
    return {
      id: 'carpentry',
      icon: KeyRound,
      label: 'Locks & Carpentry',
      tagColor: 'bg-orange-500/10 text-orange-800 border-orange-200',
      iconBg: 'bg-orange-100 text-orange-700',
    };
  }

  // 9. Cleaning & Disinfection
  if (text.includes('clean') || text.includes('pest') || text.includes('deep') || text.includes('disinfect')) {
    return {
      id: 'cleaning',
      icon: Sparkles,
      label: 'Cleaning',
      tagColor: 'bg-emerald-500/10 text-emerald-800 border-emerald-200',
      iconBg: 'bg-emerald-100 text-emerald-700',
    };
  }

  // Fallback
  return {
    id: 'general',
    icon: Wrench,
    label: 'Home Service',
    tagColor: 'bg-slate-100 text-slate-800 border-slate-200',
    iconBg: 'bg-slate-100 text-slate-700',
  };
}

/**
 * Authoritative Offer Status Helper
 * Respects server-provided is_offer and offer_status.
 * Technicians assigned or accepted to the job are never treated as offers.
 */
function isOfferJob(job) {
  if (!job) return false;
  if (job.is_assigned_to_current_employee || job.is_accepted_by_current_employee) {
    return false;
  }
  if (job.is_offer === true) {
    return true;
  }
  const offerSt = (job.offer_status || job.active_offer?.status || '').toUpperCase();
  if (offerSt === 'OFFERED') {
    return true;
  }
  return false;
}

/**
 * Status Tag (Clear, high-visibility status pill)
 */
function getStatusTag(job) {
  if (!job) return { label: 'Scheduled', badgeClass: 'bg-slate-600 text-white font-bold' };

  if (job?.is_scheduled_future) {
    return {
      label: 'Scheduled',
      badgeClass: 'bg-purple-600 text-white font-bold',
      isScheduled: true,
    };
  }

  if (isOfferJob(job)) {
    return {
      label: 'New Offer',
      badgeClass: 'bg-amber-500 text-white font-bold',
      isOffer: true,
    };
  }

  const st = ((typeof job === 'string' ? job : job.status) || '').toUpperCase();
  if (['ASSIGNED', 'ACCEPTED'].includes(st)) {
    return {
      label: 'Assigned',
      badgeClass: 'bg-indigo-600 text-white font-bold',
    };
  }
  if (['ON_THE_WAY', 'EN_ROUTE'].includes(st)) {
    return {
      label: 'En Route',
      badgeClass: 'bg-sky-600 text-white font-bold animate-pulse',
    };
  }
  if (['ARRIVED'].includes(st)) {
    return {
      label: 'Arrived at Site',
      badgeClass: 'bg-violet-600 text-white font-bold',
    };
  }
  if (['IN_PROGRESS', 'IN_SERVICE', 'INSPECTION', 'PROOF_SUBMITTED'].includes(st)) {
    return {
      label: 'In Progress',
      badgeClass: 'bg-emerald-600 text-white font-bold',
    };
  }
  if (['COMPLETED', 'WORK_COMPLETED', 'WAITING_FOR_PAYMENT'].includes(st)) {
    return {
      label: 'Completed',
      badgeClass: 'bg-teal-600 text-white font-bold',
    };
  }
  if (['CANCELLED', 'REJECTED'].includes(st)) {
    return {
      label: 'Cancelled',
      badgeClass: 'bg-rose-600 text-white font-bold',
    };
  }
  return {
    label: (typeof job === 'string' ? job : job.status) || 'Scheduled',
    badgeClass: 'bg-slate-600 text-white font-bold',
  };
}

const CATEGORIES = [
  { id: 'ALL', label: 'All Categories' },
  { id: 'goods_transport_truck', label: '🚚 Mini Truck' },
  { id: 'goods_transport_two_wheeler', label: '🛵 Two-Wheeler' },
  { id: 'packers_movers', label: '📦 Packers & Movers' },
  { id: 'electrical', label: '⚡ Electrical' },
  { id: 'ac', label: '❄️ AC & Appliances' },
  { id: 'plumbing', label: '💧 Plumbing' },
  { id: 'carpentry', label: '🔨 Locks & Carpentry' },
  { id: 'cleaning', label: '🌿 Cleaning' },
];

function matchesCategory(jobCategoryId, targetCategoryId) {
  if (!targetCategoryId || targetCategoryId === 'ALL') return true;
  if (jobCategoryId === targetCategoryId) return true;
  if (targetCategoryId === 'goods_transport_truck' && (jobCategoryId === 'goods_transport' || jobCategoryId === 'goods_transport_truck')) return true;
  if (targetCategoryId === 'goods_transport' && (jobCategoryId === 'goods_transport_truck' || jobCategoryId === 'goods_transport')) return true;
  return false;
}

function isOfferJobPastDated(job, todayStr) {
  if (!isOfferJob(job)) return false;
  if (job?.preferred_date) {
    return job.preferred_date < todayStr;
  }
  if (job?.created_at) {
    const createdDateStr = String(job.created_at).slice(0, 10);
    return createdDateStr < todayStr;
  }
  return false;
}

export function EmployeeJobsPage() {
  const { user } = useAuth();
  const employeeRuntime = useContext(EmployeeRuntimeContext);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    activeJobs = [],
    completedJobs = [],
    isJobsLoading = false,
    refreshActiveJobs,
    refreshCompletedJobs,
    activeAssignedJob,
    hasActiveJob = false,
    incomingOffers = [],
    declineOfferOptimistic,
    jobsRevision = 0,
  } = employeeRuntime || {};

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const initialTab = (searchParams.get('tab') || '').toUpperCase();
  const [activeTab, setActiveTab] = useState(
    ['OFFERS', 'ACTIVE', 'SCHEDULED', 'COMPLETED'].includes(initialTab) ? initialTab : 'ALL'
  );
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const initialLoading = isJobsLoading && activeJobs.length === 0;

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    const nextParams = new URLSearchParams(searchParams);
    if (tabId === 'ALL') {
      nextParams.delete('tab');
    } else {
      nextParams.set('tab', tabId.toLowerCase());
    }
    setSearchParams(nextParams, { replace: true });
    if (tabId === 'COMPLETED' || tabId === 'ALL') {
      refreshCompletedJobs?.();
    }
  };

  // Job Details Modal
  const [selectedJobForDetails, setSelectedJobForDetails] = useState(null);

  // Per-job inline action errors — replaces alert() entirely.
  // Maps jobId → { code, message, isExpired, isAlreadyAccepted, isBusy }
  const [actionErrors, setActionErrors] = useState({});

  const clearJobError = (jobId) =>
    setActionErrors(prev => { const n = { ...prev }; delete n[jobId]; return n; });

  // Customer Start OTP Modal
  const [otpModalJob, setOtpModalJob] = useState(null);
  const [enteredOtp, setEnteredOtp] = useState('');
  const [otpError, setOtpError] = useState('');
  const [isVerifyingOtp, setIsVerifyingOtp] = useState(false);

  // Fetch completed jobs if tab is COMPLETED or ALL
  useEffect(() => {
    if (activeTab === 'COMPLETED' || activeTab === 'ALL') {
      refreshCompletedJobs?.();
    }
  }, [activeTab, refreshCompletedJobs]);

  const loadJobs = useCallback(async (options = {}) => {
    const isBackground = options?.background === true;
    try {
      setIsRefreshing(true);
      setError('');
      await refreshActiveJobs?.({ force: true, silent: isBackground });
      if (activeTab === 'COMPLETED' || activeTab === 'ALL') {
        await refreshCompletedJobs?.();
      }
    } catch (err) {
      if (!isBackground) {
        setError(cleanErrorMessage(err?.message || 'Failed to load your field jobs.'));
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshActiveJobs, refreshCompletedJobs, activeTab]);

  // Combined jobs according to active tab
  const jobs = useMemo(() => {
    if (activeTab === 'COMPLETED') return completedJobs;
    if (activeTab === 'OFFERS') return incomingOffers;
    if (activeTab === 'SCHEDULED') return activeJobs.filter((j) => j.is_scheduled_future);
    if (activeTab === 'ACTIVE') {
      return activeJobs.filter((j) => !isOfferJob(j) && !j.is_scheduled_future);
    }
    // 'ALL' tab: combines activeJobs and completedJobs
    const map = new Map();
    activeJobs.forEach(j => map.set(j.id, j));
    completedJobs.forEach(j => {
      if (!map.has(j.id)) map.set(j.id, j);
    });
    return Array.from(map.values());
  }, [activeTab, activeJobs, completedJobs, incomingOffers]);

  const handleCopyId = (id, e) => {
    e?.stopPropagation?.();
    navigator.clipboard?.writeText(String(id));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleAcceptOffer = async (jobId, e) => {
    e?.stopPropagation?.();
    // Clear any stale error for this card before retrying
    clearJobError(jobId);
    try {
      setActionLoadingId(jobId);
      await apiAcceptJobOffer(jobId);
      // Auto-start transit for immediate live first-person navigation
      try {
        await apiTransitionJob(jobId, 'ON_THE_WAY');
      } catch (_) {
        // Continue — transition may have already been initiated
      }
      if (selectedJobForDetails?.id === jobId) setSelectedJobForDetails(null);
      navigate(`/workforce/employee/dashboard?job_id=${jobId}&nav=1`);
    } catch (err) {
      const msg = cleanErrorMessage(err?.message || 'Could not accept job offer.');
      const code = err?.code || '';
      const isBusy = code === 'EMPLOYEE_ALREADY_BUSY' || msg.includes('already has an active assigned');
      const isExpired =
        code === 'OFFER_EXPIRED' ||
        code === 'NO_ACTIVE_OFFER' ||
        msg.toLowerCase().includes('expired') ||
        msg.toLowerCase().includes('no active job offer');
      const isAlreadyAccepted =
        code === 'JOB_ALREADY_ACCEPTED' ||
        msg.toLowerCase().includes('already been accepted');
      setActionErrors(prev => ({
        ...prev,
        [jobId]: { code, message: msg, isExpired, isAlreadyAccepted, isBusy },
      }));
      // Only refresh if expired or already taken, keeping offer visible when busy
      if (isExpired || isAlreadyAccepted) {
        refreshActiveJobs?.({ force: true });
      }
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleRejectOffer = async (jobId, e) => {
    e?.stopPropagation?.();
    if (!window.confirm('Decline this job offer? It will be reassigned to another nearby technician.')) return;
    clearJobError(jobId);
    try {
      setActionLoadingId(jobId);
      // Optimistically remove from runtime state instantly without waiting
      declineOfferOptimistic?.(jobId);
      await apiRejectJobOffer(jobId, 'Technician declined');
      refreshActiveJobs?.({ force: true, silent: true });
      if (selectedJobForDetails?.id === jobId) setSelectedJobForDetails(null);
    } catch (err) {
      const msg = cleanErrorMessage(err?.message || 'Could not decline job offer.');
      const code = err?.code || '';
      setActionErrors(prev => ({
        ...prev,
        [jobId]: { code, message: msg, isExpired: false, isAlreadyAccepted: false },
      }));
      // Rollback optimistic removal
      refreshActiveJobs?.({ force: true });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleStartTrip = async (jobId, e) => {
    e?.stopPropagation?.();
    clearJobError(jobId);
    try {
      setActionLoadingId(jobId);
      await apiTransitionJob(jobId, 'ON_THE_WAY');
      if (selectedJobForDetails?.id === jobId) setSelectedJobForDetails(null);
      navigate(`/workforce/employee/dashboard?job_id=${jobId}&nav=1`);
    } catch (err) {
      const msg = cleanErrorMessage(err?.message || 'Failed to update status.');
      const code = err?.code || '';
      setActionErrors(prev => ({
        ...prev,
        [jobId]: { code, message: msg, isExpired: false, isAlreadyAccepted: false },
      }));
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleArrived = async (jobId, e) => {
    e?.stopPropagation?.();
    clearJobError(jobId);
    try {
      setActionLoadingId(jobId);

      // 1. Resolve GPS coordinates
      let lat = employeeRuntime?.liveLocation?.latitude;
      let lon = employeeRuntime?.liveLocation?.longitude;

      if (!lat || !lon) {
        try {
          const loc = await employeeRuntime?.scanCurrentLocation?.();
          lat = loc?.latitude;
          lon = loc?.longitude;
        } catch (_) {}
      }

      if (!lat || !lon) {
        try {
          const pos = await getGPSPosition(true);
          lat = pos?.coords?.latitude;
          lon = pos?.coords?.longitude;
        } catch (_) {}
      }

      if (!lat || !lon) {
        throw new Error('Unable to retrieve GPS coordinates. Please allow location permissions in your browser to verify arrival at site.');
      }

      // 2. Dedicated arrival verification with geofencing check
      await apiVerifyArrival(jobId, lat, lon);
      await loadJobs();
      if (selectedJobForDetails?.id === jobId) setSelectedJobForDetails(null);
    } catch (err) {
      const msg = cleanErrorMessage(err?.message || err || 'Failed to update status.');
      const code = err?.code || '';
      setActionErrors(prev => ({
        ...prev,
        [jobId]: { code, message: msg, isExpired: false, isAlreadyAccepted: false },
      }));
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleVerifyOtpSubmit = async (e) => {
    e.preventDefault();
    const cleanOtp = enteredOtp ? enteredOtp.trim() : '';
    if (!cleanOtp || cleanOtp.length < 4) {
      setOtpError('Please enter the customer work start OTP.');
      return;
    }
    try {
      setIsVerifyingOtp(true);
      setOtpError('');
      await apiVerifyOTP(otpModalJob.id, cleanOtp);
      setOtpModalJob(null);
      setEnteredOtp('');
      await loadJobs();
      navigate('/workforce/employee/dashboard');
    } catch (err) {
      setOtpError(cleanErrorMessage(err?.message || 'Invalid OTP code. Please check with customer.'));
    } finally {
      setIsVerifyingOtp(false);
    }
  };

  // 1. Memoized todayStr to avoid calling new Date() repeatedly in filter loops
  const todayStr = useMemo(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  }, []);

  // 2. Tab counts — single-pass O(N) evaluation
  const counts = useMemo(() => {
    let active = 0;
    let scheduled = 0;
    let validActiveCount = 0;

    activeJobs.forEach((j) => {
      if (isOfferJobPastDated(j, todayStr)) return;
      validActiveCount++;
      if (j.is_scheduled_future) {
        scheduled++;
      } else if (!isOfferJob(j)) {
        const st = (j.status || '').toUpperCase();
        if (['ASSIGNED', 'ACCEPTED', 'ON_THE_WAY', 'EN_ROUTE', 'ARRIVED', 'IN_PROGRESS', 'IN_SERVICE', 'INSPECTION', 'PROOF_SUBMITTED'].includes(st)) {
          active++;
        }
      }
    });

    let completed = 0;
    completedJobs.forEach((j) => {
      if (!isOfferJobPastDated(j, todayStr)) completed++;
    });

    let offers = 0;
    incomingOffers.forEach((j) => {
      if (!isOfferJobPastDated(j, todayStr)) offers++;
    });

    return {
      ALL: validActiveCount + completed,
      OFFERS: offers,
      ACTIVE: active,
      SCHEDULED: scheduled,
      COMPLETED: completed,
    };
  }, [activeJobs, completedJobs, incomingOffers, todayStr]);

  // 3. Category counts — evaluated for the active tab jobs and current search
  const categoryCounts = useMemo(() => {
    const countsMap = { ALL: 0 };
    const term = searchTerm.toLowerCase().trim();

    jobs.forEach((job) => {
      if (isOfferJobPastDated(job, todayStr)) return;

      if (term) {
        const matches =
          (job.service_title || job.service_category || '').toLowerCase().includes(term) ||
          (job.customer_display_name || '').toLowerCase().includes(term) ||
          (job.address || '').toLowerCase().includes(term) ||
          String(job.request_id || job.id).toLowerCase().includes(term);
        if (!matches) return;
      }

      countsMap.ALL = (countsMap.ALL || 0) + 1;
      const meta = getServiceCategoryMeta(job.service_category, job.service_title);
      const catId = meta.id;
      countsMap[catId] = (countsMap[catId] || 0) + 1;
      if (catId === 'goods_transport') {
        countsMap['goods_transport_truck'] = (countsMap['goods_transport_truck'] || 0) + 1;
      }
    });

    return countsMap;
  }, [jobs, searchTerm, todayStr]);

  // 4. Filtered jobs list with hoisted term and streamlined category matching
  const filteredJobs = useMemo(() => {
    const term = searchTerm.toLowerCase().trim();

    return jobs.filter((job) => {
      if (isOfferJobPastDated(job, todayStr)) {
        return false;
      }
      const isOffer = isOfferJob(job);
      const status = (job.status || '').toUpperCase();

      if (activeTab === 'OFFERS' && !isOffer) {
        return false;
      }
      if (activeTab === 'SCHEDULED' && !job.is_scheduled_future) {
        return false;
      }
      if (
        activeTab === 'ACTIVE' &&
        (job.is_scheduled_future ||
          isOffer ||
          !['ASSIGNED', 'ACCEPTED', 'ON_THE_WAY', 'EN_ROUTE', 'ARRIVED', 'IN_PROGRESS', 'IN_SERVICE', 'INSPECTION', 'PROOF_SUBMITTED'].includes(status))
      ) {
        return false;
      }
      if (
        activeTab === 'COMPLETED' &&
        (isOffer || !['COMPLETED', 'WORK_COMPLETED', 'WAITING_FOR_PAYMENT'].includes(status))
      ) {
        return false;
      }

      if (selectedCategory !== 'ALL') {
        const meta = getServiceCategoryMeta(job.service_category, job.service_title);
        if (!matchesCategory(meta.id, selectedCategory)) {
          return false;
        }
      }

      if (term) {
        const matches =
          (job.service_title || job.service_category || '').toLowerCase().includes(term) ||
          (job.customer_display_name || '').toLowerCase().includes(term) ||
          (job.address || '').toLowerCase().includes(term) ||
          String(job.request_id || job.id).toLowerCase().includes(term);
        if (!matches) return false;
      }

      return true;
    });
  }, [jobs, activeTab, selectedCategory, searchTerm, todayStr]);

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/employee/dashboard' }, { label: 'Jobs' }]}>
      <div className="max-w-6xl mx-auto space-y-4 font-sans pb-16">
        {/* ── TOP CLEAN HEADER (Swiggy Style) ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs">
          <div>
            <h1 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              My Orders & Jobs
            </h1>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              {counts.OFFERS > 0 ? (
                <span className="text-amber-700 font-bold">
                  ⚡ {counts.OFFERS} new service offer{counts.OFFERS > 1 ? 's' : ''} available
                </span>
              ) : (
                'Manage your customer bookings, navigation, and service fulfillment'
              )}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Search */}
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search job or location..."
                className="w-full pl-9 pr-8 py-2 bg-slate-100/90 border border-transparent hover:border-slate-300 focus:bg-white focus:border-slate-400 rounded-xl text-xs font-medium text-slate-900 outline-none transition-all"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 p-0.5"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

            <button
              onClick={() => loadJobs({ background: true })}
              disabled={isRefreshing || initialLoading}
              className="p-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl transition-all cursor-pointer shrink-0"
              title="Refresh"
            >
              <RotateCcw className={`w-4 h-4 ${isRefreshing || initialLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {/* ── BUSY TECHNICIAN OFFERS BANNER ── */}
        {hasActiveJob && incomingOffers.length > 0 && (
          <div className="bg-amber-500/10 border border-amber-300/80 rounded-2xl p-4 flex items-start justify-between gap-3 text-amber-950 shadow-xs">
            <div className="flex items-start gap-3 min-w-0">
              <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs sm:text-sm font-black text-amber-950">
                  You're currently on Job #{activeAssignedJob?.request_id || activeAssignedJob?.id}.
                </p>
                <p className="text-xs text-amber-800 mt-0.5 font-medium">
                  {incomingOffers.length} new service offer{incomingOffers.length > 1 ? 's are' : ' is'} available. You can accept one after completing your current job.
                </p>
              </div>
            </div>
            {activeTab !== 'OFFERS' && (
              <button
                type="button"
                onClick={() => handleTabChange('OFFERS')}
                className="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-white font-black text-xs rounded-xl shrink-0 transition-colors shadow-2xs cursor-pointer inline-flex items-center gap-1.5"
              >
                <span>View Offers</span>
                <span className="bg-amber-700/60 px-1.5 py-0.5 rounded-md text-[10px] font-mono">
                  {incomingOffers.length}
                </span>
              </button>
            )}
          </div>
        )}

        {/* ── FILTER & CATEGORY CONTROL BAR (Unified Segmented Panel) ── */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-3 sm:p-3.5 shadow-2xs space-y-2.5">
          {/* 1. Status Segmented Tabs */}
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-0.5 scrollbar-none no-scrollbar scroll-smooth">
            {[
              { id: 'ALL', label: 'All Jobs', count: counts.ALL },
              { id: 'OFFERS', label: '⚡ New Offers', count: counts.OFFERS, isOffer: true },
              { id: 'ACTIVE', label: '▶️ In Progress', count: counts.ACTIVE },
              { id: 'SCHEDULED', label: '📅 Scheduled', count: counts.SCHEDULED },
              { id: 'COMPLETED', label: '✅ Completed', count: counts.COMPLETED },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id)}
                  className={`px-3.5 py-2 sm:px-4 sm:py-2.5 rounded-xl font-bold text-xs whitespace-nowrap transition-all flex items-center gap-2 cursor-pointer shrink-0 ${
                    isActive
                      ? 'bg-slate-900 text-white shadow-xs'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/80 shadow-2xs'
                  }`}
                >
                  <span>{tab.label}</span>
                  {tab.count > 0 && (
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-black ${
                        tab.isOffer && counts.OFFERS > 0
                          ? 'bg-amber-500 text-white animate-pulse'
                          : isActive
                          ? 'bg-white/20 text-white'
                          : 'bg-slate-200/80 text-slate-700'
                      }`}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Hairline Divider */}
          <div className="h-px bg-slate-100 w-full" />

          {/* 2. Category Filter Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-none no-scrollbar scroll-smooth text-xs">
            {CATEGORIES.map((cat) => {
              const isSelected = selectedCategory === cat.id;
              const catCount = categoryCounts[cat.id] || 0;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => {
                    // Toggle deselection: clicking active category resets to ALL
                    setSelectedCategory((prev) => (prev === cat.id ? 'ALL' : cat.id));
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all cursor-pointer inline-flex items-center gap-1.5 shrink-0 ${
                    isSelected
                      ? 'bg-indigo-50 text-indigo-900 border border-indigo-300 font-bold shadow-2xs ring-2 ring-indigo-500/15'
                      : 'bg-white text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-slate-200/80'
                  }`}
                >
                  <span>{cat.label}</span>
                  {catCount > 0 && (
                    <span
                      className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold ${
                        isSelected
                          ? 'bg-indigo-200/80 text-indigo-950'
                          : 'bg-slate-100 text-slate-600 border border-slate-200/60'
                      }`}
                    >
                      {catCount}
                    </span>
                  )}
                  {isSelected && cat.id !== 'ALL' && (
                    <span className="text-indigo-400 hover:text-indigo-700 ml-0.5 font-bold">×</span>
                  )}
                </button>
              );
            })}

            {selectedCategory !== 'ALL' && (
              <button
                type="button"
                onClick={() => setSelectedCategory('ALL')}
                className="px-2 py-1 text-[11px] font-medium text-slate-400 hover:text-slate-700 underline decoration-slate-300 underline-offset-2 whitespace-nowrap cursor-pointer shrink-0 ml-1"
              >
                Reset filter
              </button>
            )}
          </div>
        </div>

        {/* ── CLEAN SWIGGY-STYLE JOB CARDS GRID ── */}
        {initialLoading ? (
          <div className="bg-white border border-slate-200/80 rounded-2xl p-16 text-center shadow-xs">
            <LoadingState message="Loading your orders..." />
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="bg-white border border-slate-200/80 rounded-2xl p-16 text-center shadow-xs space-y-3">
            <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Sparkles className="w-7 h-7" />
            </div>
            <h3 className="text-base font-black text-slate-900">No jobs in this view</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {searchTerm || selectedCategory !== 'ALL'
                ? 'Try clearing your search or category filter.'
                : 'You have no customer service requests matching this section.'}
            </p>
            {(searchTerm || selectedCategory !== 'ALL' || activeTab !== 'ALL') && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('ALL');
                  handleTabChange('ALL');
                }}
                className="px-4 py-2 bg-slate-900 text-white text-xs font-bold rounded-xl shadow-xs cursor-pointer inline-flex items-center gap-1.5"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Show All Jobs</span>
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredJobs.map((job) => {
              const isOffer = isOfferJob(job);
              const status = (job.status || '').toUpperCase();
              const isAssigned = !isOffer && (status === 'ASSIGNED' || status === 'ACCEPTED');
              const isOnTheWay = !isOffer && (status === 'ON_THE_WAY' || status === 'EN_ROUTE');
              const isArrived = !isOffer && status === 'ARRIVED';
              const isInProgress = !isOffer && (status === 'IN_PROGRESS' || status === 'IN_SERVICE' || status === 'INSPECTION' || status === 'PROOF_SUBMITTED');
              const isCompleted = !isOffer && (status === 'COMPLETED' || status === 'WORK_COMPLETED' || status === 'WAITING_FOR_PAYMENT');

              const catMeta = getServiceCategoryMeta(job.service_category, job.service_title);
              const statusTag = getStatusTag(job);
              const CategoryIcon = catMeta.icon;

              const mapUrl = job.address
                ? `https://maps.google.com/?q=${encodeURIComponent(job.address)}`
                : null;

              // Bug found: job.estimated_price / job.price are not fields the
              // vendor API ever returns (WorkforceJobSerializer sends
              // total_amount and a computed payment{amount_due,...} object) --
              // so this always fell through to the 450 literal, showing the
              // exact same payout on every job regardless of its real value.
              // Matches the correct pattern already used in
              // EmployeeDashboardPage.jsx (selectedJob.payment?.amount_due || selectedJob.total_amount).
              const payoutAmount = job.payment?.amount_due || job.total_amount || 0;

              return (
                <div
                  key={job.id}
                  className={`bg-white rounded-2xl border transition-all flex flex-col justify-between overflow-hidden shadow-2xs hover:shadow-md ${
                    job.is_scheduled_future
                      ? 'border-purple-300 ring-2 ring-purple-400/20'
                      : isOffer
                      ? 'border-amber-300 ring-2 ring-amber-400/20'
                      : isInProgress
                      ? 'border-emerald-300 ring-2 ring-emerald-400/20'
                      : 'border-slate-200/90'
                  }`}
                >
                  {/* ── CARD TOP SECTION ── */}
                  <div className="p-5 space-y-4">
                    {/* Header Row: Category Badge + Status + Payout */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center gap-3">
                        <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${catMeta.iconBg}`}>
                          <CategoryIcon className="w-5 h-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase border ${catMeta.tagColor}`}>
                              {catMeta.label}
                            </span>
                            {job.job_type === 'ESTIMATION' && (
                              <span className="px-2 py-0.5 rounded-md text-[10px] font-extrabold uppercase bg-amber-50 text-amber-800 border border-amber-300">
                                Estimation
                              </span>
                            )}
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${statusTag.badgeClass}`}>
                              {statusTag.label}
                            </span>
                          </div>
                          <span className="font-mono text-xs font-bold text-slate-400 mt-1 block">
                            #{job.request_id || job.id}
                          </span>
                        </div>
                      </div>

                      {/* Prominent Swiggy-Style Payout Amount */}
                      <div className="text-right shrink-0">
                        <div className="text-lg sm:text-xl font-black text-slate-900 font-mono tracking-tight">
                          ₹{Number(payoutAmount).toLocaleString('en-IN')}
                        </div>
                        <span className="text-[10px] font-semibold text-emerald-700 block">
                          Earn on finish
                        </span>
                      </div>
                    </div>

                    {/* Service Name Title */}
                    <div>
                      <h2 className="text-base font-black text-slate-900 tracking-tight leading-snug">
                        {job.service_title || job.service_category || 'Customer Service Request'}
                      </h2>
                    </div>

                    {/* ── CLEAR, UNCLUTTERED INFO ROWS ── */}
                    <div className="pt-2 border-t border-slate-100 space-y-2.5 text-xs">
                      {/* Schedule Timing */}
                      <div className="flex items-center gap-2 text-slate-700">
                        <Clock className="w-4 h-4 text-indigo-600 shrink-0" />
                        <span className="font-bold text-slate-900">
                          {job.preferred_date
                            ? `${job.preferred_date}${job.preferred_time ? ` • ${job.preferred_time}` : ''}`
                            : 'Immediate Dispatch'}
                        </span>
                      </div>

                      {/* Location & Maps Navigation */}
                      {job.address && (
                        <div className="flex items-start justify-between gap-2 text-slate-600">
                          <div className="flex items-start gap-2 min-w-0">
                            <MapPin className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                            <span className="line-clamp-2 leading-relaxed text-slate-700 font-medium">
                              {job.address}
                            </span>
                          </div>
                          {mapUrl && (
                            <a
                              href={mapUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-2.5 py-1 bg-sky-50 hover:bg-sky-100 text-sky-800 font-bold text-[11px] rounded-lg border border-sky-200 inline-flex items-center gap-1 shrink-0 transition-colors"
                            >
                              <Navigation className="w-3 h-3" />
                              <span>Map</span>
                            </a>
                          )}
                        </div>
                      )}

                      {/* Customer Info & Direct Call */}
                      <div className="flex items-center justify-between gap-2 pt-1">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-800 font-bold text-[10px] flex items-center justify-center shrink-0">
                            {(job.customer_display_name || 'C')[0].toUpperCase()}
                          </div>
                          <span className="font-bold text-slate-800 truncate">
                            {job.customer_display_name || 'Customer'}
                          </span>
                        </div>

                        {/* Bug found: WorkforceJobSerializer sends "phone", never
                            "customer_phone" -- so this Call button was always
                            hidden, even for phone-booked jobs where a real
                            number is on file. Read the real field, keep
                            customer_phone as a harmless second fallback. */}
                        {(job.phone || job.customer_phone) ? (
                          <a
                            href={`tel:${job.phone || job.customer_phone}`}
                            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-lg inline-flex items-center gap-1.5 shadow-2xs transition-all shrink-0 cursor-pointer"
                          >
                            <Phone className="w-3 h-3" />
                            <span>Call</span>
                          </a>
                        ) : (
                          <span className="text-[11px] text-slate-400 font-medium">App Booking</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* ── CARD BOTTOM ACTION BAR ── */}
                  <div className="bg-slate-50/80 px-5 py-3 border-t border-slate-100 flex items-center justify-between gap-2">
                    <button
                      type="button"
                      onClick={() => setSelectedJobForDetails(job)}
                      className="text-xs font-bold text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
                    >
                      View Details
                    </button>

                    <div className="flex items-center gap-2">
                      {/* SCHEDULED FUTURE BOOKINGS (Locked until date) */}
                      {job.is_scheduled_future && (
                        <div className="flex items-center gap-1.5 px-3 py-2 bg-purple-50 text-purple-900 border border-purple-200 rounded-xl text-xs font-semibold max-w-[280px]">
                          <Lock className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                          <span className="truncate">{job.scheduled_hold_reason || `Locked until ${job.preferred_date}`}</span>
                        </div>
                      )}

                      {/* OFFER ACTIONS — or inline error state when accept/decline fails */}
                      {!job.is_scheduled_future && isOffer && (() => {
                        const jobErr = actionErrors[job.id];
                        if (jobErr) {
                          // Busy error: technician already has an active job
                          if (jobErr.isBusy) {
                            return (
                              <>
                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold rounded-xl max-w-[280px]">
                                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                                  <span className="truncate">{jobErr.message}</span>
                                </span>
                                <button
                                  type="button"
                                  onClick={(e) => handleRejectOffer(job.id, e)}
                                  disabled={actionLoadingId === job.id}
                                  className="px-3.5 py-2 bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-200 text-xs font-bold rounded-xl transition-all cursor-pointer"
                                >
                                  Decline
                                </button>
                              </>
                            );
                          }
                          // Offer expired / no longer active → subdued pill + refresh
                          if (jobErr.isExpired || jobErr.isAlreadyAccepted) {
                            return (
                              <>
                                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-500 border border-slate-200 text-xs font-bold rounded-xl">
                                  <AlertCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                                  <span>
                                    {jobErr.isAlreadyAccepted
                                      ? 'Taken by another'
                                      : 'Offer expired'}
                                  </span>
                                </span>
                                <button
                                  type="button"
                                  onClick={() => { clearJobError(job.id); loadJobs(); }}
                                  className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-600 border border-slate-200 text-xs font-bold rounded-xl transition-all cursor-pointer inline-flex items-center gap-1"
                                >
                                  <RotateCcw className="w-3 h-3" />
                                  <span>Refresh</span>
                                </button>
                              </>
                            );
                          }
                          // Other action error → rose pill + dismiss
                          return (
                            <>
                              <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold rounded-xl max-w-[200px]">
                                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                                <span className="truncate">{jobErr.message}</span>
                              </span>
                              <button
                                type="button"
                                onClick={() => clearJobError(job.id)}
                                className="p-1.5 bg-white hover:bg-slate-100 text-slate-500 border border-slate-200 rounded-lg transition-all cursor-pointer"
                                title="Dismiss"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </>
                          );
                        }
                        // Normal offer state — Decline + Accept buttons
                        const isBusyWithActiveJob = Boolean(hasActiveJob);
                        return (
                          <>
                            <button
                              type="button"
                              onClick={(e) => handleRejectOffer(job.id, e)}
                              disabled={actionLoadingId === job.id}
                              className="px-3.5 py-2 bg-white hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-200 text-xs font-bold rounded-xl transition-all cursor-pointer"
                            >
                              Decline
                            </button>
                            <button
                              type="button"
                              onClick={(e) => handleAcceptOffer(job.id, e)}
                              disabled={actionLoadingId === job.id || isBusyWithActiveJob}
                              title={isBusyWithActiveJob ? "Finish current job to accept" : "Accept job offer"}
                              className={`px-5 py-2 text-xs font-black rounded-xl shadow-sm transition-all flex items-center gap-1.5 ${
                                isBusyWithActiveJob
                                  ? 'bg-slate-200 text-slate-500 cursor-not-allowed border border-slate-300'
                                  : 'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white cursor-pointer'
                              }`}
                            >
                              <Zap className="w-4 h-4 fill-current" />
                              <span>{isBusyWithActiveJob ? 'Finish current job to accept' : `Accept • ₹${payoutAmount}`}</span>
                            </button>
                          </>
                        );
                      })()}

                      {/* Non-offer action errors (start trip / arrived) */}
                      {!isOffer && actionErrors[job.id] && (
                        <div className="flex items-center gap-1.5">
                          <span
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 text-xs font-semibold rounded-xl max-w-[280px]"
                            title={actionErrors[job.id].message}
                          >
                            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                            <span className="truncate">{actionErrors[job.id].message}</span>
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e?.stopPropagation?.();
                              clearJobError(job.id);
                            }}
                            className="p-1.5 bg-white hover:bg-slate-100 text-slate-500 border border-slate-200 rounded-lg transition-all cursor-pointer shrink-0"
                            title="Dismiss"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}

                      {/* ASSIGNED -> START TRIP */}
                      {isAssigned && (
                        <button
                          type="button"
                          onClick={(e) => handleStartTrip(job.id, e)}
                          disabled={actionLoadingId === job.id}
                          className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-2"
                        >
                          <Play className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Start Navigation</span>
                        </button>
                      )}

                      {/* ON THE WAY -> ARRIVED */}
                      {isOnTheWay && (
                        <button
                          type="button"
                          onClick={(e) => handleArrived(job.id, e)}
                          disabled={actionLoadingId === job.id}
                          className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-2"
                        >
                          <MapPin className="w-3.5 h-3.5" />
                          <span>I've Arrived at Site</span>
                        </button>
                      )}

                      {/* ARRIVED -> VERIFY OTP or OTP ALREADY VERIFIED */}
                      {isArrived && (
                        <>
                          {job.otp_verified ? (
                            <div className="flex items-center gap-2">
                              <span className="px-3 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold rounded-xl flex items-center gap-1">
                                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                                <span>OTP Verified</span>
                              </span>
                              <Link
                                to="/workforce/employee/dashboard"
                                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-1.5"
                              >
                                <Camera className="w-3.5 h-3.5" />
                                <span>Complete Selfie in Cockpit</span>
                                <ArrowRight className="w-3.5 h-3.5" />
                              </Link>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setOtpModalJob(job);
                                setEnteredOtp('');
                                setOtpError('');
                              }}
                              className="px-5 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-2"
                            >
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>Enter Start OTP</span>
                            </button>
                          )}
                        </>
                      )}

                      {/* IN PROGRESS -> COCKPIT */}
                      {isInProgress && (
                        <Link
                          to="/workforce/employee/dashboard"
                          className="px-5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-2"
                        >
                          <span>Open Job Cockpit</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      )}

                      {/* ESTIMATION WORKFLOW LINK */}
                      {(job.job_type === 'ESTIMATION' || (job.status || '').toLowerCase().includes('inspection') || (job.status || '').toLowerCase().includes('quotation')) && (
                        <Link
                          to="/workforce/vendor/estimations"
                          className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-1.5"
                        >
                          <Wrench className="w-3.5 h-3.5" />
                          <span>Estimation Portal</span>
                        </Link>
                      )}

                      {/* COMPLETED */}
                      {isCompleted && (
                        <span className="px-3.5 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold rounded-xl flex items-center gap-1">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span>Completed</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* ── JOB DETAILS MODAL ── */}
        {selectedJobForDetails && (
          <Modal
            isOpen={Boolean(selectedJobForDetails)}
            onClose={() => setSelectedJobForDetails(null)}
            title={`Booking #${selectedJobForDetails.request_id || selectedJobForDetails.id}`}
            maxWidth="max-w-xl"
          >
            <div className="space-y-4 text-xs font-sans">
              <div className="flex items-center justify-between p-4 bg-slate-50 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    Service
                  </span>
                  <span className="font-black text-slate-900 text-sm">
                    {selectedJobForDetails.service_title || selectedJobForDetails.service_category || 'Service Request'}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                    Payout Amount
                  </span>
                  <span className="text-base font-black text-slate-900 font-mono">
                    ₹{Number(selectedJobForDetails.payment?.amount_due || selectedJobForDetails.total_amount || 0).toLocaleString('en-IN')}
                  </span>
                </div>
              </div>

              {/* Customer Info */}
              <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                  <span>Customer</span>
                </span>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-900 text-sm">
                    {selectedJobForDetails.customer_display_name || 'Customer'}
                  </span>
                  {(selectedJobForDetails.phone || selectedJobForDetails.customer_phone) && (
                    <a
                      href={`tel:${selectedJobForDetails.phone || selectedJobForDetails.customer_phone}`}
                      className="px-3 py-1 bg-emerald-600 text-white font-bold text-xs rounded-lg inline-flex items-center gap-1.5"
                    >
                      <Phone className="w-3 h-3" />
                      <span>Call Client</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Address */}
              <div className="p-4 bg-white border border-slate-200 rounded-xl space-y-2">
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-rose-500" />
                  <span>Location</span>
                </span>
                <p className="text-slate-800 font-medium leading-relaxed">
                  {selectedJobForDetails.address || 'Address provided upon dispatch.'}
                </p>
                {selectedJobForDetails.address && (
                  <a
                    href={`https://maps.google.com/?q=${encodeURIComponent(selectedJobForDetails.address)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sky-700 font-bold hover:underline pt-1"
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    <span>Open in Google Maps</span>
                  </a>
                )}
              </div>

              {/* Modal Footer */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedJobForDetails(null)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-bold rounded-xl hover:bg-slate-50 transition-all cursor-pointer"
                >
                  Close
                </button>
                {selectedJobForDetails.is_scheduled_future ? (
                  <div className="flex items-center gap-1.5 px-4 py-2 bg-purple-50 text-purple-900 border border-purple-200 rounded-xl text-xs font-semibold">
                    <Lock className="w-4 h-4 text-purple-700 shrink-0" />
                    <span>{selectedJobForDetails.scheduled_hold_reason || 'Scheduled for future date — acceptance locked.'}</span>
                  </div>
                ) : isOfferJob(selectedJobForDetails) && (
                  <button
                    type="button"
                    onClick={(e) => handleAcceptOffer(selectedJobForDetails.id, e)}
                    disabled={actionLoadingId === selectedJobForDetails.id}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-all cursor-pointer flex items-center gap-1.5"
                  >
                    <Zap className="w-4 h-4 fill-current" />
                    <span>Accept Job</span>
                  </button>
                )}
              </div>
            </div>
          </Modal>
        )}

        {/* ── START OTP VERIFICATION MODAL ── */}
        {otpModalJob && (
          <Modal
            isOpen={Boolean(otpModalJob)}
            onClose={() => setOtpModalJob(null)}
            title="Enter Start OTP"
          >
            <form onSubmit={handleVerifyOtpSubmit} className="space-y-4 text-xs font-sans">
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-amber-700" />
                  <span>Customer Verification Code</span>
                </p>
                <p className="text-[11px] leading-relaxed">
                  Ask customer <strong>{otpModalJob.customer_display_name || 'Customer'}</strong> for their 6-digit code to start <strong>#{otpModalJob.request_id || otpModalJob.id}</strong>.
                </p>
              </div>

              {otpError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-900 rounded-xl font-semibold">
                  {otpError}
                </div>
              )}

              <div>
                <input
                  type="text"
                  maxLength={6}
                  value={enteredOtp}
                  onChange={(e) => setEnteredOtp(e.target.value)}
                  placeholder="• • • • • •"
                  className="w-full px-4 py-3 text-center font-mono font-black text-2xl tracking-[0.5em] bg-white border border-slate-300 rounded-xl outline-none focus:border-slate-800 shadow-xs text-slate-900"
                  required
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setOtpModalJob(null)}
                  className="px-4 py-2 border border-slate-300 text-slate-700 font-bold rounded-xl hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isVerifyingOtp || !enteredOtp}
                  className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl shadow-xs cursor-pointer disabled:opacity-50 flex items-center gap-2"
                >
                  {isVerifyingOtp && <RotateCcw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Verify & Start</span>
                </button>
              </div>
            </form>
          </Modal>
        )}
      </div>
    </AppShell>
  );
}

export default EmployeeJobsPage;
