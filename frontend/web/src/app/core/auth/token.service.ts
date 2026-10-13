/**
 * Token Service managing JWT authentication.
 *
 * Architecture Decision (Duda 1):
 * - Primary storage: Angular reactive signal in memory.
 * - Tab persistence: sessionStorage (isolated to current browser tab, cleared on close).
 * - Justification: Prevents permanent disk exposure (localStorage) while preserving
 *   user session across page reloads (F5) without requiring a backend refresh endpoint.
 */

import { Injectable, computed, signal } from '@angular/core';

const SESSION_TOKEN_KEY = 'val_coach_auth_token';

@Injectable({
  providedIn: 'root'
})
export class TokenService {
  private readonly tokenSignal = signal<string | null>(this.readInitialToken());

  readonly currentToken = this.tokenSignal.asReadonly();
  readonly isAuthenticated = computed(() => Boolean(this.tokenSignal()));

  setToken(token: string): void {
    this.tokenSignal.set(token);
    try {
      sessionStorage.setItem(SESSION_TOKEN_KEY, token);
    } catch {
      // In restricted contexts (e.g. private mode quota exceeded), gracefully fallback to memory-only
    }
  }

  getToken(): string | null {
    return this.tokenSignal();
  }

  clearToken(): void {
    this.tokenSignal.set(null);
    try {
      sessionStorage.removeItem(SESSION_TOKEN_KEY);
    } catch {
      // No-op
    }
  }

  private readInitialToken(): string | null {
    try {
      return sessionStorage.getItem(SESSION_TOKEN_KEY);
    } catch {
      return null;
    }
  }
}
