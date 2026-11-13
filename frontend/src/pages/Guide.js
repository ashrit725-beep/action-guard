import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  Check,
  CheckCircle2,
  Code2,
  Eye,
  Scale,
  ScrollText,
  ShieldAlert,
  ShieldCheck,
  Wand2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Explainer, PageHeader, SectionCard } from "@/components/Common";
import { api } from "@/lib/api";
import { useAssistantAvailable } from "@/lib/assistant";
import { cn } from "@/lib/utils";

const ANSWERS = [
  {
    key: "ALLOW",
    Icon: CheckCircle2,
    title: "Allowed",
    body: "The agent had permission and stayed inside the limits you set. It goes ahead, and the action is written into your History.",
    tone: "allow",
  },
  {
    key: "APPROVAL_REQUIRED",
    Icon: ShieldAlert,
    title: "Needs your OK",
    body: "Something crossed a line — a spending cap, or sensitive information. Vexen pauses and waits for you. Nothing happens until you say yes.",
    tone: "approval",
  },
  {
    key: "BLOCK",
    Icon: XCircle,
    title: "Blocked",
    body: "The agent asked for something it was never given permission to do, or a rule said no. Vexen stops it and records the attempt.",
    tone: "block",
  },
];

const TONE_CLASSES = {
  allow: {
    ring: "border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.07)]",
    icon: "text-[hsl(var(--status-allow))]",
  },
  approval: {
    ring: "border-[hsl(var(--status-approval)/0.3)] bg-[hsl(var(--status-approval)/0.07)]",
    icon: "text-[hsl(var(--status-approval))]",
  },
  block: {
    ring: "border-[hsl(var(--status-block)/0.3)] bg-[hsl(var(--status-block)/0.07)]",
    icon: "text-[hsl(var(--status-block))]",
  },
};

const FAQS = [
  {
    q: "What is an “AI agent”, in normal words?",
    a: "It is a piece of software that does jobs for you on its own — booking a trip, replying to email, buying supplies. The useful part is that it acts without asking. The scary part is exactly the same thing. Vexen is the seatbelt.",
  },
  {
    q: "Do I need to know how to code?",
    a: "No. Everything on this website works by clicking. Writing code is only needed if you want to connect your own agent, and that lives on the 'For developers' page, out of your way.",
  },
  {
    q: "What happens if I forget to block something?",
    a: "Nothing bad. Vexen starts from 'no'. An agent can only do the specific things you switched on. Anything you never thought about is refused automatically.",
  },
  {
    q: "What is the difference between an agent's permissions and a rule?",
    a: "Permissions are per agent — what this one assistant may do. Rules apply to every agent at once, and they win. So a rule saying 'never touch saved cards' beats any permission you might have given by mistake.",
  },
  {
    q: "Can an agent get around Vexen?",
    a: "It cannot skip the check. Every decision is made on our server, not in the agent, and every decision is written down in a way that shows if anyone tampered with it. You can verify that yourself on the Safety check page.",
  },
  {
    q: "Will Vexen spend my money?",
    a: "Vexen never spends anything. It only answers yes or no when an agent asks. Spending caps are yours to set, and anything above a cap waits for your approval.",
  },
];

