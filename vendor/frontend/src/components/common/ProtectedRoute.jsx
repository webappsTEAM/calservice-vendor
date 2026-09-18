import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthProvider.jsx';
import { AdminRoute } from './AdminRoute.jsx';
import { EmployeeRoute } from './EmployeeRoute.jsx';
import { PlatformAdminRoute } from './PlatformAdminRoute.jsx';

export { AdminRoute, EmployeeRoute, PlatformAdminRoute };

export function SellerHubRoute({ children }) {
  const { isReady, isAuthenticated, isPlatformAdmin, isAdmin, isSeller, isGrocerySupplier } = useAuth();
  const location = useLocation();

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-700 font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-600">Verifying merchant authorization...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/workforce/login" state={{ from: location }} replace />;
  }

  const hasAccess = isPlatformAdmin || isAdmin || isSeller || isGrocerySupplier;
  if (!hasAccess) {
    return <Navigate to="/workforce/employee/dashboard" replace />;
  }

  return children;
}

export function AuthenticatedRoute({ children }) {
  const { isReady, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-700 font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-semibold text-slate-600">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/workforce/login" state={{ from: location }} replace />;
  }

  return children;
}

export function ProtectedRoute({ children, adminOnly = false }) {
  if (adminOnly) {
    return <AdminRoute>{children}</AdminRoute>;
  }
  return <EmployeeRoute>{children}</EmployeeRoute>;
}

export default ProtectedRoute;
