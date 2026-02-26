import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Applicant Ranking",
  description: "Rank and evaluate candidates from resumes",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen">{children}</body>
    </html>
  );
}
