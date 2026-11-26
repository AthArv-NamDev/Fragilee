import { createClient } from "@/lib/supabase/client";
import { clientApiBaseUrl } from "@/lib/api-origin.mjs";

const API_URL = clientApiBaseUrl({
  sameOrigin: process.env.NEXT_PUBLIC_FRAGILEE_API_SAME_ORIGIN === "true",
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
});

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Calls the Fragilee API with the signed-in user's token. The API checks the token itself, so nothing here is trusted.
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await createClient().auth.getSession(); // only used to read the token to send along
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "You are not signed in.");

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers, Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) {
        const errors = body.detail.flatMap((issue: { loc?: unknown[]; msg?: unknown }) => {
          if (typeof issue.msg !== "string") return [];
          const path = Array.isArray(issue.loc)
            ? issue.loc.filter((part) => part !== "body").map(String).join(" → ")
            : "";
          return [path ? `${path}: ${issue.msg}` : issue.msg];
        });
        if (errors.length) {
          const visible = errors.slice(0, 3).join("; ");
          message = errors.length > 3 ? `${visible}; and ${errors.length - 3} more issue(s)` : visible;
        }
      }
    } catch {}
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T; // e.g. DELETE: success with no body
  return res.json() as Promise<T>;
}
