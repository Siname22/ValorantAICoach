import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SkipLinkComponent } from './shared/ui/skip-link/skip-link.component';
import { SidebarComponent } from './shared/ui/sidebar/sidebar.component';
import { RouteFocusService } from './core/a11y/route-focus.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, SkipLinkComponent, SidebarComponent],
  template: `
    <!-- Skip link must be first focusable element for WCAG 2.2 AA -->
    <app-skip-link></app-skip-link>

    <div class="app-layout">
      <!-- Landmark: nav is inside sidebar -->
      <app-sidebar></app-sidebar>

      <!-- Landmark: main content container -->
      <main id="main-content" class="main-content" tabindex="-1">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      min-height: 100vh;
      background-color: var(--color-bg-page);
      color: var(--color-text);
    }

    .app-layout {
      display: flex;
      min-height: 100vh;
    }

    .main-content {
      flex: 1;
      padding: var(--main-padding);
      min-width: 0;
      outline: none;
    }

    @media (max-width: 900px) {
      .app-layout {
        flex-direction: column;
      }
      .main-content {
        padding: 20px 16px;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  private readonly routeFocusService = inject(RouteFocusService);

  ngOnInit(): void {
    this.routeFocusService.init();
  }
}
