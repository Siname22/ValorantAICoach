import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { SidebarComponent } from './sidebar.component';
import { I18N_ES } from '../../../core/i18n/es';

describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SidebarComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the sidebar component', () => {
    expect(component).toBeTruthy();
  });

  it('should include accessible nav landmark with aria-label', () => {
    const nav: HTMLElement = fixture.nativeElement.querySelector('nav');
    expect(nav).toBeTruthy();
    expect(nav.getAttribute('aria-label')).toBe(I18N_ES.nav.ariaLabel);
  });

  it('should render all five navigation items as native links', () => {
    const links: NodeListOf<HTMLAnchorElement> = fixture.nativeElement.querySelectorAll('nav a');
    expect(links.length).toBe(5);

    const labels = Array.from(links).map((l) => l.querySelector('.nav-label')?.textContent?.trim());
    expect(labels).toContain(I18N_ES.nav.summary);
    expect(labels).toContain(I18N_ES.nav.matches);
    expect(labels).toContain(I18N_ES.nav.reports);
    expect(labels).toContain(I18N_ES.nav.vision);
    expect(labels).toContain(I18N_ES.nav.account);
  });
});
