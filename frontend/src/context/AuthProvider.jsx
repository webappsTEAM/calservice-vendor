import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from './AuthContext.jsx';
import {
  apiFetchMe,
  apiWorkforceLogin,
  apiWorkforceSignup,
  apiServiceProviderSignup,
  apiWorkforceLogout,
  apiTogglePresence,
} from '../api/workforceService.js';

import {
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  setAuthTokens,
  clearAuthTokens,
} from '../utils/authTokens.js';
import { apiRefreshToken } from '../api/client.js';

export function AuthProvider({ children }) {
  const [isReady, setIsReady] = useState(false);
  const [user, setUser] = useState(null);
  const [employee, setEmployee] = useState(null);
  const inFlightRefreshRef = React.useRef(null);

  const refreshProfile = useCallback(async (force = false) => {
    if (inFlightRefreshRef.current && !force) {
      return inFlightRefreshRef.current;
    }

    inFlightRefreshRef.current = (async () => {
      try {
        let token = getAccessToken();
        const refreshToken = getRefreshToken();

        if (!token && !refreshToken) {
          setUser(null);
          setEmployee(null);
          return null;
        }

        // Avoid calling /auth/me/ with an already expired access token when a refresh token is available
        if (refreshToken && (!token || isTokenExpired(token))) {
          const refreshedToken = await apiRefreshToken();
          if (refreshedToken) {
            token = refreshedToken;
          }
        }

        if (!token) {
          setUser(null);
          setEmployee(null);
          return null;
        }

        // Single API call: /auth/me/ now returns presence, availability, and
        // last_known_location inline — no separate sequential onboarding profile call needed.
        const me = await apiFetchMe();

        if (me && me.username) {
          const isSuper = Boolean(me.is_superadmin || me.is_superuser || ['superadmin', 'super_admin'].includes((me.role || '').toLowerCase()));
          const isProviderAdmin = Boolean(me.is_provider_admin || (['service_provider_admin', 'admin', 'manager'].includes((me.role || '').toLowerCase()) && !isSuper));
          const isAdmin = isSuper || isProviderAdmin;
          const isEmployee = !isAdmin;

          const u = {
            id: me.id,
            username: me.username,
            email: me.email || '',
            firstName: me.first_name || '',
            lastName: me.last_name || '',
            role: me.role || (isSuper ? 'superadmin' : isProviderAdmin ? 'service_provider_admin' : 'employee'),
            companyId: me.company || me.provider_id || null,
            companyName: me.company_name || me.provider_name || '',
            providerId: me.provider_id || me.company || null,
            providerName: me.provider_name || me.company_name || '',
            isAdmin: isAdmin,
            isSuperadmin: isSuper,
            isServiceProviderAdmin: isProviderAdmin,
            isEmployee: isEmployee,
            employee_id: me.employee_id || null,
            employeeId: me.employee_id || null,
            registrationStatus: me.registration_status || (isAdmin ? 'approved' : 'not_started'),
            isOnline: Boolean(me.is_online),
            is_online: Boolean(me.is_online),
            availability: me.live_availability || me.availability || 'offline',
            live_availability: me.live_availability || me.availability || 'offline',
            last_known_location: me.last_known_location || null,
          };

          setUser(u);
          // Keep employee state for pages that still read it directly
          setEmployee(me.employee_id ? { id: me.employee_id, is_online: me.is_online, live_availability: me.live_availability } : null);
          return u;
        } else {
          if (!getRefreshToken()) {
            clearAuthTokens();
          }
          setUser(null);
          setEmployee(null);
          return null;
        }
      } catch (e) {
        // Only wipe auth tokens if server explicitly rejected with 401 AND no refresh token exists
        if (e && e.status === 401 && !getRefreshToken()) {
          clearAuthTokens();
          setUser(null);
          setEmployee(null);
        }
        return null;
      } finally {
        inFlightRefreshRef.current = null;
      }
    })();

    return inFlightRefreshRef.current;
  }, []);

  const login = useCallback(async (identifier, password) => {
    const res = await apiWorkforceLogin(identifier, password);
    if (!res) {
      throw new Error('Authentication failed. Please try again.');
    }

    const token = res.access_token || res.token;
    const refresh = res.refresh_token;
    if (token) {
      setAuthTokens(token, refresh);
    }

    // Await full authoritative profile refresh to eliminate provisional race condition
    const fullyResolvedUser = await refreshProfile(true);
    if (fullyResolvedUser) {
      return fullyResolvedUser;
    }

    if (res.user) {
      const isSuper = Boolean(res.user.is_superadmin || res.user.is_superuser || ['superadmin', 'super_admin'].includes((res.user.role || '').toLowerCase()));
      const isProviderAdmin = Boolean(res.user.is_provider_admin || (['service_provider_admin', 'admin', 'manager'].includes((res.user.role || '').toLowerCase()) && !isSuper));
      const isAdmin = isSuper || isProviderAdmin;
      const fallbackUser = {
        id: res.user.id,
        username: res.user.username,
        email: res.user.email || '',
        firstName: res.user.first_name || '',
        lastName: res.user.last_name || '',
        role: res.user.role || (isSuper ? 'superadmin' : isProviderAdmin ? 'service_provider_admin' : 'employee'),
        companyId: res.user.company || res.user.provider_id || null,
        companyName: res.user.company_name || res.user.provider_name || '',
        providerId: res.user.provider_id || res.user.company || null,
        providerName: res.user.provider_name || res.user.company_name || '',
        isAdmin: isAdmin,
        isSuperadmin: isSuper,
        isServiceProviderAdmin: isProviderAdmin,
        isEmployee: !isAdmin,
        registrationStatus: res.user.registration_status || (isAdmin ? 'approved' : 'not_started'),
        isOnline: false,
        availability: 'offline',
      };
      setUser(fallbackUser);
      return fallbackUser;
    }

    return null;
  }, [refreshProfile]);

  const signup = useCallback(async (payload) => {
    const res = await apiWorkforceSignup(payload);
    if (res) {
      const token = res.access_token || res.token;
      const refresh = res.refresh_token;
      setAuthTokens(token, refresh);
    }
    await refreshProfile(true);
    return res;
  }, [refreshProfile]);

  const signupServiceProvider = useCallback(async (payload) => {
    const res = await apiServiceProviderSignup(payload);
    if (res) {
      const token = res.access_token || res.token;
      const refresh = res.refresh_token;
      setAuthTokens(token, refresh);
    }
    await refreshProfile(true);
    return res;
  }, [refreshProfile]);


  const logout = useCallback(async (options = {}) => {
    // High-priority check: An employee cannot sign out while ONLINE
    if (!options?.skipOnlineCheck && user?.isEmployee && (user?.isOnline || employee?.is_online)) {
      const err = new Error('You are currently ONLINE. Please switch your status to OFFLINE before signing out.');
      err.code = 'CANNOT_LOGOUT_WHILE_ONLINE';
      err.status = 400;
      throw err;
    }

    // 1. Send authenticated logout request to backend
    try {
      await apiWorkforceLogout();
    } catch (err) {
      if (err?.code === 'CANNOT_LOGOUT_WHILE_ONLINE' || err?.data?.code === 'CANNOT_LOGOUT_WHILE_ONLINE' || err?.status === 400) {
        const errorMsg = err?.data?.error || err?.message || 'You are currently ONLINE. Please switch your status to OFFLINE before signing out.';
        const blockErr = new Error(errorMsg);
        blockErr.code = 'CANNOT_LOGOUT_WHILE_ONLINE';
        blockErr.status = 400;
        throw blockErr;
      }
    }

    // 2. Set flash logout notification in sessionStorage for display on the login page
    try {
      if (typeof sessionStorage !== 'undefined') {
        sessionStorage.setItem('wf_logout_notification', JSON.stringify({
          message: 'Signed out successfully. Technician presence is OFFLINE.',
          timestamp: Date.now(),
        }));
      }
    } catch (_) {}

    // 3. Clear auth tokens and state
    clearAuthTokens();
    if (typeof BroadcastChannel !== 'undefined') {
      try {
        const channel = new BroadcastChannel('wf_tab_channel');
        channel.postMessage({ type: 'LOGOUT_SYNC' });
        channel.close();
      } catch (_) {}
    }
    setUser(null);
    setEmployee(null);
  }, [user, employee]);

  const togglePresence = useCallback(async (desiredOnlineState = null) => {
    try {
      const res = await apiTogglePresence(desiredOnlineState);
      setUser(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          isOnline: Boolean(res.is_online),
          is_online: Boolean(res.is_online),
          availability: res.availability,
          live_availability: res.availability,
        };
      });
      setEmployee(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          isOnline: Boolean(res.is_online),
          is_online: Boolean(res.is_online),
          availability: res.availability,
          live_availability: res.availability,
        };
      });
      return res;
    } catch (e) {
      throw e;
    }
  }, []);

  // Cross-tab Session Sync using BroadcastChannel
  useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;
    const channel = new BroadcastChannel('wf_tab_channel');

    channel.onmessage = (event) => {
      const data = event.data;
      if (!data) return;

      if (data.type === 'LOGOUT_SYNC') {
        clearAuthTokens();
        setUser(null);
        setEmployee(null);
      }
    };

    return () => {
      channel.close();
    };
  }, []);

  // Handle unauthenticated event triggered from client.js on 401
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setEmployee(null);
    };
    window.addEventListener('workforce:auth-unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('workforce:auth-unauthorized', handleUnauthorized);
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setIsReady(true), 4000);
    refreshProfile()
      .catch(() => {})
      .finally(() => {
        clearTimeout(timer);
        setIsReady(true);
      });
  }, [refreshProfile]);

  const value = useMemo(() => ({
    isReady,
    user,
    employee,
    login,
    signup,
    signupServiceProvider,
    logout,
    refreshProfile,
    togglePresence,
    isAuthenticated: Boolean(user),
    isAdmin: user?.isAdmin || false,
    isSuperadmin: user?.isSuperadmin || false,
    isServiceProviderAdmin: user?.isServiceProviderAdmin || false,
    isEmployee: user?.isEmployee || false,
    providerId: user?.providerId || null,
    providerName: user?.providerName || '',
    isIndependent: Boolean(user?.isEmployee && !user?.providerId),
    registrationStatus: user?.registrationStatus || 'not_started',
  }), [isReady, user, employee, login, signup, signupServiceProvider, logout, refreshProfile, togglePresence]);


  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
