import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../utils/chartTheme";
import { formatNumber } from "../../utils/format";
import type { HistogramChartPoint } from "./chartData";
import { HistogramTooltip } from "./ChartTooltips";

export function ErrorHistogram({
  points,
  zeroBinMid,
}: {
  points: HistogramChartPoint[];
  zeroBinMid: number | null;
}) {
  return (
    <div
      className="h-[300px] w-full"
      role="img"
      aria-label="Histogram of signed forecast errors. Positive values mean the forecast exceeded outturn."
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 18 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="mid"
            tickFormatter={(value: number) => formatNumber(value, 0)}
            tick={{ fill: CHART.axis, fontSize: 10 }}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            minTickGap={22}
            label={{
              value: "Forecast − actual (MW)",
              position: "insideBottom",
              offset: -10,
              fill: CHART.faint,
              fontSize: 10,
            }}
          />
          <YAxis
            width={44}
            allowDecimals={false}
            tickFormatter={(value: number) => formatNumber(value, 0)}
            tick={{ fill: CHART.axis, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            content={<HistogramTooltip />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          {zeroBinMid !== null ? (
            <ReferenceLine x={zeroBinMid} stroke={CHART.zero} strokeDasharray="3 3" />
          ) : null}
          <Bar dataKey="count" name="Intervals" radius={[2, 2, 0, 0]} isAnimationActive={false}>
            {points.map((point) => (
              <Cell
                key={`${point.lower}-${point.upper}`}
                fill={
                  point.side === "overforecast"
                    ? CHART.over
                    : point.side === "underforecast"
                      ? CHART.under
                      : CHART.zero
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
