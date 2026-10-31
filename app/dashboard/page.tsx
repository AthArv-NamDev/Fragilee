import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import SignOutButton from "./SignOutButton";
import BackendCheck from "./BackendCheck";

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims(); // checks the token's signature, unlike getSession()
  if (!data?.claims) redirect("/login");

  return (
    <main className="min-h-screen px-6 py-10 max-w-3xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl">Dashboard</h1>
        <SignOutButton />
      </div>
      <p className="text-muted mt-4">Signed in as {String(data.claims.email ?? "your account")}.</p>
      <p className="text-muted mt-1 text-sm">The real dashboard comes later. This page only proves login works.</p>
      <BackendCheck />
    </main>
  );
}
