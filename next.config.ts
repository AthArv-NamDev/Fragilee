import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Keep concurrent Local Supabase development from overwriting the normal app's .next output.
  ...(process.env.FRAGILEE_ENV === "local" ? { distDir: ".next-local-supabase" } : {}),
};

export default nextConfig;
