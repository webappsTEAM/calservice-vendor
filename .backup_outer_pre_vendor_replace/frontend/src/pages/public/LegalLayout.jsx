import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Shield,
  FileText,
  HelpCircle,
  RotateCcw,
  Truck,
  Printer,
  ArrowLeft,
  ChevronRight,
  ExternalLink,
  Phone,
  Mail,
  Lock,
} from 'lucide-react';

export function LegalLayout({
  title,
  subtitle,
  activeTab = 'terms',
  children,
}) {
  const location = useLocation();

  const navItems = [
    { id: 'terms', label: 'Terms of Service', path: '/terms', icon: FileText },
    { id: 'privacy', label: 'Privacy Policy', path: '/privacy', icon: Shield },
    { id: 'support', label: 'Support & Contact', path: '/support', icon: HelpCircle },
    { id: 'refunds', label: 'Cancellation & Refunds', path: '/cancellation-refunds', icon: RotateCcw },
    { id: 'shipping', label: 'Service Delivery & Fulfillment', path: '/shipping-policy', icon: Truck },
  ];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 font-sans flex flex-col antialiased">
      {/* ── TOP HEADER / BRAND BAR ── */}
      <header className="bg-zinc-950 text-white border-b border-zinc-800 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <Link to="/workforce/login" className="flex items-center gap-2.5 text-white group">
                <div className="w-8 h-8 rounded-lg bg-zinc-100 flex items-center justify-center font-bold text-zinc-950 shadow-xs group-hover:bg-white transition-colors">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-xs font-black tracking-widest uppercase text-zinc-100 flex items-center gap-1.5">
                    <span>CAL SERVICES</span>
                    <span className="text-[10px] bg-zinc-800 text-zinc-300 font-bold px-1.5 py-0.5 rounded-full border border-zinc-700">
                      LEGAL & SUPPORT
                    </span>
                  </div>
                  <div className="text-[10px] text-zinc-400 font-medium tracking-tight">
                    Workforce Field Operations Platform
                  </div>
                </div>
              </Link>
            </div>

            {/* Header Actions */}
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={handlePrint}
                className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-800 transition-all cursor-pointer shadow-xs"
                title="Print or Save as PDF"
              >
                <Printer className="w-3.5 h-3.5 text-zinc-400" />
                <span>Print Document</span>
              </button>

              <Link
                to="/workforce/login"
                className="inline-flex items-center gap-1.5 px-4 py-1.5 min-h-[34px] rounded-lg text-xs font-bold bg-zinc-100 hover:bg-white text-zinc-950 shadow-xs transition-all cursor-pointer"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Technician Sign In</span>
              </Link>
            </div>
          </div>
        </div>

        {/* ── NAVIGATION TABS BAR ── */}
        <div className="bg-zinc-900/90 border-t border-zinc-800/80 backdrop-blur">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <nav className="flex items-center gap-1.5 overflow-x-auto py-2 scrollbar-none text-xs">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive =
                  location.pathname === item.path ||
                  location.pathname === `/workforce${item.path}` ||
                  activeTab === item.id;

                return (
                  <Link
                    key={item.id}
                    to={item.path}
                    className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg font-bold whitespace-nowrap transition-all ${
                      isActive
                        ? 'bg-zinc-800 text-white shadow-xs'
                        : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'
                    }`}
                  >
                    <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-zinc-500'}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      </header>

      {/* ── HERO BANNER ── */}
      <section className="bg-white border-b border-zinc-200/90 py-6 sm:py-8 shadow-xs">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-1.5 text-[11px] font-bold text-zinc-800 bg-zinc-100 px-2.5 py-0.5 rounded-full border border-zinc-200 mb-2">
                <Lock className="w-3 h-3 text-zinc-600" />
                <span>Authoritative Compliance & Operational Policy</span>
              </div>
              <h1 className="text-xl sm:text-2xl font-black text-zinc-950 tracking-tight">
                {title}
              </h1>
              {subtitle && (
                <p className="text-xs sm:text-sm text-zinc-600 mt-1 max-w-3xl leading-relaxed">
                  {subtitle}
                </p>
              )}
            </div>

            <div className="flex flex-col items-start md:items-end text-xs text-zinc-500 shrink-0">
              <span className="font-bold text-zinc-900">CALDIM ENGINEERING PRIVATE LIMITED</span>
              <span className="text-zinc-800 font-bold text-[11px] bg-zinc-100 px-2.5 py-0.5 rounded-full border border-zinc-200 mt-1">
                Effective Date: August 20, 2026
              </span>
              <span className="text-[10px] text-zinc-400 mt-0.5">Workforce Technology Operations</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── MAIN CONTENT CONTAINER ── */}
      <main className="flex-1 py-8">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white border border-zinc-200/90 rounded-md shadow-card overflow-hidden p-6 sm:p-10">
            {children}
          </div>
        </div>
      </main>

      {/* ── FOOTER ── */}
      <footer className="bg-zinc-950 text-zinc-400 border-t border-zinc-800 py-10 mt-auto text-xs">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pb-8 border-b border-zinc-800">
            {/* Col 1 */}
            <div className="space-y-2">
              <div className="text-sm font-bold text-white uppercase tracking-wider">
                CALDIM ENGINEERING PRIVATE LIMITED
              </div>
              <p className="text-zinc-400 text-[11px] leading-relaxed">
                Minmac center #118, First Floor, Arcot Road, Valasaravalakkam, Chennai - 600087, Tamil Nadu, India.
              </p>
              <div className="text-[11px] text-zinc-400 font-mono space-y-0.5 pt-1">
                <div>GSTIN: <span className="text-zinc-200 font-bold">33AAGCC4916J1ZP</span></div>
                <div>CIN: <span className="text-zinc-200 font-bold">U72900KA2026PTC123456</span></div>
              </div>
            </div>

            {/* Col 2 */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-white uppercase tracking-wider">
                Legal & Governance
              </div>
              <ul className="space-y-1.5 text-[11px]">
                <li>
                  <Link to="/terms" className="hover:text-white transition-colors">
                    Terms & Conditions
                  </Link>
                </li>
                <li>
                  <Link to="/privacy" className="hover:text-white transition-colors">
                    Privacy & Telemetry Policy
                  </Link>
                </li>
                <li>
                  <Link to="/cancellation-refunds" className="hover:text-white transition-colors">
                    Cancellation & Refund Framework
                  </Link>
                </li>
                <li>
                  <Link to="/shipping-policy" className="hover:text-white transition-colors">
                    Service Delivery & Fulfillment Policy
                  </Link>
                </li>
              </ul>
            </div>

            {/* Col 3 */}
            <div className="space-y-2">
              <div className="text-xs font-bold text-white uppercase tracking-wider">
                Direct Dispatch & Helpdesk
              </div>
              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <a href="mailto:support@caldimengg.in" className="text-zinc-200 hover:text-white font-mono underline transition-colors">
                    support@caldimengg.in
                  </a>
                </div>
                <div className="flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-zinc-300 shrink-0" />
                  <a href="tel:2484553855" className="hover:text-white transition-colors font-mono">
                    Office # 248-455 3855
                  </a>
                </div>
                <p className="text-[10px] text-zinc-500 pt-1">
                  Monday to Saturday, 9:00 AM to 6:00 PM Service Desk for active technicians and scheduled customer bookings.
                </p>
              </div>
            </div>
          </div>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-zinc-500">
            <div>
              &copy; {new Date().getFullYear()} CALDIM ENGINEERING PRIVATE LIMITED. All rights reserved.
            </div>
            <div className="flex items-center gap-4">
              <Link to="/workforce/login" className="hover:text-zinc-300">Technician Login</Link>
              <span>&bull;</span>
              <Link to="/workforce/signup" className="hover:text-zinc-300">Technician Registration</Link>
              <span>&bull;</span>
              <Link to="/support" className="hover:text-zinc-300">Contact Helpdesk</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LegalLayout;
