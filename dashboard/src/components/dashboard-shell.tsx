"use client";

import {
  BarChart3,
  ChartNoAxesCombined,
  Database,
  LayoutDashboard,
  Menu,
  ShieldCheck,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const navigation = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/evidence", label: "Evidence", icon: Database },
  { href: "/trends", label: "Price trends", icon: ChartNoAxesCombined },
  { href: "/economics", label: "Economics", icon: BarChart3 },
];

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="grid h-10 w-10 place-items-center rounded-xl bg-brand text-white shadow-lg shadow-emerald-950/20">
        <ShieldCheck size={23} strokeWidth={2.3} />
      </span>
      <span>
        <span className="block text-lg font-bold tracking-tight text-white">
          SuqCheck
        </span>
        <span className="block text-[10px] font-medium uppercase tracking-[0.15em] text-emerald-200/70">
          Market intelligence
        </span>
      </span>
    </Link>
  );
}

function Navigation({ close }: { close?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Dashboard">
      <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-100/45">
        Workspace
      </p>
      <ul className="space-y-1.5">
        {navigation.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <li key={href}>
              <Link
                href={href}
                onClick={close}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                  active
                    ? "bg-white text-brand shadow-sm"
                    : "text-emerald-50/70 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon size={18} aria-hidden="true" />
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-sidebar px-4 py-6 lg:flex">
        <Brand />
        <div className="mt-10">
          <Navigation />
        </div>
        <div className="mt-auto rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-xs font-semibold text-white">Evidence first</p>
          <p className="mt-1 text-xs leading-5 text-emerald-100/55">
            Every market price is weighted, verified, and explainable.
          </p>
        </div>
      </aside>

      <div className="border-b border-slate-200 bg-white px-4 py-3 lg:hidden">
        <div className="flex items-center justify-between">
          <div className="[&_span_span]:text-slate-950 [&_span_span+span]:text-slate-400">
            <Brand />
          </div>
          <button
            type="button"
            aria-label="Open navigation"
            onClick={() => setOpen(true)}
            className="rounded-lg border border-slate-200 p-2 text-slate-700"
          >
            <Menu size={20} />
          </button>
        </div>
      </div>

      {open ? (
        <div className="fixed inset-0 z-50 bg-slate-950/40 lg:hidden">
          <aside className="h-full w-72 bg-sidebar p-5 shadow-2xl">
            <div className="flex items-center justify-between">
              <Brand />
              <button
                type="button"
                aria-label="Close navigation"
                onClick={() => setOpen(false)}
                className="rounded-lg p-2 text-white hover:bg-white/10"
              >
                <X size={20} />
              </button>
            </div>
            <div className="mt-10">
              <Navigation close={() => setOpen(false)} />
            </div>
          </aside>
        </div>
      ) : null}

      <main className="min-h-screen lg:pl-64">
        <div className="mx-auto max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
