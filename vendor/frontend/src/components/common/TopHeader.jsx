import React, { useState, useEffect, useRef, useContext } from 'react';

import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { EmployeeRuntimeContext } from '../../context/EmployeeRuntimeContext.jsx';
import {
  Wrench,
  Search,
  HelpCircle,
  Bell,
  User,
  Power,
  LogOut,
  Menu,
  ChevronDown,
  ExternalLink,
  Shield,
  Settings,
  Crosshair,
  Loader2,
  Check,
  AlertTriangle,
  Trash2,
  CheckSquare,
  Square,
  X,
  CheckCheck,
  Calendar,
  Clock,
} from 'lucide-react';

import { Modal } from '../enterprise/Modal.jsx';
import { reverseGeocode } from '../../hooks/useReverseGeocode.js';
import {
  apiGetNotifications,
  apiMarkNotificationRead,
  apiClearNotifications,
  apiUpdateLocationFull,
} from '../../api/workforceService.js';
import { getGPSPosition } from '../../hooks/useGPSPosition.js';

export function TopHeader({ onToggleSidebar = () => {} }) {
  const { user, logout, togglePresence, isAdmin, isEmployee, registrationStatus } = useAuth();
  const employeeRuntime = useContext(EmployeeRuntimeContext);
  const navigate = useNavigate();
  const [isToggling, setIsToggling] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showNotifMenu, setShowNotifMenu] = useState(false);
  const [localNotifications, setLocalNotifications] = useState([]);
  const [localUnreadCount, setLocalUnreadCount] = useState(0);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedNotifIds, setSelectedNotifIds] = useState(new Set());
  const [isClearing, setIsClearing] = useState(false);
  const [globalSearch, setGlobalSearch] = useState('');
  const notifRef = useRef(null);
  const userMenuRef = useRef(null);

  // Section 15: Header Live Clock with single 1-second interval
  const [headerTime, setHeaderTime] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => {
      setHeaderTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const desktopDateStr = headerTime.toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
  const hours = headerTime.getHours();
  const minutes = String(headerTime.getMinutes()).padStart(2, '0');
  const seconds = String(headerTime.getSeconds()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const displayHours = String(hours % 12 || 12).padStart(2, '0');
  const desktopTimePart = `${displayHours}:${minutes}`;
  const desktopTimeStr = `${desktopTimePart}:${seconds} ${ampm}`;
  const mobileDayMonth = headerTime.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
  });
  const mobileTimePart = `${displayHours}:${minutes} ${ampm}`;
  const mobileTimeStr = `${mobileDayMonth} • ${mobileTimePart}`;

  const notifications = employeeRuntime ? employeeRuntime.notifications : localNotifications;
  const unreadCount = employeeRuntime ? employeeRuntime.unreadCount : localUnreadCount;

  // Close notifications dropdown when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotifMenu(false);
        setIsSelectMode(false);
        setSelectedNotifIds(new Set());
      }
    };
    if (showNotifMenu) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('touchstart', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('touchstart', handleOutsideClick);
    };
  }, [showNotifMenu]);

  // Close user menu dropdown when clicking outside
  useEffect(() => {
    const handleUserMenuOutsideClick = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setShowUserMenu(false);
      }
    };
    if (showUserMenu) {
      document.addEventListener('mousedown', handleUserMenuOutsideClick);
      document.addEventListener('touchstart', handleUserMenuOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleUserMenuOutsideClick);
      document.removeEventListener('touchstart', handleUserMenuOutsideClick);
    };
  }, [showUserMenu]);

  // Location Scan State
  const [localLocState, setLocalLocState] = useState('idle'); // 'idle' | 'locating' | 'success' | 'error'
  const [localLocCoords, setLocalLocCoords] = useState(() => {
    const loc = user?.last_known_location;
    if (loc?.latitude && loc?.longitude) {
      return { latitude: Number(loc.latitude), longitude: Number(loc.longitude), accuracy: loc.accuracy || null };
    }
    return null;
  });

  const localHandleScanCurrentLocation = async () => {
    if (localLocState === 'locating') return;
    setLocalLocState('locating');
    try {
      const pos = await getGPSPosition(true);
      const { latitude, longitude, accuracy, speed, heading } = pos.coords;
      const captured_at = new Date(pos.timestamp || Date.now()).toISOString();
      await apiUpdateLocationFull(latitude, longitude, accuracy, speed, heading, captured_at);
      setLocalLocCoords({
        latitude,
        longitude,
        accuracy,
        timestamp: pos.timestamp || Date.now(),
      });
      setLocalLocState('success');
      window.dispatchEvent(
        new CustomEvent('workforce:location-updated', {
          detail: {
            latitude,
            longitude,
            accuracy,
            speed,
            heading,
            captured_at,
            timestamp: pos.timestamp || Date.now(),
            source: 'header_scan',
          },
        })
      );
      setTimeout(() => setLocalLocState('idle'), 2500);
    } catch (_) {
      setLocalLocState('error');
      setTimeout(() => setLocalLocState('idle'), 3000);
    }
  };

  const locCoords = employeeRuntime?.liveLocation || localLocCoords;
  const locState = employeeRuntime?.locationState || localLocState;
  const handleScanCurrentLocation = employeeRuntime ? employeeRuntime.scanCurrentLocation : localHandleScanCurrentLocation;

  const [headerLocationName, setHeaderLocationName] = useState('');

  useEffect(() => {
    if (!locCoords?.latitude || !locCoords?.longitude) return;
    let isCancelled = false;
    reverseGeocode(locCoords.latitude, locCoords.longitude)
      .then((res) => {
        if (isCancelled) return;
        if (res) {
          const name = [res.locality, res.city].filter(Boolean).join(', ') || res.formatted_address || res.area;
          if (name) setHeaderLocationName(name);
        }
      })
      .catch(() => {});
    return () => {
      isCancelled = true;
    };
  }, [locCoords?.latitude, locCoords?.longitude]);

  // Background notification polling for Admin users ONLY (Employee notifications are centralized in EmployeeRuntimeProvider)
  useEffect(() => {
    if (employeeRuntime) return;
    const token = typeof window !== 'undefined'
      ? (sessionStorage.getItem('wf_token') || localStorage.getItem('wf_token'))
      : null;
    if (!user || !token) return;
    let isCancelled = false;
    let pollInterval = null;

    const fetchNotifs = async () => {
      try {
        const res = await apiGetNotifications();
        if (!isCancelled && res) {
          setLocalNotifications(res.notifications || []);
          setLocalUnreadCount(res.unread_count || 0);
        }
      } catch (err) {
        if (err?.status === 401 || err?.response?.status === 401) {
          if (pollInterval) clearInterval(pollInterval);
        }
      }
    };
    fetchNotifs();
    pollInterval = setInterval(fetchNotifs, 15000);
    return () => {
      isCancelled = true;
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [user, employeeRuntime]);

  const handleMarkAllRead = async () => {
    if (employeeRuntime) {
      await employeeRuntime.markNotificationAsRead();
      return;
    }
    try {
      await apiMarkNotificationRead();
      setLocalUnreadCount(0);
      setLocalNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch (_) {}
  };

  const handleToggleSelectMode = () => {
    setIsSelectMode((prev) => {
      if (prev) {
        setSelectedNotifIds(new Set());
      }
      return !prev;
    });
  };

  const handleToggleSelectAll = () => {
    if (selectedNotifIds.size === notifications.length && notifications.length > 0) {
      setSelectedNotifIds(new Set());
    } else {
      setSelectedNotifIds(new Set(notifications.map((n) => n.id)));
    }
  };

  const handleToggleSelectOne = (id, e) => {
    e?.stopPropagation?.();
    setSelectedNotifIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleClearAll = async (e) => {
    e?.stopPropagation?.();
    if (notifications.length === 0) return;
    try {
      setIsClearing(true);
      if (employeeRuntime) {
        await employeeRuntime.clearAllNotifications([]);
      } else {
        await apiClearNotifications(null, null, true);
        setLocalNotifications([]);
        setLocalUnreadCount(0);
      }
      setSelectedNotifIds(new Set());
      setIsSelectMode(false);
    } catch (err) {
      console.error('Failed to clear all notifications:', err);
    } finally {
      setIsClearing(false);
    }
  };

  const handleClearSelected = async (e) => {
    e?.stopPropagation?.();
    if (selectedNotifIds.size === 0) return;
    const ids = Array.from(selectedNotifIds);
    try {
      setIsClearing(true);
      if (employeeRuntime) {
        await employeeRuntime.clearAllNotifications(ids);
      } else {
        await apiClearNotifications(null, ids);
        const unreadCleared = localNotifications.filter(
          (n) => selectedNotifIds.has(n.id) && !n.is_read
        ).length;
        setLocalNotifications((prev) => prev.filter((n) => !selectedNotifIds.has(n.id)));
        setLocalUnreadCount((prev) => Math.max(0, prev - unreadCleared));
      }
      setSelectedNotifIds(new Set());
      if (notifications.length <= ids.length) {
        setIsSelectMode(false);
      }
    } catch (err) {
      console.error('Failed to clear selected notifications:', err);
    } finally {
      setIsClearing(false);
    }
  };

  const handleClearSingle = async (notifId, e) => {
    e?.stopPropagation?.();
    try {
      setIsClearing(true);
      if (employeeRuntime) {
        await employeeRuntime.clearAllNotifications([notifId]);
      } else {
        await apiClearNotifications(notifId);
        const notif = localNotifications.find((n) => n.id === notifId);
        const wasUnread = notif && !notif.is_read;
        setLocalNotifications((prev) => prev.filter((n) => n.id !== notifId));
        if (wasUnread) {
          setLocalUnreadCount((prev) => Math.max(0, prev - 1));
        }
      }
      setSelectedNotifIds((prev) => {
        const next = new Set(prev);
        next.delete(notifId);
        return next;
      });
    } catch (err) {
      console.error('Failed to clear notification:', err);
    } finally {
      setIsClearing(false);
    }
  };

  const handleMarkSelectedRead = async (e) => {
    e?.stopPropagation?.();
    if (selectedNotifIds.size === 0) return;
    const ids = Array.from(selectedNotifIds);
    try {
      if (employeeRuntime) {
        await apiMarkNotificationRead(null, ids);
        await employeeRuntime.syncNotifications();
      } else {
        await apiMarkNotificationRead(null, ids);
        const countUnreadInSelected = localNotifications.filter(
          (n) => selectedNotifIds.has(n.id) && !n.is_read
        ).length;
        setLocalNotifications((prev) =>
          prev.map((n) => (selectedNotifIds.has(n.id) ? { ...n, is_read: true } : n))
        );
        setLocalUnreadCount((prev) => Math.max(0, prev - countUnreadInSelected));
      }
    } catch (err) {
      console.error('Failed to mark selected as read:', err);
    }
  };

  const handleNotifClick = async (notif) => {
    try {
      if (!notif.is_read) {
        if (employeeRuntime) {
          await employeeRuntime.markNotificationAsRead(notif.id);
        } else {
          await apiMarkNotificationRead(notif.id);
          setLocalUnreadCount((prev) => Math.max(0, prev - 1));
          setLocalNotifications((prev) =>
            prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
          );
        }
      }
      setShowNotifMenu(false);
      if (notif.notification_type === 'JOB_OFFER' || notif.notification_type === 'JOB_OFFERED') {
        navigate('/workforce/employee/jobs?tab=offers');
      }
    } catch (_) {}
  };

  const handleLogout = async () => {

    await logout();
    navigate('/workforce/login');
  };

  const handlePresenceToggle = async () => {
    if (registrationStatus !== 'approved') return;
    if (user?.availability === 'busy') {
      alert('Cannot change availability or go offline while actively working on an assigned job.');
      return;
    }
    try {
      setIsToggling(true);
      if (employeeRuntime?.togglePresence) {
        await employeeRuntime.togglePresence();
      } else {
        await togglePresence();
      }
    } catch (err) {
      alert(err.message || 'Failed to toggle availability status');
    } finally {
      setIsToggling(false);
    }
  };

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (!globalSearch.trim()) return;
    if (isAdmin) {
      navigate(`/workforce/admin/applications?q=${encodeURIComponent(globalSearch.trim())}`);
    }
  };

  const isOnline = employeeRuntime ? employeeRuntime.isOnline : Boolean(user?.isOnline);
  // Also consult the live job queue: availability lives on the auth profile, so
  // it can lag a job that has just ended. Trusting that flag alone is what left
  // this button stuck on "ON JOB (BUSY)" after a job completed or was cancelled.
  const isBusy = Boolean(
    user?.availability === 'busy' && (employeeRuntime ? employeeRuntime.hasActiveJob : true)
  );

  return (
    <>
      <header className="bg-slate-900 text-slate-100 border-b border-slate-800 shrink-0 z-40 h-14 flex items-center px-3 sm:px-5 select-none">
        <div className="w-full flex items-center justify-between gap-3">
          {/* LEFT: Mobile Menu Toggle & Workforce Brand */}
          <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
            <button
              type="button"
              onClick={onToggleSidebar}
              className="lg:hidden p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Toggle Menu"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>

            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-slate-800 border border-slate-700/80 flex items-center justify-center text-white shadow-xs group-hover:border-slate-600 transition-colors shrink-0">
                <Wrench className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-slate-200" />
              </div>
              <div className="flex flex-col justify-center leading-none">
                <span className="font-bold text-xs sm:text-sm tracking-tight text-white font-sans">
                  SEVO
                </span>
                <span className="text-[9px] font-semibold uppercase tracking-widest text-slate-400 mt-0.5">
                  Partner
                </span>
              </div>
            </Link>
          </div>

          {/* CENTER: Flexible empty space */}
          <div className="flex-1 min-w-0" />

          {/* RIGHT: Presence Switch, Date/Time, Notifications & Account */}
          <div className="flex items-center gap-2 sm:gap-2.5 md:gap-3 shrink-0">
            {user ? (
              <>
                {/* Technician Online / Offline / Busy Switch */}
                {isEmployee && registrationStatus === 'approved' && (
                  <button
                    type="button"
                    role="switch"
                    aria-checked={isOnline}
                    aria-label={`Technician presence status: ${isBusy ? 'Busy on job' : isOnline ? 'Online' : 'Offline'}`}
                    onClick={handlePresenceToggle}
                    disabled={isToggling || isBusy}
                    className={`inline-flex items-center gap-1.5 h-7 px-2.5 rounded-full text-xs font-medium border transition-colors select-none focus:outline-none focus:ring-1 focus:ring-offset-1 focus:ring-offset-slate-900 ${
                      isBusy
                        ? 'bg-blue-950/40 border-blue-500/40 text-blue-300 cursor-not-allowed'
                        : isOnline
                          ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/40 hover:border-emerald-500/60'
                          : 'bg-slate-800/80 border border-slate-700 text-slate-400 hover:bg-slate-800 hover:text-slate-300 hover:border-slate-600'
                    } ${isToggling ? 'opacity-75 cursor-wait' : ''}`}
                    title={
                      isBusy
                        ? 'Locked Online: You are actively working on an assigned job (BUSY).'
                        : isOnline
                          ? 'You are ONLINE. Click to go OFFLINE'
                          : 'You are OFFLINE. Click to go ONLINE'
                    }
                  >
                    {isBusy ? (
                      <>
                        <span className="text-[10px] sm:text-[11px] font-bold tracking-wider uppercase text-blue-300">
                          BUSY
                        </span>
                        <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse shadow-[0_0_6px_rgba(96,165,250,0.6)] shrink-0" />
                      </>
                    ) : isOnline ? (
                      <>
                        <span className="text-[10px] sm:text-[11px] font-bold tracking-wider uppercase text-emerald-300">
                          ONLINE
                        </span>
                        {isToggling ? (
                          <Loader2 className="w-2.5 h-2.5 text-emerald-400 animate-spin shrink-0" />
                        ) : (
                          <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)] shrink-0" />
                        )}
                      </>
                    ) : (
                      <>
                        <span className="text-[10px] sm:text-[11px] font-bold tracking-wider uppercase text-slate-400">
                          OFFLINE
                        </span>
                        {isToggling ? (
                          <Loader2 className="w-2.5 h-2.5 text-slate-400 animate-spin shrink-0" />
                        ) : (
                          <span className="w-2 h-2 rounded-full border border-slate-400 bg-transparent shrink-0" />
                        )}
                      </>
                    )}
                  </button>
                )}

                {/* Subtle Divider between Presence and Date/Time */}
                {isEmployee && registrationStatus === 'approved' && (
                  <div className="hidden sm:block h-4 w-px bg-slate-800 shrink-0" />
                )}

                {/* Live Header Date & Time (Display-Only, Compact Group) */}
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/40 border border-slate-800/80 text-xs select-none">
                  <span className="font-medium text-slate-200">{desktopDateStr}</span>
                  <span className="text-slate-600 select-none">·</span>
                  <span className="font-mono text-[11px] text-slate-400">
                    {desktopTimePart}
                    <span className="text-slate-500 text-[10px]">:{seconds}</span>
                    <span className="text-slate-400 text-[10px] ml-1">{ampm}</span>
                  </span>
                </div>

                {/* Subtle Divider before Actions */}
                <div className="hidden sm:block h-4 w-px bg-slate-800 shrink-0" />

                {/* Notifications Bell & Dropdown */}
                <div className="relative" ref={notifRef}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowNotifMenu(!showNotifMenu);
                      setShowUserMenu(false);
                      if (showNotifMenu) {
                        setIsSelectMode(false);
                        setSelectedNotifIds(new Set());
                      }
                    }}
                    className="p-1.5 sm:p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-colors relative focus:outline-none focus:ring-1 focus:ring-slate-700"
                    title="Notifications"
                    aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
                    aria-expanded={showNotifMenu}
                  >
                    <Bell className="w-4 h-4" />
                    {unreadCount > 0 && (
                      <span className="absolute top-1 right-1 min-w-[14px] h-3.5 px-0.5 rounded-full bg-rose-500 text-white text-[9px] font-bold leading-none flex items-center justify-center pointer-events-none">
                        {unreadCount > 9 ? '9+' : unreadCount}
                      </span>
                    )}
                  </button>

                  {showNotifMenu && (
                    <div className="absolute right-0 mt-2 w-[390px] sm:w-[420px] max-w-[calc(100vw-20px)] bg-white text-zinc-900 rounded-md border border-zinc-200/90 shadow-modal z-50 text-xs overflow-hidden animate-in zoom-in-95 duration-150">
                      {/* Dropdown Header */}
                      <div className="px-4 py-3 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/90 gap-2">
                        <div className="flex items-center gap-2 font-bold text-zinc-900 shrink-0">
                          <Bell className="w-4 h-4 text-zinc-900" />
                          <span className="text-xs sm:text-sm font-bold text-zinc-900 tracking-tight">Notifications</span>
                          {unreadCount > 0 && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-zinc-900 text-white text-[10px] font-bold whitespace-nowrap">
                              {unreadCount} new
                            </span>
                          )}
                        </div>

                        {notifications.length > 0 && (
                          <div className="flex items-center gap-1.5 shrink-0">
                            {!isSelectMode ? (
                              <>
                                {unreadCount > 0 && (
                                  <button
                                    type="button"
                                    onClick={handleMarkAllRead}
                                    className="text-[11px] text-zinc-700 hover:text-zinc-950 font-semibold px-2 py-1 rounded-lg hover:bg-zinc-200/60 transition-colors whitespace-nowrap"
                                  >
                                    Mark all read
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={handleToggleSelectMode}
                                  className="text-[11px] text-zinc-700 hover:text-zinc-950 font-semibold px-2 py-1 rounded-lg border border-zinc-200 hover:bg-zinc-100 transition-colors whitespace-nowrap flex items-center gap-1"
                                >
                                  <CheckSquare className="w-3 h-3 text-zinc-600" />
                                  <span>Select</span>
                                </button>
                              </>
                            ) : (
                              <button
                                type="button"
                                onClick={handleToggleSelectMode}
                                className="text-[11px] text-zinc-800 hover:text-zinc-950 font-semibold px-2.5 py-1 rounded-lg bg-zinc-100 hover:bg-zinc-200 transition-colors whitespace-nowrap"
                              >
                                Cancel
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Selection Toolbar */}
                      {isSelectMode && notifications.length > 0 && (
                        <div className="px-4 py-2 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between gap-2">
                          <button
                            type="button"
                            onClick={handleToggleSelectAll}
                            className="flex items-center gap-1.5 text-xs font-semibold text-zinc-800 hover:text-zinc-950 transition-colors whitespace-nowrap"
                          >
                            {selectedNotifIds.size === notifications.length ? (
                              <CheckSquare className="w-4 h-4 text-zinc-950 shrink-0" />
                            ) : (
                              <Square className="w-4 h-4 text-zinc-400 shrink-0" />
                            )}
                            <span>
                              {selectedNotifIds.size === notifications.length
                                ? 'Deselect all'
                                : 'Select all'}{' '}
                              ({selectedNotifIds.size}/{notifications.length})
                            </span>
                          </button>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {selectedNotifIds.size > 0 ? (
                              <>
                                {notifications.some(
                                  (n) => selectedNotifIds.has(n.id) && !n.is_read
                                ) && (
                                  <button
                                    type="button"
                                    onClick={handleMarkSelectedRead}
                                    className="text-[11px] text-zinc-800 hover:text-zinc-950 font-semibold px-2 py-1 rounded-lg hover:bg-zinc-200/60 transition-colors whitespace-nowrap"
                                  >
                                    Mark read
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={handleClearSelected}
                                  disabled={isClearing}
                                  className="text-[11px] text-white bg-rose-600 hover:bg-rose-700 font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1 shadow-xs transition-colors whitespace-nowrap"
                                >
                                  {isClearing ? (
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-3.5 h-3.5" />
                                  )}
                                  <span>Clear ({selectedNotifIds.size})</span>
                                </button>
                              </>
                            ) : (
                              <span className="text-[11px] text-zinc-400 italic whitespace-nowrap">
                                Select items to clear
                              </span>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Notifications List */}
                      <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100">
                        {notifications.length === 0 ? (
                          <div className="py-10 text-center text-zinc-400 text-xs flex flex-col items-center justify-center gap-1.5">
                            <Bell className="w-7 h-7 text-zinc-300 stroke-1" />
                            <p className="font-semibold text-zinc-700 text-xs">No notifications yet</p>
                            <p className="text-[11px] text-zinc-400">You are all caught up!</p>
                          </div>
                        ) : (
                          notifications.map((n) => {
                            const isJobOffer =
                              n.notification_type === 'JOB_OFFER' ||
                              n.notification_type === 'JOB_OFFERED';
                            const isSelected = selectedNotifIds.has(n.id);

                            return (
                              <div
                                key={n.id}
                                onClick={(e) => {
                                  if (isSelectMode) {
                                    handleToggleSelectOne(n.id, e);
                                  } else {
                                    handleNotifClick(n);
                                  }
                                }}
                                className={`px-4 py-3 transition-colors cursor-pointer group relative flex items-start gap-3 ${
                                  isSelected
                                    ? 'bg-zinc-100 border-l-2 border-zinc-950'
                                    : !n.is_read
                                    ? isJobOffer
                                      ? 'bg-amber-50/70 border-l-2 border-amber-500 hover:bg-amber-50'
                                      : 'bg-zinc-50 border-l-2 border-zinc-900 hover:bg-zinc-100/70'
                                    : 'hover:bg-zinc-50'
                                }`}
                              >
                                {isSelectMode && (
                                  <div className="pt-0.5 shrink-0">
                                    {isSelected ? (
                                      <CheckSquare className="w-4 h-4 text-zinc-950" />
                                    ) : (
                                      <Square className="w-4 h-4 text-zinc-400 group-hover:text-zinc-600" />
                                    )}
                                  </div>
                                )}

                                <div className="flex-1 min-w-0">
                                  <div className="flex items-start justify-between gap-2">
                                    <p
                                      className={`font-bold text-xs truncate ${
                                        isJobOffer ? 'text-amber-950' : 'text-zinc-900'
                                      }`}
                                    >
                                      {n.title}
                                    </p>
                                    <div className="flex items-center gap-1 shrink-0">
                                      <span className="text-[10px] text-zinc-400 whitespace-nowrap font-mono">
                                        {new Date(n.created_at).toLocaleTimeString([], {
                                          hour: '2-digit',
                                          minute: '2-digit',
                                        })}
                                      </span>
                                      {!isSelectMode && (
                                        <button
                                          type="button"
                                          onClick={(e) => handleClearSingle(n.id, e)}
                                          title="Delete notification"
                                          className="opacity-0 group-hover:opacity-100 focus:opacity-100 p-0.5 text-zinc-400 hover:text-rose-600 rounded hover:bg-rose-50 transition-all"
                                        >
                                          <Trash2 className="w-3 h-3" />
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                  <p className="text-zinc-600 text-[11px] mt-0.5 line-clamp-2 leading-relaxed">
                                    {n.message}
                                  </p>
                                  {isJobOffer && !isSelectMode && (
                                    <div className="mt-1.5 flex items-center gap-1 text-[10px] font-bold text-amber-700">
                                      <span>👉 Tap to view offer in operations dashboard</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>

                      {/* Dropdown Footer */}
                      {notifications.length > 0 && !isSelectMode && (
                        <div className="px-4 py-2.5 bg-zinc-50/90 border-t border-zinc-100 flex items-center justify-between text-[11px] text-zinc-500">
                          <span>
                            {notifications.length} notification{notifications.length > 1 ? 's' : ''}
                          </span>
                          <button
                            type="button"
                            onClick={handleClearAll}
                            disabled={isClearing}
                            className="text-[11px] text-zinc-500 hover:text-rose-600 font-medium hover:underline flex items-center gap-1 transition-colors whitespace-nowrap"
                          >
                            <Trash2 className="w-3 h-3 text-zinc-400 hover:text-rose-600" />
                            <span>Clear all notifications</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>


                {/* Subtle Divider before User Account */}
                <div className="h-4 w-px bg-slate-800 shrink-0" />

                {/* User Dropdown */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    type="button"
                    onClick={() => {
                      setShowUserMenu(!showUserMenu);
                      setShowNotifMenu(false);
                    }}
                    className="flex items-center gap-2 p-1 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors focus:outline-none focus:ring-1 focus:ring-slate-700"
                    aria-expanded={showUserMenu}
                    aria-haspopup="true"
                    aria-label="User account menu"
                  >
                    <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-white shadow-xs shrink-0">
                      {user.firstName ? user.firstName[0].toUpperCase() : <User className="w-3.5 h-3.5 text-slate-300" />}
                    </div>
                    <span className="hidden md:inline text-xs font-medium text-slate-200 max-w-[110px] lg:max-w-[140px] truncate">
                      {user.firstName ? `${user.firstName} ${user.lastName}` : user.username}
                    </span>
                    <ChevronDown
                      className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-150 ${
                        showUserMenu ? 'rotate-180 text-white' : ''
                      }`}
                    />
                  </button>

                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-52 bg-white text-zinc-900 rounded-md border border-zinc-200 shadow-modal py-1 z-50 text-xs animate-in zoom-in-95 duration-150">
                      <div className="px-3.5 py-2.5 border-b border-zinc-100 bg-zinc-50/50">
                        <p className="font-bold text-zinc-900 truncate">
                          {user.firstName ? `${user.firstName} ${user.lastName}` : user.username}
                        </p>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">
                          Role: {user.isAdmin ? 'Admin' : (user.isEmployee ? 'Technician' : (user.role || 'Employee'))}
                        </p>
                      </div>

                      <div className="py-1 border-b border-zinc-100">
                        <Link
                          to={isAdmin ? "/workforce/admin/settings" : "/workforce/employee/profile"}
                          onClick={() => setShowUserMenu(false)}
                          className="w-full px-3.5 py-2 text-left hover:bg-zinc-100 text-zinc-700 flex items-center gap-2.5 transition-colors font-medium"
                        >
                          <User className="w-3.5 h-3.5 text-zinc-400" />
                          <span>My Profile</span>
                        </Link>
                        <Link
                          to={isAdmin ? "/workforce/admin/settings" : "/workforce/employee/settings"}
                          onClick={() => setShowUserMenu(false)}
                          className="w-full px-3.5 py-2 text-left hover:bg-zinc-100 text-zinc-700 flex items-center gap-2.5 transition-colors font-medium"
                        >
                          <Settings className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Settings</span>
                        </Link>
                      </div>

                      <button
                        type="button"
                        onClick={handleLogout}
                        className="w-full px-3.5 py-2 text-left hover:bg-rose-50 text-rose-600 flex items-center gap-2.5 transition-colors font-semibold"
                      >
                        <LogOut className="w-3.5 h-3.5" />
                        <span>Sign Out</span>
                      </button>
                    </div>
                  )}

                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  to="/workforce/login"
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/workforce/signup"
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white hover:bg-slate-100 text-slate-900 transition-colors shadow-xs"
                >
                  Sign Up
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Help Modal */}
      <Modal
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Workforce Operations Reference"
        icon={HelpCircle}
        maxWidth="max-w-md"
      >
        <div className="space-y-3 text-xs text-zinc-600">
          <p>
            Welcome to the <strong>{user?.companyName || 'SEVO Partner'} Enterprise Operations Hub</strong>.
          </p>
          <div className="bg-zinc-50 border border-zinc-200/80 rounded-lg p-3.5 space-y-2">
            <h4 className="font-bold text-zinc-900">Operational Guidelines:</h4>
            <ul className="list-disc list-inside space-y-1 text-zinc-600 leading-relaxed">
              <li>Admins verify onboarding dossiers, review trade certifications, and authorize services individually.</li>
              <li>Technicians must be marked ONLINE and CLOCKED IN to receive automatic job assignments.</li>
              <li>Job state transitions (Accept &rarr; Travel &rarr; Work &rarr; Proof &amp; Complete) must be executed in order.</li>
            </ul>
          </div>
          <p className="text-[11px] text-zinc-500">
            For technical support, contact your Workforce Operations administrator.
          </p>
        </div>
      </Modal>
    </>
  );
}

export default TopHeader;
