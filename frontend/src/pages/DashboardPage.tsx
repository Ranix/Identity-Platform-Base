import { useLogout } from "../hooks/useLogout";
import { useAuth } from "../lib/auth";
import { ButtonLink, PrimaryButton, Shell } from "../components/ui";

export default function DashboardPage() {
  const { user } = useAuth();
  const signOut = useLogout();

  return (
    <Shell title={`Hi, ${user?.first_name ?? "there"}`}>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm">
        <p className="text-slate-400">Signed in as</p>
        <p className="font-medium">{user?.email}</p>
      </div>
      <div className="flex flex-col gap-3">
        <ButtonLink to="/profile" variant="secondary">
          Edit profile
        </ButtonLink>
        <ButtonLink to="/security" variant="secondary">
          Security
        </ButtonLink>
        <PrimaryButton
          type="button"
          className="bg-rose-600 hover:bg-rose-500"
          onClick={() => signOut()}
        >
          Sign out
        </PrimaryButton>
      </div>
    </Shell>
  );
}
