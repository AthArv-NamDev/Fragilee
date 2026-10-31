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
  return { url, key };
}
