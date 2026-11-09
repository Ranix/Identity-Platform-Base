import { ButtonLink, Shell, TextLink } from "../components/ui";

export default function LandingPage() {
  return (
    <Shell title="Your identity, one place">
      <p className="text-slate-300">
        Central authentication and profile management for your apps. Mobile-first, API-driven.
      </p>
      <div className="mt-auto flex flex-col gap-3 pt-8">
        <ButtonLink to="/login">Sign in</ButtonLink>
        <ButtonLink to="/register" variant="secondary">
          Create account
        </ButtonLink>
        <TextLink to="/login">Already have an account?</TextLink>
      </div>
    </Shell>
  );
}
