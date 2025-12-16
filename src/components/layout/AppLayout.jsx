import React from 'react';
import { ToastProvider } from '../ui/Toast.jsx';
import AppSidebar from './AppSidebar';
import AppTopbar from './AppTopbar';

export default function AppLayout({ children }) {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
        <div className="min-h-screen grid grid-cols-12">
          <aside className="hidden lg:block col-span-3 xl:col-span-2 border-r border-[var(--border)] bg-[var(--surface)]">
            <div className="h-full sticky top-0 p-4">
              <AppSidebar />
            </div>
          </aside>
          <main className="col-span-12 lg:col-span-9 xl:col-span-10">
            <div className="sticky top-0 z-30 bg-[var(--surface)] border-b border-[var(--border)]">
              <AppTopbar />
            </div>
            <div className="px-6 lg:px-8 py-6 space-y-6 max-w-screen-2xl mx-auto">
              {children}
            </div>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
