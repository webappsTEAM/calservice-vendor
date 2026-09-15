import React from 'react';
import { Home, Layers, Shield, Sparkles, AlertCircle } from 'lucide-react';

export default function PaintingInspectionForm({ data, onChange }) {
  const handleChange = (field, value) => {
    onChange({
      ...data,
      [field]: value,
    });
  };

  return (
    <div className="space-y-5">
      <div className="bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/50 rounded-xl p-4 flex items-start gap-3">
        <Home className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-200">Painting Site Inspection & Scope</h4>
          <p className="text-xs text-blue-700 dark:text-blue-300 mt-0.5">
            Record property parameters, surface conditions, and material requirements observed during inspection.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Property Type
          </label>
          <select
            value={data.property_type || '2BHK'}
            onChange={(e) => handleChange('property_type', e.target.value)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="1RK">1 RK / Studio</option>
            <option value="1BHK">1 BHK Apartment</option>
            <option value="2BHK">2 BHK Apartment</option>
            <option value="3BHK">3 BHK Apartment</option>
            <option value="4BHK">4 BHK / Duplex</option>
            <option value="Villa">Independent Villa / House</option>
            <option value="Commercial">Commercial / Office</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Estimated Total Area (Sq.Ft.)
          </label>
          <input
            type="number"
            value={data.area_sqft || ''}
            onChange={(e) => handleChange('area_sqft', parseFloat(e.target.value) || 0)}
            placeholder="e.g. 1200"
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Surface Condition
          </label>
          <select
            value={data.surface_condition || 'Good'}
            onChange={(e) => handleChange('surface_condition', e.target.value)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="Good">Good — Fresh / Light Repaint</option>
            <option value="Moderate">Moderate — Minor Cracks / Peeling</option>
            <option value="Damp">Damp / Moisture Damage</option>
            <option value="Severe">Severe Flaking / Deep Cracks</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Paint Grade / Category
          </label>
          <select
            value={data.paint_type || 'Premium'}
            onChange={(e) => handleChange('paint_type', e.target.value)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value="Economy">Economy (Tractor / Basic Emulsion)</option>
            <option value="Standard">Standard (Premium Emulsion)</option>
            <option value="Premium">Premium (Royale / Luxury Sheen)</option>
            <option value="WeatherDefense">Weather-Defense Exterior Coat</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Brand / Grade Preference
          </label>
          <input
            type="text"
            value={data.brand_grade || 'Asian Paints / Berger'}
            onChange={(e) => handleChange('brand_grade', e.target.value)}
            placeholder="e.g. Asian Paints Royale Luxury"
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
            Number of Coats
          </label>
          <select
            value={data.number_of_coats || 2}
            onChange={(e) => handleChange('number_of_coats', parseInt(e.target.value) || 2)}
            className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          >
            <option value={1}>1 Coat (Touchup / Refresh)</option>
            <option value={2}>2 Coats (Standard Application)</option>
            <option value={3}>3 Coats (Deep Color Transition / Fresh Plaster)</option>
          </select>
        </div>
      </div>

      <div className="pt-2">
        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">
          Surface Preparation & Additional Treatments
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.requires_putty)}
              onChange={(e) => handleChange('requires_putty', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Full Putty (2 Coats)</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.requires_priming)}
              onChange={(e) => handleChange('requires_priming', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Primer Base Coat</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.crack_treatment)}
              onChange={(e) => handleChange('crack_treatment', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Crack & Seam Filling</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.waterproofing_needed)}
              onChange={(e) => handleChange('waterproofing_needed', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">Damp Proof Waterproofing</span>
          </label>

          <label className="flex items-center gap-2.5 p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800">
            <input
              type="checkbox"
              checked={Boolean(data.scaffolding_required)}
              onChange={(e) => handleChange('scaffolding_required', e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <span className="text-xs font-medium text-gray-800 dark:text-gray-200">External Scaffolding</span>
          </label>
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
          Inspection Notes & Customer Requests
        </label>
        <textarea
          rows={2}
          value={data.notes || ''}
          onChange={(e) => handleChange('notes', e.target.value)}
          placeholder="e.g. Customer wants accent wall in Master Bedroom; balcony wall has water seepage from upper floor."
          className="w-full text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 p-3 focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
      </div>
    </div>
  );
}
