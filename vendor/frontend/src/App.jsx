import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthProvider.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { EmployeeRuntimeProvider } from './context/EmployeeRuntimeProvider.jsx';
import { AdminRoute, EmployeeRoute, PlatformAdminRoute, AuthenticatedRoute } from './components/common/ProtectedRoute.jsx';

const LoginPage = lazy(() => import('./pages/auth/LoginPage.jsx').then(m => ({ default: m.LoginPage || m.default })));
const SignupPage = lazy(() => import('./pages/auth/SignupPage.jsx').then(m => ({ default: m.SignupPage || m.default })));
const ProviderSignupPage = lazy(() => import('./pages/auth/ProviderSignupPage.jsx').then(m => ({ default: m.ProviderSignupPage || m.default })));
const TermsAndConditionsPage = lazy(() => import('./pages/public/TermsAndConditionsPage.jsx').then(m => ({ default: m.TermsAndConditionsPage || m.default })));
const PrivacyPolicyPage = lazy(() => import('./pages/public/PrivacyPolicyPage.jsx').then(m => ({ default: m.PrivacyPolicyPage || m.default })));
const SupportAndContactPage = lazy(() => import('./pages/public/SupportAndContactPage.jsx').then(m => ({ default: m.SupportAndContactPage || m.default })));
const CancellationRefundsPage = lazy(() => import('./pages/public/CancellationRefundsPage.jsx').then(m => ({ default: m.CancellationRefundsPage || m.default })));
const ShippingPolicyPage = lazy(() => import('./pages/public/ShippingPolicyPage.jsx').then(m => ({ default: m.ShippingPolicyPage || m.default })));
const OnboardingWizardPage = lazy(() => import('./pages/onboarding/OnboardingWizardPage.jsx').then(m => ({ default: m.OnboardingWizardPage || m.default })));
const PendingReviewPage = lazy(() => import('./pages/onboarding/PendingReviewPage.jsx').then(m => ({ default: m.PendingReviewPage || m.default })));
const CorrectionRequiredPage = lazy(() => import('./pages/onboarding/CorrectionRequiredPage.jsx').then(m => ({ default: m.CorrectionRequiredPage || m.default })));
const RejectedPage = lazy(() => import('./pages/onboarding/RejectedPage.jsx').then(m => ({ default: m.RejectedPage || m.default })));
const EmployeeDashboardPage = lazy(() => import('./pages/employee/EmployeeDashboardPage.jsx').then(m => ({ default: m.EmployeeDashboardPage || m.default })));
const EmployeeJobsPage = lazy(() => import('./pages/employee/EmployeeJobsPage.jsx').then(m => ({ default: m.EmployeeJobsPage || m.default })));
const EmployeeProfilePage = lazy(() => import('./pages/employee/EmployeeProfilePage.jsx').then(m => ({ default: m.EmployeeProfilePage || m.default })));
const EmployeeDocumentsPage = lazy(() => import('./pages/employee/EmployeeDocumentsPage.jsx').then(m => ({ default: m.EmployeeDocumentsPage || m.default })));
const EmployeeServicesPage = lazy(() => import('./pages/employee/EmployeeServicesPage.jsx').then(m => ({ default: m.EmployeeServicesPage || m.default })));
const EmployeeSettingsPage = lazy(() => import('./pages/employee/EmployeeSettingsPage.jsx').then(m => ({ default: m.EmployeeSettingsPage || m.default })));
const EmployeePerformancePage = lazy(() => import('./pages/employee/EmployeePerformancePage.jsx').then(m => ({ default: m.EmployeePerformancePage || m.default })));
const EmployeeEarningsPage = lazy(() => import('./pages/employee/EmployeeEarningsPage.jsx').then(m => ({ default: m.EmployeeEarningsPage || m.default })));
const EmployeeLocationPage = lazy(() => import('./pages/employee/EmployeeLocationPage.jsx').then(m => ({ default: m.EmployeeLocationPage || m.default })));
const EmployeeEstimatesPage = lazy(() => import('./pages/employee/estimates/EmployeeEstimatesPage.jsx'));
const VendorEstimationsPage = lazy(() => import('./pages/vendor/estimations/VendorEstimationsPage.jsx'));
const MyVendorNetworkPage = lazy(() => import('./pages/employee/MyVendorNetworkPage.jsx').then(m => ({ default: m.MyVendorNetworkPage || m.default })));
const TechnicianInvitationsPage = lazy(() => import('./pages/employee/TechnicianInvitationsPage.jsx').then(m => ({ default: m.TechnicianInvitationsPage || m.default })));
const AdminDashboardPage = lazy(() => import('./pages/admin/AdminDashboardPage.jsx').then(m => ({ default: m.AdminDashboardPage || m.default })));
const AdminApplicationsPage = lazy(() => import('./pages/admin/AdminApplicationsPage.jsx').then(m => ({ default: m.AdminApplicationsPage || m.default })));
const AdminApplicationDetailPage = lazy(() => import('./pages/admin/AdminApplicationDetailPage.jsx').then(m => ({ default: m.AdminApplicationDetailPage || m.default })));
const AdminEmployeesPage = lazy(() => import('./pages/admin/AdminEmployeesPage.jsx').then(m => ({ default: m.AdminEmployeesPage || m.default })));
const AdminJobsPage = lazy(() => import('./pages/admin/AdminJobsPage.jsx').then(m => ({ default: m.AdminJobsPage || m.default })));
const AdminOperationsPage = lazy(() => import('./pages/admin/AdminOperationsPage.jsx').then(m => ({ default: m.AdminOperationsPage || m.default })));
const AdminWalletPage = lazy(() => import('./pages/admin/AdminWalletPage.jsx').then(m => ({ default: m.AdminWalletPage || m.default })));
const AdminScorecardsPage = lazy(() => import('./pages/admin/AdminScorecardsPage.jsx').then(m => ({ default: m.AdminScorecardsPage || m.default })));
const AdminSocialSecurityPage = lazy(() => import('./pages/admin/AdminSocialSecurityPage.jsx').then(m => ({ default: m.AdminSocialSecurityPage || m.default })));
const AdminReportsPage = lazy(() => import('./pages/admin/AdminReportsPage.jsx').then(m => ({ default: m.AdminReportsPage || m.default })));
const AdminSkillsPage = lazy(() => import('./pages/admin/AdminSkillsPage.jsx').then(m => ({ default: m.AdminSkillsPage || m.default })));
const AdminServiceProvidersPage = lazy(() => import('./pages/admin/AdminServiceProvidersPage.jsx').then(m => ({ default: m.AdminServiceProvidersPage || m.default })));
const ProviderProfilePage = lazy(() => import('./pages/admin/ProviderProfilePage.jsx').then(m => ({ default: m.ProviderProfilePage || m.default })));
const VendorTechnicianNetworkPage = lazy(() => import('./pages/admin/VendorTechnicianNetworkPage.jsx').then(m => ({ default: m.VendorTechnicianNetworkPage || m.default })));
const VendorInvitationsPage = lazy(() => import('./pages/admin/VendorInvitationsPage.jsx').then(m => ({ default: m.VendorInvitationsPage || m.default })));
const PlatformVendorsPage = lazy(() => import('./pages/platform/PlatformVendorsPage.jsx').then(m => ({ default: m.PlatformVendorsPage || m.default })));
const PlatformWorkforcePage = lazy(() => import('./pages/platform/PlatformWorkforcePage.jsx').then(m => ({ default: m.PlatformWorkforcePage || m.default })));
const CustomerTrackingPage = lazy(() => import('./pages/customer/CustomerTrackingPage.jsx').then(m => ({ default: m.CustomerTrackingPage || m.default })));
const CustomerQuotationDecisionPage = lazy(() => import('./pages/customer/CustomerQuotationDecisionPage.jsx').then(m => ({ default: m.CustomerQuotationDecisionPage || m.default })));
const AdminQuotationApprovalsPage = lazy(() => import('./pages/admin/AdminQuotationApprovalsPage.jsx').then(m => ({ default: m.AdminQuotationApprovalsPage || m.default })));
const AdminPricingPolicyPage = lazy(() => import('./pages/admin/AdminPricingPolicyPage.jsx').then(m => ({ default: m.AdminPricingPolicyPage || m.default })));
const AdminStockManagementPage = lazy(() => import('./pages/admin/AdminStockManagementPage.jsx').then(m => ({ default: m.AdminStockManagementPage || m.default })));
const InvoicesPage = lazy(() => import('./pages/admin/InvoicesPage.jsx').then(m => ({ default: m.InvoicesPage || m.default })));
import { SuperadminRoute } from './components/common/SuperadminRoute.jsx';
const WalletDashboardPage = lazy(() => import('./pages/admin/wallet/WalletDashboardPage.jsx').then(m => ({ default: m.WalletDashboardPage || m.default })));
const WalletPayoutAccountsPage = lazy(() => import('./pages/admin/wallet/WalletPayoutAccountsPage.jsx').then(m => ({ default: m.WalletPayoutAccountsPage || m.default })));
const WalletTransactionsPage = lazy(() => import('./pages/admin/wallet/WalletTransactionsPage.jsx').then(m => ({ default: m.WalletTransactionsPage || m.default })));
const WalletWithdrawalsPage = lazy(() => import('./pages/admin/wallet/WalletWithdrawalsPage.jsx').then(m => ({ default: m.WalletWithdrawalsPage || m.default })));
const EmployeeWalletDashboardPage = lazy(() => import('./pages/employee/wallet/EmployeeWalletDashboardPage.jsx').then(m => ({ default: m.EmployeeWalletDashboardPage || m.default })));
const EmployeeWalletTransactionsPage = lazy(() => import('./pages/employee/wallet/EmployeeWalletTransactionsPage.jsx').then(m => ({ default: m.EmployeeWalletTransactionsPage || m.default })));
const EmployeeWalletWithdrawalsPage = lazy(() => import('./pages/employee/wallet/EmployeeWalletWithdrawalsPage.jsx').then(m => ({ default: m.EmployeeWalletWithdrawalsPage || m.default })));
const EmployeePayoutAccountsPage = lazy(() => import('./pages/employee/wallet/EmployeePayoutAccountsPage.jsx').then(m => ({ default: m.EmployeePayoutAccountsPage || m.default })));
const AdminInventoryPage = lazy(() => import('./pages/admin/AdminInventoryPage.jsx'));
const AdminStoreProfilePage = lazy(() => import('./pages/admin/AdminStoreProfilePage.jsx'));
const AdminPromotionsPage = lazy(() => import('./pages/admin/AdminPromotionsPage.jsx'));
const AdminGroceryOrdersPage = lazy(() => import('./pages/admin/AdminGroceryOrdersPage.jsx'));
const AdminGrocerySettlementsPage = lazy(() => import('./pages/admin/AdminGrocerySettlementsPage.jsx'));
function EmployeeWorkspaceLayout() {
  return (
    <EmployeeRoute>
      <EmployeeRuntimeProvider>
        <Outlet />
      </EmployeeRuntimeProvider>
    </EmployeeRoute>
  );
}

