import {
  AlertTriangle,
  CheckCircle2,
  CircleSlash,
  Minus,
  ShieldAlert,
  ShieldCheck,
  Siren,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { DECISION_PLAIN, GRANT_PLAIN, RISK_PLAIN, SEVERITY_PLAIN } from "@/lib/plain";

const DECISION_MAP = {
  ALLOW: {
    Icon: CheckCircle2,
    cls: "border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.12)] text-[hsl(var(--status-allow))]",
    testId: "decision-badge-allow",
  },
  APPROVAL_REQUIRED: {
    Icon: ShieldAlert,
    cls: "border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.12)] text-[hsl(var(--status-approval))]",
    testId: "decision-badge-approval-required",
  },
  BLOCK: {
    Icon: XCircle,
    cls: "border-[hsl(var(--status-block)/0.35)] bg-[hsl(var(--status-block)/0.12)] text-[hsl(var(--status-block))]",
    testId: "decision-badge-block",
  },
};

/** Allowed / Blocked / Needs your OK — the three words the whole product turns on. */
export const DecisionBadge = ({ decision, className, compact = false }) => {
  const cfg = DECISION_MAP[decision];
  const copy = DECISION_PLAIN[decision];
  if (!cfg || !copy) {
    return (
      <span className={cn("vx-chip border-border bg-muted text-muted-foreground", className)}>
        <Minus className="h-3 w-3" />
        Not decided yet
      </span>
    );
  }
  const { Icon } = cfg;
  return (
    <span
      className={cn("vx-chip whitespace-nowrap", cfg.cls, className)}
      data-testid={cfg.testId}
      title={copy.plain}
    >
      <Icon className="h-3.5 w-3.5" />
      {compact ? copy.short : copy.label}
    </span>
  );
};

const RISK_MAP = {
  LOW: { Icon: ShieldCheck, cls: "border-border bg-muted text-foreground/70", testId: "risk-badge-low" },
  MEDIUM: {
    Icon: TrendingUp,
    cls: "border-[hsl(var(--risk-medium)/0.35)] bg-[hsl(var(--risk-medium)/0.12)] text-[hsl(var(--risk-medium))]",
    testId: "risk-badge-medium",
  },
  HIGH: {
    Icon: AlertTriangle,
    cls: "border-[hsl(var(--risk-high)/0.35)] bg-[hsl(var(--risk-high)/0.12)] text-[hsl(var(--risk-high))]",
    testId: "risk-badge-high",
  },
  CRITICAL: {
    Icon: Siren,
    cls: "border-[hsl(var(--risk-critical)/0.4)] bg-[hsl(var(--risk-critical)/0.14)] text-[hsl(var(--risk-critical))]",
    testId: "risk-badge-critical",
  },
};

export const RiskBadge = ({ risk, score, className, showScore = true }) => {
  const key = RISK_MAP[risk] ? risk : "LOW";
  const cfg = RISK_MAP[key];
  const copy = RISK_PLAIN[key];
  const { Icon } = cfg;
  return (
    <span
      className={cn("vx-chip whitespace-nowrap", cfg.cls, className)}
      data-testid={cfg.testId}
      title={copy.plain}
    >
      <Icon className="h-3.5 w-3.5" />
      {copy.label}
      {showScore && typeof score === "number" ? (
        <span className="vx-mono opacity-70">{score}</span>
      ) : null}
    </span>
  );
};

const GRANT_MAP = {
  ALLOW: {
    cls: "border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.12)] text-[hsl(var(--status-allow))]",
    Icon: CheckCircle2,
  },
  LIMITED: {
    cls: "border-[hsl(var(--risk-medium)/0.35)] bg-[hsl(var(--risk-medium)/0.12)] text-[hsl(var(--risk-medium))]",
    Icon: TrendingUp,
  },
  APPROVAL_REQUIRED: {
    cls: "border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.12)] text-[hsl(var(--status-approval))]",
    Icon: ShieldAlert,
  },
  BLOCK: {
    cls: "border-[hsl(var(--status-block)/0.35)] bg-[hsl(var(--status-block)/0.12)] text-[hsl(var(--status-block))]",
    Icon: CircleSlash,
  },
};

/** How one permission is set on one agent: Always allowed / with a limit / ask me / never. */
export const GrantBadge = ({ decision, className }) => {
  const key = GRANT_MAP[decision] ? decision : "BLOCK";
  const cfg = GRANT_MAP[key];
  const copy = GRANT_PLAIN[key];
  const { Icon } = cfg;
  return (
    <span
      className={cn("vx-chip whitespace-nowrap", cfg.cls, className)}
      data-testid={`grant-badge-${key.toLowerCase()}`}
      title={copy.plain}
    >
      <Icon className="h-3.5 w-3.5" />
      {copy.label}
    </span>
  );
};

export const StatusDot = ({ active, label, className }) => (
  <span className={cn("inline-flex items-center gap-2 text-xs", className)}>
    <span
      className={cn(
        "h-1.5 w-1.5 rounded-full",
        active ? "bg-[hsl(var(--status-allow))] vx-pulse-dot" : "bg-muted-foreground/50",
      )}
    />
    <span className={active ? "text-foreground" : "text-muted-foreground"}>
      {label || (active ? "Switched on" : "Switched off")}
    </span>
  </span>
);

export const SeverityBadge = ({ severity, className }) => {
  const map = {
    critical:
      "border-[hsl(var(--risk-critical)/0.4)] bg-[hsl(var(--risk-critical)/0.14)] text-[hsl(var(--risk-critical))]",
    high: "border-[hsl(var(--risk-high)/0.35)] bg-[hsl(var(--risk-high)/0.12)] text-[hsl(var(--risk-high))]",
    medium:
      "border-[hsl(var(--risk-medium)/0.35)] bg-[hsl(var(--risk-medium)/0.12)] text-[hsl(var(--risk-medium))]",
    low: "border-border bg-muted text-muted-foreground",
  };
  const copy = SEVERITY_PLAIN[severity] || SEVERITY_PLAIN.low;
  return (
    <span
      className={cn("vx-chip", map[severity] || map.low, className)}
      data-testid={`severity-badge-${severity}`}
      title={copy.plain}
    >
      {copy.label}
    </span>
  );
};
