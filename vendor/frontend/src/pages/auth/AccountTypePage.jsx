import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Building2,
  Wrench,
  Store,
  ArrowRight,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { LegalComplianceModal } from '../../components/common/LegalComplianceModal.jsx';
import { Button } from '../../components/enterprise/Button.jsx';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardBadge,
} from '../../components/enterprise/Card.jsx';

export function AccountTypePage() {
  const navigate = useNavigate();
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState('contact');

  const openLegalModal = (tab = 'contact') => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  const accountTypes = [
    {
      id: 'vendor',
      title: 'Sevo Vendor',
      subtitle: 'Service Provider & Contractor Business',
      badge: 'Provider Enterprise',
      badgeVariant: 'neutral',
      icon: Building2,
      description:
        'Register your company, manage staff & tied technicians, dispatch service jobs, and process head-wallet team earnings.',
      features: [
        'Multi-worker dispatch team management',
        'Provider head wallet & automated settlements',
        'Commercial estimations & invoice issuance',
      ],
      route: '/workforce/provider-signup',
      btnText: 'Register as Vendor',
      btnVariant: 'outline',
    },
    {
      id: 'technician',
      title: 'Sevo Service Community',
      subtitle: 'Independent Technician / Specialist',
      badge: 'Workforce Pro',
      badgeVariant: 'neutral',
      icon: Wrench,
      description:
        'Join our verified field technician network, complete trade jobs (AC, Electrical, Plumbing), and receive direct on-demand alerts.',
      features: [
        'Instant mobile dispatch & GPS job navigation',
        'Personal worker wallet with fast UPI payouts',
        'Trade qualification & skills verification',
      ],
      route: '/workforce/signup',
      btnText: 'Join as Technician',
      btnVariant: 'outline',
    },
    {
      id: 'seller',
      title: 'Sevo Seller Hub',
      subtitle: 'Grocery Store & Supermarket Merchant',
      badge: 'Grocery Marketplace',
      badgeVariant: 'amber',
      icon: Store,
      description:
        'Onboard your retail storefront, list groceries & household essentials, manage live store inventory, and receive local delivery orders.',
      features: [
        'Dedicated storefront & catalog management',
        'FSSAI & compliance verification pipeline',
        'Real-time order fulfillment & settlements',
      ],
      route: '/workforce/seller-signup',
      btnText: 'Register Grocery Store',
      btnVariant: 'primary',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex flex-col justify-between p-4 sm:p-6 lg:p-8 font-sans">
      {/* ── LEGAL & COMPLIANCE MODAL ── */}
      <LegalComplianceModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />

      {/* ── TOP HEADER / BRAND ── */}
      <header className="max-w-6xl w-full mx-auto flex items-center justify-between py-3 border-b border-zinc-200">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-zinc-950 flex items-center justify-center text-white font-bold text-xs shadow-xs border border-zinc-800">
            S
          </div>
          <div>
            <span className="font-bold text-xs tracking-wider text-zinc-950 uppercase block leading-none">
              SEVO PLATFORM
            </span>
            <span className="text-[10px] text-zinc-500 font-medium leading-tight">
              Enterprise Workforce & Commerce Engine
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs">
          <span className="text-zinc-500 hidden sm:inline">Already registered?</span>
          <Link
            to="/workforce/login"
            className="px-3 py-1.5 rounded-lg bg-white hover:bg-zinc-50 text-zinc-800 font-semibold text-xs border border-zinc-300 shadow-xs transition-colors"
          >
            Sign In
          </Link>
        </div>
      </header>

      {/* ── MAIN CONTENT: ACCOUNT CHOOSER ── */}
      <main className="max-w-6xl w-full mx-auto py-8 sm:py-12 my-auto">
        <div className="text-center max-w-2xl mx-auto mb-8 sm:mb-10">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-100 border border-zinc-200 text-zinc-700 text-[11px] font-semibold mb-2.5">
            <Sparkles className="w-3.5 h-3.5 text-zinc-600" />
            <span>Account Selection</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-zinc-950 tracking-tight">
            How would you like to partner with SEVO?
          </h1>
          <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed max-w-lg mx-auto">
            Select the account model tailored to your business operations. Every account gets access to enterprise tooling, real-time ledgers, and automated payout flows.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6">
          {accountTypes.map((type) => {
            const Icon = type.icon;
            return (
              <Card
                key={type.id}
                hoverEffect
                onClick={() => navigate(type.route)}
                className="flex flex-col justify-between"
              >
                <div>
                  <CardHeader className="border-b-0 pb-2">
                    <div className="flex items-center justify-between w-full">
                      <span className="p-1.5 rounded-lg bg-zinc-100 text-zinc-700 shrink-0">
                        <Icon className="w-4 h-4" />
                      </span>
                      <CardBadge variant={type.badgeVariant}>
                        {type.badge}
                      </CardBadge>
                    </div>
                  </CardHeader>

                  <CardContent className="pt-1 pb-4">
                    <h2 className="text-sm font-bold text-zinc-950 tracking-tight">
                      {type.title}
                    </h2>
                    <p className="text-[11px] text-zinc-500 font-medium mt-0.5">
                      {type.subtitle}
                    </p>

                    <p className="text-xs text-zinc-600 mt-2.5 leading-relaxed">
                      {type.description}
                    </p>

                    <div className="mt-4 pt-3.5 border-t border-zinc-100 space-y-2">
                      {type.features.map((feat, idx) => (
                        <div key={idx} className="flex items-start gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-zinc-400 shrink-0 mt-0.5" />
                          <span className="text-[11px] text-zinc-600 leading-tight">{feat}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </div>

                <CardFooter className="pt-3">
                  <Button
                    variant={type.btnVariant}
                    size="sm"
                    className="w-full justify-between"
                    rightIcon={ArrowRight}
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(type.route);
                    }}
                  >
                    {type.btnText}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      </main>

      {/* ── FOOTER COMPLIANCE BAR ── */}
      <footer className="max-w-6xl w-full mx-auto pt-6 border-t border-zinc-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-zinc-500">
        <div>&copy; {new Date().getFullYear()} SEVO Services & Technologies. All rights reserved.</div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => openLegalModal('privacy')}
            className="hover:text-zinc-800 transition-colors"
          >
            Privacy Policy
          </button>
          <button
            type="button"
            onClick={() => openLegalModal('terms')}
            className="hover:text-zinc-800 transition-colors"
          >
            Terms of Service
          </button>
          <button
            type="button"
            onClick={() => openLegalModal('contact')}
            className="hover:text-zinc-800 transition-colors"
          >
            Compliance & Contact
          </button>
        </div>
      </footer>
    </div>
  );
}

export default AccountTypePage;
