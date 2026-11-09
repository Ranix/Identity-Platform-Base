import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { apiFetchAuth, type UserPublic } from "../lib/api";
import { useAuth } from "../lib/auth";
import { applyFieldErrors } from "../lib/formErrors";
import { isNonBlank } from "../lib/validators";
import { Field, PrimaryButton, Shell, inputClass } from "../components/ui";

type Form = Pick<
  UserPublic,
  "first_name" | "last_name" | "email" | "phone" | "locale" | "timezone"
>;

// Same IANA catalog the backend validates against (zoneinfo.available_timezones()),
// via the browser's built-in Intl API instead of a hand-maintained list that could
// drift from it. A user typing a raw timezone string has no way to know it must be
// e.g. "America/Mexico_City" and not "CDMX" (docs/tech-debt.md item 33) — a <select>
// removes the guesswork.
const TIMEZONES: string[] =
  typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Form>();
  // Not formState.isSubmitSuccessful: setUser(updated) below changes `user`, which
  // re-triggers the reset() effect above, and reset() clears isSubmitSuccessful back
  // to false in the same cycle — the "Saved." message would flash and vanish before
  // it's ever visible. This local flag isn't touched by that reset.
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    if (user) reset(user);
  }, [user, reset]);

  const onSubmit = handleSubmit(async (data) => {
    setJustSaved(false);
    try {
      const updated = await apiFetchAuth<UserPublic>("/v1/users/me", {
        method: "PATCH",
        body: JSON.stringify(data),
      });
      setUser(updated);
      setJustSaved(true);
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Update failed" });
      }
    }
  });

  return (
    <Shell title="Profile">
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <Field label="First name" error={errors.first_name?.message}>
          <input
            className={inputClass}
            {...register("first_name", {
              required: "Required",
              validate: (v) => isNonBlank(v) || "Must not be blank",
            })}
          />
        </Field>
        <Field label="Last name" error={errors.last_name?.message}>
          <input
            className={inputClass}
            {...register("last_name", {
              required: "Required",
              validate: (v) => isNonBlank(v) || "Must not be blank",
            })}
          />
        </Field>
        <Field label="Email" error={errors.email?.message}>
          <input
            type="email"
            className={inputClass}
            {...register("email", { required: "Required" })}
          />
        </Field>
        <Field label="Phone" error={errors.phone?.message}>
          <input className={inputClass} placeholder="+1 555 123 4567" {...register("phone")} />
        </Field>
        <Field label="Locale" error={errors.locale?.message}>
          <input className={inputClass} placeholder="en or es-MX" {...register("locale")} />
        </Field>
        <Field label="Timezone" error={errors.timezone?.message}>
          {TIMEZONES.length > 0 ? (
            <select className={inputClass} {...register("timezone")}>
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          ) : (
            // Fallback for a browser without Intl.supportedValuesOf — same free-text
            // behavior as before, still validated server-side against the IANA list.
            <input className={inputClass} {...register("timezone")} />
          )}
        </Field>
        {errors.root ? <p className="text-sm text-rose-400">{errors.root.message}</p> : null}
        {justSaved ? <p className="text-sm text-emerald-400">Saved.</p> : null}
        <PrimaryButton disabled={isSubmitting} type="submit">
          Save changes
        </PrimaryButton>
      </form>
    </Shell>
  );
}
