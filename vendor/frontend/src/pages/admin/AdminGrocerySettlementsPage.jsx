import React, { useState, useEffect } from 'react';
import { DollarSign, ArrowUpRight, ArrowDownLeft, RefreshCw, FileText, CheckCircle, Clock } from 'lucide-react';
import { workforceService } from '../../api/workforceService';

export default function AdminGrocerySettlementsPage() {
  const [data, setData] = useState({ ledger_entries: [], settlements: [] });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await workforceService.getGrocerySettlements();
      setData(res || { ledger_entries: [], settlements: [] });
    } catch (err) {
      console.error('Failed to load settlements:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const totalCredits = data.ledger_entries
    .filter((e) => e.entry_type === 'CREDIT')
    .reduce((sum, e) => sum + parseFloat(e.amount || 0), 0);

  const totalDebits = data.ledger_entries
    .filter((e) => e.entry_type === 'DEBIT')
    .reduce((sum, e) => sum + parseFloat(e.amount || 0), 0);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            <DollarSign className="w-7 h-7 text-emerald-600" />
            Financial Settlement & Ledger
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable double-entry ledger tracking completed sales, platform commissions, and vendor payouts.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition shadow-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh Ledger
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Total Sales Credited</span>
          <span className="text-2xl font-black text-emerald-600">₹{totalCredits.toFixed(2)}</span>
          <p className="text-xs text-slate-500 mt-1">Net earnings credited after commission and store coupons.</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Total Debited / Settled</span>
          <span className="text-2xl font-black text-slate-900">₹{totalDebits.toFixed(2)}</span>
          <p className="text-xs text-slate-500 mt-1">Bank payouts and adjustments transferred.</p>
        </div>
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Commission Rate</span>
          <span className="text-2xl font-black text-blue-600">5.0%</span>
          <p className="text-xs text-slate-500 mt-1">Standard CalServices grocery category commission.</p>
        </div>
      </div>

      {/* Ledger Transactions Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-slate-400" />
            Immutable Ledger Entries
          </h3>
          <span className="text-xs text-slate-400">{data.ledger_entries.length} entries recorded</span>
        </div>

        {loading ? (
          <div className="py-12 text-center text-slate-400">Loading ledger...</div>
        ) : data.ledger_entries.length === 0 ? (
          <div className="py-12 text-center text-slate-400">No ledger transactions recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500 text-xs font-bold uppercase tracking-wider border-b border-slate-100">
                <tr>
                  <th className="py-3 px-5">Date</th>
                  <th className="py-3 px-5">Type</th>
                  <th className="py-3 px-5">Category</th>
                  <th className="py-3 px-5">Description</th>
                  <th className="py-3 px-5 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.ledger_entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3.5 px-5 text-xs text-slate-400 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-5 whitespace-nowrap">
                      {entry.entry_type === 'CREDIT' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                          <ArrowDownLeft className="w-3 h-3" /> Credit
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                          <ArrowUpRight className="w-3 h-3" /> Debit
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-5 text-xs font-semibold text-slate-700">
                      {entry.category}
                    </td>
                    <td className="py-3.5 px-5 text-xs text-slate-600 max-w-md truncate">
                      {entry.description || '-'}
                    </td>
                    <td className={`py-3.5 px-5 text-right font-bold whitespace-nowrap ${
                      entry.entry_type === 'CREDIT' ? 'text-emerald-600' : 'text-slate-900'
                    }`}>
                      {entry.entry_type === 'CREDIT' ? '+' : '-'}₹{parseFloat(entry.amount).toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
