import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { AlertTriangle, MessageCircleQuestion, RefreshCw, Send, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAssistantAvailable } from "@/lib/assistant";
import { sessionStore } from "@/lib/storage";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "vexen.assistant.chat";

/** Plain-word page names, so the helper knows where the person is standing. */
const PAGE_NAMES = [
  ["/app/guide", "How to use Vexen"],
  ["/app/agents", "My agents"],
  ["/app/try", "Try an action"],
  ["/app/approvals", "Waiting for you"],
  ["/app/policies", "Rules"],
  ["/app/audit", "History"],
  ["/app/security", "Safety check"],
  ["/app/developers", "For developers"],
  ["/app/settings", "Settings"],
  ["/app", "Home"],
];

const OPENERS = [
  "How do I add my first agent?",
  "How do I stop an agent spending too much?",
  "What is the difference between Blocked and Needs your OK?",
  "How do I connect my own agent in code?",
];

function pageName(pathname) {
  const hit = PAGE_NAMES.find(([prefix]) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  return hit ? hit[1] : "Vexen";
}

function loadSaved() {
  try {
    const raw = sessionStore.get(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.slice(-14) : [];
  } catch (e) {
    return [];
  }
}

/**
 * The model answers in light markdown (**bold**, `code`, dashes and numbers).
 * Rather than forbid that, render the few bits it actually uses.
 */
function renderInline(text, keyPrefix) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={key} className="font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={key} className="vx-mono rounded bg-muted px-1 py-0.5 text-[0.85em]">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={key}>{part}</span>;
  });
}

function AnswerText({ content }) {
  const blocks = [];
  content.split("\n").forEach((raw, index) => {
    const line = raw.trim();
    if (!line) return;
    const bullet = line.match(/^[-*•]\s+(.*)$/);
    const numbered = line.match(/^(\d+)[.)]\s+(.*)$/);
    if (bullet) {
      blocks.push(
        <li key={`b-${index}`} className="ml-4 list-disc pl-0.5">
          {renderInline(bullet[1], `bi-${index}`)}
        </li>,
      );
      return;
    }
    if (numbered) {
      blocks.push(
        <li key={`n-${index}`} className="ml-4 list-decimal pl-0.5">
          {renderInline(numbered[2], `ni-${index}`)}
        </li>,
      );
      return;
    }
    blocks.push(
      <p key={`p-${index}`} className={blocks.length ? "mt-2" : undefined}>
        {renderInline(line, `pi-${index}`)}
      </p>,
    );
  });
  return <div className="space-y-1">{blocks}</div>;
}

