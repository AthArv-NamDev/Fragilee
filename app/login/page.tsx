import { cookies } from "next/headers";
import LoginForm from "@/components/LoginForm";
import { safeNext } from "@/lib/redirect";
import { validTheme } from "@/lib/theme";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string; mode?: string; error?: string }> }) {
  const { next, mode, error } = await searchParams;
  const cookieStore = await cookies();
  return <LoginForm next={safeNext(next)} initialMode={mode === "signup" ? "signup" : "signin"} initialTheme={validTheme(cookieStore.get("fragilee-theme")?.value)} authError={error === "confirmation"} />;
}
