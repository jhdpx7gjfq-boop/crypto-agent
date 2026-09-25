import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'IGWT-PF26 Quant Dashboard',
  description: 'Quant research infrastructure for crypto investment intelligence',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="theme-color" content="#1f2937" />
      </head>
      <body className="bg-gray-900 text-gray-100">
        <nav className="sticky top-0 z-50 bg-gray-800 border-b border-gray-700">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="text-sm font-bold text-cyan-400">IGWT-PF26</div>
            <div className="flex gap-2 text-xs">
              <a href="/" className="hover:text-cyan-400 px-2 py-1">Dashboard</a>
              <a href="/signals" className="hover:text-cyan-400 px-2 py-1">Signals</a>
              <a href="/regime" className="hover:text-cyan-400 px-2 py-1">Regime</a>
            </div>
          </div>
        </nav>
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
