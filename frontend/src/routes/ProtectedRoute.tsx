import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { Shell } from "../components/ui";

export function ProtectedRoute() {
  const { authStatus } = useAuth();

  if (authStatus === "loading") {
    return (
      <Shell title="Loading…">
        <div
          className="flex flex-1 items-center justify-center py-12"
          role="status"
          aria-live="polite"
        >
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-indigo-400 border-t-transparent" />
        </div>
      </Shell>
    );
  }

  if (authStatus === "anonymous") {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
