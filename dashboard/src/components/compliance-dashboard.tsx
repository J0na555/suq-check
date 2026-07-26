"use client";

import {
  apiFetch,
  exportUrl,
  type ComplianceResponse,
} from "@/api/client";
import { CategoryFilter } from "@/components/category-filter";
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
import { categoryLabel, formatEtb, formatPct } from "@/lib/categories";
import { Download, Scale } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";

export function ComplianceDashboard() {
  const [category, setCategory] = useState("");
  const loader = useCallback(
    async (signal: AbortSignal) => {
      const path = category
        ? `/api/analytics/compliance?category=${encodeURIComponent(category)}`
        : "/api/analytics/compliance";
      return apiFetch<ComplianceResponse>(path, signal);
    },
    [category],
  );
  const state = useLiveData(loader, 60_000);
  const summary = state.data?.summary;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Market Insights"
        title="Price compliance"
        description="Share of shops at, above, or below manufacturer recommended price — the core Signal / Market Insights story."
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <a
              href={exportUrl({
                category: category || undefined,
                level: "district",
              })}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 hover:border-brand hover:text-brand"
            >
              <Download size={16} />
              Export CSV
            </a>
            <RefreshButton
              refreshing={state.isRefreshing}
              updatedAt={state.updatedAt}
              onClick={state.refresh}
            />
          </div>
        }
      />

      <CategoryFilter value={category} onChange={setCategory} />

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading || !summary ? (
        <LoadingGrid />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="At MRP"
              value={`${summary.at_pct}%`}
              helper={`${summary.at_mrp.toLocaleString()} shop prices`}
              icon={Scale}
            />
            <MetricCard
              label="Above MRP"
              value={`${summary.above_pct}%`}
              helper={`${summary.above_mrp.toLocaleString()} unauthorized markups`}
              icon={Scale}
              tone="amber"
            />
            <MetricCard
              label="Below MRP"
              value={`${summary.below_pct}%`}
              helper={`${summary.below_mrp.toLocaleString()} under MRP`}
              icon={Scale}
              tone="blue"
            />
            <MetricCard
              label="Shops priced"
              value={summary.shops_priced.toLocaleString()}
              helper="Store-level estimates with MRP"
              icon={Scale}
              tone="violet"
            />
          </div>

          <Card>
            <CardHeader
              title="SKU compliance"
              description="Market price versus manufacturer MRP, with shop mix"
            />
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                    <th className="px-5 py-3 font-bold">Product</th>
                    <th className="px-5 py-3 font-bold">MRP</th>
                    <th className="px-5 py-3 font-bold">Market</th>
                    <th className="px-5 py-3 font-bold">Delta</th>
                    <th className="px-5 py-3 font-bold">Band</th>
                    <th className="px-5 py-3 font-bold">Shops at / above / below</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {state.data?.items.map((item) => (
                    <tr key={item.product_id} className="hover:bg-slate-50/60">
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
                        {formatEtb(item.mrp_etb)}
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-slate-700">
                        {formatEtb(item.market_price_etb)}
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-slate-700">
                        {formatPct(item.delta_pct)}
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={item.band} />
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">
                        {item.at_mrp} / {item.above_mrp} / {item.below_mrp}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
