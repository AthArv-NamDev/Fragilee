// NEXT_PUBLIC_ values are read literally (not by a variable name) so Next.js can bake them into the browser code.
// The publishable key (or the legacy anon key) is safe in the browser. Never put the secret/service_role key here.
export function supabaseEnv() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) {
    throw new Error(
      "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY. Add them to .env.local and restart `npm run dev`.",
    );
  }
  if (process.env.NEXT_PUBLIC_FRAGILEE_ENV === "public") {
    const parsed = new URL(url);
    const match = parsed.hostname.match(/^([a-z0-9]{20})\.supabase\.co$/);
    if (parsed.protocol !== "https:" || !match) {
      throw new Error("Public Fragilee builds require an HTTPS hosted Supabase project URL.");
    }
    if (!process.env.NEXT_PUBLIC_FRAGILEE_SUPABASE_PROJECT_REF || match[1] !== process.env.NEXT_PUBLIC_FRAGILEE_SUPABASE_PROJECT_REF) {
      throw new Error("Public Fragilee builds require an explicit Supabase project reference that matches the configured URL.");
    }
    if (!isPublicSupabaseKey(key)) {
      throw new Error("Public Fragilee builds require a Supabase publishable or legacy anon key.");
    }
    const sameOriginApi = process.env.NEXT_PUBLIC_FRAGILEE_API_SAME_ORIGIN === "true";
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (sameOriginApi && apiUrl) {
      throw new Error("When using Vercel's same-origin API route, omit NEXT_PUBLIC_API_URL.");
    }
    if (!sameOriginApi && (!apiUrl || new URL(apiUrl).protocol !== "https:")) {
      throw new Error("Public Fragilee builds require an HTTPS NEXT_PUBLIC_API_URL or the Vercel same-origin API setting.");
    }
  }
  return { url, key };
}

function isPublicSupabaseKey(key: string): boolean {
  if (key.startsWith("sb_publishable_")) return true;
  const parts = key.split(".");
  if (parts.length !== 3) return false;
  try {
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const decoded = JSON.parse(atob(payload.padEnd(Math.ceil(payload.length / 4) * 4, "=")));
    return decoded?.role === "anon";
  } catch {
    return false;
  }
}
