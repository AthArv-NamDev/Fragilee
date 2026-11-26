export function clientApiBaseUrl(options: {
  sameOrigin: boolean;
  apiUrl?: string;
  localDefault?: string;
}): string;

export function serverApiBaseUrl(options: {
  serviceUrl?: string;
  sameOrigin: boolean;
  apiUrl?: string;
  localDefault?: string;
}): string;
