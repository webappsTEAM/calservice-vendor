/**
 * workforce-app/frontend/src/api/stockService.js
 *
 * VENDOR_STOCK_MANAGEMENT_IMPLEMENTATION_PLAN.md Phase 3. Thin wrappers over
 * the vendor-scoped stock endpoints in vendor/backend/inventory/views.py --
 * same pattern as vendorEstimationService.js / walletService.js in this
 * folder. Every one of these calls is scoped server-side to the logged-in
 * vendor's own company (request.company, resolved by
 * companies.middleware.CompanyMiddleware) -- there is no company_id param
 * to pass here on purpose.
 */
import { apiRequest } from './client.js';

export async function fetchVendorStock() {
  return apiRequest('/vendor/stock/');
}

export async function restockProduct(productId, { quantity, unit }) {
  return apiRequest(`/vendor/stock/${productId}/restock/`, {
    method: 'POST',
    json: { quantity, unit },
  });
}

export async function markProductOutOfStock(productId) {
  return apiRequest(`/vendor/stock/${productId}/mark-out-of-stock/`, {
    method: 'POST',
    json: {},
  });
}

export async function adjustProductStock(productId, { quantity, unit, reason }) {
  return apiRequest(`/vendor/stock/${productId}/adjust/`, {
    method: 'POST',
    json: { quantity, unit, reason },
  });
}

export async function updateProductDetails(productId, payload) {
  // payload: { price?, offer_price?, reorder_level_quantity?, reorder_level_unit?, restock_level_quantity?, restock_level_unit? }
  return apiRequest(`/vendor/stock/${productId}/update-details/`, {
    method: 'PATCH',
    json: payload,
  });
}

export async function fetchProductStockHistory(productId, { startDate, endDate } = {}) {
  const params = new URLSearchParams();
  if (startDate) params.set('start_date', startDate);
  if (endDate) params.set('end_date', endDate);
  const qs = params.toString();
  return apiRequest(`/vendor/stock/${productId}/history/${qs ? `?${qs}` : ''}`);
}

/** Best-effort human-readable message out of an apiRequest() error. */
export function extractStockErrorMessage(err, fallback = 'Something went wrong. Please try again.') {
  return err?.data?.message || err?.message || fallback;
}
