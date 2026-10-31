import { createBrowserClient } from "@supabase/ssr";
import { supabaseEnv } from "./env";

// For Client Components ("use client"). Handles sign in, sign up and sign out in the browser.
export function createClient() {
  const { url, key } = supabaseEnv();
  return createBrowserClient(url, key);
}
