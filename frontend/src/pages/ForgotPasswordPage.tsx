import { useForm } from "react-hook-form";
import { apiFetch } from "../lib/api";
import { applyFieldErrors } from "../lib/formErrors";
import { Field, PrimaryButton, Shell, TextLink, inputClass } from "../components/ui";

type Form = { email: string };

export default function ForgotPasswordPage() {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting, isSubmitSuccessful },
  } = useForm<Form>();

  const onSubmit = handleSubmit(async (data) => {
    try {
      await apiFetch("/v1/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify(data),
      });
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Request failed" });
      }
    }
  });

  return (
    <Shell title="Reset password">
      <p className="text-sm text-slate-400">
        Local dev: check API logs for{" "}
        <code className="text-slate-200">password_reset_dev_delivery</code>.
      </p>
      {isSubmitSuccessful ? (
        <p className="rounded-xl bg-slate-900 p-4 text-sm text-slate-200">
          If an account exists, reset instructions have been sent.
        </p>
      ) : (
        <form className="flex flex-col gap-4" onSubmit={onSubmit}>
          <Field label="Email" error={errors.email?.message}>
            <input
              type="email"
              className={inputClass}
              {...register("email", { required: "Required" })}
            />
          </Field>
          {errors.root ? <p className="text-sm text-rose-400">{errors.root.message}</p> : null}
          <PrimaryButton disabled={isSubmitting} type="submit">
            Send reset link
          </PrimaryButton>
        </form>
      )}
      <TextLink to="/login">Back to sign in</TextLink>
    </Shell>
  );
}
