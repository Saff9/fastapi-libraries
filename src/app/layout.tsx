import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/vault/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FastAPI Engineering Academy",
  description:
    "The Python standard-library course that FastAPI builds on — typing, dataclasses, collections.abc, functools, contextlib, inspect, and the rest. Master the primitives before the framework.",
  keywords: [
    "Python",
    "stdlib",
    "typing",
    "dataclasses",
    "collections",
    "functools",
    "contextlib",
    "inspect",
    "FastAPI",
    "engineering",
    "curriculum",
  ],
  authors: [{ name: "FastAPI Engineering Academy" }],
  icons: {
    icon: "/favicon.svg",
    apple: "/apple-touch-icon.svg",
  },
  openGraph: {
    title: "The Standard Library FastAPI Builds On",
    description:
      "The Python stdlib course for FastAPI engineers — typing, dataclasses, collections.abc, functools, contextlib, inspect, and the rest.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {children}
        </ThemeProvider>
        <Toaster />
      </body>
    </html>
  );
}
