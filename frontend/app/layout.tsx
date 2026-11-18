import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AP Development Intelligence",
  description: "Explore Andhra Pradesh investments, projects, schemes and public impact."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
