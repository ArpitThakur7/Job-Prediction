import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/context/AppContext";
import { ToastProvider } from "@/context/ToastContext";
import LayoutShell from "@/components/LayoutShell";

export const metadata: Metadata = {
  title: "Fletch | Every job, scored against your resume",
  description: "AI analyzes your skills and predicts the best opportunities in seconds with 3D interactive telemetry.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem("theme") || "luminary";
                  var darkThemes = ["cyberpunk", "gold", "quantum", "aurora"];
                  if (darkThemes.indexOf(theme) !== -1) {
                    document.documentElement.classList.add("dark");
                    document.documentElement.style.colorScheme = "dark";
                  } else {
                    document.documentElement.classList.remove("dark");
                    document.documentElement.style.colorScheme = "light";
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-full antialiased transition-colors duration-300">
        <AppProvider>
          <ToastProvider>
            <LayoutShell>{children}</LayoutShell>
          </ToastProvider>
        </AppProvider>
      </body>
    </html>
  );
}
