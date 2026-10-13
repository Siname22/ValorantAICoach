/**
 * Accessible Route Focus Service (WCAG 2.2 AA Requirement 12).
 * On NavigationEnd:
 * 1. Updates document.title to reflect the active view.
 * 2. Focuses the primary <h1> of the page (making it programmatically focusable with tabindex="-1").
 */

import { Injectable, inject } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class RouteFocusService {
  private readonly router = inject(Router);
  private readonly titleService = inject(Title);

  initialize(): void {
    this.router.events
      .pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd))
      .subscribe(() => {
        // Allow the DOM to render the new route view
        setTimeout(() => {
          this.focusPrimaryHeading();
        }, 50);
      });
  }

  setPageTitle(viewName: string): void {
    this.titleService.setTitle(`${viewName} · Valorant AI Coach`);
  }

  private focusPrimaryHeading(): void {
    const mainHeading = document.querySelector('main h1') as HTMLElement | null;
    if (mainHeading) {
      if (!mainHeading.hasAttribute('tabindex')) {
        mainHeading.setAttribute('tabindex', '-1');
      }
      mainHeading.focus({ preventScroll: false });
    }
  }
}
