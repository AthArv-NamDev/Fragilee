import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".next-local-supabase/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    "design/**",
    ".venv/**",
    ".venv-1/**",
    "backend/.venv/**"
  ]),
]);

export default eslintConfig;
