/**
 * Plain-English vocabulary for Vexen.
 *
 * Vexen is a security product, but the people using it are not all engineers.
 * Every technical term the backend returns gets a friendly label and a one-line
 * explanation here, so the whole UI can speak the same simple language.
 */

export const DECISION_PLAIN = {
  ALLOW: {
    label: "Allowed",
    short: "Allowed",
    plain: "Vexen let this happen. The agent had permission and stayed inside its limits.",
  },
  APPROVAL_REQUIRED: {
    label: "Needs your OK",
    short: "Needs OK",
    plain: "Vexen paused this and is waiting for a person to approve it. Nothing has happened yet.",
  },
  BLOCK: {
    label: "Blocked",
    short: "Blocked",
    plain: "Vexen stopped this. The agent did not have permission, or a rule said no.",
  },
};

export function decisionPlain(decision) {
  return (
    DECISION_PLAIN[decision] || {
      label: decision || "Unknown",
      short: decision || "Unknown",
      plain: "No decision has been recorded yet.",
    }
  );
}

/** How a single permission is granted to one agent. */
export const GRANT_PLAIN = {
  ALLOW: {
    label: "Always allowed",
    plain: "The agent can do this on its own, without asking anyone.",
  },
  LIMITED: {
    label: "Allowed, with a limit",
    plain: "The agent can do this up to a set amount. Anything bigger needs your OK.",
  },
  APPROVAL_REQUIRED: {
    label: "Ask me first",
    plain: "The agent must wait for a person to approve every single time.",
  },
  BLOCK: {
    label: "Never allowed",
    plain: "The agent can never do this, no matter what it asks.",
  },
};

export function grantPlain(decision) {
  return GRANT_PLAIN[decision] || { label: decision || "Unknown", plain: "" };
}

/** Workspace-wide rules (policies). These beat individual permissions. */
export const EFFECT_PLAIN = {
  DENY: {
    label: "Never allow it",
    plain: "Blocks the action for every agent, even one that has permission.",
    example: "Example: no agent may ever touch saved card details.",
  },
  REQUIRE_APPROVAL: {
    label: "Ask a person first",
    plain: "Pauses the action and waits for a human to approve it.",
    example: "Example: any purchase over $100 needs my OK.",
  },
  LIMIT: {
    label: "Cap the amount",
    plain: "Sets a hard ceiling. Anything above it needs approval.",
    example: "Example: never spend more than $500 in one go.",
  },
  MAX_TTL: {
    label: "Make access expire",
    plain: "Forces temporary access to run out after a set time.",
    example: "Example: temporary access ends after 60 minutes.",
  },
  REQUIRE_SCOPE: {
    label: "Only named items",
    plain: "Refuses the action unless the exact items it may touch are listed.",
    example: "Example: only the specific files I picked, nothing else.",
  },
};

export function effectPlain(effect) {
  return (
    EFFECT_PLAIN[effect] || {
      label: (effect || "").replace(/_/g, " ").toLowerCase(),
      plain: "",
      example: "",
    }
  );
}

/** How urgent a security finding is. */
export const SEVERITY_PLAIN = {
  critical: { label: "Fix now", plain: "This could let an agent do real damage. Handle it today." },
  high: { label: "Important", plain: "Worth fixing soon. It widens what an agent could do." },
  medium: { label: "Worth a look", plain: "Not urgent, but tidying this up reduces your risk." },
  low: { label: "Minor", plain: "Informational. Nothing is wrong right now." },
};

export function severityPlain(severity) {
  return SEVERITY_PLAIN[severity] || SEVERITY_PLAIN.low;
}

/** How risky one agent is, based on what it is allowed to do. */
export const RISK_PLAIN = {
  LOW: { label: "Low risk", plain: "Narrow permissions. Little could go wrong." },
  MEDIUM: { label: "Medium risk", plain: "Some reach. Keep an eye on it." },
  HIGH: { label: "High risk", plain: "Broad permissions. Tighten these if you can." },
  CRITICAL: { label: "Very high risk", plain: "This agent can reach sensitive things. Review it now." },
};

export function riskPlain(risk) {
  return RISK_PLAIN[risk] || RISK_PLAIN.LOW;
}

/** Where a request came from. */
export const SOURCE_PLAIN = {
  api: "A real agent, through the Vexen API",
  simulator: "A practice run, not a real agent",
  console: "Someone using this website",
};

export function sourcePlain(source) {
  return SOURCE_PLAIN[source] || "Unknown source";
}

/** Turn a permission key like "payments.charge" into "Payments — charge". */
export function humanizeKey(key) {
  if (!key) return "";
  const [group, ...rest] = String(key).split(".");
  const nice = (s) => s.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  if (!rest.length) return nice(group);
  return `${nice(group)} — ${rest.join(".").replace(/[_-]/g, " ")}`;
}
