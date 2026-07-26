"use client";

import { apiFetch, type DistrictsResponse } from "@/api/client";
import { CategoryFilter } from "@/components/category-filter";
import {
  Card,
  CardHeader,
  ErrorNotice,
  LoadingGrid,
  PageHeader,
  RefreshButton,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import { formatEtb, formatPct } from "@/lib/categories";
import { useCallback, useState } from "react";

export function DistrictsDashboard() {
  const [category, setCategory] = useState("");
  const loader = useCallback(
    async (signal: AbortSignal) => {
      const path = category
        ? `/api/analytics/districts?category=${encodeURIComponent(category)}`
        : "/api/analytics/districts";
      return apiFetch<DistrictsResponse>(path, signal);
    },
    [category],
  );
  const state = useLiveData(loader, 60_000);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Market Insights"
        title="District analysis"
        description="District-level average prices, MRP pressure, coverage, and out-of-stock rates across the Addis panel."
        actions={
          <RefreshButton
            refreshing={state.isRefreshing}
            updatedAt={state.updatedAt}
            onClick={state.refresh}
          />
        }
      />

      <CategoryFilter value={category} onChange={setCategory} />

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading ? (
        <LoadingGrid />
      ) : state.data ? (
        <Card>
          <CardHeader
            title="District matrix"
            description="Pulse-tier geography defaults to district aggregates"
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-5 py-3 font-bold">District</th>
                  <th className="px-5 py-3 font-bold">Avg price</th>
                  <th className="px-5 py-3 font-bold">Avg MRP</th>
                  <th className="px-5 py-3 font-bold">Vs MRP</th>
                  <th className="px-5 py-3 font-bold">At MRP</th>
                  <th className="px-5 py-3 font-bold">Priced cells</th>
                  <th className="px-5 py-3 font-bold">OOS rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {state.data.items.map((row) => (
                  <tr key={row.district} className="hover:bg-slate-50/60">
                    <td className="px-5 py-3.5 font-semibold text-slate-800">
                      {row.district}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-slate-700">
                      {formatEtb(row.avg_price_etb)}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {formatEtb(row.avg_mrp_etb)}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-slate-700">
                      {row.vs_mrp_pct == null ? "—" : formatPct(row.vs_mrp_pct)}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {row.at_mrp_pct == null ? "—" : `${row.at_mrp_pct}%`}
                    </td>
                    <td className="px-5 py-3.5 text-slate-500">
                      {row.priced_cells.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-amber-700">
                      {row.oos_rate_pct}%
                      <span className="ml-1 text-[11px] font-normal text-slate-400">
                        ({row.oos_cells} flags)
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
