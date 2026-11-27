import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { safeNext } from "@/lib/redirect";

// Supabase PKCE email confirmation returns a one-time code. Exchange it server-side
// so the new session is written to the same cookies used by protected app routes.
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const destination = safeNext(request.nextUrl.searchParams.get("next")) ?? "/dashboard";

  // Provider denials and expired/invalid links return query errors instead of a PKCE code.
  if (request.nextUrl.searchParams.has("error")) {
    return NextResponse.redirect(new URL("/login?error=oauth", request.url));
  }
  if (!code) return NextResponse.redirect(new URL("/login?error=confirmation", request.url));

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return NextResponse.redirect(new URL("/login?error=confirmation", request.url));

  return NextResponse.redirect(new URL(destination, request.url));
}
