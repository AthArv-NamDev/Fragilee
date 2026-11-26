import test from "node:test";
import assert from "node:assert/strict";
import { clientApiBaseUrl, serverApiBaseUrl } from "./api-origin.mjs";

test("browser calls use the Vercel deployment's same origin when enabled", () => {
  assert.equal(clientApiBaseUrl({ sameOrigin: true, apiUrl: undefined }), "");
});

test("browser calls preserve the configured standalone API URL", () => {
  assert.equal(clientApiBaseUrl({ sameOrigin: false, apiUrl: "https://api.example.test/" }), "https://api.example.test");
});

test("server calls prefer the private Vercel service binding", () => {
  assert.equal(serverApiBaseUrl({ serviceUrl: "https://internal.example.test/", sameOrigin: true }), "https://internal.example.test");
});

test("server same-origin mode fails closed if its private binding is missing", () => {
  assert.throws(() => serverApiBaseUrl({ sameOrigin: true }), /service binding is missing/);
});

test("local server calls retain the standalone API fallback", () => {
  assert.equal(serverApiBaseUrl({ sameOrigin: false, apiUrl: "", localDefault: "http://127.0.0.1:8001/" }), "http://127.0.0.1:8001");
});
