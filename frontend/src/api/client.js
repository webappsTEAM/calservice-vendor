/**
 * workforce-app/frontend/src/api/client.js
 * Universal fetch client handling Bearer tokens, CSRF tokens, silent refresh deduplication, and JSON errors.
 */

import {
  getAccessToken,
  getRefreshToken,
  setAuthTokens,
  clearAuthTokens,
  isTokenExpired,
} from '../utils/authTokens.js';
import { classifyApiError } from '../utils/apiErrors.js';

let inFlightRefreshPromise = null;

function getCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) return null;
  const cookies = document.cookie.split(';');
  for (let i = 0; i < cookies.length; i++) {
    const cookie = cookies[i].trim();
    if (cookie.substring(0, name.length + 1) === name + '=') {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return null;
}

/**
 * Performs a silent token refresh using the existing /api/auth/refresh/ endpoint.
 * Deduplicates multiple concurrent refresh requests.
 */
export async function apiRefreshToken() {
  if (inFlightRefreshPromise) {
    return inFlightRefreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    clearAuthTokens();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('workforce:auth-unauthorized'));
    }
    return null;
  }

  inFlightRefreshPromise = (async () => {
    try {
      const res = await fetch('/api/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (res.ok) {
        const data = await res.json();
        const newToken = data.access_token || data.token;
        const newRefreshToken = data.refresh_token || data.refresh || refreshToken;
        if (newToken) {
          setAuthTokens(newToken, newRefreshToken);
          return newToken;
        }
      }

      if (res.status === 401 || res.status === 400) {
        // Refresh rejected by server (invalid/expired refresh token)
        clearAuthTokens();
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('workforce:auth-unauthorized'));
        }
      }
      // For 503 (DB connection pool exhaustion), 5xx, or network errors, NEVER clear credentials
      return null;
    } catch (_) {
      return null;
    } finally {
      inFlightRefreshPromise = null;
    }
  })();

  return inFlightRefreshPromise;
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});

  if (!options.isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const csrfToken = getCookie('csrftoken');
  if (csrfToken && !headers.has('X-CSRFToken')) {
    headers.set('X-CSRFToken', csrfToken);
  }

  // Attach tab-scoped or stored Bearer token (never attach to unauthenticated login/signup endpoints)
  const isAuthEndpoint = path.includes('/auth/login') || path.includes('/auth/signup') || path.includes('/auth/refresh');
  let token = getAccessToken();
  const refreshToken = getRefreshToken();

  // Only refresh when: access token is expired, or within safety window. Never on every request.
  if (token && refreshToken && !isAuthEndpoint && isTokenExpired(token)) {
    const refreshed = await apiRefreshToken();
    if (refreshed) {
      token = refreshed;
    }
  }

  if (token && !headers.has('Authorization') && !isAuthEndpoint) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const config = {
    method: options.method || 'GET',
    headers,
    credentials: 'include',
    ...options,
  };

  if (options.json) {
    config.body = JSON.stringify(options.json);
  }

  const url = path.startsWith('http') ? path : `/api${path.startsWith('/') ? path : '/' + path}`;

  let response;
  try {
    response = await fetch(url, config);
  } catch (netErr) {
    const error = new Error('Network error. Please check your connection.');
    error.status = 0;
    error.code = 'NETWORK_ERROR';
    error.originalError = netErr;
    throw error;
  }

  // Auto-refresh token on 401 for authenticated endpoints (excluding login/refresh)
  if (response.status === 401 && !path.includes('/auth/login') && !path.includes('/auth/refresh')) {
    if (!options._isRetry) {
      const currentStoredToken = getAccessToken();
      let tokenToUse = null;

      // 1. Compare token used by failed request with current storage
      if (currentStoredToken && currentStoredToken !== token) {
        // Storage already contains a newer token from a concurrent refresh
        tokenToUse = currentStoredToken;
      } else {
        // Await the single authoritative in-flight refresh promise
        tokenToUse = await apiRefreshToken();
      }

      if (tokenToUse) {
        headers.set('Authorization', `Bearer ${tokenToUse}`);
        const retryConfig = { ...config, headers, _isRetry: true };
        try {
          response = await fetch(url, retryConfig);
        } catch (retryNetErr) {
          const error = new Error('Network error during retry.');
          error.status = 0;
          error.code = 'NETWORK_ERROR';
          error.originalError = retryNetErr;
          throw error;
        }
      }
    }
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type');
  const isJson = contentType && contentType.includes('application/json');
  const data = isJson ? await response.json() : await response.text();

  if (!response.ok) {
    let errorMsg = (data && data.error) || (data && data.detail);
    if ((!errorMsg || errorMsg === 'Validation failed.') && data?.details && typeof data.details === 'object') {
      const entries = Object.entries(data.details);
      if (entries.length > 0) {
        const [field, fieldErrs] = entries[0];
        const cleanField = field.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        const firstDetail = Array.isArray(fieldErrs) ? fieldErrs[0] : fieldErrs;
        errorMsg = `${cleanField}: ${firstDetail}`;
      }
    }
    if (!errorMsg) {
      errorMsg = data && typeof data === 'object' ? JSON.stringify(data) : 'Request failed';
    }


    const error = new Error(errorMsg);
    error.status = response.status;
    error.code = (data && data.code) || classifyApiError(response.status, data);
    error.data = data;
    throw error;
  }

  return data;
}
