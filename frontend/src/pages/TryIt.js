import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Sparkles,
  Wand2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  EmptyState,
  Explainer,
  KeyValue,
  PageHeader,
  SectionCard,
  SimulatedTag,
  Spinner,
} from "@/components/Common";
import { DecisionBadge, RiskBadge } from "@/components/StatusBadges";
import { DecisionTrace } from "@/components/DecisionTrace";
import { api, errorMessage } from "@/lib/api";
import { money } from "@/lib/format";
import { decisionPlain } from "@/lib/plain";
import { cn } from "@/lib/utils";

/** One-click things to try, so nobody stares at an empty form. */
const PRESETS = [
  { label: "Buy something for $250", key: "shopping.purchase", amount: 250, resourceId: "sku-8842" },
  { label: "Read my email", key: "email.read" },
  { label: "Look at saved card details", key: "payments.read" },
  { label: "Send an email", key: "email.send", resourceId: "alex@example.com" },
  { label: "Book a $1,200 flight", key: "travel.book", amount: 1200, resourceId: "flight-LHR-JFK" },
];

const DECISION_TONE = {
  ALLOW: "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.07)]",
  APPROVAL_REQUIRED: "border-[hsl(var(--status-approval)/0.3)] bg-[hsl(var(--status-approval)/0.07)]",
  BLOCK: "border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.07)]",
};

