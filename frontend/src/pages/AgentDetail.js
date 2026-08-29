import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  Copy,
  Fingerprint,
  KeyRound,
  Pencil,
  Plus,
  Power,
  Scale,
  ScrollText,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  CodeBlock,
  EmptyState,
  ErrorState,
  KeyValue,
  PageHeader,
  TableSkeleton,
} from "@/components/Common";
import { DecisionBadge, GrantBadge, RiskBadge, StatusDot } from "@/components/StatusBadges";
import { DecisionTrace } from "@/components/DecisionTrace";
import { api, errorMessage } from "@/lib/api";
import { describeConstraints, fullDate, money, timeAgo } from "@/lib/format";
import { cn, copyText } from "@/lib/utils";

const DECISION_OPTIONS = [
  { value: "ALLOW", label: "Allowed", help: "The agent may do this without asking." },
  { value: "LIMITED", label: "Limited", help: "Allowed up to a maximum amount; above that it escalates." },
  { value: "APPROVAL_REQUIRED", label: "Approval required", help: "Always pauses for a human decision." },
  { value: "BLOCK", label: "Blocked", help: "Never allowed, no matter what." },
];

function GrantDialog({ open, onOpenChange, agentId, catalog, existingKeys, grant, onSaved }) {
  const editing = Boolean(grant);
  const [key, setKey] = useState(grant?.key || "");
  const [decision, setDecision] = useState(grant?.decision || "ALLOW");
  const [maxAmount, setMaxAmount] = useState(grant?.constraints?.max_amount ?? "");
  const [hardMax, setHardMax] = useState(grant?.constraints?.hard_max_amount ?? "");
  const [callsPerDay, setCallsPerDay] = useState(grant?.constraints?.max_calls_per_day ?? "");
  const [scope, setScope] = useState((grant?.constraints?.allowed_resources || []).join(", "));
  const [temporary, setTemporary] = useState(Boolean(grant?.expires_at));
  const [minutes, setMinutes] = useState(60);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    setKey(grant?.key || "");
    setDecision(grant?.decision || "ALLOW");
    setMaxAmount(grant?.constraints?.max_amount ?? "");
    setHardMax(grant?.constraints?.hard_max_amount ?? "");
    setCallsPerDay(grant?.constraints?.max_calls_per_day ?? "");
    setScope((grant?.constraints?.allowed_resources || []).join(", "));
    setTemporary(Boolean(grant?.expires_at));
    setMinutes(60);
  }, [open, grant]);

  const meta = useMemo(() => catalog.find((c) => c.key === key), [catalog, key]);
  const available = useMemo(
    () => catalog.filter((c) => editing || !existingKeys.includes(c.key)),
    [catalog, existingKeys, editing],
  );
  const grouped = useMemo(() => {
    const map = new Map();
    available.forEach((c) => {
      if (!map.has(c.category)) map.set(c.category, []);
      map.get(c.category).push(c);
    });
    return Array.from(map.entries());
  }, [available]);

  const submit = async (event) => {
    event.preventDefault();
    if (!key) {
      toast.error("Pick a permission first.");
      return;
    }
    const constraints = {};
    if (decision === "LIMITED") {
      const value = Number(maxAmount);
      if (!maxAmount || Number.isNaN(value) || value < 0) {
        toast.error("A limited grant needs a maximum amount.");
        return;
      }
      constraints.max_amount = value;
      constraints.approval_required_above = value;
      if (hardMax !== "" && !Number.isNaN(Number(hardMax))) {
        constraints.hard_max_amount = Number(hardMax);
      }
    }
    if (decision !== "BLOCK") {
      if (callsPerDay !== "" && Number(callsPerDay) > 0) {
        constraints.max_calls_per_day = Number(callsPerDay);
      }
      const patterns = scope
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      if (patterns.length) constraints.allowed_resources = patterns;
    }

    setBusy(true);
    try {
      if (editing) {
        await api.patch(`/agents/${agentId}/permissions/${grant.id}`, {
          decision,
          constraints,
          expires_in_minutes: temporary ? Number(minutes) || 60 : 0,
        });
        toast.success("Permission updated");
      } else {
        await api.post(`/agents/${agentId}/permissions`, {
          key,
          decision,
          constraints,
          expires_in_minutes: temporary ? Number(minutes) || 60 : undefined,
        });
        toast.success("Permission granted");
      }
      onOpenChange(false);
      onSaved();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save that permission."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[520px]">
        <DialogHeader>
          <DialogTitle className="font-display">{editing ? "Edit permission" : "Grant a permission"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Changes take effect on the next request this agent makes."
              : "Vexen denies everything by default. Only what you grant here becomes possible."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4" data-testid="grant-form">
          <div className="space-y-1.5">
            <Label>Permission</Label>
            {editing ? (
              <p className="vx-mono rounded-md border border-border bg-muted/50 px-3 py-2 text-sm">{key}</p>
            ) : (
              <Select value={key} onValueChange={setKey}>
                <SelectTrigger data-testid="grant-permission-select">
                  <SelectValue placeholder="Choose a permission" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {grouped.map(([category, rows]) => (
                    <div key={category}>
                      <p className="px-2 py-1.5 vx-label">{category}</p>
                      {rows.map((c) => (
                        <SelectItem key={c.key} value={c.key}>
                          <span className="vx-mono text-xs">{c.key}</span>
                          {c.sensitive ? (
                            <span className="ml-2 text-[10px] uppercase text-[hsl(var(--status-block))]">sensitive</span>
                          ) : null}
                        </SelectItem>
                      ))}
                    </div>
                  ))}
                </SelectContent>
              </Select>
            )}
            {meta ? (
              <p className="text-xs text-muted-foreground">
                {meta.description}
                {meta.sensitive ? " This is a sensitive resource — Vexen escalates or blocks it." : ""}
              </p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label>Decision</Label>
            <Select value={decision} onValueChange={setDecision}>
              <SelectTrigger data-testid="grant-decision-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DECISION_OPTIONS.filter((o) => o.value !== "LIMITED" || meta?.supports_amount).map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              {DECISION_OPTIONS.find((o) => o.value === decision)?.help}
            </p>
          </div>

          {decision === "LIMITED" && meta?.supports_amount ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="grant-max">Auto-approve up to (USD)</Label>
                <Input
                  id="grant-max"
                  type="number"
                  min="0"
                  step="1"
                  value={maxAmount}
                  onChange={(e) => setMaxAmount(e.target.value)}
                  placeholder="100"
                  data-testid="grant-max-amount-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="grant-hard">Hard ceiling (optional)</Label>
                <Input
                  id="grant-hard"
                  type="number"
                  min="0"
                  step="1"
                  value={hardMax}
                  onChange={(e) => setHardMax(e.target.value)}
                  placeholder="5000"
                  data-testid="grant-hard-max-input"
                />
              </div>
              <p className="col-span-full text-xs text-muted-foreground">
                Above the auto-approve amount Vexen asks a human. Above the hard ceiling nobody can approve it.
              </p>
            </div>
          ) : null}

          {decision !== "BLOCK" ? (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="grant-scope">Resource scope (comma separated globs)</Label>
                <Input
                  id="grant-scope"
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  placeholder="research/*, reports/2026-*"
                  data-testid="grant-scope-input"
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty for unrestricted resources. File permissions require an explicit scope by policy.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="grant-calls">Daily call limit (optional)</Label>
                <Input
                  id="grant-calls"
                  type="number"
                  min="1"
                  value={callsPerDay}
                  onChange={(e) => setCallsPerDay(e.target.value)}
                  placeholder="25"
                  data-testid="grant-calls-input"
                />
              </div>
              <div className="flex items-start justify-between gap-4 rounded-lg border border-border p-3">
                <div>
                  <Label htmlFor="grant-temp" className="cursor-pointer">
                    Temporary access
                  </Label>
                  <p className="mt-1 text-xs text-muted-foreground">
                    The grant expires automatically. Org policy caps file access at 60 minutes.
                  </p>
                </div>
                <Switch id="grant-temp" checked={temporary} onCheckedChange={setTemporary} data-testid="grant-temporary-switch" />
              </div>
              {temporary ? (
                <div className="space-y-1.5">
                  <Label htmlFor="grant-minutes">Expires in (minutes)</Label>
                  <Input
                    id="grant-minutes"
                    type="number"
                    min="1"
                    value={minutes}
                    onChange={(e) => setMinutes(e.target.value)}
                    data-testid="grant-minutes-input"
                  />
                </div>
              ) : null}
            </>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy} data-testid="grant-submit-button">
              {busy ? "Saving…" : editing ? "Save changes" : "Grant permission"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function IssueKeyDialog({ open, onOpenChange, agentId, onIssued }) {
  const [name, setName] = useState("Primary key");
  const [expires, setExpires] = useState("90");
  const [secret, setSecret] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open) {
      setSecret(null);
      setName("Primary key");
      setExpires("90");
      setCopied(false);
    }
  }, [open]);

  const issue = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post(`/agents/${agentId}/credentials`, {
        name: name.trim() || "Primary key",
        expires_in_days: expires === "never" ? undefined : Number(expires),
      });
      setSecret(data.secret);
      onIssued();
    } catch (err) {
      toast.error(errorMessage(err, "Could not issue a key."));
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    const ok = await copyText(secret);
    if (ok) {
      setCopied(true);
      toast.success("Key copied");
    } else {
      toast.error("Copy failed — select the key and copy manually.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle className="font-display">{secret ? "Your agent key" : "Issue an agent key"}</DialogTitle>
          <DialogDescription>
            {secret
              ? "This is the only time the full key is shown. Store it in your agent's secret manager."
              : "The key is hashed before storage. Vexen can never show it to you again."}
          </DialogDescription>
        </DialogHeader>

        {secret ? (
          <div className="space-y-4">
            <CodeBlock code={secret} testId="issued-key-value" />
            <div className="flex gap-2">
              <Button onClick={copy} className="flex-1" data-testid="copy-key-button">
                {copied ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                {copied ? "Copied" : "Copy key"}
              </Button>
              <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="close-key-dialog">
                Done
              </Button>
            </div>
            <p className="rounded-lg border border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.08)] px-3 py-2 text-xs text-foreground/85">
              Send it as the <span className="vx-mono">X-Vexen-Key</span> header to
              <span className="vx-mono"> POST /api/v1/authorize</span>.
            </p>
          </div>
        ) : (
          <form onSubmit={issue} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="key-name">Key name</Label>
              <Input id="key-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={60} data-testid="key-name-input" />
            </div>
            <div className="space-y-1.5">
              <Label>Expires</Label>
              <Select value={expires} onValueChange={setExpires}>
                <SelectTrigger data-testid="key-expiry-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">In 30 days</SelectItem>
                  <SelectItem value="90">In 90 days (recommended)</SelectItem>
                  <SelectItem value="365">In 1 year</SelectItem>
                  <SelectItem value="never">Never expires</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy} data-testid="issue-key-submit">
                {busy ? "Issuing…" : "Issue key"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

export default function AgentDetail() {
  const { agentId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [grantOpen, setGrantOpen] = useState(false);
  const [editingGrant, setEditingGrant] = useState(null);
  const [keyOpen, setKeyOpen] = useState(false);
  const [deletingGrant, setDeletingGrant] = useState(null);
  const [deleteAgentOpen, setDeleteAgentOpen] = useState(false);
  const [traceEvent, setTraceEvent] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data: payload } = await api.get(`/agents/${agentId}`);
      setData(payload);
    } catch (err) {
      setError(errorMessage(err, "That agent could not be loaded."));
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api
      .get("/catalog/permissions")
      .then(({ data: payload }) => setCatalog(payload.items))
      .catch(() => setCatalog([]));
  }, []);

  const toggleStatus = async () => {
    const next = data.agent.status === "active" ? "disabled" : "active";
    try {
      await api.patch(`/agents/${agentId}`, { status: next });
      toast.success(next === "active" ? "Agent enabled" : "Agent disabled");
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const removeGrant = async () => {
    try {
      await api.delete(`/agents/${agentId}/permissions/${deletingGrant.id}`);
      toast.success("Permission removed", { description: "The agent can no longer do this." });
      setDeletingGrant(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const revokeKey = async (credentialId) => {
    try {
      await api.delete(`/agents/${agentId}/credentials/${credentialId}`);
      toast.success("Key revoked", { description: "Requests using it are now rejected." });
      load();
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  const deleteAgent = async () => {
    try {
      await api.delete(`/agents/${agentId}`);
      toast.success("Agent deleted");
      navigate("/app/agents");
    } catch (err) {
      toast.error(errorMessage(err));
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Agent" description="Loading agent detail…" />
        <div className="vx-card">
          <TableSkeleton rows={8} cols={4} />
        </div>
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const agent = data.agent;
  const existingKeys = data.permissions.map((p) => p.key);
  const activeKeys = data.credentials.filter((c) => c.status === "active");

  return (
    <div className="space-y-6">
      <Link
        to="/app/agents"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        data-testid="back-to-agents"
      >
        <ArrowLeft className="h-4 w-4" /> All agents
      </Link>

      <PageHeader
        title={agent.name}
        description={agent.description || agent.template_name || "Custom agent"}
        testId="agent-detail-heading"
        actions={
          <>
            <Button variant="outline" onClick={toggleStatus} data-testid="agent-toggle-status">
              <Power className="mr-1.5 h-4 w-4" />
              {agent.status === "active" ? "Disable" : "Enable"}
            </Button>
            <Button variant="outline" onClick={() => setKeyOpen(true)} data-testid="agent-issue-key">
              <KeyRound className="mr-1.5 h-4 w-4" /> Issue key
            </Button>
            <Button
              onClick={() => {
                setEditingGrant(null);
                setGrantOpen(true);
              }}
              data-testid="agent-add-permission"
            >
              <Plus className="mr-1.5 h-4 w-4" /> Grant permission
            </Button>
          </>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="vx-card p-4">
          <p className="vx-label">Status</p>
          <div className="mt-2.5">
            <StatusDot active={agent.status === "active"} className="text-sm" />
          </div>
        </div>
        <div className="vx-card p-4">
          <p className="vx-label">Risk</p>
          <div className="mt-2.5">
            <RiskBadge risk={agent.risk} score={agent.risk_score} />
          </div>
        </div>
        <div className="vx-card p-4">
          <p className="vx-label">Last activity</p>
          <p className="mt-2 text-sm text-foreground">{timeAgo(agent.last_activity_at)}</p>
        </div>
        <div className="vx-card p-4">
          <p className="vx-label">Permissions</p>
          <p className="mt-2 text-sm text-foreground">
            <span className="font-display text-lg font-semibold">{agent.permission_count}</span>{" "}
            <span className="text-muted-foreground">active of {data.permissions.length} configured</span>
          </p>
        </div>
      </section>

      {agent.risk_factors?.length ? (
        <div className="vx-panel flex items-start gap-3 p-4">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--risk-high))]" />
          <div>
            <p className="text-sm font-medium text-foreground">Why this agent scores {agent.risk_score}/100</p>
            <ul className="mt-1.5 space-y-0.5 text-xs text-muted-foreground">
              {agent.risk_factors.map((f) => (
                <li key={f}>• {f}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <Tabs defaultValue="permissions">
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="permissions" data-testid="tab-permissions">
            Permissions
          </TabsTrigger>
          <TabsTrigger value="identity" data-testid="tab-identity">
            Identity
          </TabsTrigger>
          <TabsTrigger value="activity" data-testid="tab-activity">
            Activity
          </TabsTrigger>
          <TabsTrigger value="policies" data-testid="tab-policies">
            Policies
          </TabsTrigger>
        </TabsList>

        {/* PERMISSIONS */}
        <TabsContent value="permissions" className="mt-4">
          {data.permissions.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No permissions granted"
              description="This agent currently cannot do anything at all. Vexen blocks every request it makes."
              action={
                <Button
                  onClick={() => {
                    setEditingGrant(null);
                    setGrantOpen(true);
                  }}
                  data-testid="permissions-empty-cta"
                >
                  <Plus className="mr-1.5 h-4 w-4" /> Grant the first permission
                </Button>
              }
            />
          ) : (
            <div className="vx-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[820px] border-collapse text-sm" data-testid="permissions-table">
                  <thead className="vx-sticky-head">
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-3 vx-label">Permission</th>
                      <th className="px-4 py-3 vx-label">Decision</th>
                      <th className="px-4 py-3 vx-label">Restrictions</th>
                      <th className="w-24 px-4 py-3" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.permissions.map((p) => {
                      const bits = describeConstraints(p);
                      const expired = p.expires_at && new Date(p.expires_at) < new Date();
                      return (
                        <tr key={p.id} className="border-b border-border last:border-0" data-testid="permission-row">
                          <td className="px-4 py-3">
                            <div className="vx-mono text-xs text-foreground">{p.key}</div>
                            <div className="mt-0.5 text-xs text-muted-foreground">
                              {p.label}
                              {p.sensitive ? (
                                <span className="ml-2 text-[10px] uppercase tracking-wide text-[hsl(var(--status-block))]">
                                  sensitive
                                </span>
                              ) : null}
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <GrantBadge decision={p.decision} />
                            {expired ? (
                              <div className="mt-1 text-[10px] uppercase tracking-wide text-[hsl(var(--status-block))]">
                                expired
                              </div>
                            ) : null}
                          </td>
                          <td className="px-4 py-3">
                            {bits.length ? (
                              <ul className="space-y-0.5 text-xs text-muted-foreground">
                                {bits.map((b) => (
                                  <li key={b}>{b}</li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-xs text-muted-foreground">No extra restrictions</span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => {
                                  setEditingGrant(p);
                                  setGrantOpen(true);
                                }}
                                aria-label={`Edit ${p.key}`}
                                data-testid={`edit-permission-${p.key}`}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setDeletingGrant(p)}
                                aria-label={`Remove ${p.key}`}
                                data-testid={`delete-permission-${p.key}`}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </TabsContent>

        {/* IDENTITY */}
        <TabsContent value="identity" className="mt-4 space-y-4">
          <div className="vx-card p-5">
            <div className="flex items-center gap-2">
              <Fingerprint className="h-4 w-4 text-primary" />
              <h2 className="font-display text-[15px] font-semibold text-foreground">Agent identity</h2>
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KeyValue label="Agent ID" testId="identity-agent-id">
                <span className="vx-mono text-xs">{agent.agent_id}</span>
              </KeyValue>
              <KeyValue label="Owner">
                <span>{agent.owner_name || agent.owner_email}</span>
              </KeyValue>
              <KeyValue label="Created at">
                <span className="text-xs">{fullDate(agent.created_at)}</span>
              </KeyValue>
              <KeyValue label="Credential status" testId="identity-credential-status">
                <span
                  className={cn(
                    "vx-chip",
                    agent.credential_status === "active"
                      ? "border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]"
                      : "border-border bg-muted text-muted-foreground",
                  )}
                >
                  <KeyRound className="h-3 w-3" />
                  {agent.credential_status === "active"
                    ? `${activeKeys.length} active key${activeKeys.length === 1 ? "" : "s"}`
                    : agent.credential_status === "revoked"
                      ? "All keys revoked"
                      : "No key issued"}
                </span>
              </KeyValue>
            </div>
          </div>

          <div className="vx-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-5 py-3.5">
              <h2 className="font-display text-[15px] font-semibold text-foreground">API keys</h2>
              <Button size="sm" variant="outline" onClick={() => setKeyOpen(true)} data-testid="identity-issue-key">
                <KeyRound className="mr-1.5 h-3.5 w-3.5" /> Issue key
              </Button>
            </div>
            {data.credentials.length === 0 ? (
              <p className="px-5 py-8 text-center text-sm text-muted-foreground">
                No keys yet. Issue one to let a real agent call the authorization API.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.credentials.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-3 px-5 py-3" data-testid="credential-row">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">{c.name}</p>
                      <p className="vx-mono mt-0.5 text-xs text-muted-foreground">
                        {c.prefix}… · created {timeAgo(c.created_at)} · used {c.use_count || 0}×
                        {c.expires_at ? ` · expires ${timeAgo(c.expires_at)}` : " · no expiry"}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "vx-chip",
                        c.status === "active"
                          ? "border-[hsl(var(--status-allow)/0.35)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]"
                          : "border-border bg-muted text-muted-foreground",
                      )}
                    >
                      {c.status}
                    </span>
                    {c.status === "active" ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => revokeKey(c.id)}
                        data-testid={`revoke-key-${c.id}`}
                      >
                        Revoke
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="vx-card border-[hsl(var(--status-block)/0.3)] p-5">
            <h2 className="font-display text-[15px] font-semibold text-foreground">Delete this agent</h2>
            <p className="mt-1.5 text-sm text-muted-foreground">
              Permissions, keys and pending approvals are removed. Audit history is append-only and stays.
            </p>
            <Button
              variant="outline"
              className="mt-4 border-[hsl(var(--status-block)/0.4)] text-[hsl(var(--status-block))]"
              onClick={() => setDeleteAgentOpen(true)}
              data-testid="agent-delete-button"
            >
              <Trash2 className="mr-1.5 h-4 w-4" /> Delete agent
            </Button>
          </div>
        </TabsContent>

        {/* ACTIVITY */}
        <TabsContent value="activity" className="mt-4">
          {data.activity.length === 0 ? (
            <EmptyState
              icon={ScrollText}
              title="No activity yet"
              description="When this agent asks to do something — through the API or from the Try an action page — the decision shows up here."
              action={
                <Button asChild data-testid="activity-empty-simulator">
                  <Link to="/app/try">Try an action</Link>
                </Button>
              }
            />
          ) : (
            <div className="vx-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] border-collapse text-sm" data-testid="agent-activity-table">
                  <thead className="vx-sticky-head">
                    <tr className="border-b border-border text-left">
                      <th className="px-4 py-3 vx-label">When</th>
                      <th className="px-4 py-3 vx-label">Permission</th>
                      <th className="px-4 py-3 vx-label">Resource</th>
                      <th className="px-4 py-3 vx-label">Decision</th>
                      <th className="px-4 py-3 vx-label">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.activity.map((e) => (
                      <tr
                        key={e.audit_id}
                        className="vx-row-link border-b border-border last:border-0"
                        onClick={() => setTraceEvent(e)}
                        data-testid="agent-activity-row"
                      >
                        <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                          {timeAgo(e.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          <span className="vx-mono text-xs">{e.permission_key}</span>
                          {e.amount ? (
                            <span className="vx-mono ml-2 text-xs text-muted-foreground">{money(e.amount)}</span>
                          ) : null}
                        </td>
                        <td className="px-4 py-3">
                          <span className="vx-mono text-xs text-muted-foreground">{e.resource_id || "—"}</span>
                        </td>
                        <td className="px-4 py-3">
                          <DecisionBadge decision={e.decision} compact />
                        </td>
                        <td className="max-w-[280px] px-4 py-3">
                          <span className="line-clamp-2 text-xs text-muted-foreground">{e.reason}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
                Showing the latest {data.activity.length} events.{" "}
                <Link to={`/app/audit?agent=${agent.agent_id}`} className="text-primary hover:underline">
                  Open full audit log
                </Link>
              </div>
            </div>
          )}
        </TabsContent>

        {/* POLICIES */}
        <TabsContent value="policies" className="mt-4">
          {data.policies.length === 0 ? (
            <EmptyState icon={Scale} title="No policies affect this agent" description="Organization policies apply automatically once they match a granted permission." />
          ) : (
            <div className="space-y-3">
              {data.policies.map((p) => (
                <div key={p.id} className="vx-card p-4" data-testid="agent-policy-row">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="font-display text-[14px] font-semibold text-foreground">{p.name}</h3>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{p.description}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="vx-chip border-border bg-muted vx-mono">{p.effect}</span>
                      {p.system ? (
                        <span className="vx-chip border-primary/35 bg-primary/10 text-primary">baseline</span>
                      ) : null}
                      {!p.enabled ? (
                        <span className="vx-chip border-border bg-muted text-muted-foreground">disabled</span>
                      ) : null}
                    </div>
                  </div>
                  {p.affected_permissions?.length ? (
                    <div className="mt-3 flex flex-wrap gap-1">
                      {p.affected_permissions.map((k) => (
                        <span key={k} className="vx-chip border-border bg-muted vx-mono text-muted-foreground">
                          {k}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              <p className="text-center text-xs text-muted-foreground">
                <Link to="/app/policies" className="text-primary hover:underline">
                  Manage organization policies
                </Link>
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>

      <GrantDialog
        open={grantOpen}
        onOpenChange={setGrantOpen}
        agentId={agentId}
        catalog={catalog}
        existingKeys={existingKeys}
        grant={editingGrant}
        onSaved={load}
      />
      <IssueKeyDialog open={keyOpen} onOpenChange={setKeyOpen} agentId={agentId} onIssued={load} />

      <Sheet open={Boolean(traceEvent)} onOpenChange={() => setTraceEvent(null)}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-[540px]">
          <SheetHeader>
            <SheetTitle className="font-display">Decision detail</SheetTitle>
          </SheetHeader>
          {traceEvent ? (
            <div className="mt-5 space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <DecisionBadge decision={traceEvent.decision} />
                <RiskBadge risk={traceEvent.risk} score={traceEvent.risk_score} />
                <span className="vx-mono text-[10px] text-muted-foreground">{traceEvent.audit_id}</span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <KeyValue label="Permission">
                  <span className="vx-mono text-xs">{traceEvent.permission_key}</span>
                </KeyValue>
                <KeyValue label="Resource">
                  <span className="vx-mono text-xs">{traceEvent.resource_id || "—"}</span>
                </KeyValue>
                <KeyValue label="Amount">{money(traceEvent.amount) || "—"}</KeyValue>
                <KeyValue label="Policy">
                  <span className="text-xs">{traceEvent.policy || "—"}</span>
                </KeyValue>
                <KeyValue label="Source">
                  <span className="text-xs">{traceEvent.source}</span>
                </KeyValue>
                <KeyValue label="Time">
                  <span className="text-xs">{fullDate(traceEvent.created_at)}</span>
                </KeyValue>
              </div>
              <div>
                <p className="vx-label mb-2">Reason</p>
                <p className="text-sm leading-relaxed text-foreground/85">{traceEvent.reason}</p>
              </div>
              <div>
                <p className="vx-label mb-2">Evaluation trace</p>
                <DecisionTrace trace={traceEvent.trace} dense />
              </div>
            </div>
          ) : null}
        </SheetContent>
      </Sheet>

      <AlertDialog open={Boolean(deletingGrant)} onOpenChange={() => setDeletingGrant(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">Remove {deletingGrant?.key}?</AlertDialogTitle>
            <AlertDialogDescription>
              Once removed, requests for this permission are blocked by default deny.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={removeGrant} data-testid="confirm-delete-permission">
              Remove permission
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={deleteAgentOpen} onOpenChange={setDeleteAgentOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">Delete {agent.name}?</AlertDialogTitle>
            <AlertDialogDescription>This cannot be undone. Audit history is retained.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={deleteAgent} data-testid="confirm-delete-agent-detail">
              Delete agent
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