export default function Guide() {
  const [progress, setProgress] = useState(null);
  const assistantAvailable = useAssistantAvailable();

  const load = useCallback(async () => {
    try {
      const [dashboard, policies, developers] = await Promise.all([
        api.get("/dashboard"),
        api.get("/policies"),
        api.get("/developers"),
      ]);
      const metrics = dashboard.data?.metrics || {};
      setProgress({
        agents: metrics.total_agents || 0,
        rules: policies.data?.total || 0,
        actions: metrics.total_actions || 0,
        approvals: metrics.pending_approvals || 0,
        apiCalls: developers.data?.api_calls || 0,
      });
    } catch (e) {
      setProgress(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Clear the "just signed up" marker here rather than during routing, so a
  // repeated render can never swallow it.
  useEffect(() => {
    try {
      sessionStorage.removeItem("vexen.onboarding");
    } catch (e) {
      /* private browsing */
    }
  }, []);

  const steps = [
    {
      title: "Pick your first agent",
      body: "Your workspace starts empty on purpose — nothing can act until you allow it. Browse over 10,000 ready-made agents and add one that matches what you need.",
      to: "/app/agents",
      cta: "Browse the library",
      icon: Bot,
      done: (progress?.agents || 0) > 0,
      doneLabel: `${progress?.agents || 0} agent${progress?.agents === 1 ? "" : "s"} ready`,
    },
    {
      title: "Try an action and watch the answer",
      body: "Pick an agent, pick something for it to attempt, and Vexen shows you what it would decide. Nothing real happens — it is the safest way to understand how this works.",
      to: "/app/try",
      cta: "Try an action",
      icon: Wand2,
      done: (progress?.actions || 0) > 0,
      doneLabel: `${progress?.actions || 0} action${progress?.actions === 1 ? "" : "s"} checked so far`,
    },
    {
      title: "Set a rule in your own words",
      body: "Type something like “never let any agent spend more than $200 without asking me” and Vexen turns it into a real rule you can review before saving.",
      to: "/app/policies",
      cta: "Set up rules",
      icon: Scale,
      done: (progress?.rules || 0) > 0,
      doneLabel: `${progress?.rules || 0} rule${progress?.rules === 1 ? "" : "s"} protecting you`,
    },
    {
      title: "Approve or refuse what is waiting",
      body: "When an agent needs your OK, it shows up in “Waiting for you”. You see what it wants and why it was paused, then decide. Nothing moves until you do.",
      to: "/app/approvals",
      cta: "Open my approvals",
      icon: ShieldAlert,
      done: false,
      doneLabel: null,
    },
    {
      title: "Check your history any time",
      body: "Every single decision is recorded — what was asked, what Vexen answered, and why. Nothing can be quietly edited or deleted later.",
      to: "/app/audit",
      cta: "View history",
      icon: ScrollText,
      done: (progress?.actions || 0) > 0,
      doneLabel: null,
    },
    {
      title: "Connect a real agent (only if you build software)",
      body: "If you write code, give your agent a key and it can ask Vexen for permission before every action. If you do not, you can safely skip this forever.",
      to: "/app/developers",
      cta: "Developer page",
      icon: Code2,
      done: (progress?.apiCalls || 0) > 0,
      doneLabel: `${progress?.apiCalls || 0} real API call${progress?.apiCalls === 1 ? "" : "s"}`,
      optional: true,
    },
  ];

  return (
    <div className="space-y-6" data-testid="guide-page">
      <PageHeader
        title="How to use Vexen"
        description="A five-minute read. No technical knowledge needed."
        testId="guide-header"
        actions={
          <Button asChild data-testid="guide-try-cta">
            <Link to="/app/try">
              <Wand2 className="mr-1.5 h-4 w-4" /> Try an action now
            </Link>
          </Button>
        }
      />

      <Explainer title="The idea in one sentence" testId="guide-explainer">
        <p>
          AI assistants can now do things for you — send email, buy things, open your files. Vexen
          sits in front of them and decides, every single time, whether the thing they are about to
          do is actually allowed.
        </p>
      </Explainer>

      <SectionCard
        title="Vexen only ever gives one of three answers"
        description="Once you know these three, you understand the whole product."
        icon={ShieldCheck}
        testId="guide-answers"
      >
        <div className="grid gap-3 md:grid-cols-3">
          {ANSWERS.map(({ key, Icon, title, body, tone }) => (
            <div
              key={key}
              className={cn("rounded-xl border p-4", TONE_CLASSES[tone].ring)}
              data-testid={`guide-answer-${key.toLowerCase()}`}
            >
              <Icon className={cn("h-5 w-5", TONE_CLASSES[tone].icon)} />
              <p className="mt-2.5 font-display text-[15px] font-semibold text-foreground">{title}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard
        title="Your first few minutes"
        description="Work down this list. Each step takes under a minute."
        icon={Check}
        testId="guide-steps"
      >
        <ol className="space-y-3">
          {steps.map((step, index) => {
            const StepIcon = step.icon;
            return (
              <li
                key={step.title}
                className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-start"
                data-testid={`guide-step-${index + 1}`}
              >
                <span
                  className={cn(
                    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
                    step.done
                      ? "bg-[hsl(var(--status-allow)/0.14)] text-[hsl(var(--status-allow))]"
                      : "bg-primary/10 text-primary",
                  )}
                >
                  {step.done ? <Check className="h-4 w-4" /> : <StepIcon className="h-4 w-4" />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-display text-[15px] font-semibold text-foreground">
                      {index + 1}. {step.title}
                    </p>
                    {step.optional ? (
                      <span className="vx-chip border-border bg-muted text-muted-foreground">
                        Optional
                      </span>
                    ) : null}
                    {step.done && step.doneLabel ? (
                      <span className="vx-chip border-[hsl(var(--status-allow)/0.3)] bg-[hsl(var(--status-allow)/0.1)] text-[hsl(var(--status-allow))]">
                        {step.doneLabel}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                </div>
                <Button
                  asChild
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  data-testid={`guide-step-cta-${index + 1}`}
                >
                  <Link to={step.to}>
                    {step.cta}
                    <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
                  </Link>
                </Button>
              </li>
            );
          })}
        </ol>
      </SectionCard>

      <div className="grid gap-5 lg:grid-cols-[1.15fr_1fr]">
        <SectionCard
          title="Permissions vs rules — the one thing people mix up"
          icon={Scale}
          testId="guide-permissions-vs-rules"
        >
          <div className="space-y-4">
            <div className="rounded-xl border border-border bg-muted/50 p-4">
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-primary" />
                <p className="font-display text-sm font-semibold text-foreground">
                  Permissions belong to one agent
                </p>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                “My shopping agent may buy things up to $100.” You set these on each agent's own
                page, and they only affect that agent.
              </p>
            </div>
            <div className="rounded-xl border border-primary/25 bg-accent/50 p-4">
              <div className="flex items-center gap-2">
                <Scale className="h-4 w-4 text-primary" />
                <p className="font-display text-sm font-semibold text-foreground">
                  Rules cover every agent, and rules win
                </p>
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                “No agent may ever read saved card details.” Even if you accidentally give an agent
                that permission, the rule still refuses it. This is your safety net.
              </p>
            </div>
            <p className="text-xs leading-relaxed text-muted-foreground">
              When a rule and a permission disagree, the more restrictive one always wins. Vexen is
              never permissive by accident.
            </p>
          </div>
        </SectionCard>

        <SectionCard title="Good habits" icon={Eye} testId="guide-habits">
          <ul className="space-y-3">
            {[
              "Give an agent the smallest set of permissions that lets it do its job. You can always add more later.",
              "Put a spending cap on anything that touches money, even if you trust the agent.",
              "Glance at 'Waiting for you' once a day so nothing sits paused.",
              "Open 'Safety check' weekly — it tells you which agents drifted into risky territory.",
              "If an agent starts behaving oddly, switch it off from its own page. That takes effect instantly.",
            ].map((tip) => (
              <li key={tip} className="flex items-start gap-2.5">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--status-allow))]" />
                <span className="text-sm leading-relaxed text-muted-foreground">{tip}</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <SectionCard title="Common questions" testId="guide-faq">
        <Accordion type="single" collapsible className="w-full">
          {FAQS.map((faq, index) => (
            <AccordionItem key={faq.q} value={`faq-${index}`}>
              <AccordionTrigger className="text-left text-sm font-medium" data-testid={`guide-faq-${index}`}>
                {faq.q}
              </AccordionTrigger>
              <AccordionContent className="text-sm leading-relaxed text-muted-foreground">
                {faq.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
        {assistantAvailable && (
          <p
            className="mt-4 rounded-lg border border-border bg-muted/40 p-3.5 text-sm leading-relaxed text-muted-foreground"
            data-testid="guide-assistant-hint"
          >
            Still stuck? Tap{" "}
            <span className="font-medium text-foreground">Ask for help</span> in the bottom corner of
            any page. It can see your agents, your rules and anything that got stopped, so you can ask
            things like &ldquo;why was my agent blocked?&rdquo; in your own words.
          </p>
        )}
      </SectionCard>
    </div>
  );
}
