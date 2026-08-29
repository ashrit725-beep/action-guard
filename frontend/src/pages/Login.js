import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Wordmark } from "@/components/Brand";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/lib/api";

export const AuthFrame = ({ title, subtitle, children, footer, aside }) => (
  <div className="relative flex min-h-screen flex-col bg-background">
    <div className="vx-hero-glow pointer-events-none absolute inset-x-0 top-0 h-[340px]" aria-hidden="true" />
    <header className="relative flex h-16 items-center justify-between px-4 sm:px-6">
      <Wordmark testId="auth-wordmark" />
      <ThemeToggle />
    </header>
    <main className="relative flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
      <div className="w-full max-w-[440px]">
        <div className="vx-card p-6 sm:p-8">
          <span className="vx-chip border-primary/30 bg-primary/10 text-primary">
            <ShieldCheck className="h-3.5 w-3.5" /> Vexen
          </span>
          <h1 className="mt-4 font-display text-[26px] font-bold tracking-tight text-foreground">
            {title}
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{subtitle}</p>
          <div className="mt-6">{children}</div>
        </div>
        {aside ? <div className="mt-4">{aside}</div> : null}
        {footer ? <div className="mt-5 text-center text-sm text-muted-foreground">{footer}</div> : null}
      </div>
    </main>
  </div>
);

export const PasswordField = ({ id, value, onChange, label, testId, autoComplete, placeholder }) => {
  const [visible, setVisible] = useState(false);
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={onChange}
          required
          autoComplete={autoComplete}
          placeholder={placeholder}
          className="pr-10"
          data-testid={testId}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-1 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          aria-label={visible ? "Hide password" : "Show password"}
          data-testid={`${testId}-toggle`}
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
};

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(
    params.get("expired") ? "You were signed out for security. Please sign in again." : "",
  );

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      toast.success("Welcome back");
      navigate(location.state?.from || "/app", { replace: true });
    } catch (err) {
      const message = errorMessage(err, "Could not sign you in.");
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame
      title="Welcome back"
      subtitle="Sign in to see what your AI agents have been doing."
      footer={
        <>
          New here?{" "}
          <Link
            to="/signup"
            className="font-semibold text-primary underline-offset-4 hover:underline"
            data-testid="login-to-signup"
          >
            Create a free account
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" data-testid="login-form">
        <div className="space-y-1.5">
          <Label htmlFor="login-email">Email</Label>
          <Input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="you@example.com"
            data-testid="login-email-input"
          />
        </div>
        <PasswordField
          id="login-password"
          label="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          placeholder="Your password"
          testId="login-password-input"
        />
        {error ? (
          <p
            className="rounded-lg border border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.08)] px-3 py-2 text-xs text-[hsl(var(--status-block))]"
            data-testid="login-error"
          >
            {error}
          </p>
        ) : null}
        <Button type="submit" className="w-full" disabled={busy} data-testid="login-submit-button">
          {busy ? "Signing in…" : "Sign in"}
          {!busy ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
        </Button>
      </form>
    </AuthFrame>
  );
}
