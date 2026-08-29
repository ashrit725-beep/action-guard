import { Link, NavLink, Outlet } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const LINKS = [
  { to: "/", label: "Product", end: true, testId: "marketing-nav-product" },
  { to: "/contact", label: "Contact", testId: "marketing-nav-contact" },
];

export default function MarketingLayout() {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:px-6">
          <Wordmark testId="marketing-wordmark" />
          <nav className="ml-4 hidden items-center gap-1 md:flex">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                data-testid={l.testId}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium transition-colors duration-150",
                    isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
            <ThemeToggle />
            {isAuthenticated ? (
              <Button asChild size="sm" data-testid="marketing-open-console">
                <Link to="/app">
                  Open console <ArrowRight className="ml-1.5 hidden h-4 w-4 sm:inline" />
                </Link>
              </Button>
            ) : (
              <>
                {/* On a 320px phone there is not room for both, so the quiet
                    link steps aside and the primary action gets shorter. */}
                <Button
                  asChild
                  variant="ghost"
                  size="sm"
                  className="hidden xs:inline-flex"
                  data-testid="marketing-signin"
                >
                  <Link to="/login">Sign in</Link>
                </Button>
                <Button asChild size="sm" data-testid="marketing-signup">
                  <Link to="/signup">
                    <span className="xs:hidden">Sign up</span>
                    <span className="hidden xs:inline">Create an Agent</span>
                  </Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-card">
        <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <Wordmark showTagline testId="footer-wordmark" />
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Vexen sits in front of your AI agents and decides, every single time, whether what they
              are about to do is actually allowed.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-12 gap-y-6 sm:grid-cols-3">
            <div>
              <p className="vx-label">Product</p>
              <ul className="mt-3 space-y-2 text-sm">
                <li>
                  <Link to="/" className="text-muted-foreground transition-colors hover:text-foreground">
                    Overview
                  </Link>
                </li>
                <li>
                  <Link
                    to="/app/guide"
                    className="text-muted-foreground transition-colors hover:text-foreground"
                  >
                    How it works
                  </Link>
                </li>
                <li>
                  <Link to="/app/developers" className="text-muted-foreground transition-colors hover:text-foreground">
                    For developers
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <p className="vx-label">How you stay safe</p>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                <li>Starts from &ldquo;no&rdquo;</li>
                <li>Your rules always win</li>
                <li>History you can verify</li>
              </ul>
            </div>
            <div>
              <p className="vx-label">Company</p>
              <ul className="mt-3 space-y-2 text-sm">
                <li>
                  <Link to="/contact" className="text-muted-foreground transition-colors hover:text-foreground">
                    Contact
                  </Link>
                </li>
                <li>
                  <Link to="/signup" className="text-muted-foreground transition-colors hover:text-foreground">
                    Get started
                  </Link>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div className="border-t border-border">
          <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <span>© {new Date().getFullYear()} Vexen. Security for AI agents.</span>
            <span className="vx-mono">Founded by Ashrit Talluri &amp; Aditya Mirchandani</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
