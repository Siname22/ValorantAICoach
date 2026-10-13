import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SkipLinkComponent } from './skip-link.component';
import { I18N_ES } from '../../../core/i18n/es';

describe('SkipLinkComponent', () => {
  let component: SkipLinkComponent;
  let fixture: ComponentFixture<SkipLinkComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkipLinkComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SkipLinkComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the skip-link component', () => {
    expect(component).toBeTruthy();
  });

  it('should render link pointing to #main-content with accessible text', () => {
    const link: HTMLAnchorElement = fixture.nativeElement.querySelector('a');
    expect(link).toBeTruthy();
    expect(link.getAttribute('href')).toBe('#main-content');
    expect(link.textContent?.trim()).toBe(I18N_ES.a11y.skipToContent);
    expect(link.classList.contains('skip-link')).toBeTrue();
  });
});
