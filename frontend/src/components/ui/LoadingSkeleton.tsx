export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />;
}

export function KpiGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-hidden="true">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="panel panel-pad flex min-h-[150px] flex-col gap-4">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton({ height = "h-[340px]" }: { height?: string }) {
  return (
    <div className="panel panel-pad" aria-hidden="true">
      <Skeleton className="h-5 w-52" />
      <Skeleton className="mt-2 h-3 w-80 max-w-full" />
      <Skeleton className={`mt-6 w-full ${height}`} />
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div className="panel panel-pad" aria-hidden="true">
      <Skeleton className="h-5 w-40" />
      <div className="mt-5 space-y-3">
        {Array.from({ length: 8 }, (_, index) => (
          <Skeleton key={index} className="h-9 w-full" />
        ))}
      </div>
    </div>
  );
}

export function PageSkeleton({ charts = 1 }: { charts?: number }) {
  return (
    <div className="space-y-6" role="status" aria-label="Loading analysis">
      <div className="space-y-3">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-80 max-w-full" />
        <Skeleton className="h-4 w-[560px] max-w-full" />
      </div>
      <KpiGridSkeleton />
      {Array.from({ length: charts }, (_, index) => (
        <ChartSkeleton key={index} />
      ))}
      <span className="sr-only">Loading analysis…</span>
    </div>
  );
}
