import axios from "axios";

import { localStore } from "@/lib/storage";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const ACCESS_KEY = "vexen.access";
export const REFRESH_KEY = "vexen.refresh";

export const tokens = {
  access: () => localStore.get(ACCESS_KEY),
  refresh: () => localStore.get(REFRESH_KEY),
  set: ({ access_token, refresh_token }) => {
    if (access_token) localStore.set(ACCESS_KEY, access_token);
    if (refresh_token) localStore.set(REFRESH_KEY, refresh_token);
  },
  clear: () => {
    localStore.remove(ACCESS_KEY);
    localStore.remove(REFRESH_KEY);
  },
};

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  headers: { "Content-Type": "application/json" },
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = tokens.access();
  if (token && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshing = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;

    if (status === 401 && !original._retried && tokens.refresh() && !original.skipAuth) {
      original._retried = true;
      try {
        refreshing =
          refreshing ||
          axios.post(`${BACKEND_URL}/api/auth/refresh`, { refresh_token: tokens.refresh() });
        const { data } = await refreshing;
        refreshing = null;
        tokens.set(data);
        original.headers = { ...(original.headers || {}), Authorization: `Bearer ${data.access_token}` };
        return api(original);
      } catch (e) {
        refreshing = null;
        tokens.clear();
        if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) {
          window.location.assign("/login?expired=1");
        }
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error, fallback = "Something went wrong. Please try again.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) return detail[0]?.msg || fallback;
  if (error?.message === "Network Error") return "Cannot reach the Vexen API. Check your connection.";
  return fallback;
}
