import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import SignOutButton from "@/components/SignOutButton";
import DeleteAllButton from "@/components/DeleteAllButton";

export default async function SettingsPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login");
  const email = String(data.claims.email ?? "your account");
  const card = "analysis-card rounded-[22px] bg-dark-surface border border-ink/10 p-6 md:p-7";
  return (
    <main className="mx-auto w-full max-w-[1184px] px-4 py-7 pb-24 md:px-8 md:py-12">
      <div className="mb-8 rounded-[26px] border border-ink/10 bg-dark-surface p-6 md:p-9"><p className="eyebrow text-coral">Your account</p><h1 className="editorial-title mt-3 font-display">Keep it <span className="text-coral">yours.</span></h1><p className="mt-4 max-w-xl text-sm text-muted">Manage your sign-in and saved analysis data. Your records remain private to your account.</p></div>
      <div className="grid gap-4 lg:grid-cols-2">
      <section className={card} aria-labelledby="acct">
        <p className="eyebrow text-lime">01 / access</p><h2 id="acct" className="mt-3 font-display text-2xl">Account</h2>
        <dl className="text-sm divide-y divide-ink/10">
          <div className="flex justify-between py-3"><dt className="text-muted">Email</dt><dd className="break-all text-right">{email}</dd></div>
          <div className="flex justify-between py-3"><dt className="text-muted">Plan</dt><dd>Beta · free</dd></div>
        </dl>
        <div className="mt-4"><SignOutButton /></div>
      </section>
      <section className={card} aria-labelledby="data">
        <p className="eyebrow text-coral">02 / records</p><h2 id="data" className="mt-3 font-display text-2xl mb-2">Your data</h2>
        <p className="text-sm text-muted mb-4">Your analyses, names and notes are visible only to you. You can remove them whenever you like.</p>
        <DeleteAllButton />
        <p className="text-xs text-muted mt-5">Deleting your whole account is not automatic yet. It is on the list.</p>
      </section>
      </div>
    </main>
  );
}
