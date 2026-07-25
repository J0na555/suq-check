import { TrendsDashboard } from "@/components/trends-dashboard";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Price trends",
};

export default function TrendsPage() {
  return <TrendsDashboard />;
}
