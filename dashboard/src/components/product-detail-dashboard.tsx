"use client";

import {
  apiFetch,
  type NearbyStoresResponse,
  type ProductDetail,
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
import { categoryLabel, formatEtb, formatPct } from "@/lib/categories";
import { MapPin, Percent, ShieldCheck, Store, Tag } from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";

type DetailData = {
  product: ProductDetail;
  stores: NearbyStoresResponse;
};

export function ProductDetailDashboard({ productId }: { productId: string }) {
  const loader = useCallback(
    async (signal: AbortSignal): Promise<DetailData> => {
      const [product, stores] = await Promise.all([
        apiFetch<ProductDetail>(`/api/products/${productId}`, signal),
        apiFetch<NearbyStoresResponse>(
          `/api/products/${productId}/stores`,
          signal,
        ),
      ]);
      return { product, stores };
    },
    [productId],
  );
  const state = useLiveData(loader, 60_000);
  const product = state.data?.product;
  const mrpDelta =
    product?.mrp_etb != null
      ? ((product.market_price_etb - product.mrp_etb) / product.mrp_etb) * 100
      : null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="SKU intelligence"
        title={product?.canonical_name ?? "Product detail"}
        description={
          product
            ? `${product.brand} · ${categoryLabel(product.category)} · ${product.size_label}. Shop-level pricing for Market Intelligence buyers.`
            : "Loading SKU market detail…"
        }
        actions={
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/products"
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700"
            >
              Back to products
            </Link>
            <RefreshButton
              refreshing={state.isRefreshing}
              updatedAt={state.updatedAt}
              onClick={state.refresh}
            />
          </div>
        }
      />

      {state.error ? (
        <ErrorNotice message={state.error} retry={state.refresh} />
      ) : null}

      {state.isLoading || !product ? (
        <LoadingGrid />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Market price"
              value={formatEtb(product.market_price_etb)}
              helper={`${product.store_count} stores · ${product.evidence_count} reports`}
              icon={Tag}
            />
            <MetricCard
              label="Manufacturer MRP"
              value={formatEtb(product.mrp_etb)}
              helper={
                mrpDelta == null
                  ? "No MRP on file"
                  : `${formatPct(mrpDelta)} vs market`
              }
              icon={Percent}
              tone="amber"
            />
            <MetricCard
              label="Confidence"
              value={`${product.confidence}%`}
              helper={`${product.confidence_band} band`}
              icon={ShieldCheck}
              tone="blue"
            />
            <MetricCard
              label="Spread"
              value={`${(product.spread_pct * 100).toFixed(1)}%`}
              helper={`${formatEtb(product.price_range_etb[0])} – ${formatEtb(product.price_range_etb[1])}`}
              icon={Store}
              tone="violet"
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(280px,.8fr)]">
            <Card>
              <CardHeader
                title="Price history"
                description="Daily market estimate"
              />
              <div className="p-4 sm:p-5">
                {product.history.length ? (
                  <PriceTrendChart
                    trends={[
                      {
                        product_id: product.id,
                        product_name: product.canonical_name,
                        direction: "stable",
                        change_pct: 0,
                        points: product.history.map((point) => ({
                          day: point.day,
                          price_etb: point.price_etb,
                        })),
                      },
                    ]}
                  />
                ) : (
                  <p className="grid h-72 place-items-center text-sm text-slate-400">
                    No history yet.
                  </p>
                )}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Evidence sources"
                description="What feeds this estimate"
              />
              <div className="divide-y divide-slate-100 px-5">
                {product.sources.map((source) => (
                  <div
                    key={source.source_type}
                    className="flex items-center justify-between py-3.5"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">
                        {source.label}
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {source.count} reports
                      </p>
                    </div>
                    <StatusBadge
                      status={
                        product.confidence_band === "high"
                          ? "high"
                          : product.confidence_band === "medium"
                            ? "medium"
                            : "low"
                      }
                    />
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader
              title="Shop-level prices"
              description="Market Intelligence view — individual stores vs market"
            />
            {state.data?.stores.items.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3 font-bold">Store</th>
                      <th className="px-5 py-3 font-bold">District</th>
                      <th className="px-5 py-3 font-bold">Price</th>
                      <th className="px-5 py-3 font-bold">Vs market</th>
                      <th className="px-5 py-3 font-bold">Verdict</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {state.data.stores.items.map((store) => (
                      <tr key={store.id} className="hover:bg-slate-50/60">
                        <td className="px-5 py-3.5 font-semibold text-slate-800">
                          {store.name}
                        </td>
                        <td className="px-5 py-3.5 text-slate-500">
                          <span className="inline-flex items-center gap-1">
                            <MapPin size={13} />
                            {store.district}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 font-semibold text-slate-700">
                          {formatEtb(store.price_etb)}
                        </td>
                        <td className="px-5 py-3.5 text-slate-500">
                          {formatPct(
                            (store.difference_from_market_etb /
                              state.data!.stores.market_price_etb) *
                              100,
                          )}
                        </td>
                        <td className="px-5 py-3.5 capitalize text-slate-600">
                          {store.verdict}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="p-10 text-center text-sm text-slate-400">
                No shop-level prices for this SKU yet.
              </p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
