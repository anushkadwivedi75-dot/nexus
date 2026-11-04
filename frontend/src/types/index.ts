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

export interface Project {
  id: string
  workspace_id: string
  name: string
  key: string
  description?: string | null
  lead_id?: string | null
  task_counter: number
  is_private: boolean
  status: 'active' | 'archived' | 'completed'
  created_at: string
  updated_at: string
}

export interface TaskStatus {
  id: string
  workspace_id: string
  project_id: string
  name: string
  rank: number
  color_hex: string
  is_completed_state: boolean
  created_at?: string
  updated_at?: string
}

export interface TaskAssignee {
  user_id: string
  email?: string
  full_name?: string
  avatar_url?: string | null
}

export interface TaskTag {
  id: string
  name: string
  color_hex: string
}

export interface Task {
  id: string
  workspace_id: string
  project_id: string
  task_number: number
  title: string
  description_md?: string | null
  priority: 'low' | 'medium' | 'high' | 'urgent'
  status_id: string
  rank: number
  version: number
  due_date?: string | null
  assignees: TaskAssignee[]
  tags: TaskTag[]
  created_at: string
  updated_at: string
}

export interface BoardColumn {
  status: TaskStatus
  tasks: Task[]
}

export interface BoardData {
  project_id: string
  columns: BoardColumn[]
}

export interface RoadmapMilestone {
  id: string
  task_number: number
  title: string
  status_id: string
  status_name: string
  status_color: string
  is_completed: boolean
  priority: string
  due_date: string
}

export interface CommentAuthor {
  id: string
  full_name?: string
  email?: string
  avatar_url?: string | null
}

export interface CommentMention {
  user_id: string
  full_name?: string
  email?: string
}

export interface TaskComment {
  id: string
  workspace_id: string
  task_id: string
  author_id?: string | null
  author?: CommentAuthor | null
  parent_comment_id?: string | null
  content: string
  is_deleted: boolean
  version: number
  created_at: string
  updated_at: string
  reply_count: number
  replies: TaskComment[]
  mentions: CommentMention[]
  isPending?: boolean
  error?: string | null
}

export interface CommentPagination {
  items: TaskComment[]
  next_cursor?: string | null
  has_more: boolean
}



