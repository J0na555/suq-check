"use client";

import {
  apiFetch,
  exportUrl,
  type CompetitorsResponse,
  type ProductListResponse,
} from "@/api/client";
import { CategoryFilter } from "@/components/category-filter";
import {
  Card,
  CardHeader,
  ErrorNotice,
  LoadingGrid,
  PageHeader,
  RefreshButton,
  StatusBadge,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import { categoryLabel, formatEtb, formatPct } from "@/lib/categories";
import { Download, Search } from "lucide-react";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

type ProductsData = {
  products: ProductListResponse;
  competitors: CompetitorsResponse;
};

export function ProductsDashboard() {
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");

  const loader = useCallback(
    async (signal: AbortSignal): Promise<ProductsData> => {
      const params = new URLSearchParams({ limit: "40", offset: "0" });
      if (category) params.set("category", category);
      if (submittedQuery) params.set("q", submittedQuery);
      const competitorPath = category
        ? `/api/analytics/competitors?category=${encodeURIComponent(category)}`
        : "/api/analytics/competitors";
      const [products, competitors] = await Promise.all([
        apiFetch<ProductListResponse>(`/api/products?${params}`, signal),
        apiFetch<CompetitorsResponse>(competitorPath, signal),
      ]);
      return { products, competitors };
    },
    [category, submittedQuery],
  );
  const state = useLiveData(loader, 60_000);

  const competitorById = useMemo(() => {
    const map = new Map<string, CompetitorsResponse["items"][number]>();
    for (const item of state.data?.competitors.items ?? []) {
      map.set(item.product_id, item);
    }
    return map;
  }, [state.data?.competitors.items]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Market Insights"
        title="Products & competitors"
        description="SKU-level market prices, MRP, and how each brand sits against the category median."
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

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <CategoryFilter value={category} onChange={setCategory} />
        <form
          className="flex min-w-[240px] flex-1 items-center gap-2 sm:max-w-md"
          onSubmit={(event) => {
            event.preventDefault();
            setSubmittedQuery(query.trim());
          }}
        >
          <div className="relative flex-1">
            <Search
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search brand or SKU"
              className="w-full rounded-xl border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm font-medium text-slate-800 outline-none focus:border-brand"
            />
          </div>
          <button
            type="submit"
            className="rounded-xl bg-brand px-3 py-2 text-sm font-semibold text-white"
          >
            Search
          </button>
        </form>
      </div>

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading ? (
        <LoadingGrid />
      ) : state.data ? (
        <Card>
          <CardHeader
            title={`${state.data.products.total} products`}
            description={
              state.data.competitors.category_median_etb != null
                ? `Category median ${formatEtb(state.data.competitors.category_median_etb)}`
                : "Live market estimates with manufacturer MRP"
            }
          />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-5 py-3 font-bold">Product</th>
                  <th className="px-5 py-3 font-bold">Category</th>
                  <th className="px-5 py-3 font-bold">Market</th>
                  <th className="px-5 py-3 font-bold">MRP</th>
                  <th className="px-5 py-3 font-bold">Vs median</th>
                  <th className="px-5 py-3 font-bold">7d</th>
                  <th className="px-5 py-3 font-bold">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {state.data.products.items.map((item) => {
                  const peer = competitorById.get(item.id);
                  return (
                    <tr key={item.id} className="hover:bg-slate-50/60">
                      <td className="px-5 py-3.5">
                        <Link
                          href={`/products/${item.id}`}
                          className="font-semibold text-slate-800 hover:text-brand"
                        >
                          {item.canonical_name}
                        </Link>
                        <p className="mt-0.5 text-[11px] text-slate-400">
                          {item.brand} · {item.size_label}
                        </p>
                      </td>
                      <td className="px-5 py-3.5 capitalize text-slate-500">
                        {categoryLabel(item.category)}
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-slate-700">
                        {formatEtb(item.market_price_etb)}
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">
                        {formatEtb(item.mrp_etb)}
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-slate-700">
                        {peer ? formatPct(peer.vs_category_median_pct) : "—"}
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-slate-700">
                        {peer ? formatPct(peer.change_pct) : "—"}
                      </td>
                      <td className="px-5 py-3.5">
                        <StatusBadge status={item.confidence_band} />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
