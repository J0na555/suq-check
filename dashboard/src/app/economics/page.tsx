import { EconomicsDashboard } from "@/components/economics-dashboard";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Unit economics",
};

export default function EconomicsPage() {
  return <EconomicsDashboard />;
}
