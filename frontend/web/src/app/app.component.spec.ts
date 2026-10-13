import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AppComponent } from './app.component';
import { RouteFocusService } from './core/a11y/route-focus.service';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([]),
        {
          provide: RouteFocusService,
          useValue: { init: () => {} },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create the root app component', () => {
    expect(component).toBeTruthy();
  });

  it('should render skip-link as first accessible focus target', () => {
    const skipLink = fixture.nativeElement.querySelector('app-skip-link');
    expect(skipLink).toBeTruthy();
  });

  it('should render sidebar navigation and main content landmark', () => {
    const sidebar = fixture.nativeElement.querySelector('app-sidebar');
    const main = fixture.nativeElement.querySelector('main#main-content');

    expect(sidebar).toBeTruthy();
    expect(main).toBeTruthy();
    expect(main.getAttribute('tabindex')).toBe('-1');
  });
});
