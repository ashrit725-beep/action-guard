import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Check, Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthFrame, PasswordField } from "@/pages/Login";
import { useAuth } from "@/context/AuthContext";
import { errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const RULES = [
  { label: "10 characters or more", test: (p) => p.length >= 10 },
  { label: "A capital letter", test: (p) => /[A-Z]/.test(p) },
  { label: "A small letter", test: (p) => /[a-z]/.test(p) },
  { label: "A number", test: (p) => /\d/.test(p) },
];

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const checks = useMemo(
    () => RULES.map((r) => ({ ...r, ok: r.test(form.password) })),
    [form.password],
  );
  const allOk = checks.every((c) => c.ok);

  const update = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (!allOk) {
      setError("Please pick a password that meets all four points below.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      try {
        sessionStorage.setItem("vexen.onboarding", "1");
      } catch (e) {
        /* private browsing — the dashboard has a "Start here" panel as a fallback */
      }
      await signup({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      toast.success("Your account is ready", {
        description: "Next: pick your first agent from the library.",
      });
      navigate("/app/guide", { replace: true });
    } catch (err) {
      const message = errorMessage(err, "Could not create your account.");
      setError(message);
      toast.error(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthFrame
      title="Create your free account"
      subtitle="Just your name, email and a password. Nothing else needed."
      aside={
        <div className="vx-explainer">
          <div className="flex items-start gap-2.5">
            <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <p className="text-xs leading-relaxed text-foreground/80">
              Your workspace starts empty and completely locked down — nothing can act until you say
              so. Then pick from over 10,000 ready-made agents whenever you are ready.
            </p>
          </div>
        </div>
      }
      footer={
        <>
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-semibold text-primary underline-offset-4 hover:underline"
            data-testid="signup-to-login"
          >
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" data-testid="signup-form">
        <div className="space-y-1.5">
          <Label htmlFor="signup-name">Your name</Label>
          <Input
            id="signup-name"
            value={form.name}
            onChange={update("name")}
            required
            minLength={2}
            maxLength={80}
            autoComplete="name"
            placeholder="Alex Morgan"
            data-testid="signup-name-input"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="signup-email">Email</Label>
          <Input
            id="signup-email"
            type="email"
            value={form.email}
            onChange={update("email")}
            required
            autoComplete="email"
            placeholder="you@example.com"
            data-testid="signup-email-input"
          />
        </div>
        <PasswordField
          id="signup-password"
          label="Password"
          value={form.password}
          onChange={update("password")}
          autoComplete="new-password"
          placeholder="Pick something hard to guess"
          testId="signup-password-input"
        />

        <ul className="grid grid-cols-2 gap-1.5" data-testid="password-rules">
          {checks.map((c) => (
            <li
              key={c.label}
              className={cn(
                "flex items-center gap-1.5 text-[11px]",
                c.ok ? "text-[hsl(var(--status-allow))]" : "text-muted-foreground",
              )}
            >
              {c.ok ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
              {c.label}
            </li>
          ))}
        </ul>

        {error ? (
          <p
            className="rounded-lg border border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.08)] px-3 py-2 text-xs text-[hsl(var(--status-block))]"
            data-testid="signup-error"
          >
            {error}
          </p>
        ) : null}

        <Button type="submit" className="w-full" disabled={busy} data-testid="signup-submit-button">
          {busy ? "Setting things up…" : "Create my account"}
          {!busy ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
        </Button>
      </form>
    </AuthFrame>
  );
}
