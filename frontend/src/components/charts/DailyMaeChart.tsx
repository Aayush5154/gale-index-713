import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../utils/chartTheme";
import { formatDay, formatNumber } from "../../utils/format";
import type { DailyChartPoint } from "./chartData";
import { DailyTooltip } from "./ChartTooltips";

export function DailyMaeChart({ points }: { points: DailyChartPoint[] }) {
  return (
    <div
      className="h-[300px] w-full"
      role="img"
      aria-label="Bar chart of daily mean absolute error with a line showing forecast coverage percentage."
    >
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(value: string) => formatDay(value)}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            minTickGap={12}
          />
          <YAxis
            yAxisId="mae"
            width={58}
            tickFormatter={(value: number) => formatNumber(value, 0)}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            yAxisId="coverage"
            orientation="right"
            width={44}
            domain={[0, 100]}
            ticks={[0, 50, 100]}
            tickFormatter={(value: number) => `${value}%`}
            tick={{ fill: CHART.faint, fontSize: 10 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            content={<DailyTooltip />}
            cursor={{ fill: "rgba(255,255,255,0.03)" }}
          />
          <Bar
            yAxisId="mae"
            dataKey="mae"
            name="Daily MAE"
            maxBarSize={18}
            radius={[2, 2, 0, 0]}
            isAnimationActive={false}
          >
            {points.map((point) => (
              <Cell
                key={point.date}
                fill={point.coverage < 95 ? CHART.warn : CHART.accent}
              />
            ))}
          </Bar>
          <Line
            yAxisId="coverage"
            type="monotone"
            dataKey="coverage"
            name="Coverage"
            stroke={CHART.actual}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
