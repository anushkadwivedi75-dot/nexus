/**
 * Nexus Auth Store (Zustand)
 *
 * Adheres strictly to security requirements:
 * 1. Access tokens are stored purely IN-MEMORY (never written to localStorage or sessionStorage).
 * 2. Cross-tab synchronization via AuthCoordinator (Web Locks + BroadcastChannel).
 * 3. Silent refresh on boot via HTTP-only cookie.
 */

import { create } from 'zustand';
import { apiClient } from '../services/api';
import { authCoordinator } from '../services/auth-coordination';
import type { UserProfile } from '../types';

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  setAccessToken: (token: string | null) => void;
  setUser: (user: UserProfile | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  initAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => {
  // Wire up apiClient callbacks with this store
  apiClient.configure({
    getAccessToken: () => get().accessToken,
    setAccessToken: (token: string) => set({ accessToken: token, isAuthenticated: true }),
    onAuthFailure: () => {
      set({ user: null, accessToken: null, isAuthenticated: false });
    },
  });

  // Subscribe to cross-tab auth events
  authCoordinator.subscribe((msg) => {
    if (msg.type === 'TOKEN_REFRESHED') {
      const currentToken = get().accessToken;
      if (currentToken !== msg.accessToken) {
        set({ accessToken: msg.accessToken, isAuthenticated: true });
        // Refresh user profile if not present
        if (!get().user) {
          apiClient
            .get('/users/me')
            .then((res) => {
              if (res.data) set({ user: res.data });
            })
            .catch(() => {});
        }
      }
    } else if (msg.type === 'AUTH_LOGOUT') {
      set({ user: null, accessToken: null, isAuthenticated: false });
    }
  });

  return {
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,

    clearError: () => set({ error: null }),

    setAccessToken: (token: string | null) =>
      set({ accessToken: token, isAuthenticated: !!token }),

    setUser: (user: UserProfile | null) => set({ user }),

    login: async (email: string, password: string) => {
      set({ error: null });
      try {
        const response = await apiClient.post('/auth/login', { email, password });
        const { access_token, user } = response.data;

        set({
          accessToken: access_token,
          user: user,
          isAuthenticated: true,
          error: null,
        });

        authCoordinator.broadcast({
          type: 'TOKEN_REFRESHED',
          accessToken: access_token,
          epoch: Date.now(),
        });
      } catch (err: any) {
        const msg = err.data?.detail || err.message || 'Login failed. Please check your credentials.';
        set({ error: msg });
        throw err;
      }
    },

    register: async (email: string, password: string, fullName: string) => {
      set({ error: null });
      try {
        const response = await apiClient.post('/auth/register', {
          email,
          password,
          full_name: fullName,
        });
        const { access_token, user } = response.data;

        set({
          accessToken: access_token,
          user: user,
          isAuthenticated: true,
          error: null,
        });

        authCoordinator.broadcast({
          type: 'TOKEN_REFRESHED',
          accessToken: access_token,
          epoch: Date.now(),
        });
      } catch (err: any) {
        const msg = err.data?.detail || err.message || 'Registration failed.';
        set({ error: msg });
        throw err;
      }
    },

    logout: async () => {
      try {
        await apiClient.post('/auth/logout');
      } catch (err) {
        console.warn('[useAuthStore] Logout API call failed:', err);
      } finally {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          error: null,
        });
        authCoordinator.broadcast({ type: 'AUTH_LOGOUT' });
      }
    },

    initAuth: async () => {
      set({ isLoading: true });
      try {
        // Attempt silent refresh using HTTP-only cookie
        const res = await apiClient.post('/auth/refresh');
        const token = res.data?.access_token;
        if (token) {
          set({ accessToken: token, isAuthenticated: true });
          // Fetch current user profile
          const userRes = await apiClient.get('/users/me');
          if (userRes.data) {
            set({ user: userRes.data, isAuthenticated: true });
          }
        } else {
          set({ isAuthenticated: false, user: null, accessToken: null });
        }
      } catch {
        // Unauthenticated on boot
        set({ isAuthenticated: false, user: null, accessToken: null });
      } finally {
        set({ isLoading: false });
      }
    },
  };
});
