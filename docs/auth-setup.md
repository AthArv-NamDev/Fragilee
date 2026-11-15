# Supabase sign-up and sign-in redirects

Fragilee uses the existing Supabase Auth users as the authoritative identity store; it does not use a frontend flag to decide whether a person is new.

- A successful password sign-in goes to `/dashboard` by default.
- A first sign-up with email confirmation disabled goes to `/new` when Supabase returns a session.
- With email confirmation enabled, Supabase sends the confirmation link to `/auth/callback?next=%2Fnew`; the route exchanges the one-time PKCE code and sets the cookie session before redirecting to `/new`.
- A later sign-in goes to `/dashboard`. A validated local `next` destination from a protected route takes precedence for either flow.
- If Supabase intentionally returns an obfuscated existing user during sign-up, the UI uses generic “if this email can be registered” copy rather than claiming that an account was created.

## Supabase dashboard configuration

The configured Supabase project must allow the callback URL for the app origin, for example `http://localhost:3000/auth/callback`, in **Authentication → URL Configuration → Redirect URLs**. Add the deployed app's exact callback URL as well when deploying. The `Site URL` should point at the relevant app origin.

The environment used by this checkout needs the frontend public URL/key as described in [`frontend.env.example`](../frontend.env.example). Do not use a service-role key in the browser.

The backend must use the **same Supabase project URL and public key** as the frontend: copy `NEXT_PUBLIC_SUPABASE_URL` to `SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` to `SUPABASE_ANON_KEY`. This lets the backend verify the same issuer that issued the browser session and lets the authenticated user token reach that project’s `analyses` table. A safe backend template is [`backend.env.example`](../backend/backend.env.example).

The frontend had been configured with a Supabase hostname that returned DNS NXDOMAIN. It now uses the reachable project shared with the backend. Its Auth health endpoint returned HTTP 200, and a deliberately invalid password request returned HTTP 400 with “Invalid login credentials”. A real registered-user sign-in/signup, confirmation email, dashboard session refresh, and logout were not exercised: no disposable account was created and browser access is unavailable in this chat. Backend health, metadata, CORS, and the unauthenticated-route guard were verified in-process.
