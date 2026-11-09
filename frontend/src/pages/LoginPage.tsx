import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { applyFieldErrors } from "../lib/formErrors";
import { Field, PrimaryButton, Shell, TextLink, inputClass } from "../components/ui";

type Form = { email: string; password: string };

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Form>();

  const onSubmit = handleSubmit(async (data) => {
    try {
      await login(data.email, data.password);
      navigate("/dashboard");
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Login failed" });
      }
    }
  });

  return (
    <Shell title="Sign in">
      <form className="flex flex-col gap-4" onSubmit={onSubmit}>
        <Field label="Email" error={errors.email?.message}>
          <input
            type="email"
            className={inputClass}
            autoComplete="email"
            {...register("email", { required: "Required" })}
          />
        </Field>
        <Field label="Password" error={errors.password?.message}>
          <input
            type="password"
            className={inputClass}
            autoComplete="current-password"
            {...register("password", { required: "Required" })}
          />
        </Field>
        {errors.root ? <p className="text-sm text-rose-400">{errors.root.message}</p> : null}
        <PrimaryButton disabled={isSubmitting} type="submit">
          Sign in
        </PrimaryButton>
      </form>
      <div className="flex flex-col gap-2">
        <TextLink to="/forgot-password">Forgot password?</TextLink>
        <Link to="/register" className="text-center text-sm text-slate-400">
          Need an account?
        </Link>
      </div>
    </Shell>
  );
}
