import { createClient } from "@/lib/supabase/client";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

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
    } catch {}
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T; // e.g. DELETE: success with no body
  return res.json() as Promise<T>;
}
