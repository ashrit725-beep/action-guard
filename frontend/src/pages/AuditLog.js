import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, FileCheck2, Search, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { EmptyState, ErrorState, KeyValue, PageHeader, TableSkeleton } from "@/components/Common";
import { DecisionBadge, RiskBadge } from "@/components/StatusBadges";
import { DecisionTrace } from "@/components/DecisionTrace";
import { api, errorMessage } from "@/lib/api";
import { fullDate, money, shortTime, timeAgo } from "@/lib/format";

const FILTERS = [
  { value: "all", label: "Everything" },
  { value: "allowed", label: "Allowed" },
  { value: "blocked", label: "Blocked" },
  { value: "approval", label: "Needed your OK" },
  { value: "high_risk", label: "Risky" },
  { value: "simulated", label: "Practice runs" },
  { value: "api", label: "From real agents" },
];

const LIMIT = 25;

export default function AuditLog() {
  const [params, setParams] = useSearchParams();
  const [filter, setFilter] = useState(params.get("filter") || "all");
  const [search, setSearch] = useState("");
  const [agentId, setAgentId] = useState(params.get("agent") || "");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0, counts: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data: payload } = await api.get("/audit", {
        params: {
          filter,
          search: search || undefined,
          agent_id: agentId || undefined,
          page,
          limit: LIMIT,
        },
      });
      setData(payload);
    } catch (err) {
      setError(errorMessage(err, "Could not load the audit log."));
    } finally {
      setLoading(false);
    }
  }, [filter, search, agentId, page]);

  useEffect(() => {
    const id = setTimeout(load, search ? 280 : 0);
    return () => clearTimeout(id);
  }, [load, search]);

  useEffect(() => {
    setPage(1);
  }, [filter, search, agentId]);

  useEffect(() => {
    const next = new URLSearchParams(params);
    if (filter === "all") next.delete("filter");
    else next.set("filter", filter);
    setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const openEvent = async (event) => {
    setSelected(event);
    setDetail(null);
    try {
      const { data: payload } = await api.get(`/audit/${event.audit_id}`);
      setDetail(payload);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load that event."));
    }
  };

  const verify = async () => {
    setVerifying(true);
    try {
      const { data: payload } = await api.get("/audit/verify");
      if (payload.intact) {
        toast.success("Audit trail intact", {
          description: `${payload.verified} of ${payload.checked} recent events match their integrity hash.`,
        });
      } else {
        toast.error("Integrity check failed", {
          description: `${payload.tampered.length} event(s) do not match their hash.`,
        });
      }
    } catch (err) {
      toast.error(errorMessage(err, "Verification failed."));
    } finally {
      setVerifying(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil((data.total || 0) / LIMIT));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit log"
        description="Every authorization decision and approval, append-only and sealed with an integrity hash."
        testId="audit-heading"
        actions={
          <Button variant="outline" onClick={verify} disabled={verifying} data-testid="verify-audit-button">
            <FileCheck2 className="mr-1.5 h-4 w-4" />
            {verifying ? "Verifying…" : "Verify integrity"}
          </Button>
        }
      />

      {agentId ? (
        <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm">
          <span className="text-muted-foreground">Filtered to agent</span>
          <span className="vx-mono text-xs">{agentId}</span>
          <Button variant="ghost" size="sm" onClick={() => setAgentId("")} data-testid="clear-agent-filter">
            Clear
          </Button>
        </div>
      ) : null}

      <div className="flex flex-col gap-3">
        <Tabs value={filter} onValueChange={setFilter}>
          <TabsList className="w-full justify-start overflow-x-auto" data-testid="audit-filter-tabs">
            {FILTERS.map((f) => (
              <TabsTrigger key={f.value} value={f.value} data-testid={`audit-filter-${f.value}`}>
                {f.label}
                {data.counts?.[f.value] ? (
                  <span className="vx-mono ml-1.5 text-[10px] opacity-60">{data.counts[f.value]}</span>
                ) : null}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search agent, permission, resource, reason, policy or audit ID…"
            className="pl-9"
            data-testid="audit-search-input"
          />
        </div>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : loading ? (
        <div className="vx-card">
          <TableSkeleton rows={8} cols={6} />
        </div>
      ) : data.items.length === 0 ? (
        <EmptyState
          icon={ShieldCheck}
          title={search || filter !== "all" ? "Nothing matches that" : "Nothing recorded yet"}
          description="Every action an agent attempts is written down here. Try an action, or connect a real agent, and records will start appearing."
          action={
            <Button asChild data-testid="audit-empty-cta">
              <Link to="/app/try">Try an action</Link>
            </Button>
          }
        />
      ) : (
        <div className="vx-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] border-collapse text-sm" data-testid="audit-table">
              <thead className="vx-sticky-head">
                <tr className="border-b border-border text-left">
                  <th className="px-4 py-3 vx-label">Timestamp</th>
                  <th className="px-4 py-3 vx-label">Agent</th>
                  <th className="px-4 py-3 vx-label">Permission</th>
                  <th className="px-4 py-3 vx-label">Resource</th>
                  <th className="px-4 py-3 vx-label">Amount</th>
                  <th className="px-4 py-3 vx-label">Decision</th>
                  <th className="px-4 py-3 vx-label">Risk</th>
                  <th className="px-4 py-3 vx-label">Reason</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((e) => (
                  <tr
                    key={e.audit_id}
                    className="vx-row-link border-b border-border last:border-0"
                    onClick={() => openEvent(e)}
                    data-testid="audit-row"
                  >
                    <td className="whitespace-nowrap px-4 py-3">
                      <div className="vx-mono text-xs text-foreground">{shortTime(e.created_at)}</div>
                      <div className="text-[10px] text-muted-foreground">{timeAgo(e.created_at)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="max-w-[160px] truncate font-medium text-foreground">{e.agent_name}</div>
                      <div className="vx-mono text-[10px] text-muted-foreground">{e.agent_id}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="vx-mono text-xs">{e.permission_key}</span>
                      {e.event_type === "approval" ? (
                        <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                          approval decision
                        </div>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <span className="vx-mono max-w-[160px] truncate text-xs text-muted-foreground">
                        {e.resource_id || "—"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <span className="vx-mono text-xs">{money(e.amount, e.currency) || "—"}</span>
                    </td>
                    <td className="px-4 py-3">
                      <DecisionBadge decision={e.decision} compact />
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge risk={e.risk} />
                    </td>
                    <td className="max-w-[300px] px-4 py-3">
                      <span className="line-clamp-2 text-xs text-muted-foreground">{e.reason}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border px-4 py-2.5">
            <span className="text-xs text-muted-foreground">
              Page {page} of {totalPages} · {data.total} event{data.total === 1 ? "" : "s"}
            </span>
            <div className="flex gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                data-testid="audit-prev-page"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                data-testid="audit-next-page"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}

      <Sheet open={Boolean(selected)} onOpenChange={() => setSelected(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-[560px]">
          <SheetHeader>
            <SheetTitle className="font-display">Audit event</SheetTitle>
          </SheetHeader>
          {selected ? (
            <div className="mt-5 space-y-5" data-testid="audit-detail-panel">
              <div className="flex flex-wrap items-center gap-2">
                <DecisionBadge decision={selected.decision} />
                <RiskBadge risk={selected.risk} score={selected.risk_score} />
                {detail?.event?.integrity_verified ? (
                  <span className="vx-chip border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]">
                    <ShieldCheck className="h-3.5 w-3.5" /> Integrity verified
                  </span>
                ) : null}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <KeyValue label="Audit ID">
                  <span className="vx-mono text-xs">{selected.audit_id}</span>
                </KeyValue>
                <KeyValue label="Timestamp">
                  <span className="text-xs">{fullDate(selected.created_at)}</span>
                </KeyValue>
                <KeyValue label="Agent">
                  <Link to={`/app/agents/${selected.agent_id}`} className="text-primary hover:underline">
                    {selected.agent_name}
                  </Link>
                </KeyValue>
                <KeyValue label="Agent ID">
                  <span className="vx-mono text-xs">{selected.agent_id}</span>
                </KeyValue>
                <KeyValue label="Requested permission">
                  <span className="vx-mono text-xs">{selected.permission_key}</span>
                </KeyValue>
                <KeyValue label="Resource">
                  <span className="vx-mono text-xs">{selected.resource_id || "—"}</span>
                </KeyValue>
                <KeyValue label="Amount">{money(selected.amount, selected.currency) || "—"}</KeyValue>
                <KeyValue label="Policy">
                  <span className="text-xs">{selected.policy || "—"}</span>
                </KeyValue>
                <KeyValue label="Source">
                  <span className="text-xs">
                    {selected.source}
                    {selected.simulated ? " (simulated)" : ""}
                  </span>
                </KeyValue>
                <KeyValue label="Approval">
                  <span className="text-xs">{selected.approval_status || "not required"}</span>
                </KeyValue>
              </div>

              <div>
                <p className="vx-label mb-2">Result</p>
                <p className="text-sm leading-relaxed text-foreground/85">{selected.reason}</p>
                <p className="vx-mono mt-2 text-[10px] text-muted-foreground">code: {selected.reason_code}</p>
              </div>

              {detail?.approval ? (
                <div className="vx-panel p-4">
                  <p className="vx-label">Linked approval</p>
                  <p className="mt-1.5 text-sm text-foreground">
                    {detail.approval.status} by {detail.approval.decided_by_email || "—"}
                  </p>
                  {detail.approval.note ? (
                    <p className="mt-1 text-xs italic text-muted-foreground">“{detail.approval.note}”</p>
                  ) : null}
                </div>
              ) : null}

              <div>
                <p className="vx-label mb-2">Evaluation trace</p>
                <DecisionTrace trace={selected.trace} dense />
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}
