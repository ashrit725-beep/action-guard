import { useCallback, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  Bot,
  BookOpen,
  ChevronsUpDown,
  Code2,
  LayoutDashboard,
  LogOut,
  Menu,
  Scale,
  ScrollText,
  Settings as SettingsIcon,
  ShieldAlert,
  ShieldCheck,
  User as UserIcon,
  Wand2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AssistantWidget } from "@/components/AssistantWidget";
import { Wordmark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { initials, timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Navigation uses plain, everyday words on purpose. The URLs stay stable, but
 * nobody should need to know what "audit" or "policy" means to use Vexen.
 */
const NAV = [
  { to: "/app", label: "Home", icon: LayoutDashboard, testId: "sidebar-nav-overview", end: true },
  { to: "/app/guide", label: "How to use Vexen", icon: BookOpen, testId: "sidebar-nav-guide" },
  { to: "/app/agents", label: "My agents", icon: Bot, testId: "sidebar-nav-agents" },
  { to: "/app/try", label: "Try an action", icon: Wand2, testId: "sidebar-nav-try" },
  {
    to: "/app/approvals",
    label: "Waiting for you",
    icon: ShieldAlert,
    testId: "sidebar-nav-approvals",
    counter: "approvals",
  },
  { to: "/app/policies", label: "Rules", icon: Scale, testId: "sidebar-nav-policies" },
  { to: "/app/audit", label: "History", icon: ScrollText, testId: "sidebar-nav-audit" },
  {
    to: "/app/security",
    label: "Safety check",
    icon: ShieldCheck,
    testId: "sidebar-nav-security",
    counter: "findings",
  },
  { to: "/app/developers", label: "For developers", icon: Code2, testId: "sidebar-nav-developers" },
  { to: "/app/settings", label: "Settings", icon: SettingsIcon, testId: "sidebar-nav-settings" },
];

const NavItems = ({ counts, onNavigate }) => (
  <nav className="flex flex-col gap-0.5" aria-label="Vexen navigation">
    {NAV.map(({ to, label, icon: Icon, testId, end, counter }) => {
      const count = counter ? counts[counter] : 0;
      return (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={onNavigate}
          data-testid={testId}
          className={({ isActive }) =>
            cn(
              "group flex min-h-[44px] items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
              isActive
                ? "bg-primary/12 text-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className={cn("h-[17px] w-[17px] shrink-0", isActive && "text-primary")} />
              <span className="flex-1 truncate">{label}</span>
              {count > 0 ? (
                <span
                  className="vx-mono rounded-full border border-[hsl(var(--status-approval)/0.4)] bg-[hsl(var(--status-approval)/0.14)] px-1.5 text-[10px] font-bold text-[hsl(var(--status-approval))]"
                  data-testid={`sidebar-count-${counter}`}
                >
                  {count}
                </span>
              ) : null}
            </>
          )}
        </NavLink>
      );
    })}
  </nav>
);

export default function AppShell() {
  const { user, organization, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [counts, setCounts] = useState({ approvals: 0, findings: 0, unread: 0 });
  const [notifications, setNotifications] = useState([]);
  const [mobileOpen, setMobileOpen] = useState(false);

  const loadCounts = useCallback(async () => {
    try {
      const [approvals, notif, security] = await Promise.all([
        api.get("/approvals", { params: { status: "pending", limit: 1 } }),
        api.get("/notifications", { params: { limit: 12 } }),
        api.get("/security"),
      ]);
      setCounts({
        approvals: approvals.data?.counts?.pending || 0,
        findings:
          (security.data?.counts?.by_severity?.critical || 0) +
          (security.data?.counts?.by_severity?.high || 0),
        unread: notif.data?.unread || 0,
      });
      setNotifications(notif.data?.items || []);
    } catch (e) {
      /* non-critical chrome */
    }
  }, []);

  useEffect(() => {
    loadCounts();
  }, [loadCounts, location.pathname]);

  useEffect(() => {
    const id = setInterval(loadCounts, 30000);
    return () => clearInterval(id);
  }, [loadCounts]);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const markRead = async () => {
    try {
      await api.post("/notifications/read");
      setCounts((c) => ({ ...c, unread: 0 }));
    } catch (e) {
      /* ignore */
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[268px] flex-col border-r border-border bg-card lg:flex">
        <div className="flex h-16 items-center border-b border-border px-5">
          <Wordmark to="/app" showTagline testId="sidebar-wordmark" />
        </div>
        <ScrollArea className="flex-1 px-3 py-4">
          <NavItems counts={counts} />
          <div className="mt-6 rounded-xl border border-primary/20 bg-accent/50 p-3.5">
            <p className="font-display text-[13px] font-semibold text-foreground">
              The one rule to remember
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-foreground/75">
              If Vexen cannot prove an agent is allowed to do something, it says
              <span className="font-semibold text-foreground"> no</span>. You never have to list
              everything you want to prevent.
            </p>
            <Link
              to="/app/guide"
              className="mt-1.5 inline-flex min-h-[32px] items-center text-xs font-semibold text-primary underline-offset-4 hover:underline"
              data-testid="sidebar-guide-link"
            >
              Show me how it works
            </Link>
          </div>
        </ScrollArea>
        <div className="border-t border-border p-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left transition-colors duration-150 hover:bg-muted"
                data-testid="sidebar-user-menu"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/12 text-[11px] font-bold text-primary">
                  {initials(user?.name)}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-foreground">{user?.name}</span>
                  <span className="block truncate text-xs text-muted-foreground">
                    {organization?.name}
                  </span>
                </span>
                <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-60">
              <DropdownMenuLabel className="truncate text-xs font-normal text-muted-foreground">
                {user?.email}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/app/settings")} data-testid="menu-profile">
                <UserIcon className="mr-2 h-4 w-4" /> My account
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/app/guide")} data-testid="menu-guide">
                <BookOpen className="mr-2 h-4 w-4" /> How to use Vexen
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate("/")} data-testid="menu-marketing">
                <ShieldCheck className="mr-2 h-4 w-4" /> Vexen home page
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} data-testid="menu-logout">
                <LogOut className="mr-2 h-4 w-4" /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      <div className="lg:pl-[268px]">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur sm:px-6 lg:px-8">
          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="lg:hidden"
                aria-label="Open navigation"
                data-testid="mobile-nav-trigger"
              >
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-[280px] bg-card p-0">
              <div className="flex h-16 items-center border-b border-border px-5">
                <Wordmark to="/app" showTagline testId="mobile-wordmark" />
              </div>
              <ScrollArea className="h-[calc(100vh-64px)] p-3">
                <NavItems counts={counts} onNavigate={() => setMobileOpen(false)} />
              </ScrollArea>
            </SheetContent>
          </Sheet>

          <div className="min-w-0 flex-1">
            <span className="hidden truncate text-sm text-muted-foreground sm:inline">
              {organization?.name}
            </span>
            <span className="sm:hidden">
              <Wordmark to="/app" testId="topbar-wordmark" />
            </span>
          </div>

          <DropdownMenu onOpenChange={(open) => open && counts.unread > 0 && markRead()}>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                aria-label="Notifications"
                data-testid="notifications-trigger"
              >
                <Bell className="h-[18px] w-[18px]" />
                {counts.unread > 0 ? (
                  <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-[hsl(var(--status-approval))]" />
                ) : null}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[340px] p-0">
              <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
                <span className="font-display text-sm font-semibold">Notifications</span>
                <span className="vx-mono text-[10px] text-muted-foreground">
                  {notifications.length} recent
                </span>
              </div>
              <div className="max-h-[340px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <p className="px-3 py-6 text-center text-xs leading-relaxed text-muted-foreground">
                    Nothing yet. If an agent needs your approval, or gets stopped doing something
                    risky, you will see it here.
                  </p>
                ) : (
                  notifications.map((n) => (
                    <Link
                      key={n.id}
                      to={n.link || "/app/audit"}
                      className="block border-b border-border/60 px-3 py-2.5 transition-colors duration-150 last:border-0 hover:bg-muted/60"
                      data-testid="notification-item"
                    >
                      <div className="flex items-start gap-2">
                        <span
                          className={cn(
                            "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                            n.severity === "danger"
                              ? "bg-[hsl(var(--status-block))]"
                              : n.severity === "warning"
                                ? "bg-[hsl(var(--status-approval))]"
                                : "bg-primary",
                          )}
                        />
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium text-foreground">{n.title}</p>
                          <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
                            {n.body}
                          </p>
                          <p className="vx-mono mt-1 text-[10px] text-muted-foreground">
                            {timeAgo(n.created_at)}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          <ThemeToggle />

          <Button
            size="sm"
            onClick={() => navigate("/app/try")}
            className="hidden sm:inline-flex"
            data-testid="topbar-try-action"
          >
            <Wand2 className="mr-1.5 h-4 w-4" /> Try an action
          </Button>
        </header>

        <main className="mx-auto w-full max-w-[1400px] px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:py-8 lg:pb-24">
          <Outlet context={{ refreshCounts: loadCounts }} />
        </main>

        <AssistantWidget />
      </div>
    </div>
  );
}
