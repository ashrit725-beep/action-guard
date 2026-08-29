import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { AlertCircle, Crown, Eye, LinkIcon, ShieldCheck, UserCog } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Wordmark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/context/AuthContext";
import { errorMessage, tokens } from "@/lib/api";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

/* Opened from an invitation email, so there is no session yet. */
const publicApi = axios.create({
  baseURL: `${BACKEND_URL}/api/public`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

const ROLE_ICONS = { owner: Crown, admin: UserCog, approver: ShieldCheck, viewer: Eye };

const Shell = ({ children }) => (
  <div className="min-h-screen bg-background">
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 w-full max-w-md items-center justify-between px-4">
        <Wordmark showTagline />
        <ThemeToggle />
      </div>
    </header>
    <main className="mx-auto w-full max-w-md px-4 py-8 sm:py-12">{children}</main>
  </div>
);

export default function JoinWorkspace() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  const [invite, setInvite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [gone, setGone] = useState(false);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setGone(false);
    setLoadError("");
    try {
      const { data } = await publicApi.get(`/invites/${encodeURIComponent(token)}`);
      setInvite(data);
    } catch (err) {
      if (err?.response?.status === 404) {
        setGone(true);
        setLoadError(errorMessage(err, "This invitation link is no longer valid."));
      } else {
        setLoadError(errorMessage(err, "We could not load this invitation."));
      }
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const accept = async (e) => {
    e.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      const { data } = await publicApi.post(`/invites/${encodeURIComponent(token)}/accept`, {
        name: name.trim(),
        password,
      });
      tokens.set({ access_token: data.access_token, refresh_token: data.refresh_token });
      await refreshUser();
      toast.success(`Welcome to ${data.organization?.name}`, {
        description: "You are signed in. Start with the guide if this is new to you.",
      });
      navigate("/app/guide", { replace: true });
    } catch (err) {
      setFormError(errorMessage(err, "We could not finish setting up your account."));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Shell>
        <div className="vx-card p-6" data-testid="join-loading">
          <Skeleton className="h-5 w-44" />
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-6 h-10 w-full" />
          <Skeleton className="mt-3 h-10 w-full" />
          <Skeleton className="mt-5 h-11 w-full" />
        </div>
      </Shell>
    );
  }

  if (gone || (invite && invite.state !== "pending")) {
    const copy = {
      accepted: "This invitation has already been used. Try signing in instead.",
      revoked: "This invitation was cancelled. Ask for a new one.",
      expired: "This invitation has expired. Ask whoever invited you to send another.",
    };
    return (
      <Shell>
        <div className="vx-card p-6 text-center sm:p-8" data-testid="join-unavailable">
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <LinkIcon className="h-6 w-6" />
          </span>
          <h1 className="font-display text-lg font-semibold text-foreground">
            This invitation cannot be used
          </h1>
          <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
            {copy[invite?.state] || loadError}
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Button asChild size="sm" data-testid="join-signin-link">
              <Link to="/login">Sign in</Link>
            </Button>
            <Button asChild variant="outline" size="sm" data-testid="join-home-link">
              <Link to="/">Vexen home</Link>
            </Button>
          </div>
        </div>
      </Shell>
    );
  }

  if (!invite) {
    return (
      <Shell>
        <div className="vx-card p-6 text-center sm:p-8" data-testid="join-error">
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-[hsl(var(--status-block)/0.12)] text-[hsl(var(--status-block))]">
            <AlertCircle className="h-6 w-6" />
          </span>
          <h1 className="font-display text-lg font-semibold text-foreground">
            We could not load this
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">{loadError}</p>
          <Button size="sm" className="mt-5" onClick={load} data-testid="join-retry">
            Try again
          </Button>
        </div>
      </Shell>
    );
  }

  const RoleIcon = ROLE_ICONS[invite.role] || Eye;

  return (
    <Shell>
      <div className="vx-card p-6 sm:p-7" data-testid="join-card">
        <Badge variant="outline" className="gap-1 border-primary/35 bg-primary/10 text-primary">
          <RoleIcon className="h-3 w-3" />
          {invite.role_label}
        </Badge>
        <h1 className="mt-3 font-display text-xl font-semibold leading-snug text-foreground">
          Join {invite.workspace} on Vexen
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          {invite.invited_by ? `${invite.invited_by} invited you. ` : ""}
          {invite.role_summary}
        </p>

        <div className="mt-5 rounded-lg border border-border bg-muted/40 px-3.5 py-3">
          <p className="vx-label">Your sign-in address</p>
          <p className="mt-1 break-all text-sm text-foreground" data-testid="join-email">
            {invite.email}
          </p>
        </div>

        <form onSubmit={accept} className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="join-name">Your name</Label>
            <Input
              id="join-name"
              required
              minLength={2}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Morgan"
              autoComplete="name"
              data-testid="join-name-input"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="join-password">Choose a password</Label>
            <Input
              id="join-password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              autoComplete="new-password"
              data-testid="join-password-input"
            />
            <p className="text-xs text-muted-foreground">
              Use upper and lower case letters plus a number.
            </p>
          </div>

          {formError ? (
            <p className="text-xs text-[hsl(var(--status-block))]" data-testid="join-form-error">
              {formError}
            </p>
          ) : null}

          <Button
            type="submit"
            className="h-11 w-full"
            disabled={submitting}
            data-testid="join-submit"
          >
            {submitting ? "Setting up…" : `Join ${invite.workspace}`}
          </Button>
        </form>

        <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
          Already have a Vexen account?{" "}
          <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Sign in instead
          </Link>
          . One account belongs to one workspace.
        </p>
      </div>
    </Shell>
  );
}
