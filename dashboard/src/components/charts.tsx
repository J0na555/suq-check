"use client";

import type {
  ProductTrend,
  UnitEconomicsResponse,
} from "@/api/client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const chartColors = ["#0B6E4F", "#6D5BD0", "#C47A17", "#2676A6", "#B42318"];

function compactDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function PriceTrendChart({
  trends,
  height = 300,
}: {
  trends: ProductTrend[];
  height?: number;
}) {
  const rows = new Map<string, Record<string, string | number>>();
  for (const trend of trends) {
    for (const point of trend.points) {
      const row = rows.get(point.day) ?? { day: point.day };
      row[trend.product_name] = point.price_etb;
      rows.set(point.day, row);
    }
  }
  const data = [...rows.values()].sort((a, b) =>
    String(a.day).localeCompare(String(b.day)),
  );

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 8, left: -12, bottom: 0 }}>
          <defs>
            {trends.map((trend, index) => (
              <linearGradient
                key={trend.product_id}
                id={`trend-${index}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="5%"
                  stopColor={chartColors[index % chartColors.length]}
                  stopOpacity={0.18}
                />
                <stop
                  offset="95%"
                  stopColor={chartColors[index % chartColors.length]}
                  stopOpacity={0}
                />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid stroke="#E8ECF1" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="day"
            tickFormatter={compactDate}
            tick={{ fill: "#94A3B8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94A3B8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => `${value}`}
          />
          <Tooltip
            labelFormatter={(label) => compactDate(String(label))}
            formatter={(value) => [`${Number(value).toLocaleString()} ETB`]}
            contentStyle={{
              border: "1px solid #E2E8F0",
              borderRadius: 12,
              boxShadow: "0 8px 30px rgba(15,23,42,.08)",
              fontSize: 12,
            }}
          />
          {trends.length > 1 ? (
            <Legend wrapperStyle={{ fontSize: 11, paddingTop: 12 }} />
          ) : null}
          {trends.map((trend, index) => (
            <Area
              key={trend.product_id}
              type="monotone"
              dataKey={trend.product_name}
              stroke={chartColors[index % chartColors.length]}
              strokeWidth={2.5}
              fill={`url(#trend-${index})`}
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SourceEconomicsChart({
  items,
}: {
  items: UnitEconomicsResponse["by_source"];
}) {
  const data = items.map((item) => ({
    source: item.source_type.replaceAll("_", " "),
    observations: item.observations,
    verified: item.verified_observations,
  }));

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 8, left: -8, bottom: 0 }}>
          <CartesianGrid stroke="#E8ECF1" strokeDasharray="4 4" vertical={false} />
          <XAxis
            dataKey="source"
            tick={{ fill: "#64748B", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#94A3B8", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "#F1F5F9" }}
            contentStyle={{
              border: "1px solid #E2E8F0",
              borderRadius: 12,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar
            dataKey="observations"
            fill="#CFE8DE"
            radius={[5, 5, 0, 0]}
          />
          <Bar dataKey="verified" fill="#0B6E4F" radius={[5, 5, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
