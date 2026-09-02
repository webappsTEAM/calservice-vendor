import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { AppShell } from '../../components/common/AppShell.jsx';
import { apiRequest } from '../../api/client.js';
import {
  Building2,
  Users,
  Search,
  Mail,
  Phone,
  MapPin,
  Clock,
  ShieldCheck,
  Briefcase,
  ChevronRight,
  AlertTriangle,
  Layers,
  Sparkles,
} from 'lucide-react';

export function PlatformVendorsPage() {
  const [vendors, setVendors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchVendors = async () => {
    try {
      setLoading(true);
      setError('');
      const data = await apiRequest('/workforce/platform/vendors/');
      setVendors(data.vendors || []);
    } catch (err) {
      setError(err.message || 'Failed to load platform vendor businesses.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, []);

  const filtered = vendors.filter((v) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      (v.company_name || '').toLowerCase().includes(term) ||
      (v.owner_name || '').toLowerCase().includes(term) ||
      (v.owner_email || '').toLowerCase().includes(term) ||
      (v.city || '').toLowerCase().includes(term)
    );
  });

  const totalTiedWorkers = vendors.reduce((acc, v) => acc + (v.tied_workers_count || 0), 0);

  return (
    <AppShell>
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Building2 className="w-6 h-6 text-indigo-600" />
              <h1 className="text-2xl font-bold text-slate-900">Vendor Companies Management</h1>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              SEVO Platform Admin: Complete oversight of service vendor organizations and their tied workforce.
            </p>
          </div>

          <NavLink
            to="/workforce/platform/workforce"
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Users className="w-4 h-4" />
            <span>Manage All Workforce (Solo & Tied)</span>
          </NavLink>
        </div>

        {/* Global Summary Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Registered Vendors</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">{vendors.length}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Total Tied Workforce</span>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{totalTiedWorkers}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Platform Operations</span>
            <div className="text-sm font-bold text-indigo-700 mt-2 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" />
              <span>Multi-Tenant Architecture Active</span>
            </div>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search by vendor name, owner, email, or city..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:bg-white"
            />
          </div>
          <span className="text-xs text-slate-400 font-medium">
            Showing {filtered.length} of {vendors.length} vendors
          </span>
        </div>

        {/* Vendors Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-16 flex flex-col items-center justify-center text-slate-500">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mb-2" />
              <p className="text-sm">Loading vendor directory...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-16 text-center">
              <Building2 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800">No vendor businesses found</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No vendors match your search criteria.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-5 py-3">Vendor / Business</th>
                    <th className="px-4 py-3">Owner / Contact</th>
                    <th className="px-4 py-3">Location</th>
                    <th className="px-4 py-3 text-center">Tied Workers</th>
                    <th className="px-4 py-3 text-center">Pending Invites</th>
                    <th className="px-5 py-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((v) => (
                    <tr key={v.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm shrink-0">
                            {v.company_name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <span className="font-bold text-slate-900 text-sm block">{v.company_name}</span>
                            <span className="text-[11px] text-slate-400 font-mono">ID: #{v.id} • {v.slug}</span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div>
                          <span className="font-semibold text-slate-800 block">{v.owner_name || '—'}</span>
                          <div className="text-[11px] text-slate-500 flex flex-col gap-0.5 mt-0.5">
                            {v.owner_email && (
                              <span className="flex items-center gap-1">
                                <Mail className="w-3 h-3 text-slate-400" />
                                {v.owner_email}
                              </span>
                            )}
                            {v.owner_phone && (
                              <span className="flex items-center gap-1">
                                <Phone className="w-3 h-3 text-slate-400" />
                                {v.owner_phone}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-slate-600">
                        <div className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>{v.city || v.address || '—'}</span>
                        </div>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          {v.tied_workers_count} active
                        </span>
                      </td>
                      <td className="px-4 py-4 text-center">
                        <span className="text-xs font-semibold text-slate-600">
                          {v.pending_invitations_count}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <NavLink
                          to={`/workforce/platform/workforce?vendor_id=${v.id}`}
                          className="inline-flex items-center gap-1 text-xs font-bold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          <span>View Workers</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </NavLink>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
