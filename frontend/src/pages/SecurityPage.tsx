import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { apiFetchAuth } from "../lib/api";
import { useAuth } from "../lib/auth";
import { applyFieldErrors } from "../lib/formErrors";
import { isWithinBcryptByteLimit } from "../lib/validators";
import { useLogout } from "../hooks/useLogout";
import { Field, PrimaryButton, Shell, inputClass } from "../components/ui";

type Form = {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
};

export default function SecurityPage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const signOut = useLogout();
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Form>();

  const onSubmit = handleSubmit(async (data) => {
    try {
      await apiFetchAuth<void>("/v1/users/me/password", {
        method: "POST",
        body: JSON.stringify(data),
      });
      // Server revoked every refresh token for this account (ADR-0003 addendum),
      // including this session's — treat success as an implicit logout.
      await logout();
      navigate("/login", { replace: true });
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Change failed" });
      }
    }
  });

  return (
    <Shell title="Security">
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <Field label="Current password" error={errors.current_password?.message}>
          <input
            type="password"
            className={inputClass}
            {...register("current_password", { required: "Required" })}
          />
        </Field>
        <Field label="New password" error={errors.new_password?.message}>
          <input
            type="password"
            className={inputClass}
            {...register("new_password", {
              required: "Required",
              minLength: { value: 8, message: "Min 8" },
              validate: (v) => isWithinBcryptByteLimit(v) || "Must be at most 72 bytes",
            })}
          />
        </Field>
        <Field label="Confirm new password" error={errors.new_password_confirm?.message}>
          <input
            type="password"
            className={inputClass}
            {...register("new_password_confirm", {
              required: "Required",
              validate: (v) => v === watch("new_password") || "Must match",
            })}
          />
        </Field>
        {errors.root ? <p className="text-sm text-rose-400">{errors.root.message}</p> : null}
        <PrimaryButton disabled={isSubmitting} type="submit">
          Change password
        </PrimaryButton>
      </form>
      <PrimaryButton
        type="button"
        className="bg-rose-600 hover:bg-rose-500"
        onClick={() => signOut()}
      >
        Sign out
      </PrimaryButton>
    </Shell>
  );
}
