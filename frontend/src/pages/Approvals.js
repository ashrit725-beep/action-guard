import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, ShieldAlert, ShieldCheck, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState, ErrorState, KeyValue, PageHeader, TableSkeleton } from "@/components/Common";
import { DecisionBadge, RiskBadge } from "@/components/StatusBadges";
import { api, errorMessage } from "@/lib/api";
import { fullDate, money, parseDate, shortTime, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

/** Has the one-use window on an approved request already closed? */
function approvalWindowClosed(approval) {
  if (approval.consumed_at) return false;
  const expires = parseDate(approval.expires_at);
  if (!expires) return false;
  return expires.getTime() <= Date.now();
}

export default function Approvals() {
  const [status, setStatus] = useState("pending");
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({ pending: 0, approved: 0, denied: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [decisionTarget, setDecisionTarget] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get("/approvals", { params: { status, limit: 100 } });
      setItems(data.items);
      setCounts(data.counts);
    } catch (err) {
      setError(errorMessage(err, "Could not load approval requests."));
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const decide = async () => {
    if (!decisionTarget) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/approvals/${decisionTarget.approval.id}/decision`, {
        decision: decisionTarget.decision,
        note: note.trim() || undefined,
      });
      const outcome = data.outcome?.decision;
      toast.success(
        decisionTarget.decision === "approved" ? "Approved" : "Denied",
        {
          description:
            outcome === "ALLOW"
              ? "The action was re-evaluated and allowed. It is in the audit log."
              : outcome === "BLOCK"
                ? "The action was blocked and recorded in the audit log."
                : "Recorded in the audit log.",
        },
      );
      setDecisionTarget(null);
      setNote("");
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not record that decision."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Actions Vexen paused because they crossed a limit, touched sensitive data, or matched a policy that requires a human."
        testId="approvals-heading"
      />

      <Tabs value={status} onValueChange={setStatus}>
        <TabsList data-testid="approvals-tabs">
          <TabsTrigger value="pending" data-testid="approvals-tab-pending">
            Pending {counts.pending ? `(${counts.pending})` : ""}
          </TabsTrigger>
          <TabsTrigger value="approved" data-testid="approvals-tab-approved">
            Approved {counts.approved ? `(${counts.approved})` : ""}
          </TabsTrigger>
          <TabsTrigger value="denied" data-testid="approvals-tab-denied">
            Denied {counts.denied ? `(${counts.denied})` : ""}
          </TabsTrigger>
          <TabsTrigger value="all" data-testid="approvals-tab-all">
            All
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : loading ? (
        <div className="vx-card">
          <TableSkeleton rows={4} cols={4} />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={status === "pending" ? ShieldCheck : ShieldAlert}
          title={status === "pending" ? "Nothing waiting on you" : `No ${status} requests`}
          description={
            status === "pending"
              ? "When an agent tries something that needs a human decision, it will appear here and the action stays blocked until you decide."
              : "Approval decisions you make are kept here and in the audit log."
          }
          action={
            status === "pending" ? (
              <Button asChild variant="outline" data-testid="approvals-empty-cta">
                <Link to="/app/try">See how a decision is made</Link>
              </Button>
            ) : null
          }
        />
      ) : (
        <div className="space-y-4">
          {items.map((a) => (
            <article key={a.id} className="vx-card p-5" data-testid="approval-card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Link
                      to={`/app/agents/${a.agent_id}`}
                      className="font-display text-base font-semibold text-foreground hover:text-primary"
                    >
                      {a.agent_name}
                    </Link>
                    <span className="vx-mono text-[10px] text-muted-foreground">{a.agent_id}</span>
                    {a.source === "simulator" ? (
                      <span className="vx-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                        practice
                      </span>
                    ) : null}
                  </div>
                  <p className="vx-mono mt-1 text-xs text-primary">{a.permission_key}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <RiskBadge risk={a.risk} score={a.risk_score} />
                  {a.status === "pending" ? (
                    <DecisionBadge decision="APPROVAL_REQUIRED" />
                  ) : (
                    <span
                      className={cn(
                        "vx-chip",
                        a.status === "approved"
                          ? "border-[hsl(var(--status-allow)/0.4)] bg-[hsl(var(--status-allow)/0.12)] text-[hsl(var(--status-allow))]"
                          : "border-[hsl(var(--status-block)/0.4)] bg-[hsl(var(--status-block)/0.12)] text-[hsl(var(--status-block))]",
                      )}
                      data-testid={`approval-status-${a.status}`}
                    >
                      {a.status === "approved" ? <Check className="h-3.5 w-3.5" /> : <X className="h-3.5 w-3.5" />}
                      {a.status}
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KeyValue label="Action">
                  <span className="vx-mono text-xs">
                    {a.resource}.{a.action}
                  </span>
                </KeyValue>
                <KeyValue label="Resource">
                  <span className="vx-mono text-xs">{a.resource_id || "—"}</span>
                </KeyValue>
                <KeyValue label="Amount">
                  <span className={a.amount ? "font-display text-base font-semibold" : ""}>
                    {money(a.amount, a.currency) || "—"}
                  </span>
                </KeyValue>
                <KeyValue label="Requested">
                  <span className="text-xs" title={fullDate(a.created_at)}>
                    {timeAgo(a.created_at)}
                  </span>
                </KeyValue>
              </div>

              <div className="mt-4 rounded-lg border border-border bg-muted/40 p-3">
                <p className="vx-label">Why Vexen paused this</p>
                <p className="mt-1.5 text-sm leading-relaxed text-foreground/85">{a.reason}</p>
                {a.effective_limit !== null && a.effective_limit !== undefined ? (
                  <p className="vx-mono mt-2 text-xs text-muted-foreground">
                    Configured limit {money(a.effective_limit)} · requested {money(a.amount)}
                  </p>
                ) : null}
                <p className="vx-mono mt-2 text-[10px] text-muted-foreground">Policy: {a.policy}</p>
              </div>

              {a.status === "pending" ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    onClick={() => setDecisionTarget({ approval: a, decision: "approved" })}
                    data-testid={`approve-button-${a.id}`}
                  >
                    <Check className="mr-1.5 h-4 w-4" /> Approve
                  </Button>
                  <Button
                    variant="outline"
                    className="border-[hsl(var(--status-block)/0.4)] text-[hsl(var(--status-block))]"
                    onClick={() => setDecisionTarget({ approval: a, decision: "denied" })}
                    data-testid={`deny-button-${a.id}`}
                  >
                    <X className="mr-1.5 h-4 w-4" /> Deny
                  </Button>
                  <Button variant="ghost" asChild>
                    <Link to={`/app/agents/${a.agent_id}`}>Inspect agent</Link>
                  </Button>
                </div>
              ) : (
                <div className="mt-4 space-y-1.5">
                  <p className="text-xs text-muted-foreground">
                    {a.status === "approved" ? "Approved" : "Denied"} by{" "}
                    <span className="text-foreground">{a.decided_by_email}</span> {timeAgo(a.decided_at)}
                    {a.note ? ` — “${a.note}”` : ""}
                  </p>
                  {a.status === "approved" ? (
                    <p
                      className="text-xs text-muted-foreground"
                      data-testid={`approval-usage-${a.id}`}
                    >
                      {a.consumed_at ? (
                        <>
                          The agent used this{" "}
                          <span className="text-foreground">{timeAgo(a.consumed_at)}</span>. It cannot
                          be used again.
                        </>
                      ) : approvalWindowClosed(a) ? (
                        <>
                          The agent never used it, and the{" "}
                          <span className="text-foreground">
                            {a.expires_at ? "time window has closed" : "approval has lapsed"}
                          </span>
                          . It would have to ask again.
                        </>
                      ) : (
                        <>
                          Waiting for the agent to act — good for{" "}
                          <span className="text-foreground">one</span> use until{" "}
                          <span className="text-foreground">{shortTime(a.expires_at)}</span>.
                        </>
                      )}
                    </p>
                  ) : null}
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      <Dialog open={Boolean(decisionTarget)} onOpenChange={() => setDecisionTarget(null)}>
        <DialogContent className="sm:max-w-[460px]">
          <DialogHeader>
            <DialogTitle className="font-display">
              {decisionTarget?.decision === "approved" ? "Approve this action?" : "Deny this action?"}
            </DialogTitle>
            <DialogDescription>
              {decisionTarget?.decision === "approved"
                ? "Vexen will re-run the request through the engine. Hard ceilings and DENY policies still apply."
                : "The agent's request will be blocked and recorded in the audit log."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="rounded-lg border border-border bg-muted/40 p-3">
              <p className="vx-mono text-xs text-foreground">{decisionTarget?.approval?.permission_key}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {decisionTarget?.approval?.agent_name}
                {decisionTarget?.approval?.amount ? ` · ${money(decisionTarget.approval.amount)}` : ""}
              </p>
            </div>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              maxLength={400}
              rows={3}
              placeholder="Optional note for the audit log…"
              data-testid="approval-note-input"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDecisionTarget(null)}>
              Cancel
            </Button>
            <Button
              onClick={decide}
              disabled={busy}
              className={
                decisionTarget?.decision === "denied"
                  ? "bg-[hsl(var(--status-block))] text-white hover:bg-[hsl(var(--status-block)/0.9)]"
                  : ""
              }
              data-testid="confirm-approval-decision"
            >
              {busy ? "Recording…" : decisionTarget?.decision === "approved" ? "Approve action" : "Deny action"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
