import { cookies } from "next/headers";
import AppNav from "./AppNav";
import SignOutButton from "./SignOutButton";
import ThemeSelector from "./ThemeSelector";
import Wordmark from "./Wordmark";
import { validTheme } from "@/lib/theme";

// Shared shell follows the v2 dashboard mockup: centered topbar on desktop,
// compact header and touch navigation on small screens.
export default async function AppShell({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const theme = validTheme(cookieStore.get("fragilee-theme")?.value);
  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-40 border-b border-ink/10 bg-dark-bg/90 shadow-sm backdrop-blur-xl">
        <div className="mx-auto flex min-h-[76px] max-w-[1184px] items-center justify-between gap-4 px-5 md:px-8">
          <Wordmark />
          <AppNav variant="top" />
          <div className="flex items-center gap-2">
            <ThemeSelector initialTheme={theme} />
            <SignOutButton />
          </div>
        </div>
      </header>
      <div className="flex-1 pb-20 md:pb-0 min-w-0">{children}</div>
      <AppNav variant="bottom" />
    </div>
  );
}
