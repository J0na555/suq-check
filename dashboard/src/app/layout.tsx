import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { DashboardShell } from "@/components/dashboard-shell";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "SuqCheck Market Insights",
    template: "%s | SuqCheck",
  },
  description:
    "Real-time market data for brands — MRP compliance, competitor pricing, district analysis, and out-of-stock alerts across Addis Ababa staples.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} h-full antialiased`}
    >
      <body className="min-h-full">
        <DashboardShell>{children}</DashboardShell>
      </body>
    </html>
  );
}
