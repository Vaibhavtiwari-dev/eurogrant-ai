import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "EuroGrant AI | Elite Intelligence for EU Public Grants",
  description: "Automate your EU grant search and public tender proposals with EuroGrant AI. Leverage RAG-powered intelligence to identify and win high-value opportunities.",
  keywords: ["EU Grants", "Public Tenders", "Grant Writing AI", "EuroGrant", "EU Funding", "Innovation Grants"],
  authors: [{ name: "EuroGrant Team" }],
  creator: "EuroGrant AI",
  publisher: "EuroGrant AI",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || "https://eurogrant.ai"),
  openGraph: {
    title: "EuroGrant AI | Elite Intelligence for EU Public Grants",
    description: "Automate your EU grant search and public tender proposals with EuroGrant AI.",
    url: "https://eurogrant.ai",
    siteName: "EuroGrant AI",
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/og-image.jpg",
        width: 1200,
        height: 630,
        alt: "EuroGrant AI Elite Intelligence",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "EuroGrant AI | Elite Intelligence for EU Public Grants",
    description: "Automate your EU grant search and public tender proposals with EuroGrant AI.",
    creator: "@eurogrant_ai",
    images: ["/og-image.jpg"],
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "EuroGrant AI",
    "operatingSystem": "Web",
    "applicationCategory": "BusinessApplication",
    "description": "Elite AI Intelligence for EU Public Grants and Tenders.",
    "offers": {
      "@type": "Offer",
      "price": "299.00",
      "priceCurrency": "EUR"
    }
  };

  return (
    <html lang="en" className="dark">
      <body className="font-body-md">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <AuthProvider>
          {children}
        </AuthProvider>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
