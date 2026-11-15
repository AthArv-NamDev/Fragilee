"use client";

import { useEffect, useState } from "react";
import { THEME_LABELS, type ThemeName } from "@/lib/theme";

export default function ThemeSelector({ initialTheme }: { initialTheme: ThemeName }) {
  const [theme, setTheme] = useState<ThemeName>(initialTheme);
  const nextTheme: ThemeName = theme === "light" ? "dark" : "light";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `fragilee-theme=${theme}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
  }, [theme]);

  return (
    <button
      type="button"
      aria-label={`Switch to ${THEME_LABELS[nextTheme]} theme`}
      aria-pressed={theme === "dark"}
      title={`Current theme: ${THEME_LABELS[theme]}`}
      onClick={() => setTheme(nextTheme)}
      className="grid size-11 shrink-0 place-items-center rounded-full border border-current/30 text-current transition-colors hover:bg-ink/5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sage"
    >
      {theme === "dark" ? (
        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
        </svg>
      ) : (
        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20.2 15.2A8.6 8.6 0 0 1 8.8 3.8 8.8 8.8 0 1 0 20.2 15.2Z" />
        </svg>
      )}
      <span className="sr-only">Toggle light and dark theme</span>
    </button>
  );
}
