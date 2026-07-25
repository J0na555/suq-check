import type { components } from "./types";

export type PulseResponse = components["schemas"]["PulseResponse"];
export type EvidenceLogResponse = components["schemas"]["EvidenceLogResponse"];
export type EvidenceLogItem = components["schemas"]["EvidenceLogItem"];
export type TrendsResponse = components["schemas"]["TrendsResponse"];
export type ProductTrend = components["schemas"]["ProductTrend"];
export type UnitEconomicsResponse =
  components["schemas"]["UnitEconomicsResponse"];

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
    throw new ApiError(message, response.status);
  }

  return (await response.json()) as T;
}