const AssistantPanel = () => {
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState(loadSaved);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [failed, setFailed] = useState(null);
  const [suggestions, setSuggestions] = useState(OPENERS);
  const endRef = useRef(null);

  useEffect(() => {
    try {
      sessionStore.set(STORAGE_KEY, JSON.stringify(messages.slice(-14)));
    } catch (e) {
      /* the conversation is nice to keep, not essential */
    }
  }, [messages]);

  useEffect(() => {
    if (open) {
      const id = setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 120);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [open, messages, sending]);

  const send = useCallback(
    async (text) => {
      const question = (text || "").trim();
      if (!question || sending) return;
      const next = [...messages, { role: "user", content: question }].slice(-14);
      setMessages(next);
      setDraft("");
      setSending(true);
      setFailed(null);
      try {
        const { data } = await api.post(
          "/assistant/chat",
          {
            messages: next.map((m) => ({ role: m.role, content: m.content })),
            page: pageName(location.pathname),
          },
          // the server gives up on a slow answer after about 80 seconds
          { timeout: 100000 },
        );
        setMessages((prev) => [...prev, { role: "assistant", content: data.reply }].slice(-14));
        if (Array.isArray(data.suggestions) && data.suggestions.length) {
          setSuggestions(data.suggestions);
        }
      } catch (e) {
        const detail =
          e?.response?.data?.detail || "The helper could not answer just then. Please try again.";
        setFailed({ question, detail });
        toast.error(detail);
      } finally {
        setSending(false);
      }
    },
    [location.pathname, messages, sending],
  );

  const retry = useCallback(() => {
    if (!failed) return;
    const question = failed.question;
    setMessages((prev) => {
      const trimmed = [...prev];
      if (trimmed.length && trimmed[trimmed.length - 1].role === "user") trimmed.pop();
      return trimmed;
    });
    setFailed(null);
    setTimeout(() => send(question), 50);
  }, [failed, send]);

  const clear = useCallback(() => {
    setMessages([]);
    setFailed(null);
    setSuggestions(OPENERS);
    sessionStore.remove(STORAGE_KEY);
  }, []);

  const empty = messages.length === 0;
  const chips = useMemo(() => (empty ? OPENERS : suggestions).slice(0, 4), [empty, suggestions]);

  return (
    <>
      <Button
        onClick={() => setOpen(true)}
        size="sm"
        className={cn(
          "fixed bottom-4 right-4 z-40 h-11 rounded-full pl-3.5 pr-4 shadow-lg transition-opacity sm:bottom-6 sm:right-6",
          // step out of the way once the panel itself is open
          open && "pointer-events-none opacity-0",
        )}
        aria-hidden={open}
        tabIndex={open ? -1 : 0}
        aria-label="Ask for help"
        data-testid="assistant-open-button"
      >
        <MessageCircleQuestion className="h-4 w-4 sm:mr-1.5" aria-hidden="true" />
        <span className="hidden sm:inline">Ask for help</span>
      </Button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="flex w-full flex-col gap-0 p-0 sm:max-w-md"
          data-testid="assistant-panel"
        >
          <SheetHeader className="space-y-1 border-b border-border px-5 py-4 text-left">
            <SheetTitle className="flex items-center gap-2 font-display text-base">
              <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
              Ask Vexen
            </SheetTitle>
            <SheetDescription className="text-xs leading-relaxed">
              Questions about your agents, rules or anything waiting for you. It can see your
              workspace, never your keys or password.
            </SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 px-5">
            <div className="space-y-3 py-4" data-testid="assistant-messages">
              {empty ? (
                <div className="rounded-lg border border-border bg-muted/40 p-3.5">
                  <p className="text-sm leading-relaxed text-foreground">
                    Hello. Ask me anything about running your agents — in your own words.
                  </p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                    For example, why something was stopped, or how to cap what an agent can spend.
                  </p>
                </div>
              ) : null}

              {messages.map((m, i) => (
                <div
                  key={`${m.role}-${i}`}
                  className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
                  data-testid={`assistant-message-${m.role}`}
                >
                  <div
                    className={cn(
                      "max-w-[85%] rounded-lg px-3.5 py-2.5 text-sm leading-relaxed",
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "border border-border bg-card text-foreground",
                    )}
                  >
                    {m.role === "assistant" ? (
                      <AnswerText content={m.content} />
                    ) : (
                      m.content.split("\n").map((line, li) => (
                        <p key={li} className={li ? "mt-1.5" : undefined}>
                          {line}
                        </p>
                      ))
                    )}
                  </div>
                </div>
              ))}

              {sending ? (
                <div className="flex justify-start" data-testid="assistant-thinking">
                  <div className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-3.5 py-3">
                    {[0, 1, 2].map((d) => (
                      <span
                        key={d}
                        className="h-1.5 w-1.5 animate-pulse rounded-full bg-muted-foreground"
                        style={{ animationDelay: `${d * 140}ms` }}
                      />
                    ))}
                  </div>
                </div>
              ) : null}

              {failed ? (
                <div
                  className="flex items-start gap-2 rounded-lg border border-[hsl(var(--status-block)/0.35)] bg-[hsl(var(--status-block)/0.08)] p-3"
                  data-testid="assistant-error"
                >
                  <AlertTriangle
                    className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--status-block))]"
                    aria-hidden="true"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs leading-relaxed text-foreground">{failed.detail}</p>
                    <Button
                      size="sm"
                      variant="outline"
                      className="mt-2 h-7 px-2.5 text-xs"
                      onClick={retry}
                      data-testid="assistant-retry"
                    >
                      <RefreshCw className="mr-1.5 h-3 w-3" /> Try again
                    </Button>
                  </div>
                </div>
              ) : null}

              <div ref={endRef} />
            </div>
          </ScrollArea>

          <div className="border-t border-border px-5 py-3">
            {chips.length ? (
              <div className="mb-2.5 flex flex-wrap gap-1.5" data-testid="assistant-suggestions">
                {chips.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => send(q)}
                    disabled={sending}
                    className="rounded-full border border-border bg-card px-2.5 py-1.5 text-left text-[11px] leading-tight text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
                    data-testid="assistant-suggestion"
                  >
                    {q}
                  </button>
                ))}
              </div>
            ) : null}

            <div className="flex items-end gap-2">
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(draft);
                  }
                }}
                rows={2}
                maxLength={1200}
                placeholder="Ask in your own words…"
                className="min-h-[44px] resize-none text-sm"
                aria-label="Your question"
                data-testid="assistant-input"
              />
              <Button
                size="icon"
                onClick={() => send(draft)}
                disabled={sending || !draft.trim()}
                className="h-11 w-11 shrink-0"
                aria-label="Send question"
                data-testid="assistant-send"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>

            <div className="mt-2 flex items-center justify-between">
              <p className="text-[11px] text-muted-foreground">
                Enter sends, Shift + Enter adds a line.
              </p>
              {messages.length ? (
                <button
                  type="button"
                  onClick={clear}
                  className="inline-flex items-center gap-1 text-[11px] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
                  data-testid="assistant-clear"
                >
                  <X className="h-3 w-3" /> Clear
                </button>
              ) : null}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
};

// The helper only appears when the server has a working Anthropic key, so nobody
// is offered a button that cannot answer.
export const AssistantWidget = () => {
  const available = useAssistantAvailable();
  return available ? <AssistantPanel /> : null;
};
