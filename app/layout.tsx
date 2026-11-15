import type { Metadata } from "next";
import { cookies } from "next/headers";
import { Archivo_Black, Inter } from "next/font/google";
import { validTheme } from "@/lib/theme";
import "./globals.css";

const archivo = Archivo_Black({ variable: "--font-archivo", subsets: ["latin"], weight: "400" });
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Fragilee",
  description: "An explainable early-stage startup risk tool.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const cookieStore = await cookies();
  const theme = validTheme(cookieStore.get("fragilee-theme")?.value);
  return (
    <html
      lang="en"
      data-theme={theme}
      className={`${archivo.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
