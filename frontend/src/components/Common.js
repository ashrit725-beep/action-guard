import { useState } from "react";
import { AlertCircle, Check, Copy, HelpCircle, Info, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, copyText } from "@/lib/utils";
import { compactNumber } from "@/lib/format";

export const PageHeader = ({ title, description, actions, className, testId }) => (
  <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between", className)}>
    <div className="min-w-0">
      <h1
        className="font-display text-[23px] font-bold tracking-tight text-foreground sm:text-[26px]"
        data-testid={testId}
      >
        {title}
      </h1>
      {description ? (
        <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</p>
      ) : null}
    </div>
    {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
  </div>
);

/**
 * Plain-language "what am I looking at?" panel.
 * Every console page starts with one so a non-technical person is never lost.
 */
export const Explainer = ({ title, children, points, className, testId }) => (
  <section className={cn("vx-explainer", className)} data-testid={testId || "page-explainer"}>
    <div className="flex items-start gap-2.5">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
      <div className="min-w-0">
        {title ? (
          <p className="font-display text-sm font-semibold text-foreground">{title}</p>
        ) : null}
        {children ? (
          <div className="mt-1 text-sm leading-relaxed text-foreground/80">{children}</div>
        ) : null}
        {points?.length ? (
          <ul className="mt-2 space-y-1">
            {points.map((point) => (
              <li key={point} className="flex items-start gap-2 text-sm leading-relaxed text-foreground/80">
                <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-primary/70" />
                <span>{point}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  </section>
);

/** A small "?" that explains a term in one sentence. */
export const HelpTip = ({ text, className, testId }) => (
  <TooltipProvider delayDuration={120}>
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label="What does this mean?"
          className={cn(
            "inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-primary",
            className,
          )}
          data-testid={testId || "help-tip"}
          onClick={(e) => e.preventDefault()}
        >
          <HelpCircle className="h-[15px] w-[15px]" />
        </button>
      </TooltipTrigger>
      <TooltipContent className="max-w-[280px] text-xs leading-relaxed">{text}</TooltipContent>
    </Tooltip>
  </TooltipProvider>
);

export const MetricCard = ({
  label,
  value,
  hint,
  icon: Icon,
  tone = "default",
  testId,
  onClick,
  help,
}) => {
  const tones = {
    default: "text-foreground",
    primary: "text-primary",
    allow: "text-[hsl(var(--status-allow))]",
    approval: "text-[hsl(var(--status-approval))]",
    block: "text-[hsl(var(--status-block))]",
  };
  /* The card can be clickable and can also carry a "?" tip. A <button> inside a
     <button> is invalid HTML, so a clickable card is a keyboard-operable div. */
  const clickable = Boolean(onClick);
  const interaction = clickable
    ? {
        role: "button",
        tabIndex: 0,
        onClick,
        onKeyDown: (event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onClick(event);
          }
        },
      }
    : {};
  return (
    <div
      {...interaction}
      className={cn(
        "vx-card w-full p-4 text-left sm:p-5",
        clickable &&
          "vx-card-hover cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
      )}
      data-testid={testId || "dashboard-metric-card"}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="vx-label flex items-center gap-1.5">
          {label}
          {help ? <HelpTip text={help} /> : null}
        </span>
        {Icon ? <Icon className={cn("h-4 w-4 shrink-0", tones[tone])} /> : null}
      </div>
      <div
        className={cn(
          "mt-3 font-display text-[30px] font-bold leading-none tracking-tight",
          tones[tone],
        )}
      >
        {typeof value === "number" ? compactNumber(value) : value}
      </div>
      {hint ? <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{hint}</p> : null}
    </div>
  );
};

/** Standard titled card used across every page for consistent rhythm. */
export const SectionCard = ({
  title,
  description,
  icon: Icon,
  actions,
  children,
  className,
  bodyClassName,
  testId,
}) => (
  <section className={cn("vx-card", className)} data-testid={testId}>
    {title || actions ? (
      <header className="flex flex-col gap-3 border-b border-border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-start gap-2.5">
          {Icon ? (
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Icon className="h-4 w-4" />
            </span>
          ) : null}
          <div className="min-w-0">
            <h2 className="font-display text-[15px] font-semibold text-foreground">{title}</h2>
            {description ? (
              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
            ) : null}
          </div>
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </header>
    ) : null}
    <div className={cn("px-5 py-4", bodyClassName)}>{children}</div>
  </section>
);

/** Circular score dial (0-100) used by the Security page. */
export const ScoreRing = ({ value = 0, label, size = 132, testId }) => {
  const clamped = Math.max(0, Math.min(100, Number(value) || 0));
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamped / 100) * circumference;
  const tone =
    clamped >= 80
      ? "hsl(var(--status-allow))"
      : clamped >= 55
        ? "hsl(var(--status-approval))"
        : "hsl(var(--status-block))";
  return (
    <div className="flex flex-col items-center" data-testid={testId || "score-ring"}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--muted))"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={tone}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 600ms cubic-bezier(0.22, 1, 0.36, 1)" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-display text-[30px] font-bold leading-none text-foreground">
            {clamped}
          </span>
          <span className="vx-label mt-1 text-[10px]">out of 100</span>
        </div>
      </div>
      {label ? <p className="mt-2 text-sm font-medium text-foreground">{label}</p> : null}
    </div>
  );
};

/** Numbered how-to steps, used by the Guide and empty states. */
export const NumberedSteps = ({ steps = [], className, testId }) => (
  <ol className={cn("space-y-4", className)} data-testid={testId || "numbered-steps"}>
    {steps.map((step, index) => (
      <li key={step.title} className="flex gap-3.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/12 font-display text-[13px] font-bold text-primary">
          {index + 1}
        </span>
        <div className="min-w-0 pt-0.5">
          <p className="font-display text-sm font-semibold text-foreground">{step.title}</p>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
          {step.action ? <div className="mt-2.5">{step.action}</div> : null}
        </div>
      </li>
    ))}
  </ol>
);

export const EmptyState = ({ icon: Icon, title, description, action, className, testId }) => (
  <div
    className={cn(
      "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/50 px-6 py-14 text-center",
      className,
    )}
    data-testid={testId || "empty-state"}
  >
    {Icon ? (
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
        <Icon className="h-5 w-5 text-primary" />
      </span>
    ) : null}
    <h3 className="font-display text-base font-semibold text-foreground">{title}</h3>
    {description ? (
      <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{description}</p>
    ) : null}
    {action ? <div className="mt-5 flex flex-wrap justify-center gap-2">{action}</div> : null}
  </div>
);

export const ErrorState = ({ message, onRetry, className }) => (
  <div
    className={cn("vx-card flex flex-col items-center gap-3 p-8 text-center", className)}
    data-testid="error-state"
  >
    <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[hsl(var(--status-block)/0.12)]">
      <AlertCircle className="h-5 w-5 text-[hsl(var(--status-block))]" />
    </span>
    <p className="text-sm text-foreground">{message || "We could not load this yet."}</p>
    {onRetry ? (
      <Button variant="outline" size="sm" onClick={onRetry} data-testid="error-retry-button">
        Try again
      </Button>
    ) : null}
  </div>
);

export const TableSkeleton = ({ rows = 6, cols = 5 }) => (
  <div className="space-y-2 p-4" data-testid="loading-skeleton">
    {Array.from({ length: rows }).map((_, r) => (
      <div key={r} className="flex gap-3">
        {Array.from({ length: cols }).map((__, c) => (
          <Skeleton key={c} className={cn("h-8 flex-1", c === 0 && "max-w-[220px]")} />
        ))}
      </div>
    ))}
  </div>
);

export const CardSkeleton = ({ count = 4, className }) => (
  <div
    className={cn("grid gap-4 sm:grid-cols-2 lg:grid-cols-4", className)}
    data-testid="loading-skeleton"
  >
    {Array.from({ length: count }).map((_, i) => (
      <Skeleton key={i} className="h-[116px] rounded-xl" />
    ))}
  </div>
);

export const Spinner = ({ className, label }) => (
  <div
    className={cn("flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground", className)}
  >
    <Loader2 className="h-4 w-4 animate-spin" />
    {label || "Loading…"}
  </div>
);

export const Mono = ({ children, className }) => (
  <span className={cn("vx-mono text-xs text-muted-foreground", className)}>{children}</span>
);

export const KeyValue = ({ label, children, className, testId, help }) => (
  <div className={cn("flex flex-col gap-1", className)}>
    <span className="vx-label flex items-center gap-1.5">
      {label}
      {help ? <HelpTip text={help} /> : null}
    </span>
    <div className="text-sm text-foreground" data-testid={testId}>
      {children}
    </div>
  </div>
);

export const CopyButton = ({ value, label = "Copy", size = "sm", variant = "outline", className, testId }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    const ok = await copyText(value);
    if (ok) {
      setCopied(true);
      toast.success("Copied");
      setTimeout(() => setCopied(false), 1600);
    } else {
      toast.error("Could not copy. Select the text and copy manually.");
    }
  };
  return (
    <Button
      type="button"
      size={size}
      variant={variant}
      onClick={copy}
      className={className}
      data-testid={testId || "copy-button"}
    >
      {copied ? <Check className="mr-1.5 h-3.5 w-3.5" /> : <Copy className="mr-1.5 h-3.5 w-3.5" />}
      {copied ? "Copied" : label}
    </Button>
  );
};

export const CodeBlock = ({ code, language = "bash", className, testId, copyable = true }) => (
  <div className={cn("relative", className)}>
    <pre
      className="vx-panel overflow-x-auto p-4 pr-24 vx-mono text-[12px] leading-relaxed text-foreground/90"
      data-testid={testId || "code-block"}
      data-language={language}
    >
      <code>{code}</code>
    </pre>
    {copyable ? (
      <CopyButton
        value={code}
        className="absolute right-2.5 top-2.5"
        testId={`${testId || "code-block"}-copy`}
      />
    ) : null}
  </div>
);

export const SimulatedTag = ({ className, label = "Test only" }) => (
  <span
    className={cn(
      "vx-chip border-[hsl(var(--risk-medium)/0.4)] bg-[hsl(var(--risk-medium)/0.12)] uppercase tracking-[0.1em] text-[hsl(var(--risk-medium))]",
      className,
    )}
    data-testid="simulated-tag"
  >
    {label}
  </span>
);
