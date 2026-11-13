import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Ban,
  Check,
  Clock,
  Crosshair,
  Gauge,
  Pencil,
  Plus,
  Scale,
  Sparkles,
  Trash2,
  UserCheck,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
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
  EmptyState,
  ErrorState,
  Explainer,
  HelpTip,
  PageHeader,
  SectionCard,
  TableSkeleton,
} from "@/components/Common";
import { api, errorMessage } from "@/lib/api";
import { money } from "@/lib/format";
import { EFFECT_PLAIN, effectPlain } from "@/lib/plain";
import { cn } from "@/lib/utils";

const EFFECT_ICONS = {
  DENY: Ban,
  REQUIRE_APPROVAL: UserCheck,
  LIMIT: Gauge,
  MAX_TTL: Clock,
  REQUIRE_SCOPE: Crosshair,
};

const EFFECT_TONE = {
  DENY: "border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.09)] text-[hsl(var(--status-block))]",
  REQUIRE_APPROVAL:
    "border-[hsl(var(--status-approval)/0.3)] bg-[hsl(var(--status-approval)/0.09)] text-[hsl(var(--status-approval))]",
  LIMIT: "border-[hsl(var(--risk-medium)/0.3)] bg-[hsl(var(--risk-medium)/0.09)] text-[hsl(var(--risk-medium))]",
  MAX_TTL: "border-primary/30 bg-primary/10 text-primary",
  REQUIRE_SCOPE: "border-primary/30 bg-primary/10 text-primary",
};

const EXAMPLE_PROMPTS = [
  "Never let any agent spend more than $200 without asking me first",
  "No agent may ever read saved card details or bank information",
  "Any agent sending email to someone outside my company needs my approval",
  "Temporary access should always run out after one hour",
  "Agents can only open the specific files I name, nothing else",
];

const BLANK_FORM = {
  name: "",
  description: "",
  effect: "REQUIRE_APPROVAL",
  permissions: ["*"],
  amount_gt: "",
  max_amount: "",
  max_ttl_minutes: "",
  priority: 50,
  enabled: true,
};

function describeMatch(policy) {
  const match = policy.match || {};
  const perms = match.permissions || ["*"];
  const bits = [];
  bits.push(perms.includes("*") ? "every action" : perms.join(", "));
  if (match.amount_gt !== undefined && match.amount_gt !== null) {
    bits.push(`only above ${money(match.amount_gt)}`);
  }
  if (match.resources && !match.resources.includes("*")) {
    bits.push(`only ${match.resources.join(", ")}`);
  }
  if (match.sensitive_only) bits.push("only sensitive things");
  return bits.join(" · ");
}

