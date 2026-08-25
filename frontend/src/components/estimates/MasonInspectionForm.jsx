import React from 'react';
import { Hammer, AlertTriangle, ShieldCheck, Truck } from 'lucide-react';

export default function MasonInspectionForm({ data, onChange }) {
  const handleChange = (field, value) => {
    const updated = {
      ...data,
      [field]: value,
    };

    // Auto calculate area if length & height/width present
    if (field === 'length' || field === 'height' || field === 'width') {
      const len = parseFloat(field === 'length' ? value : updated.length) || 0;
      const hgt = parseFloat(field === 'height' ? value : updated.height) || 0;
      const wid = parseFloat(field === 'width' ? value : updated.width) || 0;
      if (len > 0 && hgt > 0) {
        updated.area_sqft = Math.round(len * hgt * 100) / 100;
      } else if (len > 0 && wid > 0) {
        updated.area_sqft = Math.round(len * wid * 100) / 100;
      }
    }

    onChange(updated);
  };

  const isStructural = data.structural_impact === 'SUSPECTED_STRUCTURAL' || data.structural_impact === 'STRUCTURAL';

  return (
    <div className="space-y-5">
      <div className="bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/50 rounded-xl p-4 flex items-start gap-3">
        <Hammer className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-amber-900 dark:text-amber-200">Masonry & Civil Site Inspection</h4>
          <p className="text-xs text-amber-700 dark:text-amber-300 mt-0.5">
            Record wall dimensions, demolition requirements, and assess structural impact integrity.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Masonry Work Type
          </label>
          <select
            value={data.work_type || 'Plastering & Wall Repair'}
            onChange={(e) => handleChange('work_type', e.target.value)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            <option value="Brick & Block Work">Brick & Block Work</option>
            <option value="Plastering & Wall Repair">Plastering & Wall Repair</option>
            <option value="Wall & Partition Construction">Wall & Partition Construction</option>
            <option value="Wall Breaking & Demolition">Wall Breaking & Demolition</option>
            <option value="Tile & Flooring Repair">Tile & Flooring Repair</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Estimated Duration (Days)
          </label>
          <input
            type="number"
            min={1}
            value={data.estimated_duration_days || 1}
            onChange={(e) => handleChange('estimated_duration_days', parseInt(e.target.value) || 1)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Length (Feet)
          </label>
          <input
            type="number"
            step="0.1"
            value={data.length || ''}
            onChange={(e) => handleChange('length', e.target.value)}
            placeholder="e.g. 15.5"
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Height / Width (Feet)
          </label>
          <input
            type="number"
            step="0.1"
            value={data.height || data.width || ''}
            onChange={(e) => handleChange('height', e.target.value)}
            placeholder="e.g. 9.5"
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Calculated Surface Area (Sq.Ft.)
          </label>
          <input
            type="number"
            step="0.1"
            value={data.area_sqft || ''}
            onChange={(e) => handleChange('area_sqft', parseFloat(e.target.value) || 0)}
            placeholder="Auto-calculated or enter manually"
            className="w-full text-sm font-semibold rounded-lg border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/80 text-amber-900 dark:text-amber-300 px-3 py-2.5 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Structural Gate Selector */}
      <div className="p-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/70 space-y-3">
        <label className="block text-xs font-semibold text-gray-800 dark:text-gray-200">
          Structural Impact & Load-Bearing Assessment
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <label
            className={`flex flex-col p-3 rounded-lg border cursor-pointer transition-all ${
              data.structural_impact === 'NONE' || !data.structural_impact
                ? 'border-green-500 bg-green-50/50 dark:bg-green-950/20 text-green-900 dark:text-green-200'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="structural_impact"
                value="NONE"
                checked={data.structural_impact === 'NONE' || !data.structural_impact}
                onChange={() => handleChange('structural_impact', 'NONE')}
                className="text-green-600 focus:ring-green-500"
              />
              <span className="text-xs font-semibold">No Structural Impact</span>
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 pl-5">
              Surface repair, cosmetic partition, or minor plaster.
            </p>
          </label>

          <label
            className={`flex flex-col p-3 rounded-lg border cursor-pointer transition-all ${
              data.structural_impact === 'SUSPECTED_STRUCTURAL'
                ? 'border-amber-500 bg-amber-50/50 dark:bg-amber-950/20 text-amber-900 dark:text-amber-200'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="structural_impact"
                value="SUSPECTED_STRUCTURAL"
                checked={data.structural_impact === 'SUSPECTED_STRUCTURAL'}
                onChange={() => handleChange('structural_impact', 'SUSPECTED_STRUCTURAL')}
                className="text-amber-600 focus:ring-amber-500"
              />
              <span className="text-xs font-semibold">Suspected Structural</span>
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 pl-5">
              Deep cracks near pillar/beam or unconfirmed wall type.
            </p>
          </label>

          <label
            className={`flex flex-col p-3 rounded-lg border cursor-pointer transition-all ${
              data.structural_impact === 'STRUCTURAL'
                ? 'border-red-500 bg-red-50/50 dark:bg-red-950/20 text-red-900 dark:text-red-200'
                : 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            <div className="flex items-center gap-2">
              <input
                type="radio"
                name="structural_impact"
                value="STRUCTURAL"
                checked={data.structural_impact === 'STRUCTURAL'}
                onChange={() => handleChange('structural_impact', 'STRUCTURAL')}
                className="text-red-600 focus:ring-red-500"
              />
              <span className="text-xs font-semibold">Load-Bearing / Structural</span>
            </div>
            <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1 pl-5">
              Demolition or cutting into load-bearing wall or column.
            </p>
          </label>
        </div>

        {isStructural && (
          <div className="p-3 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
            <div className="text-xs text-red-800 dark:text-red-300">
              <strong className="font-semibold">Mandatory Structural Gate:</strong> Because this work affects structural or load-bearing elements, quotation sending will require review and clearance from a Structural Engineer or Vendor Operations Admin before it can be delivered to the customer.
            </div>
          </div>
        )}
      </div>

      <div className="pt-2">
        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Scope & Logistics
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.requires_demolition)}
              onChange={(e) => handleChange('requires_demolition', e.target.checked)}
              className="w-4 h-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Demolition / Breaking Required</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.debris_disposal_included)}
              onChange={(e) => handleChange('debris_disposal_included', e.target.checked)}
              className="w-4 h-4 text-amber-600 rounded border-gray-300 focus:ring-amber-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Debris Disposal & Truck Hauling</span>
          </label>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
          Masonry Inspection Notes
        </label>
        <textarea
          rows={2}
          value={data.notes || ''}
          onChange={(e) => handleChange('notes', e.target.value)}
          placeholder="e.g. Existing brick mortar is eroded; require polymer modified mortar bonding agent."
          className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 p-3 focus:ring-2 focus:ring-amber-500 focus:outline-none"
        />
      </div>
    </div>
  );
}
