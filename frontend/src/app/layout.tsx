import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Finder - 직군별 채용 공고 필터링",
  description: "여러 구인구직 사이트의 채용 공고를 직군별로 필터링하여 보여줍니다",
  manifest: "/manifest.json",
  themeColor: "#2563eb",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "Job Finder" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body>
        {children}
        <script
          dangerouslySetInnerHTML={{
            __html: `if("serviceWorker"in navigator)navigator.serviceWorker.register("/sw.js")`,
          }}
        />
      </body>
    </html>
  );
}
