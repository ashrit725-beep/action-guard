import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Clock,
  Crown,
  Eye,
  Mail,
  MailPlus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  UserCog,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CardSkeleton,
  CopyButton,
  EmptyState,
  ErrorState,
  Explainer,
  PageHeader,
  SectionCard,
} from "@/components/Common";
import { useAuth } from "@/context/AuthContext";
import { api, errorMessage } from "@/lib/api";
import { fullDate, initials, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const ROLE_ICONS = {
  owner: Crown,
  admin: UserCog,
  approver: ShieldCheck,
  viewer: Eye,
};

const ROLE_TONE = {
  owner: "border-primary/35 bg-primary/12 text-primary",
  admin: "border-primary/25 bg-primary/8 text-primary",
  approver:
    "border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.12)] text-[hsl(var(--status-approval))]",
  viewer: "border-border bg-muted text-muted-foreground",
};

const RoleBadge = ({ role, label }) => {
  const Icon = ROLE_ICONS[role] || Eye;
  return (
    <Badge
      variant="outline"
      className={cn("gap-1 font-medium", ROLE_TONE[role] || ROLE_TONE.viewer)}
      data-testid={`team-role-badge-${role}`}
    >
      <Icon className="h-3 w-3" />
      {label || role}
    </Badge>
  );
};

export default function Team() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("approver");
  const [inviting, setInviting] = useState(false);
  const [lastLink, setLastLink] = useState(null);

  const [removing, setRemoving] = useState(null);
  const [busyId, setBusyId] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const res = await api.get("/team");
      setData(res.data);
      const invitable = res.data?.can_invite || [];
      if (invitable.length && !invitable.some((r) => r.value === inviteRole)) {
        setInviteRole(invitable[0].value);
      }
    } catch (err) {
      setError(errorMessage(err, "Could not load your team."));
    } finally {
      setLoading(false);
    }
    // inviteRole is intentionally omitted: we only seed it on first load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const canInvite = useMemo(() => (data?.can_invite || []).length > 0, [data]);
  const canManage = Boolean(data?.can_manage_people);

  const submitInvite = async (e) => {
    e?.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      const res = await api.post("/team/invites", {
        email: inviteEmail.trim().toLowerCase(),
        role: inviteRole,
      });
      setLastLink({ email: inviteEmail.trim().toLowerCase(), url: res.data.join_url });
      setInviteEmail("");
      setInviteOpen(false);
      toast.success("Invitation sent", { description: res.data.message });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not send that invitation."));
    } finally {
      setInviting(false);
    }
  };

  const resend = async (invite) => {
    setBusyId(invite.id);
    try {
      const res = await api.post(`/team/invites/${invite.id}/resend`);
      setLastLink({ email: invite.email, url: res.data.join_url });
      toast.success("Sent again", { description: res.data.message });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not send that invitation again."));
    } finally {
      setBusyId("");
    }
  };

  const revoke = async (invite) => {
    setBusyId(invite.id);
    try {
      const res = await api.delete(`/team/invites/${invite.id}`);
      toast.success("Invitation cancelled", { description: res.data.message });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not cancel that invitation."));
    } finally {
      setBusyId("");
    }
  };

  const changeRole = async (member, role) => {
    setBusyId(member.user_id);
    try {
      const res = await api.patch(`/team/members/${member.user_id}`, { role });
      toast.success("Role changed", { description: res.data.message });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not change that role."));
    } finally {
      setBusyId("");
    }
  };

  const confirmRemove = async () => {
    if (!removing) return;
    setBusyId(removing.user_id);
    try {
      const res = await api.delete(`/team/members/${removing.user_id}`);
      toast.success("Removed", { description: res.data.message });
      setRemoving(null);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not remove that person."));
    } finally {
      setBusyId("");
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="team-loading">
        <PageHeader title="My team" testId="team-header" />
        <CardSkeleton count={3} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="My team" testId="team-header" />
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  const members = data?.members || [];
  const invites = data?.invites || [];
  const roles = data?.roles || [];

  return (
    <div className="space-y-6" data-testid="team-page">
      <PageHeader
        title="My team"
        description="Bring in the people who should see what your agents are doing — and who is allowed to say yes."
        testId="team-header"
        actions={
          canInvite ? (
            <Button onClick={() => setInviteOpen(true)} data-testid="team-invite-button">
              <UserPlus className="mr-1.5 h-4 w-4" /> Invite someone
            </Button>
          ) : null
        }
      />

      {lastLink ? (
        <div
          className="vx-card flex flex-col gap-3 border-primary/25 bg-accent/40 p-4 sm:flex-row sm:items-center sm:justify-between"
          data-testid="team-invite-link-card"
        >
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              Invitation link for {lastLink.email}
            </p>
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
              We emailed it. If it does not arrive, send them this link yourself — it works for 7
              days.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <CopyButton value={lastLink.url} label="Copy link" testId="team-copy-invite-link" />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setLastLink(null)}
              data-testid="team-dismiss-invite-link"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : null}

      <SectionCard
        title={`People in ${data?.workspace_name || "this workspace"}`}
        description={`${members.length} ${members.length === 1 ? "person" : "people"} · you are ${
          roles.find((r) => r.value === data?.your_role)?.label || data?.your_role
        }`}
        icon={Users}
        testId="team-members-card"
      >
        <ul className="divide-y divide-border">
          {members.map((member) => (
            <li
              key={member.user_id}
              className="flex flex-wrap items-center gap-3 py-3.5 first:pt-0 last:pb-0"
              data-testid="team-member-row"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-[11px] font-bold text-primary">
                {initials(member.name)}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">
                  {member.name}
                  {member.is_you ? (
                    <span className="ml-1.5 text-xs font-normal text-muted-foreground">(you)</span>
                  ) : null}
                </p>
                <p className="truncate text-xs text-muted-foreground">{member.email}</p>
              </div>
              <span className="hidden text-xs text-muted-foreground sm:block">
                {member.last_login_at
                  ? `Last seen ${timeAgo(member.last_login_at)}`
                  : member.joined_at
                    ? `Joined ${timeAgo(member.joined_at)}`
                    : ""}
              </span>
              <RoleBadge role={member.role} label={member.role_label} />
              {canManage && !member.is_you && member.role !== "owner" ? (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busyId === member.user_id}
                      data-testid="team-member-menu"
                    >
                      Manage
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-64">
                    <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
                      Change what {member.name?.split(" ")[0] || "they"} can do
                    </DropdownMenuLabel>
                    {roles
                      .filter((r) => r.value !== "owner")
                      .map((r) => (
                        <DropdownMenuItem
                          key={r.value}
                          disabled={r.value === member.role}
                          onClick={() => changeRole(member, r.value)}
                          data-testid={`team-set-role-${r.value}`}
                        >
                          <div>
                            <p className="text-sm text-foreground">
                              {r.label}
                              {r.value === member.role ? " · current" : ""}
                            </p>
                            <p className="text-[11px] leading-snug text-muted-foreground">
                              {r.summary}
                            </p>
                          </div>
                        </DropdownMenuItem>
                      ))}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      onClick={() => setRemoving(member)}
                      className="text-[hsl(var(--status-block))] focus:text-[hsl(var(--status-block))]"
                      data-testid="team-remove-member"
                    >
                      <Trash2 className="mr-2 h-4 w-4" /> Remove from workspace
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              ) : null}
            </li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard
        title="Waiting to join"
        description="Invitations that have been sent but not accepted yet."
        icon={MailPlus}
        testId="team-invites-card"
      >
        {invites.length === 0 ? (
          <EmptyState
            icon={Mail}
            title="Nobody is waiting"
            description={
              canInvite
                ? "Invite a colleague and their invitation will show up here until they join."
                : "Only owners and admins can invite people."
            }
            action={
              canInvite ? (
                <Button size="sm" onClick={() => setInviteOpen(true)} data-testid="team-invite-empty-button">
                  <UserPlus className="mr-1.5 h-4 w-4" /> Invite someone
                </Button>
              ) : null
            }
            testId="team-invites-empty"
          />
        ) : (
          <ul className="divide-y divide-border">
            {invites.map((invite) => (
              <li
                key={invite.id}
                className="flex flex-wrap items-center gap-3 py-3.5 first:pt-0 last:pb-0"
                data-testid="team-invite-row"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Clock className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">{invite.email}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    Invited {timeAgo(invite.created_at)}
                    {invite.invited_by ? ` by ${invite.invited_by}` : ""} ·{" "}
                    {invite.expired ? "expired" : `expires ${fullDate(invite.expires_at)}`}
                  </p>
                </div>
                <RoleBadge role={invite.role} label={invite.role_label} />
                {canInvite ? (
                  <div className="flex gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={busyId === invite.id}
                      onClick={() => resend(invite)}
                      data-testid="team-resend-invite"
                    >
                      <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Send again
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={busyId === invite.id}
                      onClick={() => revoke(invite)}
                      className="text-[hsl(var(--status-block))] hover:text-[hsl(var(--status-block))]"
                      data-testid="team-revoke-invite"
                    >
                      Cancel
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <Explainer
        title="What each role can do"
        points={roles.map((r) => `${r.label} — ${r.summary}`)}
        testId="team-roles-explainer"
      >
        One account belongs to one workspace, so the address you invite must not already have a Vexen
        account. Anybody who can approve will also get the approval emails, unless they switch them
        off in their own Settings.
      </Explainer>

      {/* ------------------------------ Invite dialog ------------------------------ */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent className="sm:max-w-lg" data-testid="team-invite-dialog">
          <DialogHeader>
            <DialogTitle>Invite someone to {user?.name ? "your workspace" : "Vexen"}</DialogTitle>
            <DialogDescription>
              They get an email with a link. Their account is created inside this workspace when they
              accept.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={submitInvite} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="invite-email">Their email</Label>
              <Input
                id="invite-email"
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@company.com"
                data-testid="team-invite-email-input"
              />
            </div>
            <div className="space-y-2">
              <Label>What should they be allowed to do?</Label>
              <div className="grid gap-2">
                {(data?.can_invite || []).map((r) => {
                  const Icon = ROLE_ICONS[r.value] || Eye;
                  const selected = inviteRole === r.value;
                  return (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setInviteRole(r.value)}
                      aria-pressed={selected}
                      className={cn(
                        "flex items-start gap-3 rounded-lg border px-3.5 py-3 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                        selected
                          ? "border-primary/50 bg-primary/8"
                          : "border-border hover:bg-muted",
                      )}
                      data-testid={`team-invite-role-${r.value}`}
                    >
                      <Icon
                        className={cn(
                          "mt-0.5 h-4 w-4 shrink-0",
                          selected ? "text-primary" : "text-muted-foreground",
                        )}
                      />
                      <span className="min-w-0">
                        <span className="block text-sm font-medium text-foreground">{r.label}</span>
                        <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground">
                          {r.summary}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setInviteOpen(false)}
                data-testid="team-invite-cancel"
              >
                Cancel
              </Button>
              <Button type="submit" disabled={inviting} data-testid="team-invite-submit">
                {inviting ? "Sending…" : "Send invitation"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* ------------------------------ Remove person ------------------------------ */}
      <AlertDialog open={Boolean(removing)} onOpenChange={(open) => !open && setRemoving(null)}>
        <AlertDialogContent data-testid="team-remove-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {removing?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              They are signed out straight away and lose access to this workspace. Your agents, rules
              and history are not affected. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="team-remove-cancel">Keep them</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRemove}
              className="bg-[hsl(var(--status-block))] text-white hover:bg-[hsl(var(--status-block)/0.9)]"
              data-testid="team-remove-confirm"
            >
              Remove them
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
