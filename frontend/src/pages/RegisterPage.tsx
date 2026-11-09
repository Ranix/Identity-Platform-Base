import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import { applyFieldErrors } from "../lib/formErrors";
import { isNonBlank, isWithinBcryptByteLimit } from "../lib/validators";
import { Field, PrimaryButton, Shell, TextLink, inputClass } from "../components/ui";

type Form = {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Form>();

  const onSubmit = handleSubmit(async (data) => {
    if (data.password !== data.password_confirm) {
      setError("password_confirm", { message: "Passwords do not match" });
      return;
    }
    try {
      await apiFetch("/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
      });
      navigate("/login");
    } catch (e) {
      if (!applyFieldErrors(e, setError)) {
        setError("root", { message: e instanceof Error ? e.message : "Registration failed" });
      }
    }
  });

  return (
    <Shell title="Create account">
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
        <Field label="Password" error={errors.password?.message}>
          <input
            type="password"
            className={inputClass}
            {...register("password", {
              required: "Required",
              minLength: { value: 8, message: "Min 8" },
              validate: (v) => isWithinBcryptByteLimit(v) || "Must be at most 72 bytes",
            })}
          />
        </Field>
        <Field label="Confirm password" error={errors.password_confirm?.message}>
          <input
            type="password"
            className={inputClass}
            {...register("password_confirm", {
              required: "Required",
              validate: (v) => v === watch("password") || "Must match",
            })}
          />
        </Field>
        {errors.root ? <p className="text-sm text-rose-400">{errors.root.message}</p> : null}
        <PrimaryButton disabled={isSubmitting} type="submit">
          Register
        </PrimaryButton>
      </form>
      <TextLink to="/login">Back to sign in</TextLink>
    </Shell>
  );
}
