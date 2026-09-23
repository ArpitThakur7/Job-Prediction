import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";
import LayoutShell from "@/components/LayoutShell";

export const metadata: Metadata = {
  title: "JOB-AI | Find Your Perfect Job Match",
  description: "AI analyzes your skills and predicts the best opportunities in seconds with 3D interactive telemetry.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-gradient-to-b from-[#FAFBFF] to-[#EEF2FF] text-slate-900">
        <AppProvider>
          <LayoutShell>{children}</LayoutShell>
        </AppProvider>
      </body>
    </html>
  );
}
