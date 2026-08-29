import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export const VexenMark = ({ className }) => (
  <span
    className={cn(
      "inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-primary/40 bg-primary/10",
      className,
    )}
    aria-hidden="true"
  >
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2.6 4.2 5.4v6.1c0 4.6 3.2 8.3 7.8 9.9 4.6-1.6 7.8-5.3 7.8-9.9V5.4L12 2.6Z" className="text-primary" />
      <path d="M9 9.4l3 3 3-3M9 14.6h6" className="text-primary" strokeLinecap="round" />
    </svg>
  </span>
);

export const Wordmark = ({ to = "/", className, showTagline = false, testId = "vexen-wordmark" }) => (
  <Link to={to} className={cn("group inline-flex items-center gap-2.5", className)} data-testid={testId}>
    <VexenMark />
    <span className="flex flex-col leading-none">
      <span className="font-display text-[17px] font-semibold tracking-tight text-foreground">
        Ve<span className="text-primary">x</span>en
      </span>
      {showTagline ? (
        <span className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Control AI
        </span>
      ) : null}
    </span>
  </Link>
);
