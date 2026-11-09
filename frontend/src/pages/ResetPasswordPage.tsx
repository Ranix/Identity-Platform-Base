import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { applyFieldErrors } from "../lib/formErrors";
import { isWithinBcryptByteLimit } from "../lib/validators";
import { Field, PrimaryButton, Shell, TextLink, inputClass } from "../components/ui";

type Form = { new_password: string; new_password_confirm: string };

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Form>();

  const onSubmit = handleSubmit(async (data) => {
    if (!token) {
      setError("root", { message: "Missing token in URL" });
      return;
    }
    try {
      await apiFetch("/v1/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, ...data }),
      });
      navigate("/login");
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Reset failed" });
      }
    }
  });

  return (
    <Shell title="Choose new password">
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
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
        <Field label="Confirm password" error={errors.new_password_confirm?.message}>
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
          Update password
        </PrimaryButton>
      </form>
      <TextLink to="/login">Sign in</TextLink>
    </Shell>
  );
}
