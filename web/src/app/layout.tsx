import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "ATS Resume Analyzer",
    template: "%s · ATS Resume Analyzer",
  },
  description:
    "Score your resume against applicant tracking systems, verify that every claimed skill is backed by real evidence, and get specific fixes.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans`}>
        <SiteHeader />
        <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
          {children}
        </main>
        <footer className="mx-auto w-full max-w-5xl px-4 py-8 text-xs text-muted-foreground sm:px-6">
          Resume text is sent to the Groq API for parsing. Don&apos;t upload
          anything you wouldn&apos;t share with a third-party service.
        </footer>
      </body>
    </html>
  );
}
