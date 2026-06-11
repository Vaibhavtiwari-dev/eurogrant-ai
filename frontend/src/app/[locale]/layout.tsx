import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Toaster } from "sonner";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { headers } from "next/headers";
import { MotionConfig } from "framer-motion";
import { routing } from "@/i18n/routing";

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

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function RootLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}>) {
  const { locale } = await params;

  // Ensure that the incoming `locale` is valid
  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  // Enable static rendering
  setRequestLocale(locale);

  // Read the per-request CSP nonce set by middleware.
  const nonce = (await headers()).get('x-nonce') ?? '';

  // Providing all messages to the client side
  const messages = await getMessages();

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
    <html lang={locale} className="dark">
      <body className="font-body-md">
        <script
          type="application/ld+json"
          nonce={nonce}
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <MotionConfig reducedMotion="user">
              {children}
            </MotionConfig>
          </AuthProvider>
        </NextIntlClientProvider>
        <Toaster position="top-right" richColors />
      </body>
    </html>
  );
}
