import { serverApiBaseUrl } from "@/lib/api-origin.mjs";

/** Resolve the server-side API origin using Vercel's runtime-injected binding when available. */
export function serverBackendUrl(): string {
  return serverApiBaseUrl({
    serviceUrl: process.env.FRAGILEE_BACKEND_SERVICE_URL,
    sameOrigin: process.env.NEXT_PUBLIC_FRAGILEE_API_SAME_ORIGIN === "true",
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
  });
}
