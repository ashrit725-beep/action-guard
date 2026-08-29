import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Copy text on as many devices as possible.
 *
 * The async Clipboard API only exists in secure contexts and on newer browsers,
 * so we fall back to the old textarea + execCommand trick (still works in older
 * Safari, Android WebViews and embedded browsers). Returns true when the copy
 * appears to have worked, so callers can show honest feedback.
 */
export async function copyText(value) {
  const text = String(value ?? "");
  if (!text) return false;

  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    /* fall through to the legacy path below */
  }

  try {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "fixed";
    el.style.top = "-1000px";
    el.style.opacity = "0";
    document.body.appendChild(el);
    el.focus();
    el.select();
    // iOS needs an explicit range selection
    if (el.setSelectionRange) el.setSelectionRange(0, text.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(el);
    return Boolean(ok);
  } catch (e) {
    return false;
  }
}
