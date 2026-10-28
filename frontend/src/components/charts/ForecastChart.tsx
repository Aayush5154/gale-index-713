import {
  CartesianGrid,
  Customized,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART } from "../../utils/chartTheme";
import { formatAxisTimestamp, formatNumber } from "../../utils/format";
import type { ForecastChartPoint } from "./chartData";
import { ForecastTooltip } from "./ChartTooltips";

interface AxisMap {
  [key: string]: { scale?: (value: number) => number } | undefined;
}

function ForecastPath({
  points,
  xAxisMap,
  yAxisMap,
}: {
  points: ForecastChartPoint[];
  xAxisMap?: AxisMap;
  yAxisMap?: AxisMap;
}) {
  const xScale = xAxisMap?.[0]?.scale;
  const yScale = yAxisMap?.[0]?.scale;
  if (!xScale || !yScale) return null;

  let path = "";
  let drawing = false;

  for (const point of points) {
    // Skip half-hour outturn points: the forecast is hourly.
    if (point.interval === null) continue;
    if (point.forecast === null) {
      drawing = false;
      continue;
    }
    const x = xScale(point.ts);
    const y = yScale(point.forecast);
    if (!Number.isFinite(x) || !Number.isFinite(y)) {
      drawing = false;
      continue;
    }
    path += `${drawing ? "L" : "M"}${x},${y} `;
    drawing = true;
  }

  return (
    <path
      d={path}
      fill="none"
      stroke={CHART.accent}
      strokeWidth={1.8}
      strokeLinejoin="round"
      strokeLinecap="round"
    />
  );
}

export function ForecastChart({
  points,
  rangeDays,
}: {
  points: ForecastChartPoint[];
  rangeDays: number;
}) {
  const multiDay = rangeDays > 1;
  const yValues = points
    .flatMap((point) => [point.actual, point.forecast])
    .filter((value): value is number => value !== null && Number.isFinite(value));
  const maxValue = yValues.length > 0 ? Math.max(...yValues) : 0;
  const yMax = maxValue > 0 ? Math.ceil((maxValue * 1.02) / 1000) * 1000 : 1000;
  const forecastPath = (props: { xAxisMap?: AxisMap; yAxisMap?: AxisMap }) => (
    <ForecastPath {...props} points={points} />
  );

  return (
    <div
      className="h-[340px] w-full sm:h-[390px]"
      role="img"
      aria-label="Line chart comparing hourly selected WINDFOR forecasts with half-hourly FUELHH wind outturn in megawatts."
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={points} margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
          <CartesianGrid stroke={CHART.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="ts"
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            tickFormatter={(value: number) => formatAxisTimestamp(value, multiDay)}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: CHART.grid }}
            minTickGap={46}
          />
          <YAxis
            width={62}
            tickFormatter={(value: number) => formatNumber(value, 0)}
            tick={{ fill: CHART.axis, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            domain={[0, yMax]}
          />
          <Tooltip
            content={<ForecastTooltip />}
            cursor={{ stroke: CHART.axis, strokeDasharray: "3 3" }}
          />
          <Line
            type="linear"
            dataKey="actual"
            name="FUELHH outturn"
            stroke={CHART.actual}
            strokeWidth={1.4}
            dot={false}
            activeDot={{ r: 3, fill: CHART.actual, stroke: "none" }}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Customized component={forecastPath} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
