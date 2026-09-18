import React from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import {
  ShieldAlert,
  Clock,
  CheckCircle2,
  AlertOctagon,
  Sparkles,
} from 'lucide-react';

export function SellerClaimsPage() {
  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-red-50 text-red-600 rounded-xl border border-red-100">
              <ShieldAlert className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Claims & Disputes</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-red-50 text-red-700 border border-red-200 px-2 py-0.5 rounded-full">
                  Phase 2 Roadmap
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Delivery damage claims, lost transit reimbursements, penalty disputes, and merchant protections
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to="/workforce/seller/dashboard"
              className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Seller Home
            </Link>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 max-w-6xl w-full mx-auto space-y-6">
          {/* Roadmap Info Banner */}
          <div className="p-5 bg-gradient-to-r from-red-50 via-rose-50 to-white rounded-2xl border border-red-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2 bg-red-600 text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">
                  Seller Protection & Claims Portal — Coming in Next Phase
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                  The Claims engine protects merchants by providing structured dispute submissions for goods damaged in transit, lost shipments by platform delivery riders, or incorrect customer return claims.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Metrics Bar (Clean 0 count / Phase 2) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Open Claims</span>
                <Clock className="w-4 h-4 text-red-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Awaiting Phase 2 engine</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Under Review</span>
                <AlertOctagon className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Admin arbitration</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Approved Claims</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Reimbursements issued</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Claim Value</span>
                <span className="text-xs font-bold text-slate-400">₹</span>
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">₹0.00</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Total settled amount</p>
            </div>
          </div>

          {/* Empty State Table Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-12 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-4 shadow-xs">
              <ShieldAlert className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-base font-bold text-slate-900">No Active Claims</h3>
            <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed">
              Dispute filings and transit damage claim tickets will be tracked here once the Seller Claims system is launched in the next phase.
            </p>

            <div className="mt-6 flex items-center gap-3">
              <Link
                to="/workforce/seller/dashboard"
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold transition-colors"
              >
                <span>Back to Seller Dashboard</span>
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default SellerClaimsPage;
