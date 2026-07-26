"use client";

import {
  apiFetch,
  type CompetitorsResponse,
  type ComplianceResponse,
  type OosResponse,
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
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import { categoryLabel, formatEtb, formatPct } from "@/lib/categories";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Boxes,
  MapPin,
  Package,
  Percent,
  Scale,
  Store,
} from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";

type OverviewData = {
  pulse: PulseResponse;
  trends: TrendsResponse;
  compliance: ComplianceResponse;
  competitors: CompetitorsResponse;
  oos: OosResponse;
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
  const loader = useCallback(async (signal: AbortSignal): Promise<OverviewData> => {
    const [pulse, trends, compliance, competitors, oos] = await Promise.all([
      apiFetch<PulseResponse>("/api/pulse", signal),
      apiFetch<TrendsResponse>("/api/analytics/trends?period_days=7", signal),
      apiFetch<ComplianceResponse>("/api/analytics/compliance", signal),
      apiFetch<CompetitorsResponse>("/api/analytics/competitors", signal),
      apiFetch<OosResponse>("/api/analytics/oos?days=7", signal),
    ]);
    return { pulse, trends, compliance, competitors, oos };
  }, []);
  const state = useLiveData(loader, 60_000);
  const metrics = state.data?.pulse.metrics;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Market Insights"
        title="Brand market overview"
        description="Real-time pricing, MRP compliance, competitor movement, and out-of-stock signals across Addis staples — built for businesses that price from evidence."
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
              label="MRP compliance"
              value={`${metrics.mrp_compliance_pct}%`}
              helper="Shops priced at manufacturer MRP"
              icon={Scale}
            />
            <MetricCard
              label="OOS rate"
              value={`${metrics.oos_rate_pct}%`}
              helper="Resolved cells marked out of stock"
              icon={AlertTriangle}
              tone="amber"
            />
            <MetricCard
              label="Active OOS alerts"
              value={metrics.active_oos_alerts.toLocaleString()}
              helper="Last 7 days"
              icon={Package}
              tone="violet"
            />
            <MetricCard
              label="Categories covered"
              value={metrics.categories_covered.toLocaleString()}
              helper="Live staples panel"
              icon={Boxes}
              tone="blue"
            />
            <MetricCard
              label="Stores reporting"
              value={metrics.stores_reporting.toLocaleString()}
              helper="Active retail locations"
              icon={Store}
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
                    Compliance mix
                  </p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-slate-800">
                    <Percent size={14} className="text-brand" />
                    {state.data.compliance.summary.above_pct}% above MRP
                  </p>
                </div>
              </div>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader
                title="Competitor snapshot"
                description="SKUs farthest from the category median"
                aside={
                  <Link
                    href="/products"
                    className="text-xs font-semibold text-brand hover:text-brand-dark"
                  >
                    Browse products
                  </Link>
                }
              />
              <div className="divide-y divide-slate-100">
                {state.data.competitors.items.slice(0, 5).map((item) => (
                  <Link
                    key={item.product_id}
                    href={`/products/${item.product_id}`}
                    className="flex items-center gap-3 px-5 py-3.5 hover:bg-slate-50/80"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {item.product_name}
                      </p>
                      <p className="mt-0.5 text-[11px] text-slate-400">
                        {item.brand} · {categoryLabel(item.category)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-slate-800">
                        {formatEtb(item.market_price_etb)}
                      </p>
                      <p
                        className={`text-[11px] font-semibold ${
                          item.vs_category_median_pct > 0
                            ? "text-red-600"
                            : "text-brand"
                        }`}
                      >
                        {formatPct(item.vs_category_median_pct)} vs median
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Latest OOS alerts"
                description="Shelf gaps that brands need to act on"
                aside={
                  <Link
                    href="/oos"
                    className="text-xs font-semibold text-brand hover:text-brand-dark"
                  >
                    View all alerts
                  </Link>
                }
              />
              <div className="divide-y divide-slate-100">
                {state.data.oos.items.slice(0, 5).map((item) => (
                  <div key={item.id} className="flex items-center gap-3 px-5 py-3.5">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-amber-50 text-amber-700">
                      <AlertTriangle size={16} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-slate-800">
                        {item.product_name}
                      </p>
                      <p className="mt-0.5 truncate text-[11px] text-slate-400">
                        {item.store_name ?? "Unknown store"}
                        {item.district ? ` · ${item.district}` : ""}
                      </p>
                    </div>
                    <span className="text-xs text-slate-400">
                      {relativeTime(item.observed_at)}
                    </span>
                  </div>
                ))}
                {!state.data.oos.items.length ? (
                  <p className="p-8 text-center text-sm text-slate-400">
                    No out-of-stock alerts in the last week.
                  </p>
                ) : null}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
