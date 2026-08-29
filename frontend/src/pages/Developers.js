import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  Code2,
  Download,
  KeyRound,
  Plug,
  Plus,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  CodeBlock,
  CopyButton,
  EmptyState,
  ErrorState,
  Explainer,
  KeyValue,
  MetricCard,
  PageHeader,
  SectionCard,
  Spinner,
} from "@/components/Common";
import { api, errorMessage } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const KEY_PLACEHOLDER = "vex_sk_live_xxxxxxxxxxxx";

function curlSnippet(endpoint, key) {
  return `curl -X POST ${endpoint} \\
  -H "X-Vexen-Key: ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "resource": "shopping",
    "action": "purchase",
    "resource_id": "sku-8842",
    "amount": 250,
    "currency": "USD"
  }'`;
}

function pythonSnippet(endpoint, key) {
  return `import os, time, requests

VEXEN = "${endpoint}"
APPROVALS = VEXEN.replace("/authorize", "/approvals")
KEY = os.environ["VEXEN_KEY"]  # ${key}


def ask(resource, action, approval_id=None, **details):
    r = requests.post(
        VEXEN,
        headers={"X-Vexen-Key": KEY},
        json={"resource": resource, "action": action, "approval_id": approval_id, **details},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def wait_for_person(approval_id, minutes=5):
    """Poll until a human decides. Reading the status never authorises anything."""
    deadline = time.time() + minutes * 60
    while time.time() < deadline:
        s = requests.get(f"{APPROVALS}/{approval_id}", headers={"X-Vexen-Key": KEY}, timeout=10).json()
        if s["state"] != "pending":
            return s
        time.sleep(s.get("poll_after_seconds") or 3)
    return {"state": "timeout", "may_proceed": False}


verdict = ask("shopping", "purchase", resource_id="sku-8842", amount=250)

if verdict["decision"] == "APPROVAL_REQUIRED":
    answer = wait_for_person(verdict["approval_id"])
    if answer["may_proceed"]:
        # Repeat the same request with the approval id. It works exactly once.
        verdict = ask("shopping", "purchase", resource_id="sku-8842", amount=250,
                      approval_id=verdict["approval_id"])

if verdict["decision"] == "ALLOW":
    place_the_order()          # only now does anything real happen
else:
    log("Vexen refused:", verdict["reason"])`;
}

function guardSnippet(endpoint) {
  const host = endpoint.replace("/api/v1/authorize", "");
  return `# 1. Save the guard next to your agent code:
#      curl -O ${host}/sdk/vexen.py
# 2. Put it in front of the function that actually does the thing.

import os
from vexen import Vexen, VexenBlocked, VexenNeedsApproval, VexenUnavailable

vexen = Vexen(api_key=os.environ["VEXEN_KEY"], base_url="${host}")


@vexen.guard("shopping", "purchase",
             amount=lambda kw: kw["price"],
             resource_id=lambda kw: kw["sku"],
             wait_for_approval=True)      # pauses here until a person answers
def buy_item(sku, price):
    return store.charge_card(sku, price)  # never runs unless Vexen allows it


@vexen.guard("payments", "read", resource_id="card-on-file")
def read_saved_card():
    return store.saved_card


try:
    buy_item(sku="sku-8842", price=250)
except VexenNeedsApproval as e:
    log("waiting on a person:", e.approval_id)
except VexenBlocked as e:
    log("Vexen refused:", e)
except VexenUnavailable:
    log("Vexen unreachable, so nothing was bought")  # fails closed on purpose`;
}

