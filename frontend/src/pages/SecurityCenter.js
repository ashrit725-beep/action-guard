import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  Bot,
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  Lock,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  CardSkeleton,
  EmptyState,
  ErrorState,
  Explainer,
  MetricCard,
  PageHeader,
  ScoreRing,
  SectionCard,
} from "@/components/Common";
import { RiskBadge, SeverityBadge } from "@/components/StatusBadges";
import { api, errorMessage } from "@/lib/api";
import { fullDate, money, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const SEVERITY_ORDER = ["critical", "high", "medium", "low"];

const POSTURE_COPY = {
  Protected: {
    headline: "Everything looks good",
    body: "Nothing needs your attention right now. Your agents are staying inside the limits you set.",
    tone: "allow",
  },
  "Needs attention": {
    headline: "A few things are worth tightening",
    body: "Nothing is broken, but some agents can reach further than they probably should.",
    tone: "approval",
  },
  "At risk": {
    headline: "Please look at this today",
    body: "One or more agents can reach something sensitive without a human checking first.",
    tone: "block",
  },
};

const TONE_RING = {
  allow: "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.07)]",
  approval: "border-[hsl(var(--status-approval)/0.3)] bg-[hsl(var(--status-approval)/0.07)]",
  block: "border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.07)]",
};

export default function SecurityCenter() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [integrity, setIntegrity] = useState(null);
  const [checking, setChecking] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data: payload } = await api.get("/security");
      setData(payload);
    } catch (err) {
      setError(errorMessage(err, "Could not run the safety check."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const verify = async () => {
    setChecking(true);
    try {
      const { data: payload } = await api.get("/audit/verify");
      setIntegrity(payload);
      if (payload.intact) {
        toast.success("Your history is intact", {
          description: `${payload.verified} records checked, none altered.`,
        });
      } else {
        toast.error(`${payload.tampered.length} record(s) look altered`);
      }
    } catch (err) {
      toast.error(errorMessage(err, "Could not check your history."));
    } finally {
      setChecking(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Safety check" testId="security-center-header" />
        <CardSkeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Safety check" testId="security-center-header" />
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const severity = data?.counts?.by_severity || {};
  const findings = [...(data?.findings || [])].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity),
  );
  const posture = POSTURE_COPY[data?.posture] || POSTURE_COPY.Protected;

  return (
    <div className="space-y-6" data-testid="security-center-page">
      <PageHeader
        title="Safety check"
        description="A plain-English look at how much your agents could actually do, and what is worth tightening."
        testId="security-center-header"
        actions={
          <Button variant="outline" onClick={load} data-testid="security-refresh-button">
            Run the check again
          </Button>
        }
      />

      <Explainer
        title="What this page is"
        points={[
          "Vexen looks at every agent you have and works out where you are exposed.",
          "Each item below tells you what it found, why it matters, and exactly what to do about it.",
          "Nothing here changes anything on its own — you stay in control.",
        ]}
        testId="security-explainer"
      />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,340px)_1fr]">
        <section
          className={cn("rounded-xl border p-5", TONE_RING[posture.tone])}
          data-testid="security-posture-card"
        >
          <div className="flex flex-col items-center">
            <ScoreRing value={data?.score || 0} testId="security-score-ring" />
            <p
              className="mt-3 font-display text-lg font-bold tracking-tight text-foreground"
              data-testid="security-posture-headline"
            >
              {posture.headline}
            </p>
            <p className="mt-1.5 text-center text-sm leading-relaxed text-muted-foreground">
              {posture.body}
            </p>
            <p className="mt-3 text-xs text-muted-foreground">
              Watching{" "}
              <span className="font-semibold text-foreground">{data?.counts?.agents || 0}</span>{" "}
              agents
            </p>
          </div>
        </section>

        <div className="grid gap-4 sm:grid-cols-2">
          <MetricCard
            label="Fix now"
            value={severity.critical || 0}
            tone="block"
            icon={ShieldAlert}
            hint="An agent could reach something sensitive without a person checking."
            testId="security-count-critical"
          />
          <MetricCard
            label="Important"
            value={severity.high || 0}
            tone="approval"
            icon={Activity}
            hint="Worth fixing soon — these widen what an agent can do."
            testId="security-count-high"
          />
          <MetricCard
            label="Worth a look"
            value={severity.medium || 0}
            icon={Sparkles}
            hint="Housekeeping. Tidying these reduces your risk over time."
            testId="security-count-medium"
          />
          <MetricCard
            label="Minor"
            value={severity.low || 0}
            icon={CheckCircle2}
            hint="Just so you know. Nothing is wrong."
            testId="security-count-low"
          />
        </div>
      </div>

      <SectionCard
        title="What we found"
        description={
          findings.length
            ? `${findings.length} thing${findings.length === 1 ? "" : "s"} to look at, most urgent first.`
            : "Nothing to report."
        }
        icon={ShieldCheck}
        testId="security-findings-card"
        bodyClassName={findings.length ? "px-5 py-4" : "p-0"}
      >
        {findings.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Nothing needs your attention"
            description="Every agent is inside the limits you set, and no sensitive permission is sitting unguarded. We will tell you the moment that changes."
            className="border-0"
            testId="security-findings-empty"
          />
        ) : (
          <ul className="space-y-3">
            {findings.map((finding) => (
              <li
                key={finding.id}
                className="rounded-xl border border-border bg-card p-4"
                data-testid="security-finding-item"
              >
                <div className="flex flex-wrap items-start justify-between gap-2.5">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={finding.severity} />
                      <span className="vx-label">{finding.category}</span>
                    </div>
                    <p className="mt-2 font-display text-[15px] font-semibold text-foreground">
                      {finding.title}
                    </p>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                      {finding.description}
                    </p>
                  </div>
                  {finding.agent_id ? (
                    <Button asChild variant="outline" size="sm" className="shrink-0">
                      <Link to={`/app/agents/${finding.agent_id}`}>Open this agent</Link>
                    </Button>
                  ) : null}
                </div>
                <div className="mt-3 rounded-lg border border-primary/20 bg-accent/50 p-3">
                  <p className="vx-label">What to do</p>
                  <p className="mt-1 text-sm leading-relaxed text-foreground/85">
                    {finding.recommendation}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard
          title="Agents with the most reach"
          description="These can do the most, so they deserve the most attention."
          icon={Bot}
          testId="security-high-risk-card"
          bodyClassName={data?.high_risk_agents?.length ? "px-5 py-4" : "p-0"}
        >
          {data?.high_risk_agents?.length ? (
            <ul className="space-y-2.5">
              {data.high_risk_agents.map((agent) => (
                <li
                  key={agent.agent_id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 p-3"
                  data-testid="security-high-risk-agent"
                >
                  <div className="min-w-0">
                    <Link
                      to={`/app/agents/${agent.agent_id}`}
                      className="font-display text-sm font-semibold text-foreground hover:text-primary"
                    >
                      {agent.name}
                    </Link>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {agent.permission_count || 0} permissions ·{" "}
                      {(agent.risk_factors || []).slice(0, 2).join("; ") || "Broad access"}
                    </p>
                  </div>
                  <RiskBadge risk={agent.risk} score={agent.risk_score} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              icon={ShieldCheck}
              title="No agent stands out as risky"
              description="Every agent is holding a narrow set of permissions. That is exactly what you want."
              className="border-0"
            />
          )}
        </SectionCard>

        <SectionCard
          title="Is my history trustworthy?"
          description="Every decision is stamped so tampering shows up."
          icon={Fingerprint}
          testId="security-integrity-card"
        >
          <p className="text-sm leading-relaxed text-muted-foreground">
            Each record in your History carries a fingerprint calculated from its contents. If anyone
            edited a record afterwards, the fingerprint would no longer match. Press the button and
            Vexen recalculates every fingerprint in front of you.
          </p>
          <Button
            onClick={verify}
            disabled={checking}
            className="mt-4"
            data-testid="security-verify-button"
          >
            <Lock className="mr-1.5 h-4 w-4" />
            {checking ? "Checking…" : "Check my history now"}
          </Button>

          {integrity ? (
            <div
              className={cn(
                "mt-4 rounded-xl border p-4",
                integrity.intact
                  ? "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.07)]"
                  : "border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.07)]",
              )}
              data-testid="security-integrity-result"
            >
              <div className="flex items-start gap-2.5">
                {integrity.intact ? (
                  <FileCheck2 className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--status-allow))]" />
                ) : (
                  <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--status-block))]" />
                )}
                <div>
                  <p className="font-display text-sm font-semibold text-foreground">
                    {integrity.intact
                      ? "Untouched. Every record matches its fingerprint."
                      : `${integrity.tampered.length} record(s) do not match.`}
                  </p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Checked {integrity.checked} record{integrity.checked === 1 ? "" : "s"} ·{" "}
                    {integrity.verified} verified
                  </p>
                </div>
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>

      <SectionCard
        title="Recently stopped"
        description="Things an agent tried that Vexen refused."
        icon={ShieldAlert}
        testId="security-blocked-card"
        bodyClassName="p-0"
      >
        {data?.recent_blocked?.length ? (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Agent</TableHead>
                  <TableHead>Tried to</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Why it was stopped</TableHead>
                  <TableHead className="text-right">When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.recent_blocked.map((row) => (
                  <TableRow key={row.audit_id} data-testid="security-blocked-row">
                    <TableCell className="whitespace-nowrap">
                      <Link
                        to={`/app/agents/${row.agent_id}`}
                        className="text-sm font-medium text-foreground hover:text-primary"
                      >
                        {row.agent_name}
                      </Link>
                    </TableCell>
                    <TableCell className="vx-mono whitespace-nowrap text-xs text-muted-foreground">
                      {row.permission_key || `${row.resource}.${row.action}`}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-sm">
                      {money(row.amount) || "—"}
                    </TableCell>
                    <TableCell className="max-w-[380px] text-xs leading-relaxed text-muted-foreground">
                      {row.reason}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right text-xs text-muted-foreground">
                      <span title={fullDate(row.created_at)}>{timeAgo(row.created_at)}</span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <EmptyState
            icon={ShieldCheck}
            title="Nothing has been stopped yet"
            description="When an agent asks for something it is not allowed to do, the attempt will show up here."
            className="border-0"
          />
        )}
      </SectionCard>
    </div>
  );
}
