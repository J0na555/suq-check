"use client";

import { apiFetch, type OosResponse } from "@/api/client";
import { CategoryFilter } from "@/components/category-filter";
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
import { categoryLabel } from "@/lib/categories";
import { AlertTriangle, Package } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";

function relativeTime(value: string) {
  const time = new Date(value).getTime();
  if (Number.isNaN(time)) return value;
  const minutes = Math.max(0, Math.round((Date.now() - time) / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function OosDashboard() {
  const [category, setCategory] = useState("");
  const [days, setDays] = useState(7);
  const loader = useCallback(
    async (signal: AbortSignal) => {
      const params = new URLSearchParams({ days: String(days) });
      if (category) params.set("category", category);
      return apiFetch<OosResponse>(`/api/analytics/oos?${params}`, signal);
    },
    [category, days],
  );
  const state = useLiveData(loader, 45_000);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Market Insights"
        title="Out-of-stock alerts"
        description="Distribution truth from ambassador visits — which SKUs are missing from which shelves."
        actions={
          <RefreshButton
            refreshing={state.isRefreshing}
            updatedAt={state.updatedAt}
            onClick={state.refresh}
          />
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CategoryFilter value={category} onChange={setCategory} />
        <div className="flex gap-2">
          {[7, 14, 30].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDays(value)}
              className={`rounded-xl px-3 py-2 text-sm font-semibold ${
                days === value
                  ? "bg-brand text-white"
                  : "border border-slate-200 bg-white text-slate-600"
              }`}
            >
              {value}d
            </button>
          ))}
        </div>
      </div>

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading || !state.data ? (
        <LoadingGrid />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard
              label="Active alerts"
              value={state.data.total.toLocaleString()}
              helper={`Accepted OOS flags in the last ${days} days`}
              icon={AlertTriangle}
              tone="amber"
            />
            <MetricCard
              label="Showing"
              value={String(state.data.items.length)}
              helper="Most recent alerts in this view"
              icon={Package}
              tone="violet"
            />
          </div>

          <Card>
            <CardHeader
              title="Alert feed"
              description="Product × store gaps from the panel"
            />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-5 py-3 font-bold">Product</th>
                    <th className="px-5 py-3 font-bold">Store</th>
                    <th className="px-5 py-3 font-bold">District</th>
                    <th className="px-5 py-3 font-bold">Source</th>
                    <th className="px-5 py-3 text-right font-bold">Observed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {state.data.items.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/60">
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/products/${item.product_id}`}
                          className="font-semibold text-slate-800 hover:text-brand"
                        >
                          {item.product_name}
                        </Link>
                        <p className="mt-0.5 text-[11px] text-slate-400">
                          {item.brand} · {categoryLabel(item.category)}
                        </p>
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">
                        {item.store_name ?? "—"}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">
                        {item.district ?? "—"}
                      </td>
                      <td className="px-5 py-3.5 capitalize text-slate-500">
                        {item.source_type.replaceAll("_", " ")}
                      </td>
                      <td className="px-5 py-3.5 text-right text-slate-400">
                        {relativeTime(item.observed_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!state.data.items.length ? (
                <p className="p-10 text-center text-sm text-slate-400">
                  No out-of-stock alerts for this filter.
                </p>
              ) : null}
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
