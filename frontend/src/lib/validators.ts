/** Client-side mirrors of server-side rules, so the user sees the problem before
 * the round-trip instead of only after a 422 comes back. */

/** Matches backend/app/schemas.py's BcryptPassword check (bcrypt's 72-byte hard limit). */
export function isWithinBcryptByteLimit(value: string): boolean {
  return new TextEncoder().encode(value).length <= 72;
}

/** Matches backend/app/schemas.py's NonBlankName check — catches a whitespace-only
 * value that a plain `required` rule doesn't (it only rejects a fully empty string). */
export function isNonBlank(value: string): boolean {
  return value.trim().length > 0;
}
