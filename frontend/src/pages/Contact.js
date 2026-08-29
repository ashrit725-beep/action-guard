import { useState } from "react";
import { CheckCircle2, Github, Linkedin, Mail, MapPin, Phone, Send, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, errorMessage } from "@/lib/api";

const FOUNDERS = [
  {
    name: "Ashrit Talluri",
    role: "Co-founder",
    focus: "The decision engine, the rule system, and platform security",
    initials: "AT",
    phone: "7706493107",
    phoneHref: "tel:7706493107",
    quote:
      "An agent should never be able to do something you did not explicitly allow. That is the whole product.",
  },
  {
    name: "Aditya Mirchandani",
    role: "Co-founder",
    focus: "Product, the agent library, and making all of this easy to understand",
    initials: "AM",
    phone: "+1 (404) 855-1929",
    phoneHref: "tel:+14048551929",
    quote:
      "Security tools fail when nobody understands them. Vexen shows you the exact reason for every decision.",
  },
];

const TOPICS = [
  { value: "general", label: "General enquiry" },
  { value: "demo", label: "Request a walkthrough" },
  { value: "security", label: "Security question" },
  { value: "integration", label: "Connecting a real agent" },
  { value: "investor", label: "Investor / partnership" },
];

export default function Contact() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    topic: "general",
    message: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [reference, setReference] = useState(null);

  const update = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    if (form.message.trim().length < 10) {
      toast.error("Please write at least a sentence so we can help properly.");
      return;
    }
    setSubmitting(true);
    try {
      const { data } = await api.post("/public/contact", form, { skipAuth: true });
      setReference(data.reference);
      toast.success("Message sent", { description: `Reference ${data.reference}` });
      setForm({ name: "", email: "", company: "", topic: "general", message: "" });
    } catch (error) {
      toast.error(errorMessage(error, "We could not send that message."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <section className="relative overflow-hidden border-b border-border">
        <div className="vx-hero-glow pointer-events-none absolute inset-x-0 top-0 h-[260px]" aria-hidden="true" />
        <div className="relative mx-auto max-w-6xl px-4 py-14 sm:px-6 sm:py-16">
          <span className="vx-chip border-primary/35 bg-primary/10 text-primary">
            <ShieldCheck className="h-3.5 w-3.5" /> Talk to the founders
          </span>
          <h1 className="mt-5 font-display text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            Contact Vexen
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
            Whether you are wiring a real agent into the authorization API, reviewing our security model,
            or just want a walkthrough &mdash; the two of us read every message.
          </p>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="space-y-4">
          {FOUNDERS.map((f) => (
            <article key={f.name} className="vx-card p-5 sm:p-6" data-testid="founder-card">
              <div className="flex items-start gap-4">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-primary/30 bg-primary/10 font-display text-sm font-semibold text-primary">
                  {f.initials}
                </span>
                <div className="min-w-0">
                  <h2 className="font-display text-lg font-semibold text-foreground">{f.name}</h2>
                  <p className="text-sm text-primary">{f.role}</p>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{f.focus}</p>
                </div>
              </div>
              <blockquote className="mt-4 border-l-2 border-primary/40 pl-3 text-sm italic leading-relaxed text-foreground/80">
                &ldquo;{f.quote}&rdquo;
              </blockquote>
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-border pt-3">
                <a
                  href={f.phoneHref}
                  className="inline-flex min-h-[32px] items-center gap-2 py-0.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
                  data-testid={`founder-phone-${f.initials.toLowerCase()}`}
                >
                  <Phone className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {f.phone}
                </a>
                <span className="flex items-center gap-2.5 text-muted-foreground">
                  <Linkedin className="h-4 w-4" aria-hidden="true" />
                  <Github className="h-4 w-4" aria-hidden="true" />
                </span>
              </div>
            </article>
          ))}

          <div className="vx-panel p-5">
            <p className="vx-label">Other ways to reach us</p>
            <ul className="mt-3 space-y-3 text-sm">
              <li className="flex items-center gap-2.5 text-muted-foreground">
                <Phone className="h-4 w-4 shrink-0 text-primary" />
                <span>
                  Ashrit{" "}
                  <a href="tel:7706493107" className="font-medium text-foreground hover:text-primary">
                    770-649-3107
                  </a>{" "}
                  · Aditya{" "}
                  <a href="tel:+14048551929" className="font-medium text-foreground hover:text-primary">
                    +1 (404) 855-1929
                  </a>
                </span>
              </li>
              <li className="flex items-center gap-2.5 text-muted-foreground">
                <Mail className="h-4 w-4 shrink-0 text-primary" />
                <span>Or use the form &mdash; it reaches both of us.</span>
              </li>
              <li className="flex items-center gap-2.5 text-muted-foreground">
                <MapPin className="h-4 w-4 shrink-0 text-primary" />
                <span>Remote-first team. We reply in your timezone.</span>
              </li>
              <li className="flex items-center gap-2.5 text-muted-foreground">
                <ShieldCheck className="h-4 w-4 shrink-0 text-primary" />
                <span>Security reports are looked at first.</span>
              </li>
            </ul>
          </div>
        </div>

        <div>
          {reference ? (
            <div className="vx-card p-6 sm:p-8" data-testid="contact-success">
              <CheckCircle2 className="h-6 w-6 text-[hsl(var(--status-allow))]" />
              <h2 className="mt-4 font-display text-xl font-semibold text-foreground">Message received</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                Your message is stored against reference{" "}
                <span className="vx-mono text-foreground">{reference}</span>. Ashrit and Aditya will get
                back to you.
              </p>
              <Button
                variant="outline"
                className="mt-6"
                onClick={() => setReference(null)}
                data-testid="contact-send-another"
              >
                Send another message
              </Button>
            </div>
          ) : (
            <form onSubmit={submit} className="vx-card p-6 sm:p-8" data-testid="contact-form">
              <h2 className="font-display text-lg font-semibold text-foreground">Send a message</h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Every submission is stored server-side with a reference you can quote.
              </p>

              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="contact-name">Name</Label>
                  <Input
                    id="contact-name"
                    value={form.name}
                    onChange={update("name")}
                    required
                    minLength={2}
                    maxLength={80}
                    placeholder="Jordan Reyes"
                    data-testid="contact-name-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="contact-email">Email</Label>
                  <Input
                    id="contact-email"
                    type="email"
                    value={form.email}
                    onChange={update("email")}
                    required
                    placeholder="you@example.com"
                    data-testid="contact-email-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="contact-company">
                    Company <span className="text-muted-foreground">(optional)</span>
                  </Label>
                  <Input
                    id="contact-company"
                    value={form.company}
                    onChange={update("company")}
                    maxLength={100}
                    placeholder="Optional"
                    data-testid="contact-company-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="contact-topic">Topic</Label>
                  <Select value={form.topic} onValueChange={(v) => setForm((f) => ({ ...f, topic: v }))}>
                    <SelectTrigger id="contact-topic" data-testid="contact-topic-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TOPICS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="mt-4 space-y-1.5">
                <Label htmlFor="contact-message">Message</Label>
                <Textarea
                  id="contact-message"
                  value={form.message}
                  onChange={update("message")}
                  required
                  minLength={10}
                  maxLength={4000}
                  rows={6}
                  placeholder="Tell us what your agents do today and what you need to control."
                  data-testid="contact-message-input"
                />
                <p className="text-xs text-muted-foreground">{form.message.length}/4000</p>
              </div>

              <Button
                type="submit"
                className="mt-6 w-full sm:w-auto"
                disabled={submitting}
                data-testid="contact-form-submit-button"
              >
                <Send className="mr-2 h-4 w-4" />
                {submitting ? "Sending…" : "Send message"}
              </Button>
            </form>
          )}
        </div>
      </section>
    </div>
  );
}
