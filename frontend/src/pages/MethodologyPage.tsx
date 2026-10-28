import { ExternalLink, FileJson, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "../components/ui/Badge";
import { PageSkeleton } from "../components/ui/LoadingSkeleton";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { ErrorState } from "../components/ui/States";
import { useAppData } from "../hooks/useAppData";
import type { MetadataResponse } from "../types/api";
import { formatDate } from "../utils/format";

const SECTIONS = [
  { id: "scope", label: "Scope" },
  { id: "sources", label: "Sources & resolution" },
  { id: "cutoff", label: "Decision cut-off" },
  { id: "selection", label: "Forecast selection" },
  { id: "matching", label: "Matching & units" },
  { id: "metrics", label: "Metrics" },
  { id: "quality", label: "Data quality" },
  { id: "limitations", label: "Limitations" },
  { id: "reproducibility", label: "Reproducibility" },
];

function MethodSection({
  id,
  title,
  description,
  children,
}: {
  id: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-24 border-t border-line pt-8 first:border-t-0 first:pt-0">
      <h2 className="text-lg font-semibold tracking-tight text-ink">{title}</h2>
      {description ? <p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted">{description}</p> : null}
      <div className="mt-4">{children}</div>
    </section>
  );
}

function MethodContent({ metadata }: { metadata: MetadataResponse }) {
  return (
    <div className="grid gap-10 xl:grid-cols-[190px_minmax(0,1fr)]">
      <aside className="hidden xl:block">
        <nav aria-label="On this page" className="sticky top-24">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-faint">On this page</p>
          <ul className="mt-3 space-y-1.5">
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="block rounded px-2 py-1 text-xs text-muted transition-colors hover:bg-raised hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                >
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="min-w-0 space-y-8">
        <div className="flex flex-wrap gap-2">
          <Badge tone={metadata.is_synthetic ? "warn" : "accent"}>
            {metadata.is_synthetic ? "Synthetic fixture deployment" : "Live Elexon deployment"}
          </Badge>
          <Badge tone="neutral">{metadata.environment}</Badge>
          <Badge tone="muted">v{metadata.version}</Badge>
        </div>

        <MethodSection
          id="scope"
          title="Scope"
          description="This is a retrospective forecast-accuracy tool for national GB wind generation. It supports procurement analysis of forecast error; it is not a trading, scheduling or settlement system."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-sm border border-line bg-panel px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-faint">In scope</p>
              <ul className="mt-2 space-y-1.5 text-xs leading-5 text-muted">
                <li>National wind generation outturn (FUELHH, WIND only).</li>
                <li>National wind generation forecasts (WINDFOR).</li>
                <li>Decision-time forecast selection and retrospective error.</li>
                <li>Coverage, missing-data counts and signed error distribution.</li>
              </ul>
            </div>
            <div className="rounded-sm border border-line bg-panel px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.09em] text-faint">Out of scope</p>
              <ul className="mt-2 space-y-1.5 text-xs leading-5 text-muted">
                <li>Weather, demand, price or generation-mix modelling.</li>
                <li>Procurement volumes, bid strategy or financial savings.</li>
                <li>Half-hourly forecast fabrication or statistical downscaling.</li>
                <li>Forecast bias correction or calibration.</li>
              </ul>
            </div>
          </div>
          <p className="mt-3 text-xs leading-5 text-faint">
            Target period: {formatDate(metadata.target_period.from_date)} –{" "}
            {formatDate(metadata.target_period.to_date)}. {metadata.supported_range_note}
          </p>
        </MethodSection>

        <MethodSection
          id="sources"
          title="Sources and resolution"
          description="Only official Elexon Insights Solution endpoints are queried. Documentation pages are not treated as data endpoints."
        >
          <div className="space-y-4">
            {metadata.datasets.map((dataset) => (
              <article key={dataset.key} className="rounded-sm border border-line bg-panel p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-ink">
                      {dataset.key} · {dataset.name}
                    </h3>
                    <p className="mt-1 max-w-3xl text-xs leading-5 text-muted">{dataset.description}</p>
                  </div>
                  <Badge tone="neutral">{dataset.resolution}</Badge>
                </div>
                <dl className="mt-4 grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
                  {dataset.fields.map((field) => (
                    <div key={field.name} className="flex gap-2">
                      <dt className="shrink-0 font-mono text-accent">{field.name}</dt>
                      <dd className="text-muted">{field.description}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-line pt-2 text-xs">
                  <code className="break-all font-mono text-faint">{dataset.endpoint}</code>
                  <a
                    href={dataset.documentation_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-accent hover:underline"
                  >
                    Elexon documentation
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                </div>
              </article>
            ))}
          </div>
          <Notice tone="info" title="Resolution mismatch">
            {metadata.resolution.explanation} The API returns {metadata.resolution.forecast} forecasts
            and {metadata.resolution.actual} outturn; comparison is {metadata.resolution.comparison}.
          </Notice>
        </MethodSection>

        <MethodSection
          id="cutoff"
          title="Decision cut-off"
          description="A forecast is only usable if it was published by the moment a procurement decision had to be made. The cut-off is therefore part of the query, not a display detail."
        >
          <div className="rounded-sm border border-line bg-panel p-4">
            <p className="text-sm leading-6 text-ink">{metadata.cutoff.rule}</p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted">
              <span>
                Default mode: <span className="text-ink">{metadata.cutoff.default_mode}</span>
              </span>
              <span>
                Default time: <span className="text-ink">{metadata.cutoff.default_time_local}</span>
              </span>
              <span>
                Time zone: <span className="text-ink">{metadata.cutoff.timezone}</span>
              </span>
            </div>
            <p className="mt-3 border-t border-line pt-3 text-xs leading-5 text-muted">
              {metadata.cutoff.reference}{" "}
              <a
                href={metadata.cutoff.reference_url}
                target="_blank"
                rel="noreferrer"
                className="link"
              >
                EPEX SPOT reference
              </a>
              .
            </p>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded-sm border border-line bg-panel p-4">
              <h3 className="text-xs font-semibold text-ink">Daily D-1 mode</h3>
              <p className="mt-1.5 text-xs leading-5 text-muted">
                For each delivery day D, resolve the configured London time on D-1. Different delivery
                days can therefore use different publication versions. This is the default because it
                mirrors a repeated day-ahead decision process.
              </p>
            </div>
            <div className="rounded-sm border border-line bg-panel p-4">
              <h3 className="text-xs font-semibold text-ink">Fixed timestamp mode</h3>
              <p className="mt-1.5 text-xs leading-5 text-muted">
                One cut-off applies to every interval. It must precede the first delivery interval;
                otherwise the API rejects the query. This mode is useful for auditing a specific
                historical decision or a non-standard gate closure.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-sm border border-line bg-panel p-4">
            <h3 className="text-xs font-semibold text-ink">Configurable alternatives</h3>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-muted">
              {metadata.cutoff.alternatives.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mt-2 text-xs leading-5 text-faint">
              The default is a modelling choice, not a claim that 09:20 is the client's only procurement
              deadline. Change the time or switch to a fixed cut-off to test sensitivity.
            </p>
          </div>

          <div className="mt-4">
            <Notice tone="warn" title="Decision-date ambiguity">
              “January 2026 decisions” is not the same as “delivery in January 2026”. A delivery on 1
              January uses a cut-off on 31 December 2025. The default window (1–31 January delivery)
              includes decisions made from 31 December through 30 January. If the requirement is
              decisions made during January, include delivery through 1 February so the 31 January
              cut-off is represented. The tool does not infer which definition is intended; the selected
              delivery window and cut-off are shown explicitly.
            </Notice>
          </div>

          <p className="mt-3 text-xs leading-5 text-faint">
            Cut-offs are resolved in Europe/London on each calendar day and stored as UTC. The UTC offset
            changes across daylight-saving transitions; the expected interval count follows the actual
            London-day length (23 or 25 hours on transition days).
          </p>
        </MethodSection>

        <MethodSection
          id="selection"
          title="Forecast eligibility and selection"
          description="Selection is deterministic and uses only information available at the cut-off."
        >
          <ol className="space-y-3">
            {[
              "Normalise the WINDFOR delivery start to UTC and consider only records whose startTime exactly equals the hourly delivery timestamp.",
              "Keep records whose publishTime is at or before the decision cut-off and strictly before the delivery hour.",
              "Select the latest publishTime among eligible records. A record published after the cut-off is never used, even if it is closer to delivery.",
              "Collapse exact duplicates. If several eligible values share the winning publishTime, use the highest generation value as a deterministic tie-break and flag the interval.",
              "If no eligible record exists, mark the interval missing and count it in coverage. Do not borrow a later publication or substitute a prior day's value.",
              "Record the selected publication, cut-off, lead time, eligible version count and previous eligible publication for auditability.",
            ].map((step, index) => (
              <li key={step} className="flex gap-3 text-xs leading-5 text-muted">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded border border-line-strong text-[10px] font-semibold text-accent">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ol>
          <p className="mt-3 rounded border border-line bg-panel px-3 py-2 text-xs leading-5 text-faint">
            The Elexon query is filtered by publication time. Because WINDFOR has no delivery-date filter,
            the backend derives a conservative publication window from the first and last cut-offs.
          </p>
        </MethodSection>

        <MethodSection
          id="matching"
          title="Matching, units and arithmetic"
          description="The forecast and outturn populations differ in resolution; the comparison is deliberately hourly."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-sm border border-line bg-panel p-4">
              <h3 className="text-xs font-semibold text-ink">Hourly outturn</h3>
              <p className="mt-1.5 text-xs leading-5 text-muted">
                FUELHH WIND is half-hourly average MW. For the hour beginning at HH:00, the actual is the
                arithmetic mean of the :00 and :30 readings. If either half-hour is missing or invalid,
                the hour is unavailable; it is not averaged from one reading.
              </p>
            </div>
            <div className="rounded-sm border border-line bg-panel p-4">
              <h3 className="text-xs font-semibold text-ink">Units</h3>
              <p className="mt-1.5 text-xs leading-5 text-muted">{metadata.units.generation}.</p>
              <p className="mt-1.5 text-xs leading-5 text-muted">{metadata.units.note}</p>
              <p className="mt-1.5 text-xs text-faint">{metadata.units.energy}</p>
            </div>
          </div>
          <div className="relative mt-4 overflow-x-auto rounded-sm border border-line">
            <table className="w-full min-w-[560px] border-collapse text-xs">
              <caption className="sr-only">Comparison arithmetic</caption>
              <thead>
                <tr className="border-b border-line bg-raised/30 text-left">
                  <th scope="col" className="px-3 py-2 font-semibold text-faint">Quantity</th>
                  <th scope="col" className="px-3 py-2 font-semibold text-faint">Definition</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Delivery interval", "One hour, keyed by its start timestamp in UTC."],
                  ["Forecast", "Selected WINDFOR hourly value at that delivery hour, in MW."],
                  ["Outturn", "Mean of the two FUELHH WIND half-hourly average-MW values, in MW."],
                  ["Signed error", "forecast − outturn, in MW."],
                  ["Absolute error", "|forecast − outturn|, in MW."],
                  ["Squared error", "(forecast − outturn)², in MW²."],
                  ["APE", "|forecast − outturn| / |outturn|, only when outturn ≥ 1 MW."],
                ].map(([term, definition]) => (
                  <tr key={term} className="border-b border-line/70 last:border-b-0">
                    <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-medium text-ink">
                      {term}
                    </th>
                    <td className="px-3 py-2 text-muted">{definition}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </MethodSection>

        <MethodSection
          id="metrics"
          title="Metrics and zero handling"
          description="All metrics come from the API and use the same valid hourly pairs. Coverage is reported separately and is never labelled accuracy."
        >
          <dl className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {metadata.metric_definitions.map((definition) => (
              <div key={definition.key} className="rounded-sm border border-line bg-panel p-4">
                <dt className="text-xs font-semibold text-ink">{definition.label}</dt>
                <dd className="mt-1 font-mono text-[10px] leading-4 text-accent">{definition.formula}</dd>
                <dd className="mt-1.5 text-xs leading-5 text-muted">{definition.interpretation}</dd>
                <dd className="mt-1 text-[10px] uppercase tracking-[0.08em] text-faint">
                  Unit: {definition.unit}
                </dd>
              </div>
            ))}
          </dl>
          <Notice tone="info" title="MAPE denominator floor">
            MAPE is calculated only where the actual hourly outturn is at least 1 MW. Pairs below the
            floor remain in MAE, RMSE and MBE but are excluded from MAPE and counted in the API response.
            Percentage error is unstable near zero and is not a substitute for MW-based metrics.
          </Notice>
        </MethodSection>

        <MethodSection
          id="quality"
          title="Data-quality rules"
          description="These rules are applied server-side before any metric is calculated."
        >
          <div className="relative overflow-x-auto rounded-sm border border-line">
            <table className="w-full min-w-[620px] border-collapse text-xs">
              <caption className="sr-only">Data quality handling rules</caption>
              <thead>
                <tr className="border-b border-line bg-raised/30 text-left">
                  <th scope="col" className="px-3 py-2 font-semibold text-faint">Topic</th>
                  <th scope="col" className="px-3 py-2 font-semibold text-faint">Handling</th>
                </tr>
              </thead>
              <tbody>
                {metadata.data_quality_rules.map((rule) => (
                  <tr key={rule.topic} className="border-b border-line/70 last:border-b-0">
                    <th scope="row" className="whitespace-nowrap px-3 py-2 text-left font-medium text-ink">
                      {rule.topic}
                    </th>
                    <td className="px-3 py-2 text-muted">{rule.handling}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </MethodSection>

        <MethodSection
          id="limitations"
          title="Limitations and interpretation"
          description="These are material to how the numbers should be used."
        >
          <ul className="space-y-2.5">
            {metadata.limitations.map((limitation) => (
              <li key={limitation} className="flex gap-2 text-xs leading-5 text-muted">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-warn" aria-hidden="true" />
                {limitation}
              </li>
            ))}
          </ul>
          <div className="mt-4">
            <Notice tone="warn" title="Observed positive bias is not corrected">
              In live January 2026 validation, selected WINDFOR values were persistently above FUELHH
              WIND outturn. This can reflect forecast error, the different wind-farm populations visible
              to NESO versus transmission-connected FUELHH, or both. The application applies no
              adjustment, scaling or bias correction; MBE makes the direction and magnitude visible.
            </Notice>
          </div>
        </MethodSection>

        <MethodSection
          id="reproducibility"
          title="Reproducibility and API"
          description="The browser never calls Elexon directly. All calculations are reproducible through the backend API."
        >
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-sm border border-line bg-panel p-4">
              <div className="flex items-center gap-2">
                <FileJson className="h-4 w-4 text-accent" aria-hidden="true" />
                <h3 className="text-xs font-semibold text-ink">Endpoints</h3>
              </div>
              <dl className="mt-3 space-y-1.5 font-mono text-xs">
                {[
                  ["GET /api/health", "Dependency and cache status"],
                  ["GET /api/metadata", "Methodology and dataset metadata"],
                  ["GET /api/forecasts", "Selected forecast versions"],
                  ["GET /api/comparison", "Hourly pairs and half-hour outturn"],
                  ["GET /api/metrics", "Aggregate metrics and histogram"],
                  ["GET /api/accuracy/daily", "Daily metric breakdown"],
                ].map(([endpoint, purpose]) => (
                  <div key={endpoint} className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-4">
                    <dt className="text-accent">{endpoint}</dt>
                    <dd className="text-muted">{purpose}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-3 border-t border-line pt-2 text-xs leading-5 text-muted">
                Swagger UI is served by the backend at <code className="text-ink">/docs</code>. The
                deployed frontend proxies <code className="text-ink">/api</code> to the backend service.
              </p>
            </div>

            <div className="rounded-sm border border-line bg-panel p-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-accent" aria-hidden="true" />
                <h3 className="text-xs font-semibold text-ink">Query parameters</h3>
              </div>
              <dl className="mt-3 space-y-2 text-xs leading-5">
                <div>
                  <dt className="font-mono text-accent">from_date</dt>
                  <dd className="text-muted">First delivery date, YYYY-MM-DD, London calendar.</dd>
                </div>
                <div>
                  <dt className="font-mono text-accent">to_date</dt>
                  <dd className="text-muted">Last delivery date, YYYY-MM-DD. Maximum range {metadata.max_range_days} days.</dd>
                </div>
                <div>
                  <dt className="font-mono text-accent">cutoff_mode</dt>
                  <dd className="text-muted">daily or fixed.</dd>
                </div>
                <div>
                  <dt className="font-mono text-accent">cutoff_time</dt>
                  <dd className="text-muted">HH:MM, Europe/London, used in daily mode.</dd>
                </div>
                <div>
                  <dt className="font-mono text-accent">cutoff_datetime</dt>
                  <dd className="text-muted">Local ISO datetime for fixed mode; must precede the first delivery interval.</dd>
                </div>
              </dl>
              <p className="mt-3 border-t border-line pt-2 text-xs leading-5 text-muted">
                Input validation failures return structured JSON with a stable error code and optional
                request ID. Upstream failures do not expose stack traces.
              </p>
            </div>
          </div>

          {metadata.is_synthetic ? (
            <div className="mt-4">
              <Notice tone="warn" title="Fixture mode is synthetic">
                This deployment is serving generated fixture records, not Elexon observations. Fixtures
                include deliberate missing values, duplicate publications and zero/near-zero actuals to
                exercise the data-quality path. Every response carries <code>is_synthetic=true</code>,
                and the UI labels it.
              </Notice>
            </div>
          ) : (
            <p className="mt-4 text-xs leading-5 text-faint">
              This deployment is in live mode. Upstream data can be revised; actual outturn uses the
              latest available FUELHH publication for each interval. Results may therefore differ from
              reports generated at an earlier time.
            </p>
          )}
        </MethodSection>
      </div>
    </div>
  );
}

export function MethodologyPage() {
  const { metadata, metadataLoading, metadataError, reloadMetadata } = useAppData();

  return (
    <div className="space-y-6">
      <PageHeader
        title="What the numbers mean, and what they do not"
        description="Definitions, decision-time selection rules, resolution handling, data-quality controls and limitations for this wind forecast analytics prototype."
      />

      {metadataLoading && !metadata ? (
        <PageSkeleton charts={0} />
      ) : metadataError && !metadata ? (
        <ErrorState
          error={metadataError}
          onRetry={reloadMetadata}
          title="Methodology metadata could not be loaded"
        />
      ) : metadata ? (
        <MethodContent metadata={metadata} />
      ) : null}
    </div>
  );
}
