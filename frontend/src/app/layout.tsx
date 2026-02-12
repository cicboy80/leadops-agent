import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Link from 'next/link';
import {
  LayoutDashboard,
  Upload,
  Settings,
  Zap
} from 'lucide-react';
import { NotificationBellWrapper } from '@/components/notifications/notification-bell-wrapper';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'LeadOps Agent',
  description: 'B2B Agentic Workflow for Lead Qualification',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="flex h-screen bg-slate-50 dark:bg-slate-900">
          {/* Sidebar */}
          <aside className="w-64 bg-slate-800 text-slate-100 flex flex-col">
            <div className="p-6 border-b border-slate-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-6 h-6 text-blue-400" />
                  <h1 className="text-xl font-bold">LeadOps Agent</h1>
                </div>
                <NotificationBellWrapper />
              </div>
              <p className="text-xs text-slate-400 mt-1">Automated Lead Pipeline</p>
            </div>

            <nav className="flex-1 p-4 space-y-1">
              <Link href="/" className="sidebar-nav-link">
                <LayoutDashboard className="w-5 h-5" />
                Dashboard
              </Link>
              <Link href="/upload" className="sidebar-nav-link">
                <Upload className="w-5 h-5" />
                Upload Leads
              </Link>
              <Link href="/settings" className="sidebar-nav-link">
                <Settings className="w-5 h-5" />
                Settings
              </Link>
            </nav>

            <div className="p-4 border-t border-slate-700">
              <div className="text-xs text-slate-400">
                <div>v0.1.0</div>
                <div className="mt-1">LangGraph Pipeline</div>
              </div>
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            <div className="container mx-auto p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
