import React, { useEffect, useState } from 'react';
import { apiRequest } from '../../api/client.js';
import { apiGetCatalog } from '../../api/workforceService.js';

export default function ServiceSkillRequirements({ skills }) {
  const [services, setServices] = useState([]);
  const [serviceId, setServiceId] = useState('');
  const [skillId, setSkillId] = useState('');
  const [requirements, setRequirements] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [catalogRevision, setCatalogRevision] = useState(0);
  useEffect(() => {
    let cancelled = false;
    apiGetCatalog().then(data => {
      if (!cancelled) setServices((data || []).flatMap(category =>
        (category.services || []).map(service => ({ ...service, category_name: category.name }))));
    }).catch(err => { if (!cancelled) setError(err.message || 'Could not load services.'); });
    return () => { cancelled = true; };
  }, [catalogRevision]);
  useEffect(() => {
    if (!serviceId) return;
    let cancelled = false;
    setBusy(true); setError(''); setRequirements([]);
    apiRequest(`/workforce/skills/requirements/?service_id=${serviceId}`).then(data => {
      if (!cancelled) setRequirements(data || []);
    }).catch(err => { if (!cancelled) setError(err.message || 'Could not load qualification rules.'); })
      .finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [serviceId, revision]);
  async function save(id, mandatory) {
    setBusy(true); setError('');
    try {
      await apiRequest('/workforce/skills/requirements/', { method: 'POST', json: {
        service_id: Number(serviceId), skill_id: Number(id), is_mandatory: mandatory,
      }});
      setRevision(value => value + 1);
    } catch (err) { setError(err.message || 'Could not save qualification rule.'); }
    finally { setBusy(false); }
  }
  return <section className="space-y-3 rounded-lg border border-zinc-200 bg-white p-5">
    <h2 className="text-sm font-bold">Required skills by service</h2>
    <p className="text-zinc-600">Choose a service from the shared customer catalog. Your technicians must hold every mandatory skill, verified by your company, as well as approved service access before receiving its jobs.</p>
    <label className="block font-semibold">Customer service
      <select disabled={busy} className="mt-1 block w-full rounded border p-2" value={serviceId} onChange={e => setServiceId(e.target.value)}>
        <option value="">Select a service</option>
        {services.map(service => <option key={service.id} value={service.id}>{service.category_name} — {service.name}</option>)}
      </select>
    </label>
    {error && <p role="alert" className="text-red-700">{error} <button className="underline" onClick={() => { setError(''); setCatalogRevision(v => v + 1); setRevision(v => v + 1); }}>Retry</button></p>}
    {busy && <p role="status">Updating requirements…</p>}
    {serviceId && <>
      {!busy && !requirements.length && <p>No additional skill rules configured. Approved service access is still required.</p>}
      <ul className="space-y-2">{requirements.map(row => <li key={row.id} className="flex justify-between gap-4 border-b py-2">
        <span>{row.skill_name} · {row.is_mandatory ? 'Mandatory' : 'Optional'}</span>
        <button disabled={busy} className="font-semibold text-emerald-700 disabled:opacity-40" onClick={() => save(row.skill_id, !row.is_mandatory)}>{row.is_mandatory ? 'Make optional' : 'Require skill'}</button>
      </li>)}</ul>
      <div className="flex items-end gap-3"><label className="flex-1 font-semibold">Skill<select className="mt-1 block w-full rounded border p-2" value={skillId} onChange={e => setSkillId(e.target.value)}><option value="">Select a skill</option>{skills.filter(skill => skill.is_active).map(skill => <option key={skill.id} value={skill.id}>{skill.name}</option>)}</select></label>
        <button disabled={busy || !skillId} onClick={() => save(skillId, true)} className="rounded bg-emerald-700 px-4 py-2 text-white disabled:opacity-40">Require skill</button></div>
    </>}
  </section>;
}
