import React, { useEffect, useState } from 'react';
import { AppShell } from '../../components/common/AppShell.jsx';
import { Modal } from '../../components/enterprise/Modal.jsx';
import { apiGetSkills, apiCreateSkill, apiAssignSkill, apiGetEmployees } from '../../api/workforceService.js';
import { Award, PlusCircle, CheckCircle2, AlertCircle, User, ShieldCheck } from 'lucide-react';

export function AdminSkillsPage() {
  const [skills, setSkills] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });

  // Create Skill Modal
  const [showSkillModal, setShowSkillModal] = useState(false);
  const [skillName, setSkillName] = useState('');
  const [skillCategory, setSkillCategory] = useState('HVAC');
  const [skillDesc, setSkillDesc] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Assign Skill Modal
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignEmpId, setAssignEmpId] = useState('');
  const [assignSkillId, setAssignSkillId] = useState('');
  const [proficiencyLevel, setProficiencyLevel] = useState('INTERMEDIATE');
  const [isAssigning, setIsAssigning] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [skData, empData] = await Promise.all([
        apiGetSkills().catch(() => []),
        apiGetEmployees().catch(() => []),
      ]);
      setSkills(skData || []);
      setEmployees(empData || []);
      if (empData && empData.length > 0) setAssignEmpId(empData[0].id);
      if (skData && skData.length > 0) setAssignSkillId(skData[0].id);
    } catch (_) {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateSkill = async (e) => {
    e.preventDefault();
    try {
      setIsCreating(true);
      setStatusMsg({ type: '', text: '' });
      await apiCreateSkill({
        name: skillName,
        category: skillCategory,
        description: skillDesc,
      });
      setShowSkillModal(false);
      setSkillName('');
      setSkillDesc('');
      setStatusMsg({ type: 'success', text: 'Skill created successfully.' });
      await loadData();
      setTimeout(() => setStatusMsg({ type: '', text: '' }), 4000);
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to create skill.' });
    } finally {
      setIsCreating(false);
    }
  };

  const handleAssignSkill = async (e) => {
    e.preventDefault();
    if (!assignEmpId || !assignSkillId) return;
    try {
      setIsAssigning(true);
      setStatusMsg({ type: '', text: '' });
      await apiAssignSkill(assignEmpId, {
        skill_id: assignSkillId,
        proficiency_level: proficiencyLevel,
      });
      setShowAssignModal(false);
      setStatusMsg({ type: 'success', text: 'Skill assigned and verified for technician.' });
      await loadData();
      setTimeout(() => setStatusMsg({ type: '', text: '' }), 4000);
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to assign skill.' });
    } finally {
      setIsAssigning(false);
    }
  };

  return (
    <AppShell breadcrumbs={[{ label: 'Workforce' }, { label: 'Skills & Qualifications' }]}>
      <div className="space-y-4 text-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 border border-zinc-200/90 rounded-md shadow-card">
          <div>
            <h1 className="text-base font-bold text-zinc-950 flex items-center gap-2 tracking-tight">
              <Award className="w-5 h-5 text-zinc-800" />
              <span>Workforce Skills & Verification Matrix</span>
            </h1>
            <p className="text-zinc-500 text-xs mt-1 leading-relaxed">
              Manage skill certifications and verify technician service proficiency for dispatch qualification.
            </p>
          </div>
          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={() => setShowSkillModal(true)}
              className="px-4 py-2 min-h-[38px] bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white font-bold rounded-lg shadow-xs inline-flex items-center gap-2 transition-all cursor-pointer"
            >
              <PlusCircle className="w-4 h-4 text-zinc-200" />
              <span>New Skill</span>
            </button>
            <button
              type="button"
              onClick={() => setShowAssignModal(true)}
              className="px-4 py-2 min-h-[38px] bg-white hover:bg-zinc-50 active:bg-zinc-100 text-zinc-900 border border-zinc-300 font-bold rounded-lg shadow-xs inline-flex items-center gap-2 transition-all cursor-pointer"
            >
              <ShieldCheck className="w-4 h-4 text-zinc-700" />
              <span>Assign Skill</span>
            </button>
          </div>
        </div>

        {statusMsg.text && (
          <div className={`p-3.5 rounded-lg border font-semibold flex items-center gap-2 text-xs ${statusMsg.type === 'success' ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-rose-50 border-rose-200 text-rose-900'}`}>
            {statusMsg.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-700" /> : <AlertCircle className="w-4 h-4 text-rose-700" />}
            <span>{statusMsg.text}</span>
          </div>
        )}

        <div className="bg-white border border-zinc-200/90 rounded-md overflow-hidden shadow-card">
          <div className="bg-zinc-50/80 px-4 py-3 border-b border-zinc-200/80 font-bold text-zinc-950 uppercase tracking-wider text-xs">
            Master Skill Catalog ({skills.length})
          </div>
          <table className="w-full text-left text-xs">
            <thead className="bg-zinc-50/60 text-zinc-500 uppercase text-[11px] font-bold border-b border-zinc-200">
              <tr>
                <th className="px-5 py-3.5">Skill Name</th>
                <th className="px-5 py-3.5">Category</th>
                <th className="px-5 py-3.5">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {skills.length > 0 ? (
                skills.map((s) => (
                  <tr key={s.id} className="hover:bg-zinc-50/80 transition-colors">
                    <td className="px-5 py-3.5 font-bold text-zinc-950">{s.name}</td>
                    <td className="px-5 py-3.5">
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-zinc-100 text-zinc-800 border border-zinc-200">
                        {s.category}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-zinc-500 leading-relaxed">{s.description || '—'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-5 py-12 text-center text-zinc-500">
                    No skills cataloged yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>


        {/* Modal: New Skill */}
        <Modal isOpen={showSkillModal} onClose={() => setShowSkillModal(false)} title="Create New Skill Certification">
          <form onSubmit={handleCreateSkill} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Skill Name</label>
              <input
                type="text"
                required
                value={skillName}
                onChange={(e) => setSkillName(e.target.value)}
                placeholder="e.g. Inverter AC PCB Diagnostics"
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              />
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Category</label>
              <select
                value={skillCategory}
                onChange={(e) => setSkillCategory(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              >
                <option value="HVAC">HVAC & Air Conditioning</option>
                <option value="Electrical">Electrical & Wiring</option>
                <option value="Plumbing">Plumbing & Sanitation</option>
                <option value="Appliances">Home Appliances</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Description</label>
              <textarea
                rows={3}
                value={skillDesc}
                onChange={(e) => setSkillDesc(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
              <button type="button" onClick={() => setShowSkillModal(false)} className="px-3 py-1.5 rounded border border-slate-300 text-slate-700 font-semibold">
                Cancel
              </button>
              <button type="submit" disabled={isCreating} className="px-4 py-1.5 rounded bg-blue-600 text-white font-bold hover:bg-blue-700">
                {isCreating ? 'Saving...' : 'Create Skill'}
              </button>
            </div>
          </form>
        </Modal>

        {/* Modal: Assign Skill */}
        <Modal isOpen={showAssignModal} onClose={() => setShowAssignModal(false)} title="Assign & Verify Skill to Technician">
          <form onSubmit={handleAssignSkill} className="space-y-4 text-xs">
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Select Technician</label>
              <select
                value={assignEmpId}
                onChange={(e) => setAssignEmpId(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              >
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.full_name || e.username} ({e.employee_id})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Select Skill</label>
              <select
                value={assignSkillId}
                onChange={(e) => setAssignSkillId(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              >
                {skills.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.category})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-slate-700 font-semibold mb-1">Proficiency Level</label>
              <select
                value={proficiencyLevel}
                onChange={(e) => setProficiencyLevel(e.target.value)}
                className="w-full border border-slate-300 rounded px-3 py-2 text-slate-800"
              >
                <option value="BEGINNER">BEGINNER</option>
                <option value="INTERMEDIATE">INTERMEDIATE</option>
                <option value="EXPERT">EXPERT</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
              <button type="button" onClick={() => setShowAssignModal(false)} className="px-3 py-1.5 rounded border border-slate-300 text-slate-700 font-semibold">
                Cancel
              </button>
              <button type="submit" disabled={isAssigning} className="px-4 py-1.5 rounded bg-emerald-600 text-white font-bold hover:bg-emerald-700">
                {isAssigning ? 'Assigning...' : 'Assign & Verify'}
              </button>
            </div>
          </form>
        </Modal>
      </div>
    </AppShell>
  );
}

export default AdminSkillsPage;
