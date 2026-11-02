/**
 * Nexus API Client
 *
 * Implements centralized HTTP requests with credentials, in-memory token injection,
 * CSRF protection, and automatic 401 refresh interception with cross-tab coordination.
 */

import { authCoordinator } from './auth-coordination';

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
}

class ApiClient {
  private baseUrl: string = '/api/v1';
  private getAccessTokenFn: (() => string | null) | null = null;
  private setAccessTokenFn: ((token: string) => void) | null = null;
  private onAuthFailureFn: (() => void) | null = null;
  private isRefreshing: boolean = false;
  private refreshPromise: Promise<string | null> | null = null;

  public configure(options: {
    getAccessToken: () => string | null;
    setAccessToken: (token: string) => void;
    onAuthFailure: () => void;
  }) {
    this.getAccessTokenFn = options.getAccessToken;
    this.setAccessTokenFn = options.setAccessToken;
    this.onAuthFailureFn = options.onAuthFailure;
  }

  public async request<T = any>(
    path: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = path.startsWith('http') ? path : `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    const headers = new Headers(options.headers || {});

    // Always include CSRF indicator header
    headers.set('X-Requested-With', 'XMLHttpRequest');

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    // Attach in-memory access token if available
    const token = this.getAccessTokenFn ? this.getAccessTokenFn() : null;
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const fetchConfig: RequestInit = {
      ...options,
      headers,
      credentials: 'include', // Ensures HTTP-only refresh cookies are sent
    };

    let response = await fetch(url, fetchConfig);

    // If 401 Unauthorized and not already authenticating/refreshing
    if (
      response.status === 401 &&
      !path.includes('/auth/login') &&
      !path.includes('/auth/register') &&
      !path.includes('/auth/refresh')
    ) {
      const newToken = await this.performCoordinatedRefresh();
      if (newToken) {
        // Retry the original request with the new access token
        headers.set('Authorization', `Bearer ${newToken}`);
        response = await fetch(url, {
          ...fetchConfig,
          headers,
        });
      } else {
        if (this.onAuthFailureFn) {
          this.onAuthFailureFn();
        }
      }
    }

    let data: any;
    try {
      data = await response.json();
    } catch {
      data = { success: response.ok, message: response.statusText };
    }

    if (!response.ok) {
      const errorMsg = data?.error?.message || data?.detail || `HTTP Error ${response.status}`;
      const error = new Error(errorMsg) as any;
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data as ApiResponse<T>;
  }

  private async performCoordinatedRefresh(): Promise<string | null> {
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }

    this.isRefreshing = true;
    this.refreshPromise = authCoordinator
      .executeRefresh(async () => {
        try {
          const res = await fetch(`${this.baseUrl}/auth/refresh`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'include',
          });

          if (!res.ok) {
            return null;
          }

          const json = await res.json();
          const newToken = json?.data?.access_token;
          if (newToken && this.setAccessTokenFn) {
            this.setAccessTokenFn(newToken);
            authCoordinator.broadcast({
              type: 'TOKEN_REFRESHED',
              accessToken: newToken,
              epoch: Date.now(),
            });
            return newToken;
          }
          return null;
        } catch (err) {
          console.error('[ApiClient] Refresh error:', err);
          return null;
        }
      })
      .finally(() => {
        this.isRefreshing = false;
        this.refreshPromise = null;
      });

    return this.refreshPromise;
  }

  public get<T = any>(path: string, options?: RequestInit) {
    return this.request<T>(path, { ...options, method: 'GET' });
  }

  public post<T = any>(path: string, body?: any, options?: RequestInit) {
    return this.request<T>(path, {
      ...options,
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  public patch<T = any>(path: string, body?: any, options?: RequestInit) {
    return this.request<T>(path, {
      ...options,
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  public delete<T = any>(path: string, options?: RequestInit) {
    return this.request<T>(path, { ...options, method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();

