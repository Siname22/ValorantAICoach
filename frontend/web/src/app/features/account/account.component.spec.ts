import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { AccountComponent } from './account.component';
import { ApiClientService } from '../../core/api/api-client.service';
import { TokenService } from '../../core/auth/token.service';
import { of } from 'rxjs';

describe('AccountComponent', () => {
  let component: AccountComponent;
  let fixture: ComponentFixture<AccountComponent>;
  let apiSpy: jasmine.SpyObj<ApiClientService>;
  let tokenService: TokenService;

  beforeEach(async () => {
    sessionStorage.clear();
    apiSpy = jasmine.createSpyObj('ApiClientService', [
      'getAuthMe',
      'getLinkedAccounts',
      'postAuthLogin',
      'postAuthRegister',
      'linkAccount',
      'unlinkAccount',
    ]);

    await TestBed.configureTestingModule({
      imports: [AccountComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ApiClientService, useValue: apiSpy },
      ],
    }).compileComponents();

    tokenService = TestBed.inject(TokenService);
    fixture = TestBed.createComponent(AccountComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('should create the account component', () => {
    expect(component).toBeTruthy();
  });

  it('should render login and register tabs with proper aria-selected states', () => {
    const tabLogin: HTMLElement = fixture.nativeElement.querySelector('#tab-login');
    const tabRegister: HTMLElement = fixture.nativeElement.querySelector('#tab-register');

    expect(tabLogin).toBeTruthy();
    expect(tabRegister).toBeTruthy();
    expect(tabLogin.getAttribute('aria-selected')).toBe('true');
    expect(tabRegister.getAttribute('aria-selected')).toBe('false');
  });

  it('should switch between login and register modes', () => {
    component.setRegisterMode(true);
    fixture.detectChanges();

    const emailInput = fixture.nativeElement.querySelector('#auth-email');
    expect(emailInput).toBeTruthy();

    const tabRegister: HTMLElement = fixture.nativeElement.querySelector('#tab-register');
    expect(tabRegister.getAttribute('aria-selected')).toBe('true');
  });

  it('should handle login and load user profile on success', () => {
    apiSpy.postAuthLogin.and.returnValue(
      of({
        access_token: 'fake-jwt-token',
        token_type: 'bearer',
      })
    );
    apiSpy.getAuthMe.and.returnValue(
      of({
        id: 'user-1',
        username: 'testplayer',
        email: 'test@example.com',
        is_active: true,
        is_admin: false,
        riot_id: 'Test#123',
        created_at: '2026-01-01',
      })
    );
    apiSpy.getLinkedAccounts.and.returnValue(of([]));

    component.username = 'testplayer';
    component.password = 'Secret123!';
    component.onSubmit();

    expect(apiSpy.postAuthLogin).toHaveBeenCalled();
    expect(tokenService.hasToken()).toBeTrue();
  });
});
