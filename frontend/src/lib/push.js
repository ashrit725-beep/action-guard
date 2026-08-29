/* Turning browser notifications on for this device.

   Everything here is written to be honest: if the browser cannot do push, or the
   person has blocked notifications, we say so plainly instead of pretending. */

const SW_PATH = "/sw.js";

export function pushSupported() {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

export function permissionState() {
  if (!pushSupported()) return "unsupported";
  return Notification.permission; // "default" | "granted" | "denied"
}

/* iOS only allows push once the site has been added to the home screen. */
export function iosNeedsInstall() {
  if (typeof window === "undefined") return false;
  const ua = navigator.userAgent || "";
  const isIos = /iPad|iPhone|iPod/.test(ua) || (ua.includes("Mac") && navigator.maxTouchPoints > 1);
  if (!isIos) return false;
  const standalone =
    window.navigator.standalone === true ||
    window.matchMedia?.("(display-mode: standalone)")?.matches;
  return !standalone;
}

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

async function registration() {
  const existing = await navigator.serviceWorker.getRegistration(SW_PATH);
  if (existing) return existing;
  return navigator.serviceWorker.register(SW_PATH);
}

export async function currentSubscription() {
  if (!pushSupported()) return null;
  try {
    const reg = await navigator.serviceWorker.getRegistration(SW_PATH);
    if (!reg) return null;
    return await reg.pushManager.getSubscription();
  } catch (err) {
    return null;
  }
}

/* Must be called straight from a click: browsers refuse a permission prompt
   that was not asked for by the person in front of the screen. */
export async function subscribe(publicKey) {
  if (!pushSupported()) throw new Error("This browser cannot show notifications.");
  if (!publicKey) throw new Error("Notifications are not set up on this server yet.");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error(
      permission === "denied"
        ? "Notifications are blocked for this site. Allow them in your browser settings, then try again."
        : "Notifications were not allowed.",
    );
  }

  const reg = await registration();
  await navigator.serviceWorker.ready;
  const existing = await reg.pushManager.getSubscription();
  if (existing) return existing.toJSON();

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
  return sub.toJSON();
}

export async function unsubscribe() {
  const sub = await currentSubscription();
  if (!sub) return null;
  const endpoint = sub.endpoint;
  try {
    await sub.unsubscribe();
  } catch (err) {
    /* the browser may have dropped it already */
  }
  return endpoint;
}