function RootRedirect() {
  const { isReady, isAuthenticated, isAdmin, registrationStatus } = useAuth();

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-100 text-zinc-700 font-sans">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-zinc-900 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs font-bold text-zinc-600">Loading workforce portal...</p>
        </div>
      </div>
    );
  }
  if (!isAuthenticated) return <Navigate to="/workforce/login" replace />;

  if (isAdmin) {
    return <Navigate to="/workforce/admin" replace />;
  }

  if (registrationStatus === 'approved') {
    return <Navigate to="/workforce/employee/dashboard" replace />;
  } else if (registrationStatus === 'submitted' || registrationStatus === 'under_review') {
    return <Navigate to="/workforce/onboarding/pending-review" replace />;
  } else if (registrationStatus === 'correction_required') {
    return <Navigate to="/workforce/onboarding/corrections" replace />;
  } else if (registrationStatus === 'rejected') {
    return <Navigate to="/workforce/onboarding/rejected" replace />;
  } else {
    return <Navigate to="/workforce/onboarding/wizard" replace />;
  }
}

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          {/* One Suspense boundary covering every lazily-loaded route. Without
              it, a route whose chunk is still downloading renders nothing at
              all; with it the user sees the app's own spinner. */}
          <Suspense
            fallback={
              <div className="min-h-screen flex items-center justify-center bg-slate-50">
                <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              </div>
            }
          >
          <Routes>
            {/* Root */}
            <Route path="/" element={<RootRedirect />} />

            {/* Direct Role Route Aliases */}
            <Route path="/admin" element={<Navigate to="/workforce/admin" replace />} />
            <Route path="/admin/*" element={<Navigate to="/workforce/admin" replace />} />
            <Route path="/vendor/estimations" element={<Navigate to="/workforce/admin/estimations" replace />} />
            <Route path="/employee" element={<Navigate to="/workforce/employee/dashboard" replace />} />
            <Route path="/employee/*" element={<Navigate to="/workforce/employee/dashboard" replace />} />

          {/* Public Auth */}
          <Route path="/workforce/login" element={<LoginPage />} />
          <Route path="/workforce/signup" element={<SignupPage />} />
          <Route path="/workforce/provider-signup" element={<ProviderSignupPage />} />

            {/* Public Legal, Compliance & Support Hub */}
            <Route path="/terms" element={<TermsAndConditionsPage />} />
            <Route path="/workforce/terms" element={<TermsAndConditionsPage />} />
            <Route path="/privacy" element={<PrivacyPolicyPage />} />
            <Route path="/workforce/privacy" element={<PrivacyPolicyPage />} />
            <Route path="/support" element={<SupportAndContactPage />} />
            <Route path="/contact" element={<SupportAndContactPage />} />
            <Route path="/workforce/support" element={<SupportAndContactPage />} />
            <Route path="/cancellation-refunds" element={<CancellationRefundsPage />} />
            <Route path="/refunds" element={<CancellationRefundsPage />} />
            <Route path="/workforce/cancellation-refunds" element={<CancellationRefundsPage />} />
            <Route path="/shipping-policy" element={<ShippingPolicyPage />} />
            <Route path="/workforce/shipping-policy" element={<ShippingPolicyPage />} />

            {/* Technician Onboarding Lifecycle */}
            <Route
              path="/workforce/onboarding/wizard"
              element={
                <EmployeeRoute>
                  <OnboardingWizardPage />
                </EmployeeRoute>
              }
            />
            <Route
              path="/workforce/onboarding/pending-review"
              element={
                <EmployeeRoute>
                  <PendingReviewPage />
                </EmployeeRoute>
              }
            />
            <Route
              path="/workforce/onboarding/corrections"
              element={
                <EmployeeRoute>
                  <CorrectionRequiredPage />
                </EmployeeRoute>
              }
            />
            <Route
              path="/workforce/onboarding/rejected"
              element={
                <EmployeeRoute>
                  <RejectedPage />
                </EmployeeRoute>
              }
            />

          {/* Approved Technician Workspace with Persistent Session Runtime */}
          <Route path="/workforce/employee" element={<EmployeeWorkspaceLayout />}>
            <Route index element={<Navigate to="/workforce/employee/dashboard" replace />} />
            <Route path="dashboard" element={<EmployeeDashboardPage />} />
            <Route path="jobs" element={<EmployeeJobsPage />} />
            <Route path="estimates" element={<EmployeeEstimatesPage />} />
            <Route path="estimates/:id" element={<EmployeeEstimatesPage />} />
            <Route path="schedule" element={<Navigate to="/workforce/employee/dashboard" replace />} />
            <Route path="attendance" element={<Navigate to="/workforce/employee/dashboard" replace />} />
            <Route path="leave" element={<Navigate to="/workforce/employee/dashboard" replace />} />
            <Route path="earnings" element={<EmployeeWalletDashboardPage />} />
            <Route path="wallet" element={<EmployeeWalletDashboardPage />} />
            <Route path="wallet/transactions" element={<EmployeeWalletTransactionsPage />} />
            <Route path="wallet/withdrawals" element={<EmployeeWalletWithdrawalsPage />} />
            <Route path="wallet/payout-accounts" element={<EmployeePayoutAccountsPage />} />
            <Route path="documents" element={<EmployeeDocumentsPage />} />
            <Route path="services" element={<EmployeeServicesPage />} />
            <Route path="profile" element={<EmployeeProfilePage />} />
            <Route path="settings" element={<EmployeeSettingsPage />} />
            <Route path="performance" element={<EmployeePerformancePage />} />
            <Route path="feedback" element={<EmployeePerformancePage />} />
            <Route path="location" element={<EmployeeLocationPage />} />
            <Route path="vendor-network" element={<MyVendorNetworkPage />} />
            <Route path="invitations" element={<TechnicianInvitationsPage />} />
          </Route>

            {/* Workforce Admin Operations Workspace */}
            <Route
              path="/workforce/admin"
              element={
                <AdminRoute>
                  <AdminDashboardPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/service-providers"
              element={
                <SuperadminRoute>
                  <AdminServiceProvidersPage />
                </SuperadminRoute>
              }
            />
            <Route
              path="/workforce/admin/provider-profile"
              element={
                <AdminRoute>
                  <ProviderProfilePage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/provider/profile"
              element={<Navigate to="/workforce/admin/provider-profile" replace />}
            />
            <Route
              path="/workforce/admin/applications"
              element={
                <AdminRoute>
                  <AdminApplicationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/applications/:id"
              element={
                <AdminRoute>
                  <AdminApplicationDetailPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/employees"
              element={
                <AdminRoute>
                  <AdminEmployeesPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/jobs"
              element={
                <AdminRoute>
                  <AdminJobsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/estimations"
              element={
                <AdminRoute>
                  <VendorEstimationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/vendor/estimations"
              element={
                <AdminRoute>
                  <VendorEstimationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/quotations"
              element={
                <AdminRoute>
                  <AdminQuotationApprovalsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/pricing"
              element={
                <AdminRoute>
                  <AdminPricingPolicyPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/stock"
              element={
                <AdminRoute>
                  <AdminStockManagementPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/invoices"
              element={
                <AdminRoute>
                  <InvoicesPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/dispatch"
              element={
                <AdminRoute>
                  <AdminOperationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/operations"
              element={
                <AdminRoute>
                  <AdminOperationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/services"
              element={
                <AdminRoute>
                  <AdminApplicationsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/skills"
              element={
                <AdminRoute>
                  <AdminSkillsPage />
                </AdminRoute>
              }
            />

          {/* Workforce Admin Operations Workspace */}
          <Route
            path="/workforce/admin"
            element={
              <AdminRoute>
                <AdminDashboardPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/applications"
            element={
              <AdminRoute>
                <AdminApplicationsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/applications/:id"
            element={
              <AdminRoute>
                <AdminApplicationDetailPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/employees"
            element={
              <AdminRoute>
                <AdminEmployeesPage />
              </AdminRoute>
            }
          />
          {/* SEVO Platform Admin Routes */}
          <Route
            path="/workforce/platform/vendors"
            element={
              <PlatformAdminRoute>
                <PlatformVendorsPage />
              </PlatformAdminRoute>
            }
          />
          <Route
            path="/workforce/platform/workforce"
            element={
              <PlatformAdminRoute>
                <PlatformWorkforcePage />
              </PlatformAdminRoute>
            }
          />

          {/* Vendor Admin & Operations Routes */}
          <Route
            path="/workforce/admin/technician-network"
            element={
              <AdminRoute>
                <VendorTechnicianNetworkPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/vendor-invitations"
            element={
              <AdminRoute>
                <VendorInvitationsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/jobs"
            element={
              <AdminRoute>
                <AdminJobsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/dispatch"
            element={
              <AdminRoute>
                <AdminOperationsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/operations"
            element={
              <AdminRoute>
                <AdminOperationsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/services"
            element={
              <AdminRoute>
                <AdminApplicationsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/skills"
            element={
              <AdminRoute>
                <AdminSkillsPage />
              </AdminRoute>
            }
          />

            {/* Admin Wallet Governance */}
            <Route
              path="/workforce/admin/wallet"
              element={
                <AdminRoute>
                  <WalletDashboardPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/wallet/transactions"
              element={
                <AdminRoute>
                  <WalletTransactionsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/wallet/withdrawals"
              element={
                <AdminRoute>
                  <WalletWithdrawalsPage />
                </AdminRoute>
              }
            />
            <Route
              path="/workforce/admin/wallet/payout-accounts"
              element={
                <AdminRoute>
                  <WalletPayoutAccountsPage />
                </AdminRoute>
              }
            />

          <Route
            path="/workforce/admin/wallet"
            element={
              <AdminRoute>
                <AdminWalletPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/scorecards"
            element={
              <AdminRoute>
                <AdminScorecardsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/social-security"
            element={
              <AdminRoute>
                <AdminSocialSecurityPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/reports"
            element={
              <AdminRoute>
                <AdminReportsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/inventory"
            element={
              <AdminRoute>
                <AdminInventoryPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/store-profile"
            element={
              <AdminRoute>
                <AdminStoreProfilePage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/promotions"
            element={
              <AdminRoute>
                <AdminPromotionsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/grocery-orders"
            element={
              <AdminRoute>
                <AdminGroceryOrdersPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/grocery-settlements"
            element={
              <AdminRoute>
                <AdminGrocerySettlementsPage />
              </AdminRoute>
            }
          />
          <Route
            path="/workforce/admin/settings"
            element={
              <AdminRoute>
                <AdminDashboardPage />
              </AdminRoute>
            }
          />

          {/* Customer Live Tracking Routes */}
          <Route path="/track/:jobId" element={<CustomerTrackingPage />} />
          <Route path="/customer/track/:jobId" element={<CustomerTrackingPage />} />

          {/* Customer quotation decision */}
          <Route path="/customer/quote/:token" element={<CustomerQuotationDecisionPage />} />
          <Route path="/booking/quote/:token" element={<CustomerQuotationDecisionPage />} />
          <Route path="/workforce/customer/quote/:token" element={<CustomerQuotationDecisionPage />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/workforce/login" replace />} />
        </Routes>
          </Suspense>
      </BrowserRouter>
    </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
