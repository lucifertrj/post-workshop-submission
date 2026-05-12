"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

type Series = {
  name: string;
  values: number[];
  color: string;
  dashed?: boolean;
  alpha?: number;
};

export default function SignalChart({
  series,
  height = 200,
  yLabel,
  showZeroLine = true,
}: {
  series: Series[];
  height?: number;
  yLabel?: string;
  showZeroLine?: boolean;
}) {
  // Recharts wants an array of objects with merged keys per x
  const maxLen = Math.max(0, ...series.map((s) => s.values.length));
  const data: Record<string, number>[] = [];
  for (let i = 0; i < maxLen; i++) {
    const row: Record<string, number> = { i };
    series.forEach((s) => {
      if (i < s.values.length) row[s.name] = s.values[i];
    });
    data.push(row);
  }

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="rgba(244,235,225,0.06)" />
          <XAxis
            dataKey="i"
            type="number"
            tick={{ fill: "rgba(244,235,225,0.7)", fontSize: 11 }}
            stroke="rgba(244,235,225,0.2)"
          />
          <YAxis
            tick={{ fill: "rgba(244,235,225,0.7)", fontSize: 11 }}
            stroke="rgba(244,235,225,0.2)"
            label={
              yLabel
                ? {
                    value: yLabel,
                    angle: -90,
                    position: "insideLeft",
                    fill: "rgba(244,235,225,0.5)",
                    fontSize: 11,
                  }
                : undefined
            }
          />
          {showZeroLine && (
            <ReferenceLine y={0} stroke="rgba(244,235,225,0.2)" />
          )}
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(10,16,20,0.92)",
              border: "1px solid rgba(244,235,225,0.15)",
              borderRadius: "6px",
              fontSize: "12px",
              color: "rgba(244,235,225,0.9)",
            }}
            labelStyle={{ color: "rgba(244,235,225,0.6)" }}
            formatter={(v: number) => v.toFixed(4)}
          />
          {series.map((s) => (
            <Line
              key={s.name}
              dataKey={s.name}
              stroke={s.color}
              strokeWidth={s.dashed ? 1 : 1.2}
              strokeDasharray={s.dashed ? "4 3" : undefined}
              strokeOpacity={s.alpha ?? 1}
              dot={false}
              isAnimationActive={false}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
