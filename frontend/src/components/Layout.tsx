import {
  Activity,
  BookOpen,
  Crosshair,
  LayoutDashboard,
  RefreshCw,
  Wind,
} from "lucide-react";
import { useEffect } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

import { useAppData } from "../hooks/useAppData";
import { Badge } from "./ui/Badge";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/overview", label: "Overview", icon: LayoutDashboard },
  { to: "/explorer", label: "Forecast Explorer", icon: Activity },
  { to: "/accuracy", label: "Accuracy Analysis", icon: Crosshair },
  { to: "/methodology", label: "Methodology", icon: BookOpen },
];

const PAGE_TITLES: Record<string, string> = {
  "/overview": "Overview",
  "/explorer": "Forecast Explorer",
  "/accuracy": "Accuracy Analysis",
  "/methodology": "Methodology & Data Quality",
};

function navLinkClass({ isActive }: { isActive: boolean }): string {
  return [
    "flex items-center gap-2.5 border-l-2 px-3 py-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-panel",
    isActive
      ? "border-accent bg-white/[0.03] text-accent"
      : "border-transparent text-muted hover:bg-white/[0.03] hover:text-ink",
  ].join(" ");
}

function ApiStatus() {
  const { health, healthError, healthLoading, refreshHealth } = useAppData();

  let dot = "bg-faint";
  let label = "API status unknown";
  let detail = "No health response yet.";
  if (health) {
    if (health.status === "degraded") {
      dot = "bg-warn";
      label = "API degraded";
      detail = health.dependencies.map((item) => `${item.name}: ${item.status}`).join(" · ");
    } else {
      dot = "bg-accent";
      label = "API online";
      detail = `Last checked ${new Date(health.timestamp_utc).toLocaleTimeString("en-GB", {
        timeZone: "Europe/London",
        hour: "2-digit",
        minute: "2-digit",
      })} Europe/London`;
    }
  } else if (healthError) {
    dot = "bg-danger";
    label = "API offline";
    detail = healthError.message;
  } else if (healthLoading) {
    dot = "bg-muted";
    label = "Connecting";
  }

  return (
    <div className="flex items-center gap-2">
      <span
        className={`inline-flex items-center gap-2 text-xs text-muted`}
        title={detail}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${dot}`} aria-hidden="true" />
        <span className="hidden sm:inline">{label}</span>
        <span className="sr-only sm:hidden">{label}</span>
      </span>
      <button
        type="button"
        onClick={refreshHealth}
        className="rounded p-1.5 text-faint transition-colors hover:bg-raised hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        aria-label="Refresh API status"
        title="Refresh API status"
      >
        <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}

export function Layout() {
  const { metadata, health } = useAppData();
  const location = useLocation();
  const currentTitle = PAGE_TITLES[location.pathname] ?? "Page not found";
  const synthetic = metadata?.is_synthetic ?? health?.is_synthetic ?? false;

  useEffect(() => {
    document.title = `${currentTitle} · Wind Forecast Analytics`;
  }, [currentTitle]);

  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#main"
        className="sr-only z-50 rounded-sm bg-accent px-4 py-2 text-sm font-semibold text-canvas focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>

      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-line bg-panel lg:flex">
        <div className="flex h-14 items-center gap-2.5 border-b border-line px-5">
          <Wind className="h-5 w-5 text-accent" aria-hidden="true" />
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight text-ink">Wind Forecast</p>
            <p className="text-[10px] uppercase tracking-[0.14em] text-faint">Analytics</p>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Primary">
          <div className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={{ pathname: item.to, search: location.search }}
                  className={navLinkClass}
                >
                  <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {item.label}
                </NavLink>
              );
            })}
          </div>
        </nav>

        <div className="border-t border-line px-5 py-4">
          <p className="text-xs leading-5 text-faint">
            Elexon FUELHH &amp; WINDFOR
            <br />
            MW · Europe/London
          </p>
        </div>
      </aside>

      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-line bg-canvas">
          <div className="flex h-14 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-2.5">
              <Wind className="h-4 w-4 text-accent lg:hidden" aria-hidden="true" />
              <span className="truncate text-sm font-medium text-ink">{currentTitle}</span>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              {synthetic ? (
                <Badge tone="warn">Synthetic fixture</Badge>
              ) : metadata ? (
                <Badge tone="accent">Live Elexon</Badge>
              ) : null}
              <ApiStatus />
            </div>
          </div>

          <nav
            className="flex gap-1 overflow-x-auto border-t border-line px-2 py-2 lg:hidden"
            aria-label="Primary mobile"
          >
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={{ pathname: item.to, search: location.search }}
                  className={({ isActive }) =>
                    [
                      "flex shrink-0 items-center gap-2 rounded-sm px-3 py-1.5 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                      isActive ? "bg-raised text-accent" : "text-muted hover:text-ink",
                    ].join(" ")
                  }
                >
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {item.label}
                </NavLink>
              );
            })}
          </nav>
        </header>

        {synthetic ? (
          <div className="border-b border-warn/20 bg-warn/[0.06] px-4 py-2 text-xs leading-5 text-warn sm:px-6 lg:px-8">
            <strong className="font-semibold">Fixture mode.</strong> The API is serving a labelled
            synthetic dataset for offline demonstration. These are not Elexon observations and must
            not be used for procurement decisions.
          </div>
        ) : null}

        <main id="main" className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Outlet />
        </main>

        <footer className="mx-auto w-full max-w-[1440px] border-t border-line px-4 py-6 text-xs leading-5 text-faint sm:px-6 lg:px-8">
          <p>
            Source: Elexon Insights Solution (FUELHH, WINDFOR). Times displayed in Europe/London;
            data normalised to UTC. Generation values are MW as supplied.
          </p>
          <p className="mt-1">
            This is an independent analytics prototype. See{" "}
            <NavLink to={{ pathname: "/methodology", search: location.search }} className="link">
              methodology and data quality
            </NavLink>{" "}
            for definitions and limitations.
          </p>
        </footer>
      </div>
    </div>
  );
}
