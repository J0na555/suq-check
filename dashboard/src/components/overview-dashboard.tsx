"use client";

import {
  apiFetch,
  type EvidenceLogResponse,
  type PulseResponse,
  type TrendsResponse,
} from "@/api/client";
import { PriceTrendChart } from "@/components/charts";
import {
  Card,
  CardHeader,
  ErrorNotice,
  LoadingGrid,
  MetricCard,
  PageHeader,
  RefreshButton,
  StatusBadge,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import {
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  FileCheck2,
  MapPin,
  ReceiptText,
  ShieldCheck,
  Store,
} from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";

type OverviewData = {
  pulse: PulseResponse;
  trends: TrendsResponse;
  evidence: EvidenceLogResponse;
};

function relativeTime(value: string) {
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return value;
  const minutes = Math.max(0, Math.round((Date.now() - time) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function OverviewDashboard() {
  const loader = useCallback(
    async (signal: AbortSignal): Promise<OverviewData> => {
      const [pulse, trends, evidence] = await Promise.all([
        apiFetch<PulseResponse>("/api/pulse", signal),
        apiFetch<TrendsResponse>("/api/analytics/trends?period_days=7", signal),
        apiFetch<EvidenceLogResponse>("/api/evidence?limit=6&offset=0", signal),
      ]);
      return { pulse, trends, evidence };
    },
    [],
  );
  const state = useLiveData(loader, 60_000);
  const metrics = state.data?.pulse.metrics;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Business intelligence"
        title="Market overview"
        description="A live view of essential-product coverage, price movement, and evidence quality across the SuqCheck network."
        actions={
          <RefreshButton
            refreshing={state.isRefreshing}
            updatedAt={state.updatedAt}
            onClick={state.refresh}
          />
        }
      />

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading ? (
        <LoadingGrid />
      ) : metrics && state.data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard
              label="Verified today"
              value={metrics.verified_prices_today.toLocaleString()}
              helper="Accepted price observations"
              icon={FileCheck2}
            />
            <MetricCard
              label="Products covered"
              value={metrics.products_covered.toLocaleString()}
              helper="Essential packaged SKUs"
              icon={Boxes}
              tone="blue"
            />
            <MetricCard
              label="Stores reporting"
              value={metrics.stores_reporting.toLocaleString()}
              helper="Active retail locations"
              icon={Store}
              tone="violet"
            />
            <MetricCard
              label="New receipts"
              value={metrics.new_receipts_today.toLocaleString()}
              helper="Submitted today"
              icon={ReceiptText}
              tone="amber"
            />
            <MetricCard
              label="Avg. confidence"
              value={`${metrics.average_confidence}%`}
              helper="Across current estimates"
              icon={ShieldCheck}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,.75fr)]">
            <Card>
              <CardHeader
                title="Seven-day price movement"
                description="Market-wide estimates in Ethiopian birr"
                aside={
                  <Link
                    href="/trends"
                    className="text-xs font-semibold text-brand hover:text-brand-dark"
                  >
                    Explore trends
                  </Link>
                }
              />
              <div className="p-4 sm:p-5">
                {state.data.trends.items.length ? (
                  <PriceTrendChart trends={state.data.trends.items.slice(0, 4)} />
                ) : (
                  <p className="grid h-72 place-items-center text-sm text-slate-400">
                    No trend history is available yet.
                  </p>
                )}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Market signals"
                description="Notable movement in the current pulse"
              />
              <div className="divide-y divide-slate-100 px-5">
                {state.data.pulse.movers.map((mover) => {
                  const rising = mover.value > 0;
                  return (
                    <div
                      key={`${mover.product_id}-${mover.kind}`}
                      className="flex items-center gap-3 py-4"
                    >
                      <span
                        className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${
                          rising
                            ? "bg-red-50 text-red-600"
                            : "bg-emerald-50 text-brand"
                        }`}
                      >
                        {rising ? (
                          <ArrowUpRight size={17} />
                        ) : (
                          <ArrowDownRight size={17} />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-semibold text-slate-800">
                          {mover.product_name}
                        </p>
                        <p className="mt-0.5 text-[11px] capitalize text-slate-400">
                          {mover.kind.replaceAll("_", " ")}
                        </p>
                      </div>
                      <span
                        className={`text-sm font-bold ${
                          rising ? "text-red-600" : "text-brand"
                        }`}
                      >
                        {mover.display_value}
                      </span>
                    </div>
                  );
                })}
              </div>
              <div className="grid grid-cols-2 gap-3 border-t border-slate-100 bg-slate-50/70 p-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Cheapest district
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                    <MapPin size={14} className="text-brand" />
                    {state.data.pulse.cheapest_district}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Most active
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 truncate text-sm font-semibold text-slate-800">
                    <Store size={14} className="text-brand" />
                    {state.data.pulse.most_active_store}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader
              title="Latest evidence decisions"
              description="The newest observations and their verification outcome"
              aside={
                <Link
                  href="/evidence"
                  className="text-xs font-semibold text-brand hover:text-brand-dark"
                >
                  View ingestion log
                </Link>
              }
            />
            {state.data.evidence.items.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3 font-bold">Product</th>
                      <th className="px-5 py-3 font-bold">Store</th>
                      <th className="px-5 py-3 font-bold">Source</th>
                      <th className="px-5 py-3 font-bold">Price</th>
                      <th className="px-5 py-3 font-bold">Decision</th>
                      <th className="px-5 py-3 text-right font-bold">Observed</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {state.data.evidence.items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/60">
                        <td className="px-5 py-3.5 font-semibold text-slate-800">
                          {item.product_name}
                        </td>
                        <td className="px-5 py-3.5 text-slate-500">
                          {item.store_name ?? "Market-wide"}
                        </td>
                        <td className="px-5 py-3.5 capitalize text-slate-500">
                          {item.source_type.replaceAll("_", " ")}
                        </td>
                        <td className="px-5 py-3.5 font-semibold text-slate-700">
                          {item.price_etb.toLocaleString()} ETB
                        </td>
                        <td className="px-5 py-3.5">
                          <StatusBadge status={item.status} />
                        </td>
                        <td className="px-5 py-3.5 text-right text-slate-400">
                          {relativeTime(item.observed_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="p-10 text-center text-sm text-slate-400">
                No evidence has been submitted yet.
              </p>
            )}
          </Card>
        </>
      ) : null}
    </div>
  );
}
