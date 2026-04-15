import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import SessionTabs from "@/components/SessionTabs";

export const metadata: Metadata = {
  title: "RRG — Relative Rotation Graph",
  description: "Personal RRG viewer with RVOL-weighted tails and fundamental overlay",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-gray-950 text-gray-100">
        <header className="px-4 py-3 bg-gray-950 border-b border-gray-800 flex items-center gap-4">
          <h1 className="text-lg font-semibold tracking-tight text-gray-100">RRG</h1>
          <span className="text-xs text-gray-500">Relative Rotation Graph · weekly · JdK normalized</span>
        </header>
        <Suspense fallback={<div className="h-10 bg-gray-950 border-b border-gray-800" />}>
          <SessionTabs />
        </Suspense>
        <main className="flex-1 p-4">{children}</main>
      </body>
    </html>
  );
}
