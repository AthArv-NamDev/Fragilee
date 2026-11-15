"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "◫" },
  { href: "/new", label: "Test the idea", icon: "✦" },
  { href: "/history", label: "History", icon: "◷" },
  { href: "/guide", label: "How to read this", icon: "?" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

// Top links on desktop, a bar along the bottom on phones. Current page is marked for screen readers too.
export default function AppNav({ variant }: { variant: "top" | "bottom" }) {
  const path = usePathname();
  const current = (h: string) => path === h || path.startsWith(h + "/") || (h === "/history" && path.startsWith("/analysis"));
  if (variant === "bottom") {
    return (
      <nav aria-label="App" className="app-nav-bottom fixed bottom-0 inset-x-0 z-40 grid grid-cols-5 border-t border-ink/10 bg-dark-surface/95 backdrop-blur pb-[env(safe-area-inset-bottom)]">
        {ITEMS.map((i) => (
          <Link key={i.href} href={i.href} aria-current={current(i.href) ? "page" : undefined} className="flex min-h-14 flex-col items-center justify-center gap-0.5 px-1 py-1 text-[11px] text-muted transition-colors hover:text-text aria-[current=page]:text-lime">
            <span aria-hidden="true" className="text-lg leading-none">{i.icon}</span>{i.label === "How to read this" ? "Guide" : i.label === "Test the idea" ? "Test" : i.label}
          </Link>
        ))}
      </nav>
    );
  }
  return (
    <nav aria-label="App" className="app-nav-top hidden items-center gap-7 text-sm text-muted">
      {ITEMS.map((i) => (
        <Link key={i.href} href={i.href} aria-current={current(i.href) ? "page" : undefined}
          className="whitespace-nowrap rounded-full border border-transparent px-3 py-2 text-muted transition-colors hover:border-ink/10 hover:text-text aria-[current=page]:border-coral/30 aria-[current=page]:bg-coral-soft aria-[current=page]:text-text">
          {i.label}
        </Link>
      ))}
    </nav>
  );
}
