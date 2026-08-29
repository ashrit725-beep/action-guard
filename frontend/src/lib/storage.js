/**
 * Storage that cannot crash the app.
 *
 * Reading or writing localStorage throws outright in a few real situations:
 * Safari with "block all cookies", iOS private mode quota limits, embedded
 * webviews, and locked-down enterprise browsers. Vexen keeps working (just
 * without remembering the theme or session) instead of showing a blank page.
 */
const memory = new Map();

function backing(kind) {
  try {
    const store = kind === "session" ? window.sessionStorage : window.localStorage;
    const probe = "__vexen_probe__";
    store.setItem(probe, "1");
    store.removeItem(probe);
    return store;
  } catch (e) {
    return null;
  }
}

function make(kind) {
  return {
    get(key) {
      const store = backing(kind);
      if (!store) return memory.has(`${kind}:${key}`) ? memory.get(`${kind}:${key}`) : null;
      try {
        return store.getItem(key);
      } catch (e) {
        return null;
      }
    },
    set(key, value) {
      const store = backing(kind);
      if (!store) {
        memory.set(`${kind}:${key}`, String(value));
        return;
      }
      try {
        store.setItem(key, String(value));
      } catch (e) {
        memory.set(`${kind}:${key}`, String(value));
      }
    },
    remove(key) {
      const store = backing(kind);
      memory.delete(`${kind}:${key}`);
      if (!store) return;
      try {
        store.removeItem(key);
      } catch (e) {
        /* nothing else we can do */
      }
    },
  };
}

export const localStore = make("local");
export const sessionStore = make("session");
