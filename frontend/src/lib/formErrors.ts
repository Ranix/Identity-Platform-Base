import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { HttpError } from "./api";

/**
 * Maps a failed request's field-level errors (from a FastAPI 422) onto a React
 * Hook Form's setError, so the user sees e.g. "must be a valid IANA time zone
 * name" next to the Timezone field instead of only a generic banner.
 * Returns true if it applied at least one field error, so the caller knows
 * whether a root-level fallback message is still needed.
 */
export function applyFieldErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
): boolean {
  if (!(error instanceof HttpError) || error.fieldErrors.length === 0) return false;
  for (const { field, message } of error.fieldErrors) {
    setError(field as Path<T>, { message });
  }
  return true;
}
