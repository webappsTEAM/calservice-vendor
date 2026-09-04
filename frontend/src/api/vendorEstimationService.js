/**
 * workforce-app/frontend/src/api/vendorEstimationService.js
 * Scalable Frontend API client for Service Estimations, Inspections & Quotation Builder.
 * Supports multi-service inspection categories (HVAC/AC, Plumbing, Electrical, Appliances, Painting, etc.).
 */
import { apiRequest } from './client.js';

/**
 * Fetch list of estimation leads with status, category, search, and date filtering.
 * @param {Object} params - { status, category, date, search, page }
 */
export async function apiGetVendorEstimations(params = {}) {
  const query = new URLSearchParams();
  if (params.status && params.status !== 'all') query.set('status', params.status);
  if (params.category && params.category !== 'all') query.set('category', params.category);
  if (params.date) query.set('date', params.date);
  if (params.search) query.set('search', params.search);
  if (params.page) query.set('page', params.page);

  const qs = query.toString() ? `?${query.toString()}` : '';
  return apiRequest(`/vendor/estimations/${qs}`, { method: 'GET' });
}

export const apiGetEstimations = apiGetVendorEstimations;

/**
 * Fetch single estimation lead details, including equipment specs, customer info,
 * findings, uploaded photos, and existing quotations.
 * @param {number|string} id - ServiceRequest ID or Estimation ID
 */
export async function apiGetVendorEstimationDetail(id) {
  return apiRequest(`/vendor/estimations/${id}/`, { method: 'GET' });
}

export const apiGetEstimationDetail = apiGetVendorEstimationDetail;

/**
 * Vendor confirms / accepts the estimation job lead.
 * @param {number|string} id
 * @param {Object} [payload] - { vendor_id, vendor_name }
 */
export async function apiConfirmVendorEstimation(id, payload = {}) {
  return apiRequest(`/vendor/estimations/${id}/confirm/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export const apiConfirmEstimation = apiConfirmVendorEstimation;

/**
 * Assign technician to estimation job.
 * @param {number|string} id
 * @param {Object} data - { technician_id, technician_name, technician_phone }
 */
export async function apiAssignTechnician(id, data) {
  return apiRequest(`/vendor/estimations/${id}/assign-technician/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Mark technician trip started (on the way).
 * @param {number|string} id
 */
export async function apiStartJourney(id) {
  return apiRequest(`/vendor/estimations/${id}/start-journey/`, {
    method: 'POST',
  });
}

/**
 * Mark technician arrived on-site.
 * @param {number|string} id
 */
export async function apiMarkArrived(id) {
  return apiRequest(`/vendor/estimations/${id}/arrived/`, {
    method: 'POST',
  });
}

/**
 * Verify 6-digit start OTP provided by the customer upon on-site arrival.
 * @param {number|string} id
 * @param {string} otp
 */
export async function apiVerifyOtp(id, otp) {
  return apiRequest(`/vendor/estimations/${id}/verify-otp/`, {
    method: 'POST',
    body: JSON.stringify({ otp: String(otp).trim() }),
  });
}

/**
 * Save structured defect findings for the on-site inspection.
 * @param {number|string} id
 * @param {Array} findings - [{ finding_type, title, severity, description, recommended_action, quantity, unit }]
 */
export async function apiSaveInspectionFindings(id, findings) {
  return apiRequest(`/vendor/estimations/${id}/inspection/findings/`, {
    method: 'POST',
    body: JSON.stringify({ findings }),
  });
}

/**
 * Upload an inspection defect photo.
 * @param {number|string} id
 * @param {FormData|Object} data - FormData with 'photo', 'caption', and optional 'finding_id'
 */
export async function apiUploadInspectionPhoto(id, data) {
  if (data instanceof FormData) {
    return apiRequest(`/vendor/estimations/${id}/inspection/photos/`, {
      method: 'POST',
      body: data,
      isFormData: true,
    });
  }
  return apiRequest(`/vendor/estimations/${id}/inspection/photos/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Mark inspection complete with diagnosis summary and internal notes.
 * @param {number|string} id
 * @param {Object} data - { diagnosis_summary, notes }
 */
export async function apiCompleteInspection(id, data) {
  return apiRequest(`/vendor/estimations/${id}/inspection/complete/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Save / Preview draft quotation with line items and taxes.
 * @param {number|string} id
 * @param {Object} quoteData - { valid_until, tax_rate_percent, discount_amount, notes, items: [...] }
 */
export async function apiSaveQuotation(id, quoteData) {
  return apiRequest(`/vendor/estimations/${id}/quotation/`, {
    method: 'POST',
    body: JSON.stringify(quoteData),
  });
}

/**
 * Send quotation to the customer.
 * @param {number|string} id
 * @param {number|string} quoteId
 */
export async function apiSendQuotation(id, quoteId) {
  return apiRequest(`/vendor/estimations/${id}/quotation/${quoteId}/send/`, {
    method: 'POST',
  });
}

/**
 * Revise a quotation (creates a new version V2, V3...).
 * @param {number|string} id
 * @param {number|string} quoteId
 */
export async function apiReviseQuotation(id, quoteId) {
  return apiRequest(`/vendor/estimations/${id}/quotation/${quoteId}/revise/`, {
    method: 'POST',
  });
}

/**
 * Record collection of the inspection fee.
 * @param {number|string} id
 * @param {Object} data - { payment_method: "CASH"|"UPI", payment_reference: "..." }
 */
export async function apiCollectFee(id, data) {
  return apiRequest(`/vendor/estimations/${id}/fee/collect/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Record waiver of the inspection fee.
 * @param {number|string} id
 * @param {Object} data - { reason: "..." }
 */
export async function apiWaiveFee(id, data) {
  return apiRequest(`/vendor/estimations/${id}/fee/waive/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Customer decision simulator / receiver (APPROVE | REJECT).
 * @param {number|string} id
 * @param {Object} data - { decision: "APPROVE"|"REJECT", rejection_reason, rejection_note }
 */
export async function apiCustomerDecide(id, data) {
  return apiRequest(`/vendor/estimations/${id}/customer-decide/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Fetch available technicians / staff for the vendor.
 */
export async function apiGetVendorTechnicians() {
  return apiRequest('/vendor/technicians/', { method: 'GET' });
}

/**
 * Fetch authoritative DB invoice for an estimation (either converted job or cancelled with fee collected).
 * @param {number|string} id - ServiceRequest ID or Estimation ID
 */
export async function apiGetEstimationInvoice(id) {
  return apiRequest(`/vendor/estimations/${id}/invoice/`, { method: 'GET' });
}
