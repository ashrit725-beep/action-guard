import { useCallback, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import {
  AlertCircle,
  ArrowRight,
  Ban,
  CheckCircle2,
  Clock,
  LinkIcon,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Wordmark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { errorMessage } from "@/lib/api";
import { fullDate, money, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

/* This page is opened from an email on a phone, so it never assumes a session
   and never uses the authenticated axios client. */
const publicApi = axios.create({
  baseURL: `${BACKEND_URL}/api/public`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

const Shell = ({ children }) => (
  <div className="min-h-screen bg-background">
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 w-full max-w-xl items-center justify-between px-4">
        <Wordmark showTagline />
        <ThemeToggle />
      </div>
    </header>
    <main className="mx-auto w-full max-w-xl px-4 py-6 sm:py-10">{children}</main>
  </div>
);

const Row = ({ label, children, mono }) => (
  <div className="flex flex-col gap-1 border-b border-border py-3 last:border-b-0 sm:flex-row sm:items-baseline sm:gap-4">
    <span className="vx-label shrink-0 sm:w-[132px]">{label}</span>
    <div className={cn("min-w-0 break-words text-sm text-foreground", mono && "vx-mono text-xs")}>
      {children}
    </div>
  </div>
);

const Outcome = ({ tone, icon: Icon, title, body, children, testId }) => {
  const tones = {
    allow: "text-[hsl(var(--status-allow))] bg-[hsl(var(--status-allow)/0.12)]",
    block: "text-[hsl(var(--status-block))] bg-[hsl(var(--status-block)/0.12)]",
    approval: "text-[hsl(var(--status-approval))] bg-[hsl(var(--status-approval)/0.12)]",
    muted: "text-muted-foreground bg-muted",
  };
  return (
    <div className="vx-card p-6 text-center sm:p-8" data-testid={testId}>
      <span
        className={cn(
          "mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl",
          tones[tone] || tones.muted,
        )}
      >
        <Icon className="h-6 w-6" />
      </span>
      <h1 className="font-display text-lg font-semibold text-foreground">{title}</h1>
      {body ? (
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">{body}</p>
      ) : null}
      {children ? <div className="mt-5 flex flex-wrap justify-center gap-2">{children}</div> : null}
    </div>
  );
};

const OpenConsoleButton = ({ url, label = "Open Vexen" }) =>
  url ? (
    <Button asChild variant="outline" size="sm" data-testid="approve-open-console-link">
      <a href={url}>
        {label}
        <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
      </a>
    </Button>
  ) : (
    <Button asChild variant="outline" size="sm" data-testid="approve-open-console-link">
      <Link to="/app/approvals">
        {label}
        <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
      </Link>
    </Button>
  );

export default function ApproveByLink() {
  const { token } = useParams();
  const [searchParams] = useSearchParams();
  const intent = (searchParams.get("intent") || "").toLowerCase();

  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [gone, setGone] = useState(false);
  const [note, setNote] = useState("");
  const [showNote, setShowNote] = useState(false);
  const [submitting, setSubmitting] = useState("");
  const [result, setResult] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    setGone(false);
    try {
      const { data } = await publicApi.get(`/approvals/${encodeURIComponent(token)}`);
      setRequest(data);
    } catch (err) {
      if (err?.response?.status === 404) {
        setGone(true);
        setLoadError(errorMessage(err, "This link is no longer valid."));
      } else {
        setLoadError(errorMessage(err, "We could not load this request."));
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (decision) => {
    setSubmitting(decision);
    try {
      const { data } = await publicApi.post(`/approvals/${encodeURIComponent(token)}/decision`, {
        decision,
        note: note.trim() || undefined,
      });
      setResult(data);
    } catch (err) {
      setLoadError(errorMessage(err, "We could not record that decision."));
      // Something changed underneath us (someone else decided, or it expired):
      // reload so the person sees the truth rather than a stale screen.
      load();
    } finally {
      setSubmitting("");
    }
  };

  if (loading) {
    return (
      <Shell>
        <div className="vx-card p-6" data-testid="approve-loading">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="mt-3 h-4 w-full max-w-sm" />
          <div className="mt-6 space-y-3">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
          <Skeleton className="mt-6 h-12 w-full" />
        </div>
      </Shell>
    );
  }

  if (gone) {
    return (
      <Shell>
        <Outcome
          tone="muted"
          icon={LinkIcon}
          title="This link has expired"
          body={loadError}
          testId="approve-link-invalid"
        >
          <OpenConsoleButton label="Open Vexen" />
        </Outcome>
      </Shell>
    );
  }

  if (!request) {
    return (
      <Shell>
        <Outcome
          tone="block"
          icon={AlertCircle}
          title="We could not load this"
          body={loadError || "Check your connection and try again."}
          testId="approve-load-error"
        >
          <Button size="sm" onClick={load} data-testid="approve-retry-button">
            Try again
          </Button>
        </Outcome>
      </Shell>
    );
  }

  const consoleUrl = request.console_url;

  if (result) {
    const approved = result.state === "approved";
    return (
      <Shell>
        <Outcome
          tone={approved ? "allow" : "block"}
          icon={approved ? ShieldCheck : Ban}
          title={approved ? "Approved" : "Refused"}
          body={result.message}
          testId="approve-result"
        >
          <OpenConsoleButton url={consoleUrl} label="See it in Vexen" />
        </Outcome>
        <p className="mt-4 text-center text-xs text-muted-foreground" data-testid="approve-result-meta">
          Recorded against {result.decided_by} in your workspace history.
        </p>
      </Shell>
    );
  }

  if (request.state !== "pending") {
    const alreadyApproved = request.state === "approved" || request.state === "used";
    const copy = {
      approved: "Someone already approved this.",
      used: "This was approved and the agent has already used it. An approval works once.",
      denied: "Someone already refused this.",
      expired: "This was approved but the time ran out, so the agent was not allowed to proceed.",
    };
    return (
      <Shell>
        <Outcome
          tone={alreadyApproved ? "allow" : "muted"}
          icon={alreadyApproved ? CheckCircle2 : Clock}
          title="Already decided"
          body={copy[request.state] || "This request is no longer waiting for anyone."}
          testId="approve-already-decided"
        >
          <OpenConsoleButton url={consoleUrl} />
        </Outcome>
        <div className="vx-card mt-4 px-5 py-2" data-testid="approve-decided-detail">
          <Row label="Agent">{request.agent_name}</Row>
          <Row label="Wanted to">{request.what}</Row>
          {request.decided_by ? <Row label="Decided by">{request.decided_by}</Row> : null}
          {request.decided_at ? <Row label="When">{fullDate(request.decided_at)}</Row> : null}
          {request.note ? <Row label="Note">{request.note}</Row> : null}
        </div>
      </Shell>
    );
  }

  const amount = request.amount_display || money(request.amount, request.currency);
  const busy = Boolean(submitting);

  return (
    <Shell>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge
          variant="outline"
          className="border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval-bg))] text-[hsl(var(--status-approval))]"
          data-testid="approve-state-badge"
        >
          <ShieldAlert className="mr-1 h-3.5 w-3.5" />
          Waiting for you
        </Badge>
        <span className="text-xs text-muted-foreground" data-testid="approve-requested-at">
          Asked {timeAgo(request.requested_at)}
        </span>
      </div>

      <div className="vx-card p-5 sm:p-6" data-testid="approve-request-card">
        <h1 className="font-display text-xl font-semibold leading-snug text-foreground">
          {request.agent_name} wants to {String(request.what || "do something").toLowerCase()}
          {amount ? ` for ${amount}` : ""}
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Nothing has happened yet. The agent is stopped until you decide.
        </p>

        <div className="mt-5">
          <Row label="Agent">{request.agent_name}</Row>
          <Row label="Wants to">{request.what}</Row>
          {amount ? (
            <Row label="Amount">
              <span className="font-semibold text-foreground">{amount}</span>
            </Row>
          ) : null}
          {request.resource_id ? (
            <Row label="On" mono>
              {request.resource_id}
            </Row>
          ) : null}
          <Row label="Why it paused">{request.reason}</Row>
          <Row label="Workspace">{request.workspace}</Row>
        </div>

        <div className="mt-5">
          {showNote ? (
            <div className="space-y-1.5" data-testid="approve-note-field">
              <Label htmlFor="approve-note">Add a note (optional)</Label>
              <Textarea
                id="approve-note"
                value={note}
                onChange={(e) => setNote(e.target.value.slice(0, 400))}
                placeholder="Why you are saying yes or no — saved in the history."
                rows={3}
                data-testid="approve-note-input"
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowNote(true)}
              className="text-xs font-medium text-primary underline-offset-4 transition-colors hover:underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              data-testid="approve-add-note-button"
            >
              Add a note
            </button>
          )}
        </div>

        <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
          <Button
            className="h-12 flex-1 text-[15px]"
            disabled={busy}
            onClick={() => decide("approved")}
            data-testid="approve-approve-button"
          >
            <ShieldCheck className="mr-2 h-4 w-4" />
            {submitting === "approved" ? "Approving…" : "Approve once"}
          </Button>
          <Button
            variant="outline"
            className="h-12 flex-1 border-[hsl(var(--status-block)/0.4)] text-[15px] text-[hsl(var(--status-block))] hover:bg-[hsl(var(--status-block)/0.08)] hover:text-[hsl(var(--status-block))]"
            disabled={busy}
            onClick={() => decide("denied")}
            data-testid="approve-refuse-button"
          >
            <Ban className="mr-2 h-4 w-4" />
            {submitting === "denied" ? "Refusing…" : "Refuse"}
          </Button>
        </div>

        {intent === "approve" || intent === "refuse" ? (
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground" data-testid="approve-intent-hint">
            You tapped “{intent === "approve" ? "Approve once" : "Refuse"}” in the email. Confirm it
            above — we always ask once more so an email scanner can never decide for you.
          </p>
        ) : null}

        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          An approval lets the agent go ahead <strong className="text-foreground">once</strong>, within{" "}
          {request.valid_for_minutes} minutes. It cannot be reused.
        </p>

        {loadError ? (
          <p
            className="mt-3 text-xs text-[hsl(var(--status-block))]"
            data-testid="approve-error-message"
          >
            {loadError}
          </p>
        ) : null}
      </div>

      <div className="mt-4 text-center">
        <OpenConsoleButton url={consoleUrl} label="Open Vexen instead" />
      </div>
    </Shell>
  );
}
