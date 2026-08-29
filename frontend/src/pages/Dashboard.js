import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  CheckCircle2,
  Wand2,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardSkeleton, ErrorState, EmptyState, MetricCard, PageHeader, TableSkeleton } from "@/components/Common";
import { DecisionBadge, RiskBadge, SeverityBadge } from "@/components/StatusBadges";
import { api, errorMessage } from "@/lib/api";
import { money, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const RISK_ROWS = [
  { key: "LOW", label: "Low risk", cls: "text-foreground" },
  { key: "MEDIUM", label: "Medium risk", cls: "text-[hsl(var(--risk-medium))]" },
  { key: "HIGH", label: "High risk", cls: "text-[hsl(var(--risk-high))]" },
  { key: "CRITICAL", label: "Very high risk", cls: "text-[hsl(var(--risk-critical))]" },
];

const ONBOARDING_STEPS = [
  {
    title: "Add your first agent",
    body: "Pick from over 10,000 ready-made agents, already set up safely.",
    to: "/app/agents",
    cta: "Browse the library",
    icon: Bot,
  },
  {
    title: "See a decision happen",
    body: "Try an action and watch Vexen allow it, pause it, or refuse it.",
    to: "/app/try",
    cta: "Try an action",
    icon: Wand2,
  },
  {
    title: "Read the two-minute guide",
    body: "Everything you need to know, in plain English.",
    to: "/app/guide",
    cta: "Open the guide",
    icon: BookOpen,
  },
];

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const res = await api.get("/dashboard");
      setData(res.data);
    } catch (err) {
      setError(errorMessage(err, "Could not load your security overview."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 30000);
    return () => clearInterval(id);
  }, [load]);

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" description="Loading your agent security posture…" />
        <CardSkeleton />
        <div className="vx-card">
          <TableSkeleton />
        </div>
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const m = data.metrics;
  const protectedNow = data.security_status === "Protected";
  const totalRisk = RISK_ROWS.reduce((sum, r) => sum + (data.risk_overview?.[r.key] || 0), 0) || 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome back, ${(data.user?.name || "").split(" ")[0] || "there"}`}
        description="Here is what your AI agents have been up to. Vexen checks every single thing they try to do."
        testId="dashboard-heading"
        actions={
          <>
            <Button variant="outline" asChild data-testid="dashboard-view-agents">
              <Link to="/app/agents">
                <Bot className="mr-1.5 h-4 w-4" /> My agents
              </Link>
            </Button>
            <Button asChild data-testid="dashboard-try-action">
              <Link to="/app/try">
                <Wand2 className="mr-1.5 h-4 w-4" /> Try an action
              </Link>
            </Button>
          </>
        }
      />

      {/* Security status */}
      <section
        className={cn(
          "vx-card flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6",
          protectedNow
            ? "border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.06)]"
            : "border-[hsl(var(--status-approval)/0.4)] bg-[hsl(var(--status-approval)/0.06)]",
        )}
        data-testid="security-status-panel"
      >
        <div className="flex items-start gap-4">
          <span
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border",
              protectedNow
                ? "border-[hsl(var(--status-allow)/0.4)] bg-[hsl(var(--status-allow)/0.12)]"
                : "border-[hsl(var(--status-approval)/0.4)] bg-[hsl(var(--status-approval)/0.12)]",
            )}
          >
            {protectedNow ? (
              <ShieldCheck className="h-5 w-5 text-[hsl(var(--status-allow))]" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-[hsl(var(--status-approval))]" />
            )}
          </span>
          <div>
            <p className="vx-label">How things stand</p>
            <h2
              className={cn(
                "mt-1 font-display text-2xl font-semibold tracking-tight",
                protectedNow ? "text-[hsl(var(--status-allow))]" : "text-[hsl(var(--status-approval))]",
              )}
              data-testid="security-status-value"
            >
              {data.security_status}
            </h2>
            <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">{data.status_detail}</p>
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-start gap-2 sm:items-end">
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <span className="vx-pulse-dot h-1.5 w-1.5 rounded-full bg-[hsl(var(--status-allow))]" />
            Watching {m.total_agents} agent{m.total_agents === 1 ? "" : "s"}
          </span>
          <Button variant="outline" size="sm" asChild data-testid="dashboard-open-security">
            <Link to="/app/security">
              Run a safety check <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
            </Link>
          </Button>
        </div>
      </section>

      {/* First-run guidance — shown until the workspace has an agent */}
      {m.total_agents === 0 ? (
        <section className="vx-card p-5 sm:p-6" data-testid="dashboard-onboarding">
          <h2 className="font-display text-lg font-bold tracking-tight text-foreground">
            Start here
          </h2>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Your workspace is empty, which means nothing can act on your behalf yet. Three short steps
            and you will see exactly how Vexen works.
          </p>
          <div className="mt-5 grid gap-3 md:grid-cols-3">
            {ONBOARDING_STEPS.map((step, index) => {
              const StepIcon = step.icon;
              return (
                <div
                  key={step.title}
                  className="flex flex-col rounded-xl border border-border bg-muted/40 p-4"
                  data-testid={`dashboard-onboarding-step-${index + 1}`}
                >
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/12 text-primary">
                    <StepIcon className="h-4 w-4" />
                  </span>
                  <p className="mt-3 font-display text-sm font-semibold text-foreground">
                    {index + 1}. {step.title}
                  </p>
                  <p className="mt-1.5 flex-1 text-xs leading-relaxed text-muted-foreground">
                    {step.body}
                  </p>
                  <Button asChild size="sm" variant="outline" className="mt-3.5">
                    <Link to={step.to}>
                      {step.cta}
                      <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {/* Metrics */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Agents switched on"
          value={m.active_agents}
          hint={`${m.total_agents} in this workspace altogether`}
          icon={Bot}
          help="An agent that is switched off has every request refused, instantly."
          testId="metric-active-agents"
          onClick={() => navigate("/app/agents")}
        />
        <MetricCard
          label="Things tried today"
          value={m.actions_today}
          hint={`${m.allowed_today} allowed · ${m.approval_today} waiting for you`}
          icon={Activity}
          testId="metric-actions-today"
          onClick={() => navigate("/app/audit")}
        />
        <MetricCard
          label="Stopped today"
          value={m.blocked_today}
          hint={`${m.total_blocked} stopped in total`}
          icon={ShieldX}
          tone="block"
          help="Things an agent asked to do that Vexen refused outright."
          testId="metric-blocked-actions"
          onClick={() => navigate("/app/audit?filter=blocked")}
        />
        <MetricCard
          label="Waiting for you"
          value={m.pending_approvals}
          hint={m.pending_approvals ? "Paused until you decide" : "Nothing waiting on you"}
          icon={ShieldAlert}
          tone={m.pending_approvals ? "approval" : "default"}
          testId="metric-pending-approvals"
          onClick={() => navigate("/app/approvals")}
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="vx-card p-5">
          <div className="flex items-center justify-between">
            <p className="vx-label">Spending Vexen stopped</p>
            <Wallet className="h-4 w-4 text-[hsl(var(--status-approval))]" />
          </div>
          <p
            className="mt-3 font-display text-[28px] font-semibold leading-none tracking-tight text-[hsl(var(--status-approval))]"
            data-testid="metric-spend-prevented"
          >
            {money(m.unauthorized_spend_prevented) || "$0"}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Money an agent tried to spend that Vexen refused or paused for your approval.
          </p>
        </div>
        <div className="vx-card p-5">
          <div className="flex items-center justify-between">
            <p className="vx-label">Spending you allowed</p>
            <CheckCircle2 className="h-4 w-4 text-[hsl(var(--status-allow))]" />
          </div>
          <p className="mt-3 font-display text-[28px] font-semibold leading-none tracking-tight text-foreground">
            {money(m.approved_spend) || "$0"}
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Money that went through — either inside the caps you set, or approved by you.
          </p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Live activity */}
        <section className="vx-card overflow-hidden" data-testid="live-activity-panel">
          <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
            <div>
              <h2 className="font-display text-[15px] font-semibold text-foreground">What just happened</h2>
              <p className="text-xs text-muted-foreground">The most recent things your agents tried</p>
            </div>
            <Button variant="ghost" size="sm" asChild data-testid="activity-view-all">
              <Link to="/app/audit">View all</Link>
            </Button>
          </div>
          {data.recent_activity?.length ? (
            <ul className="divide-y divide-border">
              {data.recent_activity.slice(0, 8).map((row) => (
                <li key={row.audit_id} className="flex items-center gap-3 px-5 py-3" data-testid="activity-row">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/app/agents/${row.agent_id}`}
                        className="truncate text-sm font-medium text-foreground hover:text-primary"
                      >
                        {row.agent_name}
                      </Link>
                      {row.simulated ? (
                        <span className="vx-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                          practice
                        </span>
                      ) : null}
                    </div>
                    <p className="vx-mono mt-0.5 truncate text-[11px] text-muted-foreground">
                      {row.permission_key}
                      {row.amount ? ` · ${money(row.amount)}` : ""}
                      {row.event_type === "approval" ? " · approval decision" : ""}
                    </p>
                  </div>
                  <span className="vx-mono hidden shrink-0 text-[10px] text-muted-foreground sm:block">
                    {timeAgo(row.created_at)}
                  </span>
                  <DecisionBadge decision={row.decision} compact />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              className="m-5 border-0"
              icon={Activity}
              title="Nothing has happened yet"
              description="Try an action to see how Vexen decides, or connect a real agent with a key. Every decision shows up here straight away."
              action={
                <Button asChild data-testid="activity-empty-cta">
                  <Link to="/app/try">
                    <Wand2 className="mr-1.5 h-4 w-4" /> Try an action
                  </Link>
                </Button>
              }
            />
          )}
        </section>

        <div className="space-y-6">
          {/* Risk overview */}
          <section className="vx-card p-5" data-testid="risk-overview-panel">
            <h2 className="font-display text-[15px] font-semibold text-foreground">How risky your agents are</h2>
            <p className="text-xs text-muted-foreground">Based on what each one is allowed to do</p>
            <ul className="mt-4 space-y-3">
              {RISK_ROWS.map((r) => {
                const count = data.risk_overview?.[r.key] || 0;
                return (
                  <li key={r.key} data-testid={`risk-row-${r.key.toLowerCase()}`}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{r.label}</span>
                      <span className={cn("font-display font-semibold", r.cls)}>{count}</span>
                    </div>
                    <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all duration-500",
                          r.key === "LOW" && "bg-muted-foreground/60",
                          r.key === "MEDIUM" && "bg-[hsl(var(--risk-medium))]",
                          r.key === "HIGH" && "bg-[hsl(var(--risk-high))]",
                          r.key === "CRITICAL" && "bg-[hsl(var(--risk-critical))]",
                        )}
                        style={{ width: `${Math.round((count / totalRisk) * 100)}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>

          {/* Security events */}
          <section className="vx-card overflow-hidden" data-testid="security-events-panel">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <h2 className="font-display text-[15px] font-semibold text-foreground">Recently stopped or paused</h2>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/app/security">All</Link>
              </Button>
            </div>
            {data.security_events?.length ? (
              <ul className="divide-y divide-border">
                {data.security_events.slice(0, 5).map((e) => (
                  <li key={e.id} className="px-5 py-3" data-testid="security-event-row">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[13px] font-medium leading-snug text-foreground">{e.title}</p>
                      <SeverityBadge severity={e.severity} />
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">{e.description}</p>
                    <p className="vx-mono mt-1 text-[10px] text-muted-foreground">{timeAgo(e.created_at)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-5 py-8 text-center text-xs text-muted-foreground">
                No blocked actions or escalations recorded yet.
              </p>
            )}
          </section>

          {/* Findings */}
          {data.findings?.length ? (
            <section className="vx-card overflow-hidden" data-testid="findings-preview-panel">
              <div className="border-b border-border px-5 py-3.5">
                <h2 className="font-display text-[15px] font-semibold text-foreground">Worth your attention</h2>
              </div>
              <ul className="divide-y divide-border">
                {data.findings.map((f) => (
                  <li key={f.id} className="px-5 py-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-[13px] font-medium leading-snug text-foreground">{f.title}</p>
                      <SeverityBadge severity={f.severity} />
                    </div>
                    {f.agent_name ? (
                      <p className="vx-mono mt-1 text-[10px] text-muted-foreground">{f.agent_name}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
