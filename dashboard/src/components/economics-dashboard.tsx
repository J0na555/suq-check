"use client";

import { apiFetch, type UnitEconomicsResponse } from "@/api/client";
import { SourceEconomicsChart } from "@/components/charts";
import {
  Card,
  CardHeader,
  ErrorNotice,
  MetricCard,
  PageHeader,
  RefreshButton,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import { BadgeCheck, Bot, CircleDollarSign, ScanLine } from "lucide-react";
import { useCallback, useState } from "react";

const periods = [7, 30, 90] as const;

export function EconomicsDashboard() {
  const [period, setPeriod] = useState<(typeof periods)[number]>(30);
  const loader = useCallback(
    (signal: AbortSignal) =>
      apiFetch<UnitEconomicsResponse>(
        `/api/analytics/unit-economics?period_days=${period}`,
        signal,
      ),
    [period],
  );
  const state = useLiveData(loader, 60_000);
  const data = state.data;
  const verificationRate =
    data && data.observations
      ? (data.verified_observations / data.observations) * 100
      : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operating efficiency"
        title="Unit economics"
        description="Measured ingestion and AI processing costs. These figures describe system operations, not revenue or customer traction."
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
        <div className="grid animate-pulse gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-36 rounded-2xl border border-slate-200 bg-white"
            />
          ))}
        </div>
      ) : data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              label="Observations"
              value={data.observations.toLocaleString()}
              helper={`Submitted in ${period} days`}
              icon={ScanLine}
              tone="blue"
            />
            <MetricCard
              label="Verified"
              value={data.verified_observations.toLocaleString()}
              helper={`${verificationRate.toFixed(1)}% verification rate`}
              icon={BadgeCheck}
            />
            <MetricCard
              label="Gemini cost"
              value={`${data.gemini_cost_etb.toLocaleString(undefined, { maximumFractionDigits: 2 })} ETB`}
              helper={`${data.total_tokens.toLocaleString()} tokens`}
              icon={Bot}
              tone="violet"
            />
            <MetricCard
              label="AI cost / verified"
              value={
                data.cost_per_verified_observation_etb == null
                  ? "—"
                  : `${data.cost_per_verified_observation_etb.toFixed(3)} ETB`
              }
              helper="Model processing cost only"
              icon={CircleDollarSign}
              tone="amber"
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(330px,.8fr)]">
            <Card>
              <CardHeader
                title="Volume by evidence source"
                description="Submitted observations compared with verified observations"
              />
              <div className="p-5">
                {data.by_source.length ? (
                  <SourceEconomicsChart items={data.by_source} />
                ) : (
                  <p className="grid h-72 place-items-center text-sm text-slate-400">
                    No source activity in this period.
                  </p>
                )}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Source efficiency"
                description="AI cost per verified observation"
              />
              <div className="divide-y divide-slate-100 px-5">
                {data.by_source.map((source) => (
                  <div
                    key={source.source_type}
                    className="flex items-center justify-between gap-4 py-4"
                  >
                    <div>
                      <p className="text-sm font-semibold capitalize text-slate-800">
                        {source.source_type.replaceAll("_", " ")}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {source.verified_observations.toLocaleString()} verified
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-slate-800">
                        {source.cost_per_verified_observation_etb == null
                          ? "—"
                          : `${source.cost_per_verified_observation_etb.toFixed(3)} ETB`}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {source.gemini_cost_etb.toFixed(2)} ETB total
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      ) : null}
    </div>
  );
}
