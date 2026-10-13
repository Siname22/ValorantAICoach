import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type BentoCardVariant = 'default' | 'highlight' | 'lime';
export type BentoCardSpan = 1 | 2 | '1' | '2' | 'full';

let nextCardId = 0;

@Component({
  selector: 'app-bento-card',
  standalone: true,
  template: `
    <section
      class="bento-card"
      [class.variant-highlight]="variant() === 'highlight'"
      [class.variant-lime]="variant() === 'lime'"
      [class.span-2]="span() === 2 || span() === '2'"
      [class.span-full]="span() === 'full'"
      [attr.aria-labelledby]="headingId()"
    >
      @if (title()) {
        <header class="bento-card-header">
          <h2 [id]="headingId()" class="bento-card-title">{{ title() }}</h2>
          @if (subtitle()) {
            <p class="bento-card-subtitle">{{ subtitle() }}</p>
          }
        </header>
      }

      <div class="bento-card-body">
        <ng-content></ng-content>
      </div>
    </section>
  `,
  styles: [`
    :host {
      display: contents;
    }

    .bento-card {
      background-color: var(--color-bg-card);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-card);
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      position: relative;
      overflow: hidden;
    }

    .bento-card-header {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .bento-card-title {
      font-size: var(--font-size-h2);
      font-weight: 600;
      color: var(--color-text-primary);
    }

    .bento-card-subtitle {
      font-size: 13px;
      color: var(--color-text-secondary);
    }

    .bento-card-body {
      flex: 1;
      display: flex;
      flex-direction: column;
    }

    /* Variant: Highlight (Violet #6D3FE0 with white text) */
    .bento-card.variant-highlight {
      background-color: var(--color-card-highlight);
      border-color: rgba(255, 255, 255, 0.15);
      color: var(--color-card-highlight-text);
    }

    .bento-card.variant-highlight .bento-card-title {
      color: var(--color-card-highlight-text);
    }

    .bento-card.variant-highlight .bento-card-subtitle {
      color: rgba(255, 255, 255, 0.8);
    }

    /* Variant: Lime (#C6FF3D with dark text) */
    .bento-card.variant-lime {
      background-color: var(--color-action-primary);
      border-color: transparent;
      color: var(--color-action-text);
    }

    .bento-card.variant-lime .bento-card-title {
      color: var(--color-action-text);
    }

    .bento-card.variant-lime .bento-card-subtitle {
      color: rgba(11, 13, 18, 0.75);
    }

    /* Spans for Bento Grid Layout */
    .bento-card.span-2 {
      grid-column: span 2;
    }

    .bento-card.span-full {
      grid-column: 1 / -1;
    }

    @media (max-width: 900px) {
      .bento-card.span-2 {
        grid-column: 1 / -1;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class BentoCardComponent {
  readonly title = input<string>();
  readonly subtitle = input<string>();
  readonly variant = input<BentoCardVariant>('default');
  readonly span = input<BentoCardSpan>(1);
  readonly customId = input<string>();

  private readonly autoId = `bento-heading-${++nextCardId}`;

  readonly headingId = computed(() => this.customId() || this.autoId);
}
