import type { components } from "./types";

export type PulseResponse = components["schemas"]["PulseResponse"];
export type EvidenceLogResponse = components["schemas"]["EvidenceLogResponse"];
export type EvidenceLogItem = components["schemas"]["EvidenceLogItem"];
export type TrendsResponse = components["schemas"]["TrendsResponse"];
export type ProductTrend = components["schemas"]["ProductTrend"];
export type UnitEconomicsResponse =
  components["schemas"]["UnitEconomicsResponse"];
export type ProductListResponse = components["schemas"]["ProductListResponse"];
export type ProductDetail = components["schemas"]["ProductDetail"];
export type NearbyStoresResponse =
  components["schemas"]["NearbyStoresResponse"];
export type ComplianceResponse = components["schemas"]["ComplianceResponse"];
export type DistrictsResponse = components["schemas"]["DistrictsResponse"];
export type OosResponse = components["schemas"]["OosResponse"];
export type CompetitorsResponse = components["schemas"]["CompetitorsResponse"];

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "https://suq-check-api.onrender.com"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    let message = `The API returned ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // The status code still gives the user an actionable error.
    }
    if (response.status === 404) {
      message = `${message} Market Insights routes need the local API (USE_FIXTURES=true on :8000) or a redeployed backend — production may not have them yet.`;
    }
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}

export function exportUrl(params: {
  category?: string;
  brand?: string;
  level?: "district" | "store";
}) {
  const query = new URLSearchParams();
  if (params.category) query.set("category", params.category);
  if (params.brand) query.set("brand", params.brand);
  if (params.level) query.set("level", params.level);
  const suffix = query.toString() ? `?${query}` : "";
  return `${API_URL}/api/exports/market-insights.csv${suffix}`;
}
