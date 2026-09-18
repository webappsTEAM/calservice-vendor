import React from 'react';
import { Link } from 'react-router-dom';
import { Sidebar } from '../../components/common/Sidebar.jsx';
import {
  RotateCcw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  Tag,
} from 'lucide-react';

export function SellerReturnsPage() {
  return (
    <div className="flex min-h-screen bg-slate-100 font-sans text-slate-800">
      <Sidebar />

      <main className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 sticky top-0 z-10 px-8 py-5 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <span className="p-2.5 bg-amber-50 text-amber-600 rounded-xl border border-amber-100">
              <RotateCcw className="w-5 h-5" />
            </span>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Returns & Replacements</h1>
                <span className="text-[10px] font-bold uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full">
                  Phase 2 Roadmap
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Reverse logistics, item quality inspection, replacement approvals, and refunds
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
          <div className="p-5 bg-gradient-to-r from-amber-50 via-orange-50 to-white rounded-2xl border border-amber-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3.5">
              <div className="p-2 bg-amber-600 text-white rounded-xl shrink-0 mt-0.5 shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-slate-900 text-sm">
                  Returns & Reverse Logistics — Coming in Next Phase
                </h3>
                <p className="text-xs text-slate-600 mt-1 max-w-2xl leading-relaxed">
                  The Returns module will handle customer return requests, photographic evidence inspection, pickup verification, merchant accept/reject decisions, and automated refund ledger adjustments.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Metrics Bar (Clean 0 count / Phase 2) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Return Requests</span>
                <Clock className="w-4 h-4 text-amber-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Awaiting Phase 2 engine</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">In Transit</span>
                <RotateCcw className="w-4 h-4 text-blue-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Rider return pickups</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Under Inspection</span>
                <AlertTriangle className="w-4 h-4 text-purple-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Quality check queue</p>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Resolved</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              </div>
              <p className="text-2xl font-extrabold text-slate-900 font-mono mt-2">0</p>
              <p className="text-[11px] text-slate-400 mt-0.5">Refunded / Replaced</p>
            </div>
          </div>

          {/* Empty State Table Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-12 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 bg-slate-50 border border-slate-200 rounded-2xl flex items-center justify-center text-slate-400 mb-4 shadow-xs">
              <RotateCcw className="w-8 h-8 text-slate-400" />
            </div>
            <h3 className="text-base font-bold text-slate-900">No Return Requests</h3>
            <p className="text-xs text-slate-500 max-w-md mt-1.5 leading-relaxed">
              Customer return requests and reverse pickup workflows will appear here once the return management pipeline is enabled in the next phase.
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

export default SellerReturnsPage;
