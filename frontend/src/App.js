import { Suspense, lazy } from "react";
import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { Spinner } from "@/components/Common";
import MarketingLayout from "@/components/MarketingLayout";
import AppShell from "@/components/AppShell";

const Landing = lazy(() => import("@/pages/Landing"));
const Contact = lazy(() => import("@/pages/Contact"));
const Login = lazy(() => import("@/pages/Login"));
const Signup = lazy(() => import("@/pages/Signup"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Guide = lazy(() => import("@/pages/Guide"));
const Agents = lazy(() => import("@/pages/Agents"));
const AgentDetail = lazy(() => import("@/pages/AgentDetail"));
const TryIt = lazy(() => import("@/pages/TryIt"));
const Approvals = lazy(() => import("@/pages/Approvals"));
const AuditLog = lazy(() => import("@/pages/AuditLog"));
const SecurityCenter = lazy(() => import("@/pages/SecurityCenter"));
const Policies = lazy(() => import("@/pages/Policies"));
const Developers = lazy(() => import("@/pages/Developers"));
const Settings = lazy(() => import("@/pages/Settings"));
const NotFound = lazy(() => import("@/pages/NotFound"));

const FullScreenLoader = () => (
  <div className="flex min-h-screen items-center justify-center bg-background">
    <Spinner label="Loading Vexen…" />
  </div>
);

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoader />;
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return children;
};

const GuestRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <FullScreenLoader />;
  if (isAuthenticated) {
    // Someone who just created an account goes straight to the guide, so the
    // very first thing they see is an explanation rather than empty numbers.
    // The flag is cleared by the Guide page itself, never during render —
    // render can run more than once, which would swallow it.
    let target = "/app";
    try {
      if (sessionStorage.getItem("vexen.onboarding") === "1") target = "/app/guide";
    } catch (e) {
      /* private browsing — the dashboard has a "Start here" panel as a fallback */
    }
    return <Navigate to={target} replace />;
  }
  return children;
};

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Suspense fallback={<FullScreenLoader />}>
            <Routes>
              <Route element={<MarketingLayout />}>
                <Route path="/" element={<Landing />} />
                <Route path="/contact" element={<Contact />} />
              </Route>

              <Route
                path="/login"
                element={
                  <GuestRoute>
                    <Login />
                  </GuestRoute>
                }
              />
              <Route
                path="/signup"
                element={
                  <GuestRoute>
                    <Signup />
                  </GuestRoute>
                }
              />

              <Route
                path="/app"
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="guide" element={<Guide />} />
                <Route path="agents" element={<Agents />} />
                <Route path="agents/:agentId" element={<AgentDetail />} />
                <Route path="try" element={<TryIt />} />
                <Route path="approvals" element={<Approvals />} />
                <Route path="audit" element={<AuditLog />} />
                <Route path="security" element={<SecurityCenter />} />
                <Route path="policies" element={<Policies />} />
                <Route path="developers" element={<Developers />} />
                <Route path="settings" element={<Settings />} />
                {/* The old simulator was removed — send anyone with a stale link
                    to the friendlier "Try an action" checker. */}
                <Route path="simulator" element={<Navigate to="/app/try" replace />} />
              </Route>

              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          <Toaster position="top-right" closeButton />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
