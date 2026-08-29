import { ArrowUpRight, Check, Info, Minus, X } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS = {
  pass: {
    Icon: Check,
    dot: "bg-[hsl(var(--status-allow))]",
    text: "text-[hsl(var(--status-allow))]",
    label: "Pass",
  },
  escalate: {
    Icon: ArrowUpRight,
    dot: "bg-[hsl(var(--status-approval))]",
    text: "text-[hsl(var(--status-approval))]",
    label: "Escalate",
  },
  fail: {
    Icon: X,
    dot: "bg-[hsl(var(--status-block))]",
    text: "text-[hsl(var(--status-block))]",
    label: "Fail",
  },
  info: { Icon: Info, dot: "bg-muted-foreground", text: "text-muted-foreground", label: "Info" },
  skip: { Icon: Minus, dot: "bg-muted-foreground/60", text: "text-muted-foreground", label: "Skipped" },
};

export const DecisionTrace = ({ trace = [], className, dense = false }) => {
  if (!trace?.length) {
    return (
      <div className={cn("rounded-xl border border-dashed border-border p-6 text-center", className)}>
        <p className="text-sm text-muted-foreground">
          No evaluation trace on this event. Authorization decisions always carry one.
        </p>
      </div>
    );
  }
  return (
    <ol className={cn("vx-panel divide-y divide-border overflow-hidden", className)} data-testid="decision-trace-panel">
      {trace.map((step, index) => {
        const cfg = STATUS[step.status] || STATUS.info;
        const { Icon } = cfg;
        return (
          <li
            key={`${step.step}-${index}`}
            className={cn("flex items-start gap-3 px-4", dense ? "py-2.5" : "py-3")}
            data-testid="decision-trace-step"
          >
            <div className="flex w-5 flex-col items-center pt-1">
              <span className={cn("flex h-4 w-4 items-center justify-center rounded-full", cfg.dot)}>
                <Icon className="h-2.5 w-2.5 text-background" strokeWidth={3} />
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="vx-mono text-[10px] text-muted-foreground">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="font-display text-[13px] font-medium text-foreground">{step.label}</span>
                <span className={cn("vx-mono text-[10px] uppercase tracking-wider", cfg.text)}>{cfg.label}</span>
              </div>
              <p className="mt-0.5 break-words text-xs leading-relaxed text-muted-foreground">{step.detail}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
};