function jsSnippet(endpoint, key) {
  return `const VEXEN = "${endpoint}";
const APPROVALS = VEXEN.replace("/authorize", "/approvals");
const KEY = process.env.VEXEN_KEY; // ${key}

const headers = { "X-Vexen-Key": KEY, "Content-Type": "application/json" };

async function ask(resource, action, details = {}) {
  const res = await fetch(VEXEN, {
    method: "POST",
    headers,
    body: JSON.stringify({ resource, action, ...details }),
  });
  if (!res.ok) throw new Error(\`Vexen said \${res.status}\`);
  return res.json();
}

// Poll while a person makes up their mind. This never authorises anything.
async function waitForPerson(approvalId, minutes = 5) {
  const deadline = Date.now() + minutes * 60_000;
  while (Date.now() < deadline) {
    const res = await fetch(\`\${APPROVALS}/\${approvalId}\`, { headers });
    const status = await res.json();
    if (status.state !== "pending") return status;
    await new Promise((r) => setTimeout(r, (status.poll_after_seconds || 3) * 1000));
  }
  return { state: "timeout", may_proceed: false };
}

const purchase = { resource_id: "sku-8842", amount: 250 };
let verdict = await ask("shopping", "purchase", purchase);

if (verdict.decision === "APPROVAL_REQUIRED") {
  const answer = await waitForPerson(verdict.approval_id);
  if (answer.may_proceed) {
    // Same request, plus the approval id. Good for one use only.
    verdict = await ask("shopping", "purchase", { ...purchase, approval_id: verdict.approval_id });
  }
}

if (verdict.decision === "ALLOW") {
  await placeTheOrder(); // only now does anything real happen
} else {
  console.log("Vexen refused:", verdict.reason);
}`;
}

const RESPONSE_EXAMPLE = `{
  "decision": "APPROVAL_REQUIRED",
  "reason": "$250.00 exceeds the auto-approve limit of $100.00; Policy \u201cPurchases above $100 require approval\u201d requires human approval.",
  "reason_code": "APPROVAL_REQUIRED",
  "policy": "Purchases above $100 require approval",
  "risk": "HIGH",
  "risk_score": 52,
  "permission": "shopping.purchase",
  "effective_limit": 100.0,
  "audit_id": "VEX-EVT-52A4B680DED3",
  "request_id": "VEX-REQ-5DB94542FC6B",
  "approval_id": "appr_3a0be82578b749639d9b",
  "approval_status": "pending",
  "approval_expires_at": null,
  "approval_check_url": ".../api/v1/approvals/appr_3a0be82578b749639d9b",
  "agent": { "id": "VEX-AGT-1733A686", "name": "Shopping Agent" },
  "evaluated_at": "2026-08-29T15:22:19.904511+00:00"
}`;

