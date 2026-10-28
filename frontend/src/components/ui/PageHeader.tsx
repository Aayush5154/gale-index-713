import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-5 border-b border-line pb-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl">
        <h1 className="text-balance text-2xl font-semibold tracking-tight text-ink sm:text-[28px]">
          {title}
        </h1>
        <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
