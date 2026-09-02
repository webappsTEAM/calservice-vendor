import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';

export function PlatformAdminRoute({ children }) {
  const { isReady, isAuthenticated, isPlatformAdmin, isAdmin } = useAuth();
  const location = useLocation();

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-700 font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-600">Verifying SEVO Platform Admin authorization...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/workforce/login" state={{ from: location }} replace />;
  }

  if (!isPlatformAdmin) {
    // Non-platform admin gets redirected to their vendor admin or employee dashboard
    if (isAdmin) {
      return <Navigate to="/workforce/admin" replace />;
    }
    return <Navigate to="/workforce/employee/dashboard" replace />;
  }

  return children;
}

export default PlatformAdminRoute;
