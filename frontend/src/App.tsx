import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { AppShell } from "@/components/layout/app-shell"
import { OverviewPage } from "@/pages/overview"
import { ProjectsPage } from "@/pages/projects"
import { TasksPage } from "@/pages/tasks"
import { MembersPage } from "@/pages/members"
import { SettingsPage } from "@/pages/settings"
import { InboxPage } from "@/pages/inbox"
import { ActivityPage } from "@/pages/activity"

export function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/members" element={<MembersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}

export default App