export default function Policies() {
  const [items, setItems] = useState([]);
  const [effects, setEffects] = useState([]);
  const [permissionKeys, setPermissionKeys] = useState([]);
  const [generatorAvailable, setGeneratorAvailable] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [draft, setDraft] = useState(null);
  const [savingDraft, setSavingDraft] = useState(false);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(BLANK_FORM);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const { data } = await api.get("/policies");
      setItems(data.items || []);
      setEffects(data.effects || []);
      setPermissionKeys(data.permission_keys || []);
      setGeneratorAvailable(Boolean(data.generator_available));
    } catch (err) {
      setError(errorMessage(err, "Could not load your rules."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const groupedKeys = useMemo(() => {
    const map = new Map();
    permissionKeys.forEach((key) => {
      const group = key.split(".")[0];
      if (!map.has(group)) map.set(group, []);
      map.get(group).push(key);
    });
    return Array.from(map.entries());
  }, [permissionKeys]);

  /* ----------------------------- AI generator ---------------------------- */
  const generate = async (text) => {
    const value = (text ?? prompt).trim();
    if (value.length < 8) {
      toast.error("Write the rule as a full sentence so it can be read properly.");
      return;
    }
    if (text) setPrompt(value);
    setGenerating(true);
    setDraft(null);
    try {
      // the server gives up on a slow answer after about 90 seconds
      const { data } = await api.post("/policies/generate", { prompt: value }, { timeout: 120000 });
      setDraft(data.rule);
      toast.success("Here is what I understood", {
        description: "Check it over before you save it.",
      });
    } catch (err) {
      toast.error(errorMessage(err, "Could not turn that into a rule."));
    } finally {
      setGenerating(false);
    }
  };

  const saveDraft = async () => {
    if (!draft) return;
    setSavingDraft(true);
    try {
      await api.post("/policies", {
        name: draft.name,
        description: draft.description,
        effect: draft.effect,
        match: draft.match,
        params: draft.params,
        priority: draft.priority,
        enabled: true,
        source: "ai",
        rationale: draft.rationale,
      });
      toast.success("Rule saved and now protecting you");
      setDraft(null);
      setPrompt("");
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save that rule."));
    } finally {
      setSavingDraft(false);
    }
  };

  const editDraft = () => {
    if (!draft) return;
    setEditing(null);
    setForm({
      name: draft.name,
      description: draft.description || "",
      effect: draft.effect,
      permissions: draft.match?.permissions || ["*"],
      amount_gt: draft.match?.amount_gt ?? "",
      max_amount: draft.params?.max_amount ?? "",
      max_ttl_minutes: draft.params?.max_ttl_minutes ?? "",
      priority: draft.priority || 50,
      enabled: true,
    });
    setDialogOpen(true);
  };

  /* ------------------------------- Manual CRUD --------------------------- */
  const openCreate = () => {
    setEditing(null);
    setForm(BLANK_FORM);
    setDialogOpen(true);
  };

  const openEdit = (policy) => {
    setEditing(policy);
    setForm({
      name: policy.name,
      description: policy.description || "",
      effect: policy.effect,
      permissions: policy.match?.permissions || ["*"],
      amount_gt: policy.match?.amount_gt ?? "",
      max_amount: policy.params?.max_amount ?? "",
      max_ttl_minutes: policy.params?.max_ttl_minutes ?? "",
      priority: policy.priority || 50,
      enabled: policy.enabled !== false,
    });
    setDialogOpen(true);
  };

  const submitForm = async () => {
    if (form.name.trim().length < 3) {
      toast.error("Give the rule a short name so you recognise it later.");
      return;
    }
    if (form.effect === "LIMIT" && form.max_amount === "") {
      toast.error("A cap needs a maximum amount.");
      return;
    }
    if (form.effect === "MAX_TTL" && form.max_ttl_minutes === "") {
      toast.error("An expiry rule needs a number of minutes.");
      return;
    }
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      effect: form.effect,
      match: {
        permissions: form.permissions.length ? form.permissions : ["*"],
        agents: ["*"],
        resources: ["*"],
        ...(form.amount_gt === "" ? {} : { amount_gt: Number(form.amount_gt) }),
      },
      params: {
        ...(form.max_amount === "" ? {} : { max_amount: Number(form.max_amount) }),
        ...(form.max_ttl_minutes === "" ? {} : { max_ttl_minutes: Number(form.max_ttl_minutes) }),
      },
      priority: Number(form.priority) || 50,
      enabled: form.enabled,
    };
    setSaving(true);
    try {
      if (editing) {
        await api.patch(`/policies/${editing.id}`, payload);
        toast.success("Rule updated");
      } else {
        await api.post("/policies", { ...payload, source: draft ? "ai" : "manual" });
        toast.success("Rule saved and now protecting you");
        setDraft(null);
        setPrompt("");
      }
      setDialogOpen(false);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save that rule."));
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async (policy, next) => {
    setItems((rows) => rows.map((r) => (r.id === policy.id ? { ...r, enabled: next } : r)));
    try {
      await api.patch(`/policies/${policy.id}`, { enabled: next });
      toast.success(next ? "Rule switched on" : "Rule switched off");
    } catch (err) {
      setItems((rows) => rows.map((r) => (r.id === policy.id ? { ...r, enabled: !next } : r)));
      toast.error(errorMessage(err, "Could not change that rule."));
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/policies/${deleteTarget.id}`);
      toast.success("Rule deleted");
      setDeleteTarget(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not delete that rule."));
    }
  };

  const togglePermission = (key) => {
    setForm((f) => {
      if (key === "*") return { ...f, permissions: ["*"] };
      const without = f.permissions.filter((k) => k !== "*");
      const next = without.includes(key)
        ? without.filter((k) => k !== key)
        : [...without, key];
      return { ...f, permissions: next.length ? next : ["*"] };
    });
  };

  return (
    <div className="space-y-6" data-testid="policies-page">
      <PageHeader
        title="Rules"
        description="Rules apply to every agent at once, and they always win. This is your safety net."
        testId="policies-header"
        actions={
          <Button onClick={openCreate} data-testid="policies-create-button">
            <Plus className="mr-1.5 h-4 w-4" /> Add a rule myself
          </Button>
        }
      />

      <Explainer
        title="Rules beat permissions"
        points={[
          "A permission says what one agent may do. A rule says what no agent may do, no matter what.",
          "If a rule and a permission disagree, the stricter one wins. You cannot accidentally loosen things with a rule.",
          "Vexen ships with a few rules already switched on — like never letting an agent read saved card details.",
        ]}
        testId="policies-explainer"
      />

      <SectionCard
        title="Describe a rule in your own words"
        description="Type it like you would say it out loud. Vexen turns it into a real rule and shows you before saving."
        icon={Sparkles}
        testId="policies-ai-card"
      >
        {generatorAvailable ? (
          <div className="space-y-4">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder="e.g. Never let any agent spend more than $200 without asking me first"
              data-testid="policies-ai-prompt"
            />
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={() => generate()} disabled={generating} data-testid="policies-ai-generate">
                <Sparkles className="mr-1.5 h-4 w-4" />
                {generating ? "Reading that…" : "Turn this into a rule"}
              </Button>
              <span className="text-xs text-muted-foreground">
                Nothing is saved until you approve it.
              </span>
            </div>

            <div>
              <p className="vx-label">Not sure what to write? Tap one</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {EXAMPLE_PROMPTS.map((example) => (
                  <Button
                    key={example}
                    variant="outline"
                    size="sm"
                    disabled={generating}
                    onClick={() => generate(example)}
                    className="h-auto whitespace-normal py-1.5 text-left text-xs"
                    data-testid="policies-ai-example"
                  >
                    {example}
                  </Button>
                ))}
              </div>
            </div>

            {draft ? (
              <div
                className="rounded-xl border border-primary/30 bg-accent/50 p-4 vx-rise"
                data-testid="policies-ai-draft"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="vx-chip border-primary/30 bg-primary/10 text-primary">
                    Check this before saving
                  </span>
                  <span className={cn("vx-chip", EFFECT_TONE[draft.effect])}>
                    {effectPlain(draft.effect).label}
                  </span>
                  {typeof draft.confidence === "number" ? (
                    <span className="vx-chip border-border bg-muted text-muted-foreground">
                      {Math.round(draft.confidence * 100)}% sure
                    </span>
                  ) : null}
                </div>

                <p className="mt-3 font-display text-[15px] font-semibold text-foreground">
                  {draft.name}
                </p>
                <p className="mt-1.5 text-sm leading-relaxed text-foreground/80">
                  {draft.description}
                </p>

                <div className="mt-3.5 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-border bg-card p-3">
                    <p className="vx-label">What it does</p>
                    <p className="mt-1 text-sm text-foreground/85">
                      {effectPlain(draft.effect).plain}
                    </p>
                  </div>
                  <div className="rounded-lg border border-border bg-card p-3">
                    <p className="vx-label">When it applies</p>
                    <p className="vx-mono mt-1 text-xs text-foreground/85">{describeMatch(draft)}</p>
                    {draft.params?.max_amount ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Cap: {money(draft.params.max_amount)}
                      </p>
                    ) : null}
                    {draft.params?.max_ttl_minutes ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        Expires after {draft.params.max_ttl_minutes} minutes
                      </p>
                    ) : null}
                  </div>
                </div>

                {draft.rationale ? (
                  <div className="mt-3 rounded-lg border border-border bg-card p-3">
                    <p className="vx-label">Why it read your sentence this way</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                      {draft.rationale}
                    </p>
                  </div>
                ) : null}

                <div className="mt-4 flex flex-wrap gap-2">
                  <Button onClick={saveDraft} disabled={savingDraft} data-testid="policies-ai-save">
                    <Check className="mr-1.5 h-4 w-4" />
                    {savingDraft ? "Saving…" : "Yes, save this rule"}
                  </Button>
                  <Button variant="outline" onClick={editDraft} data-testid="policies-ai-edit">
                    <Pencil className="mr-1.5 h-4 w-4" /> Change it first
                  </Button>
                  <Button variant="ghost" onClick={() => setDraft(null)} data-testid="policies-ai-discard">
                    <X className="mr-1.5 h-4 w-4" /> Discard
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm leading-relaxed text-muted-foreground">
            Writing rules in plain English is switched off on this workspace. You can still add rules
            yourself with the button at the top of the page.
          </p>
        )}
      </SectionCard>

      <SectionCard
        title={`Your rules${items.length ? ` (${items.length})` : ""}`}
        description="Checked from the top down. The strictest match wins."
        icon={Scale}
        testId="policies-list-card"
        bodyClassName={loading || items.length ? "px-5 py-4" : "p-0"}
      >
        {error ? (
          <ErrorState message={error} onRetry={load} />
        ) : loading ? (
          <TableSkeleton rows={4} cols={3} />
        ) : items.length === 0 ? (
          <EmptyState
            icon={Scale}
            title="No rules yet"
            description="Describe your first rule above in plain English, or add one yourself."
            className="border-0"
            action={
              <Button onClick={openCreate} data-testid="policies-empty-cta">
                Add a rule
              </Button>
            }
          />
        ) : (
          <ul className="space-y-3">
            {items.map((policy) => {
              const Icon = EFFECT_ICONS[policy.effect] || Scale;
              return (
                <li
                  key={policy.id}
                  className={cn(
                    "rounded-xl border border-border bg-card p-4",
                    !policy.enabled && "opacity-60",
                  )}
                  data-testid="policy-item"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 gap-3">
                      <span
                        className={cn(
                          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border",
                          EFFECT_TONE[policy.effect],
                        )}
                      >
                        <Icon className="h-4 w-4" />
                      </span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-display text-[15px] font-semibold text-foreground">
                            {policy.name}
                          </p>
                          {policy.system ? (
                            <span className="vx-chip border-primary/25 bg-primary/10 text-primary">
                              Built in
                            </span>
                          ) : null}
                          {policy.source === "ai" ? (
                            <span className="vx-chip border-border bg-muted text-muted-foreground">
                              From your words
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                          {policy.description || effectPlain(policy.effect).plain}
                        </p>
                        <p className="vx-mono mt-2 text-[11px] text-muted-foreground">
                          Applies to {describeMatch(policy)}
                          {policy.params?.max_amount
                            ? ` · cap ${money(policy.params.max_amount)}`
                            : ""}
                          {policy.params?.max_ttl_minutes
                            ? ` · expires after ${policy.params.max_ttl_minutes}m`
                            : ""}
                        </p>
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <Switch
                          checked={policy.enabled !== false}
                          onCheckedChange={(next) => toggleEnabled(policy, next)}
                          aria-label={policy.enabled ? "Switch rule off" : "Switch rule on"}
                          data-testid={`policy-toggle-${policy.id}`}
                        />
                        <span className="text-xs text-muted-foreground">
                          {policy.enabled !== false ? "On" : "Off"}
                        </span>
                      </div>
                      {!policy.system ? (
                        <>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => openEdit(policy)}
                            aria-label="Edit rule"
                            data-testid={`policy-edit-${policy.id}`}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTarget(policy)}
                            aria-label="Delete rule"
                            className="text-[hsl(var(--status-block))]"
                            data-testid={`policy-delete-${policy.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          Cannot be edited
                          <HelpTip
                            className="ml-1 inline-flex"
                            text="Built-in rules are Vexen's baseline protection. You can switch one off, but you cannot rewrite it."
                          />
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </SectionCard>

      {/* --------------------------- Create / edit --------------------------- */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle className="font-display">
              {editing ? "Change this rule" : "Add a rule"}
            </DialogTitle>
            <DialogDescription>
              Rules apply to every agent in your workspace. The stricter setting always wins.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="policy-name">Name it</Label>
              <Input
                id="policy-name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                maxLength={120}
                placeholder="e.g. Big purchases need my approval"
                data-testid="policy-name-input"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="policy-description">
                What is it for? <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Textarea
                id="policy-description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={2}
                maxLength={600}
                placeholder="A note to your future self."
                data-testid="policy-description-input"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="policy-effect">What should happen?</Label>
              <Select
                value={form.effect}
                onValueChange={(value) => setForm((f) => ({ ...f, effect: value }))}
              >
                <SelectTrigger id="policy-effect" data-testid="policy-effect-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(effects.length ? effects.map((e) => e.value) : Object.keys(EFFECT_PLAIN)).map(
                    (value) => (
                      <SelectItem key={value} value={value}>
                        {effectPlain(value).label}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs leading-relaxed text-muted-foreground">
                {effectPlain(form.effect).plain} {effectPlain(form.effect).example}
              </p>
            </div>

            <div className="space-y-1.5">
              <Label>Which actions does it cover?</Label>
              <div className="flex flex-wrap gap-1.5">
                <Button
                  type="button"
                  variant={form.permissions.includes("*") ? "default" : "outline"}
                  size="sm"
                  onClick={() => togglePermission("*")}
                  data-testid="policy-permission-all"
                >
                  Every action
                </Button>
                {form.permissions
                  .filter((k) => k !== "*")
                  .map((key) => (
                    <Button
                      key={key}
                      type="button"
                      variant="default"
                      size="sm"
                      onClick={() => togglePermission(key)}
                      className="vx-mono text-[11px]"
                    >
                      {key}
                      <X className="ml-1.5 h-3 w-3" />
                    </Button>
                  ))}
              </div>
              <Select value="" onValueChange={(value) => togglePermission(value)}>
                <SelectTrigger data-testid="policy-permission-select">
                  <SelectValue placeholder="Add a specific action…" />
                </SelectTrigger>
                <SelectContent className="max-h-[300px]">
                  {groupedKeys.map(([group, keys]) => (
                    <SelectGroup key={group}>
                      <SelectLabel className="capitalize">{group}</SelectLabel>
                      {keys.map((key) => (
                        <SelectItem key={key} value={key} className="vx-mono text-xs">
                          {key}
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="policy-amount-gt" className="flex items-center gap-1.5">
                  Only above this amount
                  <HelpTip text="Leave blank to apply the rule to everything. Set 200 to only apply when more than $200 is involved." />
                </Label>
                <Input
                  id="policy-amount-gt"
                  type="number"
                  min="0"
                  value={form.amount_gt}
                  onChange={(e) => setForm((f) => ({ ...f, amount_gt: e.target.value }))}
                  placeholder="Any amount"
                  data-testid="policy-amount-gt-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="policy-priority" className="flex items-center gap-1.5">
                  Order
                  <HelpTip text="Lower numbers are checked first. Blocks usually sit at 10-19, approvals at 20-29." />
                </Label>
                <Input
                  id="policy-priority"
                  type="number"
                  min="1"
                  max="99"
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                  data-testid="policy-priority-input"
                />
              </div>
            </div>

            {form.effect === "LIMIT" ? (
              <div className="space-y-1.5">
                <Label htmlFor="policy-max-amount">Hard cap</Label>
                <Input
                  id="policy-max-amount"
                  type="number"
                  min="0"
                  value={form.max_amount}
                  onChange={(e) => setForm((f) => ({ ...f, max_amount: e.target.value }))}
                  placeholder="e.g. 500"
                  data-testid="policy-max-amount-input"
                />
              </div>
            ) : null}

            {form.effect === "MAX_TTL" ? (
              <div className="space-y-1.5">
                <Label htmlFor="policy-ttl">Access runs out after (minutes)</Label>
                <Input
                  id="policy-ttl"
                  type="number"
                  min="1"
                  value={form.max_ttl_minutes}
                  onChange={(e) => setForm((f) => ({ ...f, max_ttl_minutes: e.target.value }))}
                  placeholder="e.g. 60"
                  data-testid="policy-ttl-input"
                />
              </div>
            ) : null}

            <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 p-3">
              <div>
                <p className="text-sm font-medium text-foreground">Switch it on straight away</p>
                <p className="text-xs text-muted-foreground">You can turn it off any time.</p>
              </div>
              <Switch
                checked={form.enabled}
                onCheckedChange={(next) => setForm((f) => ({ ...f, enabled: next }))}
                data-testid="policy-enabled-switch"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submitForm} disabled={saving} data-testid="policy-submit-button">
              {saving ? "Saving…" : editing ? "Save changes" : "Add this rule"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteTarget)} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display">Delete this rule?</AlertDialogTitle>
            <AlertDialogDescription>
              “{deleteTarget?.name}” will stop protecting your agents immediately. Your history is
              kept either way.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-[hsl(var(--status-block))] text-white hover:bg-[hsl(var(--status-block)/0.9)]"
              data-testid="policy-confirm-delete"
            >
              Delete rule
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
