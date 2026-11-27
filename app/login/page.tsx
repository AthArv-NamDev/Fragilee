import { cookies } from "next/headers";
import LoginForm from "@/components/LoginForm";
import { safeNext } from "@/lib/redirect";
import { validTheme } from "@/lib/theme";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; mode?: string; error?: string }> }) {
  const { next, mode, error } = await searchParams;
  const cookieStore = await cookies();
  const authError = error === "confirmation" || error === "oauth" ? error : undefined;
  return <LoginForm next={safeNext(next)} initialMode={error === "confirmation" || mode === "signup" ? "signup" : "signin"} initialTheme={validTheme(cookieStore.get("fragilee-theme")?.value)} authError={authError} />;
}
