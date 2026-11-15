import { createClient } from "@/lib/supabase/server";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type ServerResult<T> = { ok: true; data: T } | { ok: false; status: number; message: string };

// Calls the API from the server with the signed-in user's token. The API still checks the token itself.
export async function serverApi<T>(path: string): Promise<ServerResult<T>> {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims(); // verified first
  if (!claims?.claims) return { ok: false, status: 401, message: "Not signed in" };
  const { data } = await supabase.auth.getSession(); // only to read the token to forward
  const token = data.session?.access_token;
  if (!token) return { ok: false, status: 401, message: "Not signed in" };
  try {
    const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
    if (!res.ok) return { ok: false, status: res.status, message: res.statusText };
    return { ok: true, data: (await res.json()) as T };
  } catch {
    return { ok: false, status: 0, message: "Could not reach the API" };
  }
}
