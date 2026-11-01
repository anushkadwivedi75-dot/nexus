import * as React from "react"
import { Sidebar } from "@/components/layout/sidebar"
import { Header } from "@/components/layout/header"
import { MobileNav } from "@/components/layout/mobile-nav"
import { CommandPalette } from "@/components/layout/command-palette"

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background font-sans">
      {/* Desktop Left Sidebar (hidden on mobile) */}
      <Sidebar className="hidden md:flex shrink-0" />

      {/* Mobile Sliding Navigation Drawer */}
      <MobileNav />

      {/* Main Layout Area */}
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Header />

        {/* Scrollable Page Content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-6xl w-full">
            {children}
          </div>
        </main>
      </div>

      {/* Global Command Palette */}
      <CommandPalette />
    </div>
  )
}

