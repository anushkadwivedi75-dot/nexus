export interface UserProfile {
  id: string
  name: string
  email: string
  avatarUrl?: string
  role: string
}

export interface Workspace {
  id: string
  name: string
  slug: string
  plan: 'Starter' | 'Pro' | 'Enterprise'
  role: 'owner' | 'admin' | 'member'
  membersCount: number
  colorHex: string
  initials: string
}

export interface ProjectPreview {
  id: string
  key: string
  name: string
  description: string
  leadName: string
  leadAvatar?: string
  status: 'active' | 'planning' | 'completed' | 'paused'
  tasksTotal: number
  tasksCompleted: number
  colorHex: string
  updatedAt: string
}

export interface ActivityItem {
  id: string
  actorName: string
  actorAvatar?: string
  action: string
  targetTitle: string
  targetKey?: string
  timestamp: string
  type: 'task' | 'project' | 'comment' | 'member'
}

export interface StatCard {
  label: string
  value: string | number
  change: string
  isPositive: boolean
  description: string
}

