import type { LucideIcon } from "lucide-react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import type { ReactNode } from "react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-brand">
          {eyebrow}
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950 sm:text-3xl">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      </div>
      {actions}
    </header>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.03)] ${className}`}
    >
      {children}
    </section>
  );
}

export function CardHeader({
  title,
  description,
  aside,
}: {
  title: string;
  description?: string;
  aside?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
      <div>
        <h2 className="font-semibold text-slate-900">{title}</h2>
        {description ? (
          <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
        ) : null}
      </div>
      {aside}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = "green",
}: {
  label: string;
  value: string;
  helper: string;
  icon: LucideIcon;
  tone?: "green" | "amber" | "blue" | "violet";
}) {
  const tones = {
    green: "bg-emerald-50 text-brand",
    amber: "bg-amber-50 text-amber-700",
    blue: "bg-blue-50 text-blue-700",
    violet: "bg-violet-50 text-violet-700",
  };

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <span className={`rounded-xl p-2.5 ${tones[tone]}`}>
          <Icon aria-hidden="true" size={18} />
        </span>
      </div>
      <p className="mt-4 text-3xl font-bold tracking-tight text-slate-950">
        {value}
      </p>
      <p className="mt-1 text-xs text-slate-400">{helper}</p>
    </Card>
  );
}

export function StatusBadge({
  status,
}: {
  status:
    | "accepted"
    | "pending"
    | "rejected"
    | "high"
    | "medium"
    | "low"
    | "at"
    | "above"
    | "below";
}) {
  const styles = {
    accepted: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
    pending: "bg-amber-50 text-amber-700 ring-amber-600/10",
    rejected: "bg-red-50 text-red-700 ring-red-600/10",
    high: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
    medium: "bg-amber-50 text-amber-700 ring-amber-600/10",
    low: "bg-red-50 text-red-700 ring-red-600/10",
    at: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
    above: "bg-red-50 text-red-700 ring-red-600/10",
    below: "bg-blue-50 text-blue-700 ring-blue-600/10",
  };

  const labels: Record<typeof status, string> = {
    accepted: "accepted",
    pending: "pending",
    rejected: "rejected",
    high: "high",
    medium: "medium",
    low: "low",
    at: "at MRP",
    above: "above MRP",
    below: "below MRP",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold capitalize ring-1 ring-inset ${styles[status]}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {labels[status]}
    </span>
  );
}

export function RefreshButton({
  refreshing,
  updatedAt,
  onClick,
}: {
  refreshing: boolean;
  updatedAt: Date | null;
  onClick: () => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="hidden text-right text-xs text-slate-400 sm:block">
        {updatedAt
          ? `Updated ${updatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
          : "Waiting for API"}
      </span>
      <button
        type="button"
        onClick={onClick}
        disabled={refreshing}
        className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
      >
        <RefreshCw
          aria-hidden="true"
          className={refreshing ? "animate-spin" : ""}
          size={16}
        />
        Refresh
      </button>
    </div>
  );
}

export function ErrorNotice({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 shrink-0" size={18} />
        <div>
          <p className="font-semibold">Live data is temporarily unavailable</p>
          <p className="mt-0.5 text-amber-800">
            {message} The free API may need a moment to wake up.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={retry}
        className="shrink-0 rounded-lg bg-amber-900 px-3 py-2 font-semibold text-white hover:bg-amber-950"
      >
        Try again
      </button>
    </div>
  );
}

export function LoadingGrid() {
  return (
    <div className="grid animate-pulse gap-4 sm:grid-cols-2 xl:grid-cols-5">
      {Array.from({ length: 5 }).map((_, index) => (
        <div
          key={index}
          className="h-36 rounded-2xl border border-slate-200 bg-white p-5"
        >
          <div className="h-3 w-24 rounded bg-slate-100" />
          <div className="mt-8 h-8 w-20 rounded bg-slate-100" />
          <div className="mt-3 h-2.5 w-32 rounded bg-slate-100" />
        </div>
      ))}
    </div>
  );
}
