import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

/** F-008: sign out and return to landing. */
export function useLogout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  return useCallback(async () => {
    await logout();
    navigate("/", { replace: true });
  }, [logout, navigate]);
}
