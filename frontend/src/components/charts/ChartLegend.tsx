export function ChartLegend({
  items,
}: {
  items: Array<{ label: string; color: string; dashed?: boolean }>;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-muted">
      {items.map((item) => (
        <span key={item.label} className="inline-flex items-center gap-2">
          <span
            className="h-0.5 w-4 rounded"
            style={{
              backgroundColor: item.dashed ? "transparent" : item.color,
              borderTop: item.dashed ? `1px dashed ${item.color}` : undefined,
            }}
            aria-hidden="true"
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}
