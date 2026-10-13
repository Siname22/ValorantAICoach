import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BentoCardComponent } from './bento-card.component';

describe('BentoCardComponent', () => {
  let component: BentoCardComponent;
  let fixture: ComponentFixture<BentoCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BentoCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BentoCardComponent);
    component = fixture.componentInstance;
  });

  it('should create the bento card component', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should set aria-labelledby when title is provided', () => {
    fixture.componentRef.setInput('title', 'Tarjeta de Prueba');
    fixture.detectChanges();

    const section: HTMLElement = fixture.nativeElement.querySelector('section');
    expect(section).toBeTruthy();
    expect(section.getAttribute('aria-labelledby')).toBeTruthy();

    const heading: HTMLElement = fixture.nativeElement.querySelector('h2');
    expect(heading).toBeTruthy();
    expect(heading.textContent?.trim()).toBe('Tarjeta de Prueba');
  });

  it('should apply variant class when specified', () => {
    fixture.componentRef.setInput('variant', 'highlight');
    fixture.detectChanges();

    const section: HTMLElement = fixture.nativeElement.querySelector('section');
    expect(section.classList.contains('variant-highlight')).toBeTrue();
  });
});
