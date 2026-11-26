const trimTrailingSlashes = (value) => value.replace(/\/+$/, "");

export function clientApiBaseUrl({ sameOrigin, apiUrl, localDefault = "http://localhost:8000" }) {
  return sameOrigin ? "" : trimTrailingSlashes(apiUrl || localDefault);
}

export function serverApiBaseUrl({ serviceUrl, sameOrigin, apiUrl, localDefault = "http://localhost:8000" }) {
  if (serviceUrl) return trimTrailingSlashes(serviceUrl);
  if (sameOrigin) throw new Error("The Vercel backend service binding is missing.");
  return trimTrailingSlashes(apiUrl || localDefault);
}