export default function TryIt() {
  const [agents, setAgents] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [agentId, setAgentId] = useState("");
  const [permissionKey, setPermissionKey] = useState("");
  const [resourceId, setResourceId] = useState("");
  const [amount, setAmount] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [showTrace, setShowTrace] = useState(false);

  const load = useCallback(async () => {
    try {
      const [agentsRes, catalogRes] = await Promise.all([
        api.get("/agents", { params: { limit: 200 } }),
        api.get("/catalog/permissions"),
      ]);
      const agentItems = agentsRes.data?.items || [];
      setAgents(agentItems);
      setPermissions(catalogRes.data?.items || []);
      if (agentItems.length) setAgentId(agentItems[0].agent_id);
    } catch (err) {
      toast.error(errorMessage(err, "Could not load your agents."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => {
    const map = new Map();
    permissions.forEach((p) => {
      if (!map.has(p.category)) map.set(p.category, []);
      map.get(p.category).push(p);
    });
    return Array.from(map.entries());
  }, [permissions]);

  const selectedPermission = useMemo(
    () => permissions.find((p) => p.key === permissionKey) || null,
    [permissions, permissionKey],
  );
  const selectedAgent = useMemo(
    () => agents.find((a) => a.agent_id === agentId) || null,
    [agents, agentId],
  );

  const availablePresets = useMemo(
    () => PRESETS.filter((preset) => permissions.some((p) => p.key === preset.key)),
    [permissions],
  );

  const run = async (override) => {
    const key = override?.key || permissionKey;
    const permission = permissions.find((p) => p.key === key);
    if (!agentId) {
      toast.error("Pick an agent first.");
      return;
    }
    if (!permission) {
      toast.error("Pick what you want the agent to try.");
      return;
    }
    const nextAmount = override ? override.amount : amount === "" ? null : Number(amount);
    const nextResourceId = override ? override.resourceId : resourceId.trim() || null;

    if (override) {
      setPermissionKey(key);
      setAmount(override.amount != null ? String(override.amount) : "");
      setResourceId(override.resourceId || "");
    }

    setRunning(true);
    setShowTrace(false);
    try {
      const { data } = await api.post("/policies/test", {
        agent_id: agentId,
        resource: permission.resource,
        action: permission.action,
        resource_id: nextResourceId,
        amount: Number.isFinite(nextAmount) ? nextAmount : null,
      });
      setResult({ ...data.result, tried: permission });
    } catch (err) {
      toast.error(errorMessage(err, "Could not check that action."));
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Try an action" testId="try-header" />
        <Spinner label="Getting your agents ready…" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="try-page">
      <PageHeader
        title="Try an action"
        description="Ask “what would happen if my agent tried this?” and get the real answer, without anything actually happening."
        testId="try-header"
        actions={<SimulatedTag label="Nothing happens for real" />}
      />

      <Explainer
        title="This is a safe practice run"
        points={[
          "Vexen makes the same decision it would make for a real agent, using your real permissions and rules.",
          "Nothing is bought, sent or changed, and this does not appear in your History.",
          "It is the fastest way to check a rule actually does what you meant.",
        ]}
        testId="try-explainer"
      />

      {agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="You need an agent first"
          description="Add an agent from the library, then come back here and try an action against it."
          action={
            <Button asChild data-testid="try-empty-cta">
              <Link to="/app/agents">Browse the agent library</Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,420px)_1fr]">
          <SectionCard title="Set up the attempt" icon={Wand2} testId="try-form-card">
            <div className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="try-agent">Which agent is trying it?</Label>
                <Select value={agentId} onValueChange={setAgentId}>
                  <SelectTrigger id="try-agent" data-testid="try-agent-select">
                    <SelectValue placeholder="Pick an agent" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[320px]">
                    {agents.map((a) => (
                      <SelectItem key={a.agent_id} value={a.agent_id}>
                        {a.name}
                        {a.status !== "active" ? " (switched off)" : ""}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedAgent ? (
                  <p className="text-xs text-muted-foreground">
                    {selectedAgent.permission_count || 0} permissions ·{" "}
                    <Link
                      to={`/app/agents/${selectedAgent.agent_id}`}
                      className="text-primary underline-offset-4 hover:underline"
                    >
                      open this agent
                    </Link>
                  </p>
                ) : null}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="try-permission">What is it trying to do?</Label>
                <Select value={permissionKey} onValueChange={setPermissionKey}>
                  <SelectTrigger id="try-permission" data-testid="try-permission-select">
                    <SelectValue placeholder="Pick an action" />
                  </SelectTrigger>
                  <SelectContent className="max-h-[340px]">
                    {grouped.map(([category, items]) => (
                      <SelectGroup key={category}>
                        <SelectLabel>{category}</SelectLabel>
                        {items.map((p) => (
                          <SelectItem key={p.key} value={p.key}>
                            {p.label}
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    ))}
                  </SelectContent>
                </Select>
                {selectedPermission ? (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {selectedPermission.description}
                    {selectedPermission.sensitive ? (
                      <span className="ml-1 font-semibold text-[hsl(var(--risk-high))]">
                        This one is sensitive.
                      </span>
                    ) : null}
                  </p>
                ) : null}
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="try-resource">
                  Which thing exactly? <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Input
                  id="try-resource"
                  value={resourceId}
                  onChange={(e) => setResourceId(e.target.value)}
                  maxLength={200}
                  placeholder="e.g. invoice-2042, or an email address"
                  data-testid="try-resource-input"
                />
              </div>

              {selectedPermission?.supports_amount ? (
                <div className="space-y-1.5">
                  <Label htmlFor="try-amount">How much money is involved?</Label>
                  <Input
                    id="try-amount"
                    type="number"
                    min="0"
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="e.g. 250"
                    data-testid="try-amount-input"
                  />
                  <p className="text-xs text-muted-foreground">
                    Try a small number and then a big one to see a spending cap kick in.
                  </p>
                </div>
              ) : null}

              <Button
                onClick={() => run(null)}
                disabled={running || !permissionKey}
                className="w-full"
                data-testid="try-run-button"
              >
                {running ? "Checking…" : "See what Vexen would do"}
              </Button>
            </div>

            {availablePresets.length ? (
              <div className="mt-5 border-t border-border pt-4">
                <p className="vx-label flex items-center gap-1.5">
                  <Lightbulb className="h-3.5 w-3.5" /> Or try one of these
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {availablePresets.map((preset) => (
                    <Button
                      key={preset.label}
                      variant="outline"
                      size="sm"
                      disabled={running}
                      onClick={() => run(preset)}
                      data-testid={`try-preset-${preset.key.replace(/\./g, "-")}`}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </div>
              </div>
            ) : null}
          </SectionCard>

          <div className="space-y-5">
            {result ? (
              <>
                <section
                  className={cn("rounded-xl border p-5 vx-rise", DECISION_TONE[result.decision])}
                  data-testid="try-result-card"
                >
                  <div className="flex flex-wrap items-center gap-2.5">
                    <DecisionBadge decision={result.decision} />
                    <RiskBadge risk={result.risk} score={result.risk_score} />
                    <SimulatedTag label="Practice run" />
                  </div>
                  <h2
                    className="mt-3.5 font-display text-xl font-bold tracking-tight text-foreground"
                    data-testid="try-result-headline"
                  >
                    {decisionPlain(result.decision).label}
                  </h2>
                  <p className="mt-1.5 text-sm leading-relaxed text-foreground/80">
                    {decisionPlain(result.decision).plain}
                  </p>

                  <div className="mt-4 rounded-lg border border-border bg-card p-3.5">
                    <p className="vx-label">Why</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-foreground/85" data-testid="try-result-reason">
                      {result.reason}
                    </p>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <KeyValue label="Action tried">
                      <span className="vx-mono text-xs">{result.tried?.label}</span>
                    </KeyValue>
                    <KeyValue
                      label="Permission used"
                      help="The specific permission on this agent that Vexen looked at."
                    >
                      <span className="vx-mono text-xs">{result.permission_key || "None found"}</span>
                    </KeyValue>
                    <KeyValue label="Limit that applied" help="The spending cap Vexen compared against.">
                      <span className="text-sm">
                        {result.effective_limit === null || result.effective_limit === undefined
                          ? "No cap involved"
                          : money(result.effective_limit)}
                      </span>
                    </KeyValue>
                    <KeyValue label="Rule that decided it">
                      <span className="vx-mono text-xs">{result.policy || "—"}</span>
                    </KeyValue>
                  </div>

                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-4 -ml-2"
                    onClick={() => setShowTrace((s) => !s)}
                    data-testid="try-toggle-trace"
                  >
                    {showTrace ? (
                      <ChevronUp className="mr-1.5 h-4 w-4" />
                    ) : (
                      <ChevronDown className="mr-1.5 h-4 w-4" />
                    )}
                    {showTrace ? "Hide" : "Show"} the step-by-step check
                  </Button>

                  {showTrace ? (
                    <div className="mt-3">
                      <p className="mb-2 text-xs leading-relaxed text-muted-foreground">
                        Vexen runs the same checks in the same order every time. Here is what happened
                        on this attempt.
                      </p>
                      <DecisionTrace trace={result.trace} dense />
                    </div>
                  ) : null}
                </section>

                {result.decision === "APPROVAL_REQUIRED" ? (
                  <div className="vx-explainer" data-testid="try-approval-hint">
                    <div className="flex items-start gap-2.5">
                      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--status-approval))]" />
                      <p className="text-sm leading-relaxed text-foreground/80">
                        In real life this is the moment the agent stops and waits. It would appear
                        under <strong>Waiting for you</strong>, and nothing would happen until you
                        approved it.
                      </p>
                    </div>
                  </div>
                ) : null}
              </>
            ) : (
              <EmptyState
                icon={Sparkles}
                title="Nothing tried yet"
                description="Pick an agent and an action on the left, then press the button. You will see the answer, the reason behind it, and every check Vexen made."
                className="h-full"
                testId="try-empty-result"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
