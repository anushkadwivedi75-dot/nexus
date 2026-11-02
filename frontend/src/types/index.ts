export interface UserProfile {
  id: string
  name?: string
  full_name?: string
  email: string
  avatarUrl?: string
  avatar_url?: string | null
  role?: string
  is_active?: boolean
  is_verified?: boolean
  created_at?: string
}

export interface SessionItem {
  id: string
  ip_address?: string | null
  user_agent?: string | null
  created_at: string
  expires_at: string
  is_current: boolean
}

export interface Workspace {
  id: string
  name: string
  slug: string
  plan?: 'Starter' | 'Pro' | 'Enterprise'
  role: 'owner' | 'admin' | 'member'
  membersCount?: number
  members_count?: number
  colorHex?: string
  initials?: string
  owner_id?: string
  logo_url?: string | null
  created_at?: string
  updated_at?: string
}

export interface WorkspaceMemberItem {
  id: string
  workspace_id: string
  user_id: string
  role: 'owner' | 'admin' | 'member'
  joined_at: string
  user: {
    id: string
    email: string
    full_name: string
    avatar_url?: string | null
  }
}

export interface WorkspaceInvitationItem {
  id: string
  workspace_id: string
  email: string
  role: 'admin' | 'member'
  status: 'pending' | 'accepted' | 'revoked' | 'expired'
  invited_by?: string | null
  expires_at: string
  created_at: string
  raw_token?: string
  invite_url?: string
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

