import { EvidenceDashboard } from "@/components/evidence-dashboard";
import type { Metadata } from "next";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Evidence log",
};

export default function EvidencePage() {
  return (
    <Suspense
      fallback={
        <div className="h-[600px] animate-pulse rounded-2xl border border-slate-200 bg-white" />
      }
    >
      <EvidenceDashboard />
    </Suspense>
  );
}
