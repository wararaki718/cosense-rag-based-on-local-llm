import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Scrapbox RAG",
  description: "Knowledge discovery with local LLM",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja" data-theme="cupcake">
      <body>{children}</body>
    </html>
  );
}
