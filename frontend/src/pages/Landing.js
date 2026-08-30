import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BadgeCheck,
  CheckCircle2,
  Clock,
  Fingerprint,
  Gauge,
  KeyRound,
  Layers,
  Library,
  PlayCircle,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  Wallet,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DecisionBadge } from "@/components/StatusBadges";
import { DecisionTrace } from "@/components/DecisionTrace";

const PIPELINE = ["Who is asking", "What it may do", "Your rules", "Answer", "Written down"];

const SAMPLE_TRACE = [
  { step: "identity", label: "Is this really that agent?", status: "pass", detail: "Yes — key checks out." },
  { step: "agent_status", label: "Is the agent switched on?", status: "pass", detail: "Yes, it is active." },
  { step: "authentication", label: "Is the request signed?", status: "pass", detail: "Valid agent key." },
  {
    step: "permission_lookup",
    label: "Is it allowed to buy things?",
    status: "pass",
    detail: "Yes — allowed, but with a limit.",
  },
  {
    step: "numeric_limits",
    label: "Is $1,249 inside the limit?",
    status: "escalate",
    detail: "No. The limit is $100, so this needs a person.",
  },
  {
    step: "policy_evaluation",
    label: "Do your rules allow it?",
    status: "escalate",
    detail: "Your rule “anything over $100 needs my OK” applies.",
  },
  {
    step: "approval_requirement",
    label: "Does a human need to approve?",
    status: "escalate",
    detail: "Yes. It waits for you before anything happens.",
  },
  { step: "risk_assessment", label: "How risky is this?", status: "info", detail: "High — worth a look." },
];

const CAPABILITIES = [
  {
    icon: Fingerprint,
    title: "Every agent has an identity",
    body: "Each agent gets its own key, so you always know which one asked for what. Revoke it and it stops working instantly.",
    snippet: <span className="vx-mono text-xs text-muted-foreground">VEX-AGT-7F29A1C4</span>,
  },
  {
    icon: SlidersHorizontal,
    title: "You choose what it can touch",
    body: "67 separate things an agent might do — reading email, buying, opening files, paying invoices. You switch on only what you want.",
    snippet: (
      <span className="flex flex-wrap gap-1.5">
        <span className="vx-chip vx-mono border-border bg-muted">Search shops</span>
        <span className="vx-chip vx-mono border-border bg-muted">Read saved cards</span>
      </span>
    ),
  },
  {
    icon: Wallet,
    title: "Spending caps that actually hold",
    body: "Let it buy small things on its own, ask you about bigger ones, and set a ceiling nobody — not even you in a hurry — can go past.",
    snippet: <span className="vx-mono text-xs text-muted-foreground">on its own $100 · never above $5,000</span>,
  },
  {
    icon: Clock,
    title: "Access that expires by itself",
    body: "Give an agent access just for now. When the time runs out, Vexen starts saying no again. Nothing for you to remember.",
    snippet: <span className="vx-mono text-xs text-muted-foreground">expires in 60 minutes</span>,
  },
  {
    icon: ShieldAlert,
    title: "You approve the big stuff",
    body: "Anything risky stops and waits for you. The approval is tied to that exact request, so it cannot be reused for something else.",
    snippet: <DecisionBadge decision="APPROVAL_REQUIRED" />,
  },
  {
    icon: Gauge,
    title: "A weekly safety check",
    body: "Vexen tells you, in plain English, which agents drifted into risky territory and exactly what to do about it.",
    snippet: <span className="vx-mono text-xs text-muted-foreground">risk 67/100 · high</span>,
  },
  {
    icon: ScrollText,
    title: "A history nobody can rewrite",
    body: "Every decision is written down with the reason behind it, sealed so that tampering shows up. You can verify it yourself in one click.",
    snippet: <span className="vx-mono text-xs text-muted-foreground">VEX-EVT-8B21C4E90D77</span>,
  },
];

const ACTIVITY = [
  { agent: "Personal Assistant", action: "Read your calendar", decision: "ALLOW" },
  { agent: "Shopping Agent", action: "Buy something · $1,249", decision: "APPROVAL_REQUIRED" },
  { agent: "Shopping Agent", action: "Read saved card details", decision: "BLOCK" },
  { agent: "Research Agent", action: "Open a document", decision: "ALLOW" },
];

