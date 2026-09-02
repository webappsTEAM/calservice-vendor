import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthProvider.jsx';
import { apiGetMyPerformance } from '../../api/workforceService.js';
import { AppShell } from '../../components/common/AppShell.jsx';
import { MetricStrip } from '../../components/enterprise/MetricStrip.jsx';
import { StatusBadge } from '../../components/enterprise/StatusBadge.jsx';
import { LoadingState } from '../../components/enterprise/LoadingState.jsx';
import { ErrorState } from '../../components/enterprise/ErrorState.jsx';
import {
  Award,
  Star,
  CheckCircle2,
  ThumbsUp,
  Percent,
  MessageSquare,
  TrendingUp,
  Calendar,
  User,
  Clock,
  Sparkles,
} from 'lucide-react';

export function EmployeePerformancePage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const loadPerformance = async () => {
    try {
      setIsLoading(true);
      setError('');
      const res = await apiGetMyPerformance();
      setData(res);
    } catch (err) {
      setError(err.message || 'Failed to load performance metrics from server.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPerformance();
  }, []);

  if (isLoading) {
    return (
      <AppShell breadcrumbs={[{ label: 'Home' }, { label: 'Feedback & Performance' }]}>
        <LoadingState message="Calculating authoritative performance & ratings..." />
      </AppShell>
    );
  }

  const metrics = data?.metrics || {
    jobs_completed: 0,
    total_jobs_assigned: 0,
    completion_rate: 0,
    average_rating: 0,
    csat_score: 0,
    feedback_submissions_count: 0,
    issue_resolution_rate: 0,
  };

  const distribution = data?.rating_distribution || { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
  const scorecard = data?.scorecard || { tier: 'UNRATED', sla_score: 0, average_rating: 0, rating_count: 0 };
  const feedbacks = data?.feedbacks || [];
  const totalFeedbackCount = metrics.feedback_submissions_count || 0;

  const tierStyles = {
    GOLD: { label: 'Gold', className: 'bg-amber-50 border-amber-300 text-amber-800' },
    SILVER: { label: 'Silver', className: 'bg-slate-100 border-slate-300 text-slate-700' },
    BRONZE: { label: 'Bronze', className: 'bg-orange-50 border-orange-300 text-orange-800' },
    UNRATED: { label: 'Unrated', className: 'bg-slate-50 border-slate-200 text-slate-500' },
  };
  const tierStyle = tierStyles[scorecard.tier] || tierStyles.UNRATED;

  const metricCards = [
    {
      title: 'Jobs Completed',
      value: metrics.jobs_completed,
      icon: CheckCircle2,
      color: 'blue',
      change: `${metrics.total_jobs_assigned} assigned total`,
    },
    {
      title: 'Average Rating',
      value: metrics.average_rating > 0 ? `${metrics.average_rating} / 5.0` : '—',
      icon: Star,
      color: 'amber',
      change: `${totalFeedbackCount} ratings recorded`,
    },
    {
      title: 'CSAT Score',
      value: metrics.csat_score > 0 ? `${metrics.csat_score}%` : '—',
      icon: ThumbsUp,
      color: 'emerald',
      change: '4★ & 5★ satisfaction share',
    },
    {
      title: 'Completion Rate',
      value: `${metrics.completion_rate}%`,
      icon: Percent,
      color: 'indigo',
      change: 'Fulfilled vs. assigned',
    },
    {
      title: 'On-Time Resolution',
      value: `${metrics.issue_resolution_rate}%`,
      icon: TrendingUp,
      color: 'emerald',
      change: 'Without revisit or delay',
    },
  ];

  return (
    <AppShell breadcrumbs={[{ label: 'Home', to: '/workforce/employee/dashboard' }, { label: 'Performance' }]}>
      <div className="space-y-4 max-w-6xl mx-auto text-xs">
        {error && <ErrorState message={error} onDismiss={() => setError('')} />}

        {/* Top Metric Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {metricCards.map((m, idx) => {
            const Icon = m.icon;
            return (
              <div key={idx} className="bg-white border border-zinc-200/90 rounded-md p-4 shadow-card space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-zinc-500 uppercase tracking-wider">{m.title}</span>
                  <div className="p-1.5 rounded-md bg-zinc-100 border border-zinc-200 text-zinc-800 shadow-2xs">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                </div>
                <div className="text-xl font-extrabold text-zinc-950 font-mono tracking-tight">{m.value}</div>
                <p className="text-[10px] text-zinc-500 truncate font-medium">{m.change}</p>
              </div>
            );
          })}
        </div>

        {/* SEVO Section 4: persisted rating + SLA scorecard tier -- the
            same signal that feeds the dispatch-ranking bonus, so a worker
            can see it directly rather than it being used silently. */}
        <div className={`border rounded p-3.5 shadow-sm flex items-center justify-between gap-3 ${tierStyle.className}`}>
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4" />
            <div>
              <p className="text-xs font-bold">{tierStyle.label} Tier Scorecard</p>
              <p className="text-[11px] opacity-80">
                {scorecard.rating_count > 0
                  ? `${scorecard.rating_count} rated job${scorecard.rating_count === 1 ? "" : "s"} · SLA score ${scorecard.sla_score}%`
                  : "Complete and get rated on 3+ jobs to unlock a tier."}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold font-mono">{scorecard.average_rating > 0 ? scorecard.average_rating.toFixed(1) : '—'}</p>
            <p className="text-[10px] opacity-70">avg. rating</p>
          </div>
        </div>

        {/* Rating Breakdown & CSAT Overview */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Left Column: Star Rating Distribution (5 cols) */}
          <div className="lg:col-span-5 bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card flex flex-col">
            <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 flex items-center justify-between">
              <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                <span>Rating Distribution ({totalFeedbackCount} Reviews)</span>
              </h2>
            </div>

            <div className="p-5 space-y-4 text-xs flex-1 flex flex-col justify-center">
              {totalFeedbackCount > 0 ? (
                <div className="space-y-3">
                  {[5, 4, 3, 2, 1].map((stars) => {
                    const count = distribution[stars] || 0;
                    const pct = totalFeedbackCount > 0 ? Math.round((count / totalFeedbackCount) * 100) : 0;
                    return (
                      <div key={stars} className="flex items-center gap-3">
                        <span className="w-12 font-bold text-zinc-800 font-mono text-[11px] flex items-center gap-1">
                          <span>{stars}</span>
                          <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                        </span>
                        <div className="flex-1 h-2.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                          <div
                            className="h-full bg-slate-800 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        <span className="w-14 text-right text-zinc-500 font-mono text-[11px] font-semibold">
                          {count} ({pct}%)
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 space-y-2">
                  <div className="w-10 h-10 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto text-zinc-400">
                    <Star className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-zinc-950 text-xs">No customer ratings yet</h3>
                  <p className="text-[11px] text-zinc-500 max-w-xs mx-auto leading-relaxed">
                    Ratings will be calculated automatically when customers review your completed service requests.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Performance Guidelines & Quality Standards (7 cols) */}
          <div className="lg:col-span-7 bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card flex flex-col">
            <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 flex items-center justify-between">
              <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
                <Award className="w-4 h-4 text-zinc-800" />
                <span>Workforce Service Quality Benchmark</span>
              </h2>
            </div>

            <div className="p-5 space-y-4 text-xs text-zinc-600 flex-1 flex flex-col justify-between">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3.5 bg-zinc-50 border border-zinc-200/80 rounded-lg space-y-1">
                  <h4 className="font-bold text-zinc-950 text-xs">Target CSAT Standard</h4>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">
                    Maintain an average CSAT &ge; <strong className="text-zinc-950">85%</strong> to remain eligible for priority automated dispatching.
                  </p>
                </div>
                <div className="p-3.5 bg-zinc-50 border border-zinc-200/80 rounded-lg space-y-1">
                  <h4 className="font-bold text-zinc-950 text-xs">Proof of Work Compliance</h4>
                  <p className="text-[11px] text-zinc-500 leading-relaxed">
                    100% of jobs require valid arrival GPS telemetry, customer work start OTP, and before/after photos.
                  </p>
                </div>
              </div>

              <div className="p-3.5 bg-zinc-100/70 border border-zinc-200/90 rounded-lg text-xs text-zinc-800 space-y-0.5">
                <p className="font-bold text-zinc-950">Authoritative Data Integration Notice</p>
                <p className="text-zinc-500 leading-relaxed">
                  All metrics displayed here are computed directly from completed ServiceRequest records and customer feedback submissions stored in PostgreSQL.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Customer Reviews & Feedback Submissions */}
        <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card">
          <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 flex items-center justify-between">
            <h2 className="text-xs font-bold text-zinc-950 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-zinc-800" />
              <span>Customer Feedback & Reviews ({feedbacks.length})</span>
            </h2>
            <button
              type="button"
              onClick={loadPerformance}
              className="text-xs font-bold text-zinc-800 hover:text-zinc-950 hover:underline cursor-pointer"
            >
              Refresh
            </button>
          </div>

          <div className="p-0">
            {feedbacks.length > 0 ? (
              <div className="divide-y divide-zinc-100">
                {feedbacks.map((fb) => (
                  <div key={fb.id} className="p-4 space-y-2 hover:bg-zinc-50/80 transition-colors">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <div className="flex items-center text-amber-500">
                          {[1, 2, 3, 4, 5].map((s) => (
                            <Star
                              key={s}
                              className={`w-3.5 h-3.5 ${
                                s <= fb.rating ? 'fill-amber-400 text-amber-400' : 'text-zinc-300'
                              }`}
                            />
                          ))}
                        </div>
                        <span className="font-bold text-zinc-950 text-xs">{fb.rating}.0</span>
                        <span className="text-zinc-400">•</span>
                        <span className="font-bold text-zinc-800 text-xs">
                          {fb.customer_name || 'Customer'}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-[11px] text-zinc-500 font-mono">
                        <span>Job: <strong className="text-zinc-950">{fb.request_id || `SR-${fb.job}`}</strong></span>
                        <span>•</span>
                        <span>{new Date(fb.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <p className="text-xs text-zinc-700 italic leading-relaxed">
                      "{fb.review || 'Service completed satisfactorily according to scope.'}"
                    </p>

                    {fb.service_title && (
                      <span className="inline-block px-2.5 py-0.5 bg-zinc-100 text-zinc-800 rounded-full text-[10px] font-bold border border-zinc-200">
                        {fb.service_title}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-12 px-4 text-center space-y-2">
                <div className="w-12 h-12 rounded-full bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto text-zinc-400">
                  <MessageSquare className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-zinc-950 text-xs">No customer feedback yet</h3>
                <p className="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
                  Customer feedback will appear here as soon as clients review your completed work orders.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default EmployeePerformancePage;

