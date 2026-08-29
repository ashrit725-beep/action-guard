import { useCallback, useEffect, useState } from "react";
import {
  Bell,
  Briefcase,
  Check,
  Laptop,
  LockKeyhole,
  LogOut,
  Trash2,
  User as UserIcon,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { PasswordField } from "@/pages/Login";
import {
  Explainer,
  HelpTip,
  KeyValue,
  PageHeader,
  SectionCard,
  Spinner,
} from "@/components/Common";
import { useAuth } from "@/context/AuthContext";
import { api, errorMessage } from "@/lib/api";
import { fullDate, initials, money, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

const NOTIFICATION_COPY = [
  {
    key: "approval_requests",
    title: "When an agent needs my OK",
    body: "The important one. Tells you something is paused and waiting.",
  },
  {
    key: "blocked_actions",
    title: "When an agent gets stopped",
    body: "Useful for spotting an agent that is trying things it should not.",
  },
  {
    key: "high_risk_agents",
    title: "When an agent becomes risky",
    body: "Alerts you if an agent quietly gains a lot of reach.",
  },
  {
    key: "weekly_digest",
    title: "A weekly summary",
    body: "One calm round-up instead of individual alerts.",
  },
];

export default function Settings() {
  const { user, organization, role, refreshUser } = useAuth();

  const [profile, setProfile] = useState({ name: "", job_title: "", timezone: "UTC" });
  const [savingProfile, setSavingProfile] = useState(false);

  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });
  const [savingPassword, setSavingPassword] = useState(false);

  const [prefs, setPrefs] = useState({
    approval_requests: true,
    blocked_actions: true,
    high_risk_agents: true,
    weekly_digest: false,
  });
  const [savingPrefs, setSavingPrefs] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [workspace, setWorkspace] = useState(null);
  const [members, setMembers] = useState([]);
  const [counts, setCounts] = useState({});
  const [workspaceForm, setWorkspaceForm] = useState({ name: "", industry: "" });
  const [defaults, setDefaults] = useState(null);
  const [savingWorkspace, setSavingWorkspace] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [sessionsRes, orgRes] = await Promise.all([
        api.get("/auth/sessions"),
        api.get("/organization"),
      ]);
      setSessions(sessionsRes.data?.items || []);
      const org = orgRes.data?.organization || null;
      setWorkspace(org);
      setMembers(orgRes.data?.members || []);
      setCounts(orgRes.data?.counts || {});
      setWorkspaceForm({ name: org?.name || "", industry: org?.industry || "" });
      setDefaults(
        org?.agent_defaults || {
          default_status: "active",
          default_purchase_limit: 100,
          default_temp_access_minutes: 60,
          require_approval_for_sensitive: true,
          block_payment_credentials: true,
        },
      );
    } catch (err) {
      toast.error(errorMessage(err, "Could not load your settings."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (user) {
      setProfile({
        name: user.name || "",
        job_title: user.job_title || "",
        timezone: user.timezone || "UTC",
      });
      setPrefs((p) => ({ ...p, ...(user.notification_prefs || {}) }));
    }
  }, [user]);

  const saveProfile = async () => {
    if (profile.name.trim().length < 2) {
      toast.error("Please enter your name.");
      return;
    }
    setSavingProfile(true);
    try {
      await api.patch("/auth/profile", {
        name: profile.name.trim(),
        job_title: profile.job_title.trim() || undefined,
        timezone: profile.timezone || undefined,
      });
      await refreshUser();
      toast.success("Saved");
    } catch (err) {
      toast.error(errorMessage(err, "Could not save your details."));
    } finally {
      setSavingProfile(false);
    }
  };

  const changePassword = async () => {
    if (!passwords.current_password || passwords.new_password.length < 10) {
      toast.error("Enter your current password and a new one with at least 10 characters.");
      return;
    }
    setSavingPassword(true);
    try {
      const { data } = await api.post("/auth/password", passwords);
      toast.success("Password changed", { description: data.message });
      setPasswords({ current_password: "", new_password: "" });
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not change your password."));
    } finally {
      setSavingPassword(false);
    }
  };

  const savePrefs = async (next) => {
    setPrefs(next);
    setSavingPrefs(true);
    try {
      await api.patch("/auth/notifications", next);
      await refreshUser();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save that preference."));
    } finally {
      setSavingPrefs(false);
    }
  };

  const revokeSession = async (sessionId, isCurrent) => {
    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      if (isCurrent) {
        toast.success("Signed out on this device");
        window.location.assign("/login");
        return;
      }
      toast.success("That device was signed out");
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not sign that device out."));
    }
  };

  const revokeOthers = async () => {
    try {
      const { data } = await api.post("/auth/sessions/revoke-others");
      toast.success(`${data.revoked} other device(s) signed out`);
      load();
    } catch (err) {
      toast.error(errorMessage(err, "Could not sign the other devices out."));
    }
  };

  const saveWorkspace = async () => {
    if (workspaceForm.name.trim().length < 2) {
      toast.error("Give your workspace a name.");
      return;
    }
    setSavingWorkspace(true);
    try {
      const { data } = await api.patch("/organization", {
        name: workspaceForm.name.trim(),
        industry: workspaceForm.industry.trim() || null,
        agent_defaults: defaults,
      });
      setWorkspace(data.organization);
      await refreshUser();
      toast.success("Workspace updated");
    } catch (err) {
      toast.error(errorMessage(err, "Could not update the workspace."));
    } finally {
      setSavingWorkspace(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Settings" testId="settings-header" />
        <Spinner label="Loading your settings…" />
      </div>
    );
  }

  const canEditWorkspace = role === "owner" || role === "admin";

  return (
    <div className="space-y-6" data-testid="settings-page">
      <PageHeader
        title="Settings"
        description="Your details, your password, the devices you are signed in on, and how your workspace behaves."
        testId="settings-header"
      />

      <Tabs defaultValue="account">
        <TabsList data-testid="settings-tabs">
          <TabsTrigger value="account" data-testid="settings-tab-account">
            My account
          </TabsTrigger>
          <TabsTrigger value="security" data-testid="settings-tab-security">
            Password & devices
          </TabsTrigger>
          <TabsTrigger value="notifications" data-testid="settings-tab-notifications">
            Alerts
          </TabsTrigger>
          <TabsTrigger value="workspace" data-testid="settings-tab-workspace">
            Workspace
          </TabsTrigger>
        </TabsList>

        {/* ------------------------------ Account ------------------------------ */}
        <TabsContent value="account" className="mt-5 space-y-5">
          <SectionCard title="Your details" icon={UserIcon} testId="settings-profile-card">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
              <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-primary/12 font-display text-xl font-bold text-primary">
                {initials(user?.name)}
              </span>
              <div className="grid flex-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="settings-name">Your name</Label>
                  <Input
                    id="settings-name"
                    value={profile.name}
                    onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                    maxLength={80}
                    data-testid="settings-name-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="settings-email">Email</Label>
                  <Input id="settings-email" value={user?.email || ""} disabled data-testid="settings-email-input" />
                  <p className="text-xs text-muted-foreground">
                    Your email cannot be changed here yet.
                  </p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="settings-title">
                    What you do <span className="text-muted-foreground">(optional)</span>
                  </Label>
                  <Input
                    id="settings-title"
                    value={profile.job_title}
                    onChange={(e) => setProfile((p) => ({ ...p, job_title: e.target.value }))}
                    maxLength={80}
                    placeholder="e.g. Small business owner"
                    data-testid="settings-title-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="settings-timezone">Time zone</Label>
                  <Input
                    id="settings-timezone"
                    value={profile.timezone}
                    onChange={(e) => setProfile((p) => ({ ...p, timezone: e.target.value }))}
                    maxLength={64}
                    placeholder="UTC"
                    data-testid="settings-timezone-input"
                  />
                </div>
              </div>
            </div>
            <Button
              onClick={saveProfile}
              disabled={savingProfile}
              className="mt-5"
              data-testid="settings-save-profile"
            >
              {savingProfile ? "Saving…" : "Save my details"}
            </Button>
          </SectionCard>

          <SectionCard title="Your workspace at a glance" icon={Briefcase} testId="settings-summary-card">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <KeyValue label="Workspace">{workspace?.name || "—"}</KeyValue>
              <KeyValue label="Your role">{role || "owner"}</KeyValue>
              <KeyValue label="Agents">{counts.agents ?? 0}</KeyValue>
              <KeyValue label="Recorded decisions">{counts.audit_events ?? 0}</KeyValue>
            </div>
          </SectionCard>
        </TabsContent>

        {/* ------------------------------ Security ----------------------------- */}
        <TabsContent value="security" className="mt-5 space-y-5">
          <Explainer
            title="Changing your password signs out your other devices"
            testId="settings-security-explainer"
          >
            <p>
              That is deliberate. If someone else had access, changing your password removes them
              straight away.
            </p>
          </Explainer>

          <SectionCard title="Change your password" icon={LockKeyhole} testId="settings-password-card">
            <div className="grid max-w-xl gap-4">
              <PasswordField
                id="settings-current-password"
                label="Current password"
                value={passwords.current_password}
                onChange={(e) => setPasswords((p) => ({ ...p, current_password: e.target.value }))}
                autoComplete="current-password"
                placeholder="The one you use now"
                testId="settings-current-password-input"
              />
              <PasswordField
                id="settings-new-password"
                label="New password"
                value={passwords.new_password}
                onChange={(e) => setPasswords((p) => ({ ...p, new_password: e.target.value }))}
                autoComplete="new-password"
                placeholder="At least 10 characters, with a capital, a small letter and a number"
                testId="settings-new-password-input"
              />
              <Button
                onClick={changePassword}
                disabled={savingPassword}
                className="justify-self-start"
                data-testid="settings-save-password"
              >
                {savingPassword ? "Updating…" : "Change my password"}
              </Button>
            </div>
          </SectionCard>

          <SectionCard
            title="Where you are signed in"
            description="Anything you do not recognise, sign it out."
            icon={Laptop}
            testId="settings-sessions-card"
            actions={
              sessions.filter((s) => !s.current && !s.revoked).length ? (
                <Button variant="outline" size="sm" onClick={revokeOthers} data-testid="settings-revoke-others">
                  <LogOut className="mr-1.5 h-3.5 w-3.5" /> Sign out everywhere else
                </Button>
              ) : null
            }
            bodyClassName="p-0"
          >
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Device</TableHead>
                    <TableHead>Location</TableHead>
                    <TableHead>Signed in</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id} data-testid="settings-session-row">
                      <TableCell className="max-w-[320px]">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm text-foreground">
                            {session.user_agent || "Unknown device"}
                          </span>
                          {session.current ? (
                            <span className="vx-chip shrink-0 border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]">
                              This one
                            </span>
                          ) : null}
                          {session.revoked ? (
                            <span className="vx-chip shrink-0 border-border bg-muted text-muted-foreground">
                              Signed out
                            </span>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell className="vx-mono whitespace-nowrap text-xs text-muted-foreground">
                        {session.ip || "—"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                        <span title={fullDate(session.created_at)}>{timeAgo(session.created_at)}</span>
                      </TableCell>
                      <TableCell className="text-right">
                        {session.revoked ? (
                          <span className="text-xs text-muted-foreground">—</span>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-[hsl(var(--status-block))]"
                            onClick={() => revokeSession(session.id, session.current)}
                            data-testid={`settings-revoke-${session.id}`}
                          >
                            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                            {session.current ? "Sign out" : "Remove"}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </SectionCard>
        </TabsContent>

        {/* --------------------------- Notifications --------------------------- */}
        <TabsContent value="notifications" className="mt-5">
          <SectionCard
            title="What should we tell you about?"
            description={savingPrefs ? "Saving…" : "Changes save as you flip them."}
            icon={Bell}
            testId="settings-notifications-card"
          >
            <ul className="divide-y divide-border">
              {NOTIFICATION_COPY.map((item) => (
                <li
                  key={item.key}
                  className="flex items-start justify-between gap-4 py-3.5 first:pt-0 last:pb-0"
                  data-testid={`settings-pref-${item.key}`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{item.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{item.body}</p>
                  </div>
                  <Switch
                    checked={Boolean(prefs[item.key])}
                    onCheckedChange={(next) => savePrefs({ ...prefs, [item.key]: next })}
                    aria-label={item.title}
                    data-testid={`settings-pref-switch-${item.key}`}
                  />
                </li>
              ))}
            </ul>
          </SectionCard>
        </TabsContent>

        {/* ------------------------------ Workspace ---------------------------- */}
        <TabsContent value="workspace" className="mt-5 space-y-5">
          <SectionCard title="Workspace" icon={Briefcase} testId="settings-workspace-card">
            {!canEditWorkspace ? (
              <p className="mb-4 text-sm text-muted-foreground">
                Only the workspace owner can change these settings.
              </p>
            ) : null}
            <div className="grid max-w-2xl gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="workspace-name">Workspace name</Label>
                <Input
                  id="workspace-name"
                  value={workspaceForm.name}
                  onChange={(e) => setWorkspaceForm((f) => ({ ...f, name: e.target.value }))}
                  maxLength={80}
                  disabled={!canEditWorkspace}
                  data-testid="settings-workspace-name-input"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="workspace-industry">
                  What you do <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Input
                  id="workspace-industry"
                  value={workspaceForm.industry}
                  onChange={(e) => setWorkspaceForm((f) => ({ ...f, industry: e.target.value }))}
                  maxLength={60}
                  disabled={!canEditWorkspace}
                  placeholder="e.g. Online shop"
                  data-testid="settings-workspace-industry-input"
                />
              </div>
            </div>
          </SectionCard>

          {defaults ? (
            <SectionCard
              title="Defaults for new agents"
              description="Applied whenever you add an agent, so you start safe by default."
              icon={Check}
              testId="settings-defaults-card"
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="default-limit" className="flex items-center gap-1.5">
                    Spending cap for new agents
                    <HelpTip text="Anything above this waits for your approval. Set it low; you can always raise it per agent." />
                  </Label>
                  <Input
                    id="default-limit"
                    type="number"
                    min="0"
                    value={defaults.default_purchase_limit}
                    onChange={(e) =>
                      setDefaults((d) => ({ ...d, default_purchase_limit: Number(e.target.value) }))
                    }
                    disabled={!canEditWorkspace}
                    data-testid="settings-default-limit-input"
                  />
                  <p className="text-xs text-muted-foreground">
                    Currently {money(defaults.default_purchase_limit) || "$0"}
                  </p>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="default-ttl" className="flex items-center gap-1.5">
                    Temporary access lasts (minutes)
                    <HelpTip text="When you grant access 'just for now', this is how long it lives before it expires by itself." />
                  </Label>
                  <Input
                    id="default-ttl"
                    type="number"
                    min="1"
                    value={defaults.default_temp_access_minutes}
                    onChange={(e) =>
                      setDefaults((d) => ({
                        ...d,
                        default_temp_access_minutes: Number(e.target.value),
                      }))
                    }
                    disabled={!canEditWorkspace}
                    data-testid="settings-default-ttl-input"
                  />
                </div>
              </div>

              <ul className="mt-5 divide-y divide-border">
                {[
                  {
                    key: "require_approval_for_sensitive",
                    title: "Always ask me before an agent touches something sensitive",
                    body: "Recommended. Sensitive means things like saved cards, secrets and personal records.",
                  },
                  {
                    key: "block_payment_credentials",
                    title: "Never let an agent read payment details",
                    body: "Strongly recommended. There is almost no good reason to switch this off.",
                  },
                ].map((item) => (
                  <li
                    key={item.key}
                    className="flex items-start justify-between gap-4 py-3.5 first:pt-0 last:pb-0"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{item.title}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                        {item.body}
                      </p>
                    </div>
                    <Switch
                      checked={Boolean(defaults[item.key])}
                      onCheckedChange={(next) => setDefaults((d) => ({ ...d, [item.key]: next }))}
                      disabled={!canEditWorkspace}
                      aria-label={item.title}
                      data-testid={`settings-default-switch-${item.key}`}
                    />
                  </li>
                ))}
              </ul>

              <Button
                onClick={saveWorkspace}
                disabled={savingWorkspace || !canEditWorkspace}
                className="mt-5"
                data-testid="settings-save-workspace"
              >
                {savingWorkspace ? "Saving…" : "Save workspace settings"}
              </Button>
            </SectionCard>
          ) : null}

          <SectionCard
            title="People in this workspace"
            icon={Users}
            testId="settings-members-card"
            bodyClassName="p-0"
          >
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead className="text-right">Joined</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {members.map((member) => (
                    <TableRow key={member.user_id} data-testid="settings-member-row">
                      <TableCell className="text-sm font-medium text-foreground">
                        {member.name}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">{member.email}</TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "vx-chip",
                            member.role === "owner"
                              ? "border-primary/30 bg-primary/10 text-primary"
                              : "border-border bg-muted text-muted-foreground",
                          )}
                        >
                          {member.role}
                        </span>
                      </TableCell>
                      <TableCell className="whitespace-nowrap text-right text-xs text-muted-foreground">
                        {timeAgo(member.joined_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            <p className="border-t border-border px-5 py-3 text-xs text-muted-foreground">
              Inviting other people is coming soon. Your workspace and everything in it is completely
              separate from every other workspace on Vexen.
            </p>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
