import { Link } from "react-router-dom";

export function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col px-4 py-6">
      <header className="mb-6">
        <p className="text-xs uppercase tracking-wide text-slate-400">Identity Platform</p>
        <h1 className="text-2xl font-semibold">{title}</h1>
      </header>
      <main className="flex flex-1 flex-col gap-4">{children}</main>
    </div>
  );
}

export function PrimaryButton(props: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const { className = "", ...rest } = props;
  return (
    <button
      className={`w-full rounded-xl bg-indigo-500 px-4 py-3 font-medium text-white hover:bg-indigo-400 disabled:opacity-50 ${className}`}
      {...rest}
    />
  );
}

export function TextLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link to={to} className="text-center text-sm text-indigo-300 hover:text-indigo-200">
      {children}
    </Link>
  );
}

const buttonBaseClass =
  "inline-flex w-full items-center justify-center rounded-xl px-4 py-3 font-medium transition-colors disabled:opacity-50";

/** F-008: single focusable navigation control styled as primary button */
export function ButtonLink({
  to,
  children,
  variant = "primary",
}: {
  to: string;
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "danger";
}) {
  const variantClass =
    variant === "primary"
      ? "bg-indigo-500 text-white hover:bg-indigo-400"
      : variant === "danger"
        ? "bg-rose-600 text-white hover:bg-rose-500"
        : "bg-slate-800 text-white hover:bg-slate-700";
  return (
    <Link to={to} className={`${buttonBaseClass} ${variantClass}`}>
      {children}
    </Link>
  );
}

export function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-slate-300">{label}</span>
      {children}
      {error ? <span className="text-xs text-rose-400">{error}</span> : null}
    </label>
  );
}

export const inputClass =
  "rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-base outline-none focus:border-indigo-400";
