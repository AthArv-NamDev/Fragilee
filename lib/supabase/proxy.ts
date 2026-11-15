import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { supabaseEnv } from "./env";
import { LANDING_AFTER_LOGIN, safeNext } from "../redirect";

// Pages that need a login. Add new private screens here.
const PROTECTED = ["/dashboard", "/new", "/history", "/guide", "/analysis", "/settings"];

export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });
  const { url, key } = supabaseEnv();

  const supabase = createServerClient(url, key, {
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // Do not put code between createServerClient and getClaims(). getClaims() checks the token's signature,
  // unlike getSession(), which only reads the cookie.
  const { data } = await supabase.auth.getClaims();
  const signedIn = Boolean(data?.claims);
  const path = request.nextUrl.pathname;

  const goTo = (to: string) => {
    const redirect = NextResponse.redirect(new URL(to, request.url));
    response.cookies.getAll().forEach((c) => redirect.cookies.set(c)); // keep any refreshed session cookies
    return redirect;
  };

  if (!signedIn && PROTECTED.some((p) => path === p || path.startsWith(p + "/"))) return goTo(`/login?next=${encodeURIComponent(path + request.nextUrl.search)}`);   // sign in (or sign up), then carry on
  if (signedIn && path === "/login") return goTo(safeNext(request.nextUrl.searchParams.get("next")) ?? LANDING_AFTER_LOGIN);
  return response;
}
