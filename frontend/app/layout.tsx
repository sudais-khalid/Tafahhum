import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tafahhum · تَفَهُّم",
  description: "Explore the legacy of Quranic interpretation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Amiri is a Naskh revival drawn from the Bulaq press types — the
            typographic tradition printed Tafsir actually belongs to. Urdu is set
            in Nastaliq, the script Urdu readers expect. */}
        <link
          href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Noto+Nastaliq+Urdu:wght@400;600&family=Spectral:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