export default function Developers() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [keyName, setKeyName] = useState("Primary key");
  const [expiresInDays, setExpiresInDays] = useState("");
  const [creating, setCreating] = useState(false);
  const [revealedSecret, setRevealedSecret] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data: payload } = await api.get("/developers");
      setData(payload);
      if (payload.agents?.length && !selectedAgentId) {
        setSelectedAgentId(payload.agents[0].agent_id);
      }
    } catch (err) {
      setError(errorMessage(err, "Could not load the developer page."));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selectedAgent = useMemo(
    () => data?.agents?.find((a) => a.agent_id === selectedAgentId) || null,
    [data, selectedAgentId],
  );

  const endpoint = data?.authorize_endpoint || "/api/v1/authorize";
  const sampleKey = revealedSecret?.secret || KEY_PLACEHOLDER;

  const createKey = async () => {
    if (!selectedAgentId) {
      toast.error("Pick an agent first.");
      return;
    }
    setCreating(true);
    try {
      const { data: payload } = await api.post(`/agents/${selectedAgentId}/credentials`, {
        name: keyName.trim() || "Primary key",
        expires_in_days: expiresInDays === "" ? undefined : Number(expiresInDays),
      });
      setRevealedSecret({ secret: payload.secret, agentId: selectedAgentId });
      setCreateOpen(false);
      setKeyName("Primary key");
      setExpiresInDays("");
      toast.success("Key created", { description: "Copy it now — it is only shown once." });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not create a key."));
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (agentId, credentialId) => {
    try {
      await api.delete(`/agents/${agentId}/credentials/${credentialId}`);
      toast.success("Key revoked. It stops working immediately.");
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not revoke that key."));
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="For developers" testId="developers-header" />
        <Spinner label="Loading your API details…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="For developers" testId="developers-header" />
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="developers-page">
      <PageHeader
        title="For developers"
        description="Connect your own AI agent so it asks Vexen for permission before it acts."
        testId="developers-header"
        actions={
          <Button onClick={() => setCreateOpen(true)} data-testid="developers-create-key-button">
            <Plus className="mr-1.5 h-4 w-4" /> Create an agent key
          </Button>
        }
      />

      <Explainer
        title="You can safely skip this page"
        points={[
          "Everything else in Vexen works by clicking. This page is only for people who write software.",
          "The idea is simple: before your agent does anything, it asks Vexen, and Vexen answers ALLOW, BLOCK or APPROVAL_REQUIRED.",
          "Your agent authenticates with its own key. Keys are stored hashed and shown to you exactly once.",
        ]}
        testId="developers-explainer"
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="Agents available"
          value={data?.agents?.length || 0}
          icon={Bot}
          hint="Each one can hold up to 5 active keys."
          testId="developers-agent-count"
        />
        <MetricCard
          label="Real API calls"
          value={data?.api_calls || 0}
          icon={Plug}
          tone="primary"
          hint="Requests that arrived from your own agents."
          testId="developers-api-calls"
        />
        <MetricCard
          label="Possible answers"
          value="3"
          icon={ShieldCheck}
          hint="ALLOW · BLOCK · APPROVAL_REQUIRED"
          testId="developers-decisions"
        />
      </div>

      <SectionCard title="Where to send requests" icon={Plug} testId="developers-endpoint-card">
        <div className="grid gap-4 sm:grid-cols-2">
          <KeyValue label="Ask for permission">
            <div className="flex flex-col items-start gap-1.5">
              <code className="vx-mono block w-full break-all text-xs leading-relaxed text-foreground">
                POST {endpoint}
              </code>
              <CopyButton value={endpoint} label="Copy" testId="developers-copy-endpoint" />
            </div>
          </KeyValue>
          <KeyValue label="Check what an agent may do">
            <div className="flex flex-col items-start gap-1.5">
              <code className="vx-mono block w-full break-all text-xs leading-relaxed text-foreground">
                GET {data?.introspect_endpoint}
              </code>
              <CopyButton value={data?.introspect_endpoint || ""} label="Copy" />
            </div>
          </KeyValue>
          <KeyValue label="How your agent signs in" help="Send this header on every request.">
            <code className="vx-mono block break-all text-xs text-foreground">
              {data?.auth_header || "X-Vexen-Key"}: your_agent_key
            </code>
          </KeyValue>
          <KeyValue
            label="Wait for a person's answer"
            help="Poll this while someone decides. Reading it never allows anything by itself."
          >
            <div className="flex flex-col items-start gap-1.5">
              <code className="vx-mono block w-full break-all text-xs leading-relaxed text-foreground">
                GET {data?.approval_endpoint || `${data?.base_url || ""}/api/v1/approvals/{approval_id}`}
              </code>
              <CopyButton
                value={data?.approval_endpoint || ""}
                label="Copy"
                testId="developers-copy-approval-endpoint"
              />
            </div>
          </KeyValue>
          <KeyValue label="If the key is missing or revoked">
            <span className="text-sm text-muted-foreground">
              You get <code className="vx-mono text-xs">401</code>. Vexen never guesses.
            </span>
          </KeyValue>
          <KeyValue label="How long an approval lasts" help="A yes is not a standing permission.">
            <span className="text-sm text-muted-foreground" data-testid="developers-approval-rule">
              A person&apos;s approval works{" "}
              <span className="font-medium text-foreground">once</span>, within{" "}
              <span className="font-medium text-foreground">
                {data?.approval_valid_minutes || 30} minutes
              </span>
              . Reusing it, or changing the amount, sends the request back for approval.
            </span>
          </KeyValue>
        </div>
      </SectionCard>

      {revealedSecret ? (
        <section
          className="rounded-xl border border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.07)] p-5 vx-rise"
          data-testid="developers-secret-panel"
        >
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[hsl(var(--status-approval))]" />
            <div className="min-w-0 flex-1">
              <p className="font-display text-[15px] font-semibold text-foreground">
                Copy this key now — you will not see it again
              </p>
              <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                Vexen only stores a scrambled version, so we genuinely cannot show it to you a second
                time. If you lose it, revoke it and make a new one.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card p-3">
                <code
                  className="vx-mono min-w-0 flex-1 break-all text-xs text-foreground"
                  data-testid="developers-secret-value"
                >
                  {revealedSecret.secret}
                </code>
                <CopyButton value={revealedSecret.secret} label="Copy key" testId="developers-copy-secret" />
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="mt-2 -ml-2"
                onClick={() => setRevealedSecret(null)}
                data-testid="developers-dismiss-secret"
              >
                I have saved it
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      <SectionCard
        title="Copy and paste"
        description="Working examples using your real endpoint."
        icon={Code2}
        testId="developers-snippets-card"
      >
        <Tabs defaultValue="curl">
          <TabsList data-testid="developers-snippet-tabs">
            <TabsTrigger value="curl" data-testid="developers-tab-curl">
              curl
            </TabsTrigger>
            <TabsTrigger value="python" data-testid="developers-tab-python">
              Python
            </TabsTrigger>
            <TabsTrigger value="js" data-testid="developers-tab-js">
              JavaScript
            </TabsTrigger>
            <TabsTrigger value="guard" data-testid="developers-tab-guard">
              Stop it in your code
            </TabsTrigger>
            <TabsTrigger value="response" data-testid="developers-tab-response">
              What comes back
            </TabsTrigger>
          </TabsList>
          <TabsContent value="curl" className="mt-4">
            <CodeBlock code={curlSnippet(endpoint, sampleKey)} language="bash" testId="developers-curl" />
          </TabsContent>
          <TabsContent value="python" className="mt-4">
            <CodeBlock
              code={pythonSnippet(endpoint, sampleKey)}
              language="python"
              testId="developers-python"
            />
          </TabsContent>
          <TabsContent value="js" className="mt-4">
            <CodeBlock code={jsSnippet(endpoint, sampleKey)} language="javascript" testId="developers-js" />
          </TabsContent>
          <TabsContent value="guard" className="mt-4">
            <div className="mb-3 rounded-lg border border-border bg-muted/40 p-3.5">
              <p className="text-sm leading-relaxed text-muted-foreground">
                Vexen can only stop what runs through it. Wrap the function that does the real
                thing — charging a card, sending the email, opening the file — and a refusal means
                that function never runs. If Vexen cannot be reached, the guard refuses too, because
                doing nothing is safer than doing something nobody approved.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button asChild size="sm" variant="outline" data-testid="developers-download-sdk">
                  <a href="/sdk/vexen.py" download>
                    <Download className="mr-1.5 h-3.5 w-3.5" /> Download vexen.py
                  </a>
                </Button>
                <span className="text-xs text-muted-foreground">
                  One file, only needs <code className="vx-mono text-xs">requests</code>.
                </span>
              </div>
            </div>
            <CodeBlock
              code={guardSnippet(endpoint)}
              language="python"
              testId="developers-guard"
            />
          </TabsContent>
          <TabsContent value="response" className="mt-4">
            <p className="mb-3 text-sm leading-relaxed text-muted-foreground">
              Read <code className="vx-mono text-xs">decision</code> and act on it. If it is{" "}
              <code className="vx-mono text-xs">APPROVAL_REQUIRED</code>, keep the{" "}
              <code className="vx-mono text-xs">approval_id</code> and retry once a human has
              approved it — passing that id back proves the approval is real.
            </p>
            <CodeBlock code={RESPONSE_EXAMPLE} language="json" testId="developers-response" />
          </TabsContent>
        </Tabs>
      </SectionCard>

      <SectionCard
        title="Agent keys"
        description="Each agent signs in with its own key, so you always know which agent asked."
        icon={KeyRound}
        testId="developers-keys-card"
        bodyClassName={data?.agents?.length ? "px-5 py-4" : "p-0"}
      >
        {data?.agents?.length ? (
          <ul className="space-y-3">
            {data.agents.map((agent) => (
              <li
                key={agent.agent_id}
                className="rounded-xl border border-border bg-card p-4"
                data-testid="developers-agent-row"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <Link
                      to={`/app/agents/${agent.agent_id}`}
                      className="font-display text-[15px] font-semibold text-foreground hover:text-primary"
                    >
                      {agent.name}
                    </Link>
                    <p className="vx-mono mt-0.5 text-[11px] text-muted-foreground">
                      {agent.agent_id}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "vx-chip",
                        agent.credential_status === "active"
                          ? "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]"
                          : "border-border bg-muted text-muted-foreground",
                      )}
                    >
                      {agent.credential_status === "active" ? "Key active" : "No active key"}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedAgentId(agent.agent_id);
                        setCreateOpen(true);
                      }}
                      data-testid={`developers-add-key-${agent.agent_id}`}
                    >
                      <Plus className="mr-1.5 h-3.5 w-3.5" /> New key
                    </Button>
                  </div>
                </div>

                {agent.credentials?.length ? (
                  <ul className="mt-3 space-y-2">
                    {agent.credentials.map((cred) => (
                      <li
                        key={cred.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/40 px-3 py-2.5"
                        data-testid="developers-credential-row"
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground">{cred.name}</p>
                          <p className="vx-mono mt-0.5 text-[11px] text-muted-foreground">
                            {cred.prefix}••••••••  · made {timeAgo(cred.created_at)}
                            {cred.expires_at ? ` · expires ${timeAgo(cred.expires_at)}` : ""}
                          </p>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          <span
                            className={cn(
                              "vx-chip",
                              cred.status === "active"
                                ? "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]"
                                : "border-border bg-muted text-muted-foreground",
                            )}
                          >
                            {cred.status}
                          </span>
                          {cred.status === "active" ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-[hsl(var(--status-block))]"
                              aria-label="Revoke key"
                              onClick={() => revokeKey(agent.agent_id, cred.id)}
                              data-testid={`developers-revoke-${cred.id}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-muted-foreground">
                    No keys yet. This agent cannot call the API until you make one.
                  </p>
                )}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            icon={Bot}
            title="No agents to connect yet"
            description="Add an agent first, then come back and give it a key."
            className="border-0"
            action={
              <Button asChild>
                <Link to="/app/agents">Browse the agent library</Link>
              </Button>
            }
          />
        )}
      </SectionCard>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="font-display">Create an agent key</DialogTitle>
            <DialogDescription>
              The full key is shown once, right after you create it. Store it somewhere safe.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="key-agent">Which agent is this key for?</Label>
              <Select value={selectedAgentId} onValueChange={setSelectedAgentId}>
                <SelectTrigger id="key-agent" data-testid="developers-key-agent-select">
                  <SelectValue placeholder="Pick an agent" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {(data?.agents || []).map((a) => (
                    <SelectItem key={a.agent_id} value={a.agent_id}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedAgent ? (
                <p className="text-xs text-muted-foreground">
                  {selectedAgent.permission_count || 0} permissions ·{" "}
                  {selectedAgent.credentials?.filter((c) => c.status === "active").length || 0} active
                  keys
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="key-name">Name this key</Label>
              <Input
                id="key-name"
                value={keyName}
                onChange={(e) => setKeyName(e.target.value)}
                maxLength={60}
                placeholder="e.g. Production key"
                data-testid="developers-key-name-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="key-expiry">
                Expire it after (days) <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="key-expiry"
                type="number"
                min="1"
                max="730"
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(e.target.value)}
                placeholder="Leave blank for no expiry"
                data-testid="developers-key-expiry-input"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={createKey} disabled={creating} data-testid="developers-key-submit">
              {creating ? "Creating…" : "Create key"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <p className="text-xs leading-relaxed text-muted-foreground">
        Keys are hashed before storage and compared in constant time. Revoking a key takes effect on
        the very next request. Every API call is recorded in your{" "}
        <Link to="/app/audit" className="text-primary underline-offset-4 hover:underline">
          History
        </Link>{" "}
        alongside the agent that made it.
      </p>
    </div>
  );
}
