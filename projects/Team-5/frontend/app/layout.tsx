import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import BackgroundLines from "@/components/BackgroundLines";
import ScrollHue from "@/components/ScrollHue";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jbMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jb-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Proximal Methods in Practice — ISTA vs FISTA",
  description:
    "Visual comparison of ISTA and FISTA on image deblurring (TV regularization) and sparse signal recovery (LASSO).",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jbMono.variable} antialiased`}
    >
      <body className="relative min-h-screen">
        <BackgroundLines />
        <ScrollHue />
        {children}
      </body>
    </html>
  );
}