function DemoDialog({ open, onOpenChange }) {
  const [failed, setFailed] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const videoRef = useRef(null);
  const recheckRef = useRef(null);

  /**
   * React forwards `error` events raised by child <source> elements up to the
   * <video> handler. A single failing candidate is NOT fatal — browsers that
   * ship without H.264 (some Linux/ARM Chromium builds) reject the MP4 and then
   * happily play the WebM. So we only show the fallback once the browser has
   * genuinely run out of candidates (networkState === NETWORK_NO_SOURCE).
   */
  const handleMediaError = (event) => {
    const el = videoRef.current;
    if (!el) return;
    if (event.target !== el) {
      if (recheckRef.current) window.clearTimeout(recheckRef.current);
      recheckRef.current = window.setTimeout(() => {
        const node = videoRef.current;
        if (node && node.networkState === 3 /* NETWORK_NO_SOURCE */) setFailed(true);
      }, 2000);
      return;
    }
    setFailed(true);
  };

  /**
   * Some browsers (iOS Safari especially) refuse to start a video with sound
   * unless the play call is tied to a tap. That is not an error — we just tell
   * the viewer to press play instead of showing a scary fallback.
   */
  useEffect(() => {
    if (!open) {
      setFailed(false);
      setBlocked(false);
      if (recheckRef.current) {
        window.clearTimeout(recheckRef.current);
        recheckRef.current = null;
      }
      return undefined;
    }
    const el = videoRef.current;
    if (!el) return undefined;
    let cancelled = false;
    const attempt = el.play();
    if (attempt && typeof attempt.catch === "function") {
      attempt
        .then(() => {
          if (!cancelled) setBlocked(false);
        })
        .catch(() => {
          if (!cancelled) setBlocked(true);
        });
    }
    return () => {
      cancelled = true;
      if (recheckRef.current) {
        window.clearTimeout(recheckRef.current);
        recheckRef.current = null;
      }
      try {
        el.pause();
      } catch {
        /* dialog is unmounting; nothing to clean up */
      }
    };
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-4xl p-0">
        <DialogHeader className="px-5 pb-3 pt-5">
          <DialogTitle className="font-display">See Vexen in three minutes</DialogTitle>
          <DialogDescription>
            A real walkthrough: creating an account, adding an agent, watching Vexen allow, pause
            and block what it tries to do, and approving a paused purchase from a phone.
          </DialogDescription>
        </DialogHeader>
        <div className="border-t border-border bg-muted/40 p-3">
          {failed ? (
            <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
              <PlayCircle className="h-8 w-8 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                This browser could not play the video.
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2">
                <Button asChild size="sm" variant="outline" data-testid="landing-demo-download">
                  <a href="/demo/vexen-demo.mp4" target="_blank" rel="noreferrer">
                    Open the video directly
                  </a>
                </Button>
                <Button asChild size="sm" variant="outline" data-testid="landing-demo-download-webm">
                  <a href="/demo/vexen-demo.webm" target="_blank" rel="noreferrer">
                    Try the WebM version
                  </a>
                </Button>
                <Button asChild size="sm" data-testid="landing-demo-fallback-signup">
                  <Link to="/signup">Try Vexen instead</Link>
                </Button>
              </div>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                className="w-full rounded-lg bg-foreground/5"
                controls
                autoPlay
                playsInline
                preload="metadata"
                poster="/demo/vexen-demo-poster.png"
                onError={handleMediaError}
                onPlay={() => setBlocked(false)}
                data-testid="landing-demo-video"
              >
                <source src="/demo/vexen-demo.mp4" type="video/mp4" />
                <source src="/demo/vexen-demo.webm" type="video/webm" />
                Your browser cannot play this video.
              </video>
              <p
                className="px-1 pt-2.5 text-xs text-muted-foreground"
                data-testid="landing-demo-caption"
              >
                {blocked
                  ? "Press play to start the walkthrough — it has spoken narration, so turn your sound on."
                  : "Three minutes, with spoken narration and on-screen captions. Use the controls to skip around."}
              </p>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Landing() {
  const [demoOpen, setDemoOpen] = useState(false);

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div className="vx-hero-glow pointer-events-none absolute inset-x-0 top-0 h-[420px]" aria-hidden="true" />
        <div className="relative mx-auto grid max-w-6xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:py-24">
          <div className="vx-rise">
            <span className="vx-chip border-primary/35 bg-primary/10 text-primary">
              <ShieldCheck className="h-3.5 w-3.5" />
              Keep your AI helpers in check
            </span>
            <h1 className="mt-5 font-display text-4xl font-semibold leading-[1.05] tracking-tight text-foreground sm:text-5xl lg:text-[56px]">
              Let AI do things for you.
              <br />
              <span className="text-primary">Stay in control.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-[17px]">
              AI assistants can now buy things, send email and open your files on their own. Vexen sits
              in front of them and decides, every single time, whether what they are about to do is
              actually allowed. You pick what they can touch. You approve the big stuff.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg" data-testid="landing-create-agent-button">
                <Link to="/signup">
                  Get started free <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button
                size="lg"
                variant="outline"
                onClick={() => setDemoOpen(true)}
                data-testid="landing-watch-demo-button"
              >
                <PlayCircle className="mr-2 h-4 w-4" /> Watch the demo
              </Button>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[hsl(var(--status-allow))]" /> Starts from
                &ldquo;no&rdquo;
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[hsl(var(--status-allow))]" /> No technical
                knowledge needed
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-[hsl(var(--status-allow))]" /> 10,000+
                ready-made agents
              </span>
            </div>
          </div>

          {/* Product diagram */}
          <div className="vx-card vx-grid-bg relative overflow-hidden p-5 sm:p-6" data-testid="landing-flow-diagram">
            <div className="relative">
              <div className="flex items-stretch gap-2">
                <FlowNode label="Your AI agent" sub="wants to do something" icon={Layers} />
                <FlowArrow />
                <FlowNode label="Vexen" sub="decides" icon={ShieldCheck} highlight />
                <FlowArrow />
                <FlowNode label="It happens" sub="only if allowed" icon={KeyRound} />
              </div>

              <div className="mt-6 rounded-lg border border-border bg-card/80 p-3">
                <p className="vx-label">What Vexen checks, in order</p>
                <div className="mt-3 flex flex-wrap items-center gap-1.5">
                  {PIPELINE.map((node, i) => (
                    <span key={node} className="flex items-center gap-1.5">
                      <span className="vx-chip border-border bg-muted/70 text-foreground/85">{node}</span>
                      {i < PIPELINE.length - 1 ? (
                        <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      ) : null}
                    </span>
                  ))}
                </div>
              </div>

              <div className="mt-4 overflow-hidden rounded-lg border border-border bg-card/80">
                <div className="flex items-center justify-between border-b border-border px-3 py-2">
                  <p className="vx-label">Happening right now</p>
                  <span className="inline-flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span className="vx-pulse-dot h-1.5 w-1.5 rounded-full bg-[hsl(var(--status-allow))]" />
                    watching
                  </span>
                </div>
                <ul className="divide-y divide-border/70">
                  {ACTIVITY.map((row) => (
                    <li key={row.agent + row.action} className="flex items-center gap-3 px-3 py-2.5">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px] font-medium text-foreground">{row.agent}</span>
                        <span className="block truncate text-[11px] text-muted-foreground">{row.action}</span>
                      </span>
                      <DecisionBadge decision={row.decision} compact />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-16">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            How it works, in 30 seconds
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              {
                n: "01",
                title: "Your agent asks first",
                body: "Before it buys, sends or opens anything, it tells Vexen what it wants to do and how much money is involved.",
                icon: Layers,
              },
              {
                n: "02",
                title: "Vexen runs the checks",
                body: "Who is asking, whether it is switched on, what you allowed, your spending caps, your rules, and how risky this is.",
                icon: ShieldCheck,
              },
              {
                n: "03",
                title: "You get one of three answers",
                body: "Allowed, Blocked, or Needs your OK — always with the reason written down in plain English.",
                icon: ScrollText,
              },
            ].map((s) => (
              <div key={s.n} className="vx-card p-5">
                <div className="flex items-center justify-between">
                  <span className="vx-mono text-xs text-primary">{s.n}</span>
                  <s.icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <h3 className="mt-4 font-display text-base font-semibold text-foreground">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-2">
            <DecisionBadge decision="ALLOW" />
            <DecisionBadge decision="APPROVAL_REQUIRED" />
            <DecisionBadge decision="BLOCK" />
            <span className="text-xs text-muted-foreground">
              If Vexen cannot prove something is allowed, it says no. You never have to list everything
              you want to prevent.
            </span>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="border-b border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-16">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Everything you need to trust an agent
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Vexen is not another chatbot. It is the permission system for what your AI is allowed to
            actually do.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((c) => (
              <div
                key={c.title}
                className="vx-card vx-card-hover flex flex-col p-5"
                data-testid="landing-capability-card"
              >
                <c.icon className="h-[18px] w-[18px] text-primary" />
                <h3 className="mt-4 font-display text-[15px] font-semibold text-foreground">{c.title}</h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">{c.body}</p>
                <div className="mt-4 border-t border-border pt-3">{c.snippet}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Signature moment */}
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 sm:py-16 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
          <div>
            <span className="vx-chip border-[hsl(var(--status-approval)/0.4)] bg-[hsl(var(--status-approval)/0.12)] text-[hsl(var(--status-approval))]">
              <ShieldAlert className="h-3.5 w-3.5" /> The moment that matters
            </span>
            <h2 className="mt-5 font-display text-2xl font-semibold tracking-tight text-foreground">
              A $1,249 purchase, stopped before it happened
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              This shopping agent can browse and add things to a basket freely, and buy anything under
              $100 on its own. When it tries to spend $1,249, Vexen pauses and waits for a person. When
              it reaches for the saved card details, Vexen refuses outright &mdash; even if someone
              handed it that permission by mistake.
            </p>
            <ul className="mt-6 space-y-2.5 text-sm">
              {[
                ["Search for products", "ALLOW"],
                ["Add to basket", "ALLOW"],
                ["Buy something · $1,249", "APPROVAL_REQUIRED"],
                ["Read saved card details", "BLOCK"],
              ].map(([k, d]) => (
                <li
                  key={k}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2"
                >
                  <span className="text-xs text-foreground/85">{k}</span>
                  <DecisionBadge decision={d} compact />
                </li>
              ))}
            </ul>
            <Button asChild className="mt-7" data-testid="landing-run-demo-button">
              <Link to="/signup">
                Try this yourself <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
          <div>
            <p className="vx-label mb-3">Exactly what Vexen checked</p>
            <DecisionTrace trace={SAMPLE_TRACE} dense />
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-[hsl(var(--status-approval)/0.35)] bg-[hsl(var(--status-approval)/0.08)] px-3 py-2.5">
              <ShieldAlert className="h-4 w-4 shrink-0 text-[hsl(var(--status-approval))]" />
              <p className="text-xs text-foreground/85">
                Answer: <span className="font-semibold">Needs your OK</span> &mdash; it may spend up to
                $100 alone, and it asked for $1,249.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="border-b border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-16">
          <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
            Built so that mistakes fail safely
          </h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [
                "It starts from “no”",
                "No permission, expired access or an action nobody thought about? Refused, automatically.",
                XCircle,
              ],
              [
                "Your rules always win",
                "A rule that says “never” beats any permission, however it got granted.",
                ShieldCheck,
              ],
              [
                "History you can verify",
                "Records are sealed with a fingerprint, so you can prove nothing was quietly changed.",
                ScrollText,
              ],
              [
                "10,000+ safe starting points",
                "Ready-made agents for your line of work, each already locked down sensibly.",
                Library,
              ],
            ].map(([title, body, Icon]) => (
              <div key={title} className="vx-card p-5">
                <Icon className="h-4 w-4 text-primary" />
                <h3 className="mt-3.5 font-display text-[15px] font-semibold text-foreground">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <div className="vx-card flex flex-col items-start gap-6 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
            <div>
              <h2 className="font-display text-2xl font-semibold tracking-tight text-foreground">
                AI is powerful. Vexen keeps it on a lead.
              </h2>
              <p className="mt-2 max-w-xl text-sm text-muted-foreground">
                Sign up with your name, email and a password. Pick an agent from the library, and watch
                Vexen decide what it may and may not do &mdash; on real requests, in seconds.
              </p>
              <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <BadgeCheck className="h-3.5 w-3.5 text-[hsl(var(--status-allow))]" />
                Free to start · your workspace begins completely locked down
              </p>
            </div>
            <Button asChild size="lg" className="shrink-0" data-testid="landing-footer-cta">
              <Link to="/signup">
                Get started free <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      <DemoDialog open={demoOpen} onOpenChange={setDemoOpen} />
    </div>
  );
}

const FlowNode = ({ label, sub, icon: Icon, highlight }) => (
  <div
    className={`flex flex-1 flex-col items-center justify-center rounded-lg border px-2 py-4 text-center ${
      highlight ? "border-primary/45 bg-primary/10" : "border-border bg-card/80"
    }`}
  >
    <Icon className={`h-4 w-4 ${highlight ? "text-primary" : "text-muted-foreground"}`} />
    <span className="mt-2 font-display text-[13px] font-semibold text-foreground">{label}</span>
    <span className="mt-0.5 text-[10px] text-muted-foreground">{sub}</span>
  </div>
);

const FlowArrow = () => (
  <div className="flex items-center" aria-hidden="true">
    <ArrowRight className="h-4 w-4 text-muted-foreground" />
  </div>
);
