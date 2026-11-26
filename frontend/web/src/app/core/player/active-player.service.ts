/**
 * Single source of truth for the player (Riot ID + region) selected by the user.
 * Shared by the summary, matches and reports screens so they never diverge.
 * Persisted in sessionStorage (same lifetime policy as the auth token).
 */

import { Injectable, signal } from '@angular/core';

export interface ActivePlayer {
  readonly gameName: string;
  readonly tagLine: string;
  readonly region: string;
}

const STORAGE_KEY = 'val_coach_active_player';

/** Parses "Name#TAG" into its parts; returns null when malformed. */
export function parseRiotId(raw: string): { gameName: string; tagLine: string } | null {
  const idx = raw.lastIndexOf('#');
  if (idx <= 0) return null;
  const gameName = raw.slice(0, idx).trim();
  const tagLine = raw.slice(idx + 1).trim();
  return gameName && tagLine ? { gameName, tagLine } : null;
}

@Injectable({ providedIn: 'root' })
export class ActivePlayerService {
  private readonly state = signal<ActivePlayer | null>(this.read());
  private readonly selectionVersion = signal(0);

  readonly player = this.state.asReadonly();
  readonly version = this.selectionVersion.asReadonly();

  set(player: ActivePlayer): void {
    this.selectionVersion.update((version) => version + 1);
    this.state.set({ ...player });
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(player));
    } catch {
      // memory-only fallback
    }
  }

  clear(): void {
    this.selectionVersion.update((version) => version + 1);
    this.state.set(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      // no-op
    }
  }

  /** True when `p` is still the player currently selected (guards stale responses). */
  isCurrent(gameName: string, tagLine: string, region: string, version?: number): boolean {
    const cur = this.state();
    return (
      !!cur && cur.gameName === gameName && cur.tagLine === tagLine && cur.region === region &&
      (version === undefined || this.selectionVersion() === version)
    );
  }

  private read(): ActivePlayer | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const p = JSON.parse(raw) as Partial<ActivePlayer>;
      return p.gameName && p.tagLine && p.region
        ? { gameName: p.gameName, tagLine: p.tagLine, region: p.region }
        : null;
    } catch {
      return null;
    }
  }
}
