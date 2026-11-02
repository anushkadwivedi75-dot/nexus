/**
 * Nexus Cross-Tab Authentication Coordinator
 *
 * Implements Section 6.3 & Section 6.4 of NEXUS_SYSTEM_BLUEPRINT_PHASE_0_v1.3.1.
 * - Primary coordinator: Web Locks API (`navigator.locks.request`)
 * - Secondary coordinator: BroadcastChannel (`nexus_auth_bus`) + localStorage lease fallback
 * - Event fanout: `TOKEN_REFRESHED`, `AUTH_LOGOUT`, `AUTH_ERROR`
 */

export type AuthMessage =
  | { type: 'TOKEN_REFRESHED'; accessToken: string; epoch: number }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'AUTH_ERROR'; message: string };

const CHANNEL_NAME = 'nexus_auth_bus';
const LOCK_NAME = 'nexus_auth_refresh_lock';
const LEASE_KEY = 'nexus_auth_lease';
const LEASE_DURATION_MS = 6000;
const LEASE_WAIT_TIMEOUT_MS = 7000;

interface LeasePayload {
  tabId: string;
  expiresAt: number;
}

export class AuthCoordinator {
  private tabId: string;
  private channel: BroadcastChannel | null = null;
  private listeners: Set<(msg: AuthMessage) => void> = new Set();

  constructor() {
    this.tabId = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2);
    if (typeof BroadcastChannel !== 'undefined') {
      try {
        this.channel = new BroadcastChannel(CHANNEL_NAME);
        this.channel.onmessage = (event: MessageEvent<AuthMessage>) => {
          this.notifyListeners(event.data);
        };
      } catch (err) {
        console.warn('[AuthCoordinator] BroadcastChannel unavailable:', err);
      }
    }
  }

  public subscribe(callback: (msg: AuthMessage) => void): () => void {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  public broadcast(message: AuthMessage): void {
    if (this.channel) {
      try {
        this.channel.postMessage(message);
      } catch (err) {
        console.warn('[AuthCoordinator] Failed to broadcast message:', err);
      }
    }
    // Also notify listeners in current tab
    this.notifyListeners(message);
  }

  private notifyListeners(message: AuthMessage): void {
    this.listeners.forEach((listener) => {
      try {
        listener(message);
      } catch (err) {
        console.error('[AuthCoordinator] Listener error:', err);
      }
    });
  }

  /**
   * Coordinates token refresh across tabs.
   * If another tab is already refreshing, waits for the broadcasted token.
   * Otherwise, executes `refreshFn` under mutual exclusion.
   */
  public async executeRefresh<T>(refreshFn: () => Promise<T>): Promise<T> {
    if (typeof navigator !== 'undefined' && 'locks' in navigator && typeof navigator.locks?.request === 'function') {
      return this.executeWithWebLock(refreshFn);
    }
    return this.executeWithLocalStorageFallback(refreshFn);
  }

  private async executeWithWebLock<T>(refreshFn: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      navigator.locks.request(
        LOCK_NAME,
        { mode: 'exclusive' },
        async () => {
          try {
            const result = await refreshFn();
            resolve(result);
          } catch (err) {
            reject(err);
          }
        }
      ).catch(reject);
    });
  }

  private async executeWithLocalStorageFallback<T>(refreshFn: () => Promise<T>): Promise<T> {
    const startTime = Date.now();

    while (Date.now() - startTime < LEASE_WAIT_TIMEOUT_MS) {
      const acquired = this.tryAcquireLease();

      if (acquired) {
        let heartbeatInterval: any = null;
        try {
          // Heartbeat every 2 seconds to prevent premature expiration
          heartbeatInterval = setInterval(() => {
            this.renewLease();
          }, 2000);

          const result = await refreshFn();
          return result;
        } finally {
          if (heartbeatInterval) clearInterval(heartbeatInterval);
          this.releaseLease();
        }
      }

      // Another tab holds lease; wait for broadcast or timeout
      const waitPromise = new Promise<T | null>((resolve) => {
        let timer: any = null;
        const cleanup = this.subscribe((msg) => {
          if (msg.type === 'TOKEN_REFRESHED') {
            cleanup();
            if (timer) clearTimeout(timer);
            resolve(msg as unknown as T);
          }
        });

        timer = setTimeout(() => {
          cleanup();
          resolve(null);
        }, 1500);
      });

      const waitedResult = await waitPromise;
      if (waitedResult) {
        return waitedResult;
      }

      // Small jitter before retry
      await new Promise((r) => setTimeout(r, 100 + Math.random() * 200));
    }

    // Fallback: force execute after bounded timeout
    return refreshFn();
  }

  private tryAcquireLease(): boolean {
    try {
      const now = Date.now();
      const raw = localStorage.getItem(LEASE_KEY);
      if (raw) {
        const lease: LeasePayload = JSON.parse(raw);
        if (lease.expiresAt > now && lease.tabId !== this.tabId) {
          return false;
        }
      }

      const newLease: LeasePayload = {
        tabId: this.tabId,
        expiresAt: now + LEASE_DURATION_MS,
      };
      localStorage.setItem(LEASE_KEY, JSON.stringify(newLease));

      // Verify we won
      const check = localStorage.getItem(LEASE_KEY);
      if (check) {
        const parsed: LeasePayload = JSON.parse(check);
        return parsed.tabId === this.tabId;
      }
      return false;
    } catch {
      return true; // If localStorage is disabled or throws, allow proceeding
    }
  }

  private renewLease(): void {
    try {
      const raw = localStorage.getItem(LEASE_KEY);
      if (raw) {
        const lease: LeasePayload = JSON.parse(raw);
        if (lease.tabId === this.tabId) {
          lease.expiresAt = Date.now() + LEASE_DURATION_MS;
          localStorage.setItem(LEASE_KEY, JSON.stringify(lease));
        }
      }
    } catch {
      // Ignored
    }
  }

  private releaseLease(): void {
    try {
      const raw = localStorage.getItem(LEASE_KEY);
      if (raw) {
        const lease: LeasePayload = JSON.parse(raw);
        if (lease.tabId === this.tabId) {
          localStorage.removeItem(LEASE_KEY);
        }
      }
    } catch {
      // Ignored
    }
  }
}

export const authCoordinator = new AuthCoordinator();
