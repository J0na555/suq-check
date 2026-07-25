"use client";

import {
  apiFetch,
  type EvidenceLogResponse,
  type EvidenceLogItem,
} from "@/api/client";
import {
  Card,
  ErrorNotice,
  PageHeader,
  RefreshButton,
  StatusBadge,
} from "@/components/ui";
import { useLiveData } from "@/hooks/use-live-data";
import { ChevronDown, ChevronLeft, ChevronRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

const filters = ["all", "accepted", "pending", "rejected"] as const;
type Filter = (typeof filters)[number];
const pageSize = 20;

function EvidenceRow({ item }: { item: EvidenceLogItem }) {
  return (
    <tr className="group border-b border-slate-100 last:border-0 hover:bg-slate-50/70">
      <td className="px-5 py-4">
        <p className="font-semibold text-slate-800">{item.product_name}</p>
        <p className="mt-1 text-xs text-slate-400">
          {item.store_name ?? "Market-wide observation"}
        </p>
      </td>
      <td className="px-5 py-4 capitalize text-slate-500">
        {item.source_type.replaceAll("_", " ")}
      </td>
      <td className="whitespace-nowrap px-5 py-4 font-semibold text-slate-700">
        {item.price_etb.toLocaleString()} ETB
      </td>
      <td className="px-5 py-4">
        <StatusBadge status={item.status} />
      </td>
      <td className="whitespace-nowrap px-5 py-4 text-slate-500">
        {new Date(item.observed_at).toLocaleString([], {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}
      </td>
      <td className="w-12 px-5 py-4">
        {item.rejection_reason ? (
          <details className="relative">
            <summary
              aria-label="Show verification reason"
              className="grid h-8 w-8 cursor-pointer list-none place-items-center rounded-lg border border-slate-200 text-slate-500 hover:bg-white"
            >
              <ChevronDown size={15} />
            </summary>
            <div className="absolute right-0 z-20 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-600 shadow-xl">
              <p className="mb-1 font-bold text-slate-800">
                Verification reason
              </p>
              {item.rejection_reason}
            </div>
          </details>
        ) : null}
      </td>
    </tr>
  );
}

export function EvidenceDashboard() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const rawStatus = searchParams.get("status") ?? "all";
  const status: Filter = filters.includes(rawStatus as Filter)
    ? (rawStatus as Filter)
    : "all";
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const offset = (page - 1) * pageSize;

  const loader = useCallback(
    (signal: AbortSignal) => {
      const query = new URLSearchParams({
        limit: String(pageSize),
        offset: String(offset),
      });
      if (status !== "all") query.set("status", status);
      return apiFetch<EvidenceLogResponse>(
        `/api/evidence?${query.toString()}`,
        signal,
      );
    },
    [offset, status],
  );
  const state = useLiveData(loader, 30_000);

  function updateQuery(nextStatus: Filter, nextPage = 1) {
    const query = new URLSearchParams();
    if (nextStatus !== "all") query.set("status", nextStatus);
    if (nextPage > 1) query.set("page", String(nextPage));
    router.push(`${pathname}${query.size ? `?${query}` : ""}`);
  }

  const totalPages = state.data
    ? Math.max(1, Math.ceil(state.data.total / pageSize))
    : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Verification pipeline"
        title="Evidence log"
        description="Audit every submitted observation, its source, and the decision made by the verification gate."
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

      <Card>
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
            {filters.map((filter) => (
              <button
                key={filter}
                type="button"
                onClick={() => updateQuery(filter)}
                className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-semibold capitalize transition ${
                  status === filter
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                {filter}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-400">
            {state.data
              ? `${state.data.total.toLocaleString()} observations`
              : "Loading observations…"}
          </p>
        </div>

        {state.isLoading ? (
          <div className="animate-pulse space-y-3 p-5">
            {Array.from({ length: 7 }).map((_, index) => (
              <div key={index} className="h-14 rounded-xl bg-slate-100" />
            ))}
          </div>
        ) : state.data?.items.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 text-[10px] uppercase tracking-wider text-slate-400">
                  <th className="px-5 py-3 font-bold">Product / store</th>
                  <th className="px-5 py-3 font-bold">Source</th>
                  <th className="px-5 py-3 font-bold">Price</th>
                  <th className="px-5 py-3 font-bold">Decision</th>
                  <th className="px-5 py-3 font-bold">Observed</th>
                  <th className="px-5 py-3 font-bold">
                    <span className="sr-only">Reason</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {state.data.items.map((item) => (
                  <EvidenceRow key={item.id} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-14 text-center">
            <p className="font-semibold text-slate-700">No evidence found</p>
            <p className="mt-1 text-sm text-slate-400">
              There are no {status === "all" ? "" : status} observations yet.
            </p>
          </div>
        )}

        {state.data ? (
          <div className="flex items-center justify-between border-t border-slate-100 px-5 py-4">
            <p className="text-xs text-slate-400">
              Page {Math.min(page, totalPages)} of {totalPages}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => updateQuery(status, page - 1)}
                className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                <ChevronLeft size={14} /> Previous
              </button>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => updateQuery(status, page + 1)}
                className="inline-flex h-9 items-center gap-1 rounded-lg border border-slate-200 px-3 text-xs font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-40"
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
