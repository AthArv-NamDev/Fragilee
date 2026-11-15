// Where to go after signing in. Only our own private pages are allowed, so a crafted link can never send someone elsewhere.
const ALLOWED = ["/dashboard", "/new", "/history", "/guide", "/settings", "/analysis"];

export function safeNext(value: string | null | undefined): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.includes("\\") || /[\u0000-\u001f]/.test(value)) return null;
  const path = value.split(/[?#]/)[0];
  return ALLOWED.some((p) => path === p || path.startsWith(p + "/")) ? value : null;
}
export const LANDING_AFTER_LOGIN = "/dashboard";
export const LANDING_AFTER_SIGNUP = "/new";
