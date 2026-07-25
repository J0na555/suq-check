"use client";

import { apiFetch, type TrendsResponse } from "@/api/client";
import { PriceTrendChart } from "@/components/charts";
import {
  Card,
  CardHeader,
  ErrorNotice,
  PageHeader,
  RefreshButton,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  TrendingUp,
} from "lucide-react";
import { useCallback, useState } from "react";

const periods = [7, 30, 90] as const;

export function TrendsDashboard() {
  const [period, setPeriod] = useState<(typeof periods)[number]>(7);
  const loader = useCallback(
    (signal: AbortSignal) =>
      apiFetch<TrendsResponse>(
        `/api/analytics/trends?period_days=${period}`,
        signal,
      ),
    [period],
  );
  const state = useLiveData(loader, 60_000);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Price intelligence"
        title="Market trends"
        description="Compare market-wide price estimates and identify the products moving fastest across the reporting period."
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

      <div className="flex w-fit gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm">
        {periods.map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setPeriod(value)}
            className={`rounded-lg px-4 py-2 text-xs font-semibold transition ${
              period === value
                ? "bg-brand text-white"
                : "text-slate-500 hover:bg-slate-50"
            }`}
          >
            {value} days
          </button>
        ))}
      </div>

      {state.isLoading ? (
        <div className="h-[430px] animate-pulse rounded-2xl border border-slate-200 bg-white" />
      ) : state.data?.items.length ? (
        <>
          <Card>
            <CardHeader
              title={`${period}-day price comparison`}
              description="Daily market estimates in Ethiopian birr"
            />
            <div className="p-4 sm:p-6">
              <PriceTrendChart trends={state.data.items} height={370} />
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {state.data.items.map((trend) => {
              const Icon =
                trend.direction === "up"
                  ? ArrowUpRight
                  : trend.direction === "down"
                    ? ArrowDownRight
                    : ArrowRight;
              const latest = trend.points.at(-1)?.price_etb;
              return (
                <Card key={trend.product_id} className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-800">
                        {trend.product_name}
                      </p>
                      <p className="mt-3 text-2xl font-bold text-slate-950">
                        {latest?.toLocaleString() ?? "—"}{" "}
                        <span className="text-sm font-medium text-slate-400">
                          ETB
                        </span>
                      </p>
                    </div>
                    <span
                      className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${
                        trend.direction === "up"
                          ? "bg-red-50 text-red-600"
                          : trend.direction === "down"
                            ? "bg-emerald-50 text-brand"
                            : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      <Icon size={18} />
                    </span>
                  </div>
                  <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-4">
                    <span className="text-xs capitalize text-slate-400">
                      {trend.direction} over {period} days
                    </span>
                    <span
                      className={`text-sm font-bold ${
                        trend.change_pct > 0
                          ? "text-red-600"
                          : trend.change_pct < 0
                            ? "text-brand"
                            : "text-slate-500"
                      }`}
                    >
                      {trend.change_pct > 0 ? "+" : ""}
                      {trend.change_pct.toFixed(1)}%
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>
        </>
      ) : (
        <Card className="grid min-h-80 place-items-center p-10 text-center">
          <div>
            <TrendingUp className="mx-auto text-slate-300" size={30} />
            <p className="mt-3 font-semibold text-slate-700">
              No price history yet
            </p>
            <p className="mt-1 text-sm text-slate-400">
              Trends appear after accepted evidence is rolled into daily prices.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}
