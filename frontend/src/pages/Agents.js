import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Bot,
  Check,
  ChevronLeft,
  ChevronRight,
  KeyRound,
  Library,
  MoreHorizontal,
  Plus,
  Search,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  EmptyState,
  ErrorState,
  Explainer,
  HelpTip,
  PageHeader,
  TableSkeleton,
} from "@/components/Common";
import { RiskBadge, StatusDot } from "@/components/StatusBadges";
import { api, errorMessage } from "@/lib/api";
import { compactNumber, money, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const LIBRARY_PAGE_SIZE = 24;
const AGENTS_PAGE_SIZE = 25;

/* ------------------------------------------------------------------ *
 * Agent library — 10,000+ ready-made agents, searched on the server.
 * ------------------------------------------------------------------ */
function AgentLibrary({ open, onOpenChange, onDeployed }) {
  const [data, setData] = useState(null);
  const [facets, setFacets] = useState({ categories: ["All"], industries: [], tiers: [] });
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [industry, setIndustry] = useState("All");
  const [tier, setTier] = useState("All");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(null);

  const fetchPage = useCallback(async () => {
    setLoading(true);
    try {
      const { data: payload } = await api.get("/catalog/templates", {
        params: {
          search: search.trim() || undefined,
          category,
          industry,
          tier,
          page,
          limit: LIBRARY_PAGE_SIZE,
        },
      });
      setData(payload);
      setFacets({
        categories: payload.categories || ["All"],
        industries: payload.industries || [],
        tiers: payload.tiers || [],
      });
    } catch (err) {
      toast.error(errorMessage(err, "Could not load the agent library."));
    } finally {
      setLoading(false);
    }
  }, [search, category, industry, tier, page]);

  useEffect(() => {
    if (!open) return undefined;
    const id = setTimeout(fetchPage, search ? 260 : 0);
    return () => clearTimeout(id);
  }, [open, fetchPage, search]);

  useEffect(() => {
    setPage(1);
  }, [search, category, industry, tier]);

  const deploy = async (template) => {
    setDeploying(template.id);
    try {
      const { data: agent } = await api.post("/agents", {
        name: template.name.slice(0, 60),
        template_id: template.id,
        description: template.tagline?.slice(0, 300),
      });
      toast.success(`${agent.name} is ready`, {
        description: `${agent.permission_count} permissions set up for you. You can change any of them.`,
      });
      onOpenChange(false);
      onDeployed(agent);
    } catch (err) {
      toast.error(errorMessage(err, "Could not add that agent."));
    } finally {
      setDeploying(null);
    }
  };

  const totalPages = data?.pages || 1;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] w-[calc(100vw-2rem)] max-w-6xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-5 py-4">
          <DialogTitle className="font-display">Pick a ready-made agent</DialogTitle>
          <DialogDescription>
            {data ? data.library_size.toLocaleString() : "10,000+"} agents, already set up safely. Choose
            the field you work in and how much freedom to give it. You can change everything
            afterwards.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-3 border-b border-border px-5 py-3 lg:grid-cols-[1.6fr_1fr_1fr_1fr]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search — try “email”, “invoice”, “nurse”…"
              className="pl-9"
              data-testid="template-search-input"
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger data-testid="template-category-select">
              <SelectValue placeholder="Any type of job" />
            </SelectTrigger>
            <SelectContent className="max-h-[320px]">
              {facets.categories.map((c) => (
                <SelectItem key={c} value={c}>
                  {c === "All" ? "Any type of job" : c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={industry} onValueChange={setIndustry}>
            <SelectTrigger data-testid="template-industry-select">
              <SelectValue placeholder="Every field" />
            </SelectTrigger>
            <SelectContent className="max-h-[320px]">
              {facets.industries.map((i) => (
                <SelectItem key={i.slug} value={i.slug}>
                  {i.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={tier} onValueChange={setTier}>
            <SelectTrigger data-testid="template-tier-select">
              <SelectValue placeholder="Any freedom level" />
            </SelectTrigger>
            <SelectContent className="max-h-[320px]">
              {facets.tiers.map((t) => (
                <SelectItem key={t.slug} value={t.slug}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <TableSkeleton rows={6} cols={3} />
          ) : !data?.items?.length ? (
            <EmptyState
              icon={Search}
              title="Nothing matches that"
              description="Try a simpler word, or clear the filters and browse."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearch("");
                    setCategory("All");
                    setIndustry("All");
                    setTier("All");
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {data.items.map((t) => (
                <div
                  key={t.id}
                  className="vx-card vx-card-hover flex flex-col p-4"
                  data-testid="template-card"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-display text-[14px] font-semibold leading-snug text-foreground">
                      {t.name}
                    </h3>
                    <span className="vx-mono shrink-0 text-[10px] text-muted-foreground">
                      {t.permission_count} rules
                    </span>
                  </div>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    <span className="vx-chip border-primary/25 bg-primary/10 text-primary">
                      {t.category}
                    </span>
                    {t.tier ? (
                      <span className="vx-chip border-border bg-muted text-muted-foreground">
                        {t.tier}
                      </span>
                    ) : (
                      <span className="vx-chip border-border bg-muted text-muted-foreground">
                        Popular
                      </span>
                    )}
                  </div>
                  <p className="mt-2.5 flex-1 text-xs leading-relaxed text-muted-foreground">
                    {t.tagline}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-1">
                    {t.grant_counts?.allow ? (
                      <span className="vx-chip border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]">
                        {t.grant_counts.allow} can do
                      </span>
                    ) : null}
                    {t.grant_counts?.limited ? (
                      <span className="vx-chip border-[hsl(var(--risk-medium)/0.3)] bg-[hsl(var(--risk-medium)/0.1)] text-[hsl(var(--risk-medium))]">
                        {t.grant_counts.limited} capped
                      </span>
                    ) : null}
                    {t.grant_counts?.approval ? (
                      <span className="vx-chip border-[hsl(var(--status-approval)/0.3)] bg-[hsl(var(--status-approval)/0.1)] text-[hsl(var(--status-approval))]">
                        {t.grant_counts.approval} ask first
                      </span>
                    ) : null}
                    {t.grant_counts?.blocked ? (
                      <span className="vx-chip border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.1)] text-[hsl(var(--status-block))]">
                        {t.grant_counts.blocked} never
                      </span>
                    ) : null}
                  </div>
                  {t.spend_cap ? (
                    <p className="mt-2 text-[11px] text-muted-foreground">
                      Can spend up to {money(t.spend_cap)} on its own
                    </p>
                  ) : null}
                  <Button
                    size="sm"
                    className="mt-3 w-full"
                    onClick={() => deploy(t)}
                    disabled={deploying === t.id}
                    data-testid={`deploy-template-${t.id}`}
                  >
                    {deploying === t.id ? "Adding…" : "Add this agent"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-5 py-3">
          <span className="text-xs text-muted-foreground" data-testid="template-result-count">
            {data ? `${data.total.toLocaleString()} matching agents` : "Loading…"}
            {data && data.total > 0 ? ` · page ${data.page} of ${totalPages.toLocaleString()}` : ""}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              data-testid="template-prev-page"
            >
              <ChevronLeft className="mr-1 h-3.5 w-3.5" /> Back
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages || loading}
              onClick={() => setPage((p) => p + 1)}
              data-testid="template-next-page"
            >
              More <ChevronRight className="ml-1 h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
function CreateAgentDialog({ open, onOpenChange, onCreated }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/agents", {
        name: name.trim(),
        description: description.trim() || undefined,
        template_id: "custom-agent",
      });
      toast.success(`${data.name} created`, {
        description: "It cannot do anything yet. Open it and switch on what it needs.",
      });
      setName("");
      setDescription("");
      onOpenChange(false);
      onCreated(data);
    } catch (err) {
      toast.error(errorMessage(err, "Could not create the agent."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[460px]">
        <DialogHeader>
          <DialogTitle className="font-display">Start from scratch</DialogTitle>
          <DialogDescription>
            Your agent begins able to do nothing at all. You then switch on exactly what it needs —
            the safest way to build one.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4" data-testid="create-agent-form">
          <div className="space-y-1.5">
            <Label htmlFor="agent-name">Give it a name</Label>
            <Input
              id="agent-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              minLength={2}
              maxLength={60}
              placeholder="e.g. My shopping helper"
              data-testid="create-agent-name-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="agent-description">
              What is it for? <span className="text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="agent-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={300}
              rows={3}
              placeholder="A note so you remember later."
              data-testid="create-agent-description-input"
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy} data-testid="create-agent-submit-button">
              {busy ? "Creating…" : "Create agent"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RenameDialog({ agent, onOpenChange, onSaved }) {
  const [name, setName] = useState(agent?.name || "");
  const [busy, setBusy] = useState(false);

  useEffect(() => setName(agent?.name || ""), [agent]);

  const save = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      await api.patch(`/agents/${agent.agent_id}`, { name: name.trim() });
      toast.success("Renamed");
      onOpenChange(false);
      onSaved();
    } catch (err) {
      toast.error(errorMessage(err, "Could not rename the agent."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={Boolean(agent)} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle className="font-display">Rename this agent</DialogTitle>
          <DialogDescription className="vx-mono text-xs">{agent?.agent_id}</DialogDescription>
        </DialogHeader>
        <form onSubmit={save} className="space-y-4">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            maxLength={60}
            data-testid="rename-agent-input"
          />
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={busy} data-testid="rename-agent-submit">
              Save
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
export default function Agents() {
  const navigate = useNavigate();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [risk, setRisk] = useState("all");
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [renaming, setRenaming] = useState(null);
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get("/agents", {
        params: {
          search: search || undefined,
          status,
          risk,
          page,
          limit: AGENTS_PAGE_SIZE,
        },
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(errorMessage(err, "Could not load your agents."));
    } finally {
      setLoading(false);
    }
  }, [search, status, risk, page]);

  useEffect(() => {
    const id = setTimeout(load, search ? 280 : 0);
    return () => clearTimeout(id);
  }, [load, search]);

  useEffect(() => {
    setPage(1);
  }, [search, status, risk]);

  const toggleStatus = async (agent) => {
    const next = agent.status === "active" ? "disabled" : "active";
    try {
      await api.patch(`/agents/${agent.agent_id}`, { status: next });
      toast.success(next === "active" ? "Switched on" : "Switched off", {
        description:
          next === "active"
            ? "This agent can ask to do things again."
            : "Everything this agent tries is now refused.",
      });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not change that agent."));
    }
  };

  const remove = async () => {
    if (!deleting) return;
    try {
      await api.delete(`/agents/${deleting.agent_id}`);
      toast.success("Agent deleted", { description: "Its history is kept, and cannot be edited." });
      setDeleting(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete the agent."));
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / AGENTS_PAGE_SIZE));
  const filtersOn = Boolean(search) || status !== "all" || risk !== "all";

  return (
    <div className="space-y-6" data-testid="agents-page">
      <PageHeader
        title="My agents"
        description="Each agent is one AI helper. Open one to see exactly what it is allowed to do."
        testId="agents-heading"
        actions={
          <>
            <Button
              variant="outline"
              onClick={() => setLibraryOpen(true)}
              data-testid="open-template-library-button"
            >
              <Library className="mr-1.5 h-4 w-4" /> Add from library
            </Button>
            <Button onClick={() => setCreateOpen(true)} data-testid="create-agent-button">
              <Plus className="mr-1.5 h-4 w-4" /> Start from scratch
            </Button>
          </>
        }
      />

      <Explainer
        title="What you are looking at"
        points={[
          "Every agent starts able to do nothing. What you see under Permissions is the complete list of what it can do.",
          "Switching an agent off stops it instantly — every request it makes is refused straight away.",
          "Our library has over 10,000 ready-made agents, already set up safely for different jobs and fields.",
        ]}
        testId="agents-explainer"
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search your agents by name…"
            className="pl-9"
            data-testid="agents-search-input"
          />
        </div>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="sm:w-[170px]" data-testid="agents-status-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">On and off</SelectItem>
            <SelectItem value="active">Switched on</SelectItem>
            <SelectItem value="disabled">Switched off</SelectItem>
          </SelectContent>
        </Select>
        <Select value={risk} onValueChange={setRisk}>
          <SelectTrigger className="sm:w-[180px]" data-testid="agents-risk-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Any risk level</SelectItem>
            <SelectItem value="low">Low risk</SelectItem>
            <SelectItem value="medium">Medium risk</SelectItem>
            <SelectItem value="high">High risk</SelectItem>
            <SelectItem value="critical">Very high risk</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {error ? (
        <ErrorState message={error} onRetry={load} />
      ) : loading ? (
        <div className="vx-card">
          <TableSkeleton rows={6} cols={6} />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bot}
          title={filtersOn ? "Nothing matches that" : "No agents yet"}
          description={
            filtersOn
              ? "Try clearing the search or filters."
              : "Pick one from our library of 10,000+ ready-made agents. Each one comes already set up safely, and you can change anything afterwards."
          }
          action={
            <Button onClick={() => setLibraryOpen(true)} data-testid="agents-empty-cta">
              <Library className="mr-1.5 h-4 w-4" /> Browse the library
            </Button>
          }
        />
      ) : (
        <div className="vx-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] border-collapse text-sm" data-testid="agents-table">
              <thead className="vx-sticky-head">
                <tr className="border-b border-border text-left">
                  <th className="vx-label px-4 py-3">Agent</th>
                  <th className="vx-label px-4 py-3">On or off</th>
                  <th className="vx-label px-4 py-3">
                    <span className="inline-flex items-center gap-1.5">
                      Risk
                      <HelpTip text="How much this agent could affect if something went wrong. Based on what it is allowed to do." />
                    </span>
                  </th>
                  <th className="vx-label px-4 py-3">Can do</th>
                  <th className="vx-label px-4 py-3">Last active</th>
                  <th className="vx-label px-4 py-3">
                    <span className="inline-flex items-center gap-1.5">
                      Key
                      <HelpTip text="Only needed if you connect your own software to this agent." />
                    </span>
                  </th>
                  <th className="w-10 px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {items.map((agent) => (
                  <tr
                    key={agent.agent_id}
                    className="vx-row-link border-b border-border last:border-0"
                    onClick={() => navigate(`/app/agents/${agent.agent_id}`)}
                    data-testid="agent-row"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground">{agent.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {agent.category || "Custom"}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusDot active={agent.status === "active"} />
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge risk={agent.risk} score={agent.risk_score} showScore={false} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-foreground">
                        {agent.permission_count}
                      </span>
                      <span className="ml-1 text-xs text-muted-foreground">things</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted-foreground">
                        {timeAgo(agent.last_activity_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "vx-chip",
                          agent.credential_status === "active"
                            ? "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]"
                            : "border-border bg-muted text-muted-foreground",
                        )}
                      >
                        <KeyRound className="h-3 w-3" />
                        {agent.credential_status === "active" ? "Connected" : "Not connected"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Actions for ${agent.name}`}
                            data-testid={`agent-actions-${agent.agent_id}`}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-52">
                          <DropdownMenuItem onClick={() => navigate(`/app/agents/${agent.agent_id}`)}>
                            Open this agent
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => setRenaming(agent)}
                            data-testid="agent-action-rename"
                          >
                            Rename
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => toggleStatus(agent)}
                            data-testid="agent-action-toggle"
                          >
                            {agent.status === "active" ? (
                              <>
                                <X className="mr-2 h-4 w-4" /> Switch off
                              </>
                            ) : (
                              <>
                                <Check className="mr-2 h-4 w-4" /> Switch on
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => setDeleting(agent)}
                            className="text-[hsl(var(--status-block))]"
                            data-testid="agent-action-delete"
                          >
                            <Trash2 className="mr-2 h-4 w-4" /> Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-4 py-2.5">
            <span className="text-xs text-muted-foreground" data-testid="agents-count">
              {compactNumber(total)} agent{total === 1 ? "" : "s"}
              {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
            </span>
            {totalPages > 1 ? (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  data-testid="agents-prev-page"
                >
                  <ChevronLeft className="mr-1 h-3.5 w-3.5" /> Back
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  data-testid="agents-next-page"
                >
                  Next <ChevronRight className="ml-1 h-3.5 w-3.5" />
                </Button>
              </div>
            ) : (
              <Link
                to="/app/guide"
                className="text-xs font-medium text-primary underline-offset-4 hover:underline"
              >
                What do these columns mean?
              </Link>
            )}
          </div>
        </div>
      )}

      <AgentLibrary
        open={libraryOpen}
        onOpenChange={setLibraryOpen}
        onDeployed={(agent) => navigate(`/app/agents/${agent.agent_id}`)}
      />
      <CreateAgentDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(agent) => navigate(`/app/agents/${agent.agent_id}`)}
      />
      <RenameDialog agent={renaming} onOpenChange={() => setRenaming(null)} onSaved={load} />

      <AlertDialog open={Boolean(deleting)} onOpenChange={() => setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">
              Delete {deleting?.name}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Its permissions, keys and anything waiting for your approval are removed. Its history
              stays, because history can never be edited or deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              onClick={remove}
              className="bg-[hsl(var(--status-block))] text-white hover:bg-[hsl(var(--status-block)/0.9)]"
              data-testid="confirm-delete-agent"
            >
              Delete agent
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
