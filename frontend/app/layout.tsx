import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SafeOps Studio",
  description: "Secure role-based script execution studio",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
