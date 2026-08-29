export const DECISIONS = {
  ALLOW: { label: "Allowed", short: "Allow" },
  BLOCK: { label: "Blocked", short: "Block" },
  APPROVAL_REQUIRED: { label: "Approval required", short: "Approval" },
};

/**
 * Older phones and browsers are strict about date strings. The API sends ISO
 * timestamps with microseconds (2026-08-29T14:02:08.345126+00:00), which some
 * Safari and Android WebView versions refuse to parse, so we normalise before
 * giving up. Returns null when the value genuinely is not a date.
 */
export function parseDate(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const raw = String(value);
  let d = new Date(raw);
  if (!Number.isNaN(d.getTime())) return d;
  const normalised = raw
    .trim()
    .replace(" ", "T")
    .replace(/(\.\d{3})\d+/, "$1")
    .replace(/([+-]\d{2})(\d{2})$/, "$1:$2")
    .replace(/([+-]00:00|UTC)$/, "Z");
  d = new Date(normalised);
  if (!Number.isNaN(d.getTime())) return d;
  const withoutFraction = normalised.replace(/\.\d+/, "");
  d = new Date(withoutFraction);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function money(value, currency = "USD") {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  if (Number.isNaN(n)) return null;
  const decimals = n % 1 === 0 ? 0 : 2;
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
      maximumFractionDigits: decimals,
    }).format(n);
  } catch (e) {
    /* very old or unusual locales: plain formatting still reads fine */
    return `$${n.toFixed(decimals)}`;
  }
}

export function compactNumber(value) {
  const n = Number(value || 0);
  if (n < 1000) return String(n);
  try {
    return new Intl.NumberFormat("en-US", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(n);
  } catch (e) {
    /* Intl "compact" notation is newer than some devices */
    if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
    if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
    return `${(n / 1000).toFixed(1)}K`;
  }
}

export function timeAgo(value) {
  const date = parseDate(value);
  if (!date) return "Never";
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 5) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  try {
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch (e) {
    return date.toDateString();
  }
}

export function fullDate(value) {
  const d = parseDate(value);
  if (!d) return "\u2014";
  try {
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch (e) {
    return d.toISOString().replace("T", " ").slice(0, 19);
  }
}

export function shortTime(value) {
  const d = parseDate(value);
  if (!d) return "\u2014";
  try {
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (e) {
    return d.toISOString().slice(11, 19);
  }
}

export function grantLabel(decision) {
  switch (decision) {
    case "ALLOW":
      return "Allowed";
    case "LIMITED":
      return "Limited";
    case "APPROVAL_REQUIRED":
      return "Approval required";
    case "BLOCK":
      return "Blocked";
    default:
      return decision || "—";
  }
}

export function describeConstraints(permission) {
  const c = permission?.constraints || {};
  const bits = [];
  if (c.max_amount !== undefined && c.max_amount !== null) {
    bits.push(`Auto-approve up to ${money(c.max_amount)}`);
  }
  if (c.hard_max_amount !== undefined && c.hard_max_amount !== null) {
    bits.push(`Hard ceiling ${money(c.hard_max_amount)}`);
  }
  if (c.require_approval) bits.push("Approval always required");
  if (c.max_calls_per_day) bits.push(`${c.max_calls_per_day} calls/day`);
  if (c.allowed_resources?.length) bits.push(`Scope: ${c.allowed_resources.join(", ")}`);
  if (c.denied_resources?.length) bits.push(`Denied: ${c.denied_resources.join(", ")}`);
  if (c.allow_sensitive) bits.push("Sensitive access waived");
  if (permission?.expires_at) bits.push(`Expires ${timeAgo(permission.expires_at)}`);
  return bits;
}

export function initials(name) {
  return (name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}
