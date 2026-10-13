/**
 * AUTO-GENERATED API CLIENT FROM openapi.json. DO NOT EDIT DIRECTLY.
 */

import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import * as Models from './api-models';

@Injectable({
  providedIn: 'root'
})
export class ApiClientService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = '/v1';

  // 1. Auth endpoints
  register(body: Models.RegisterRequest): Observable<Models.UserResponse> {
    return this.http.post<Models.UserResponse>(`${this.baseUrl}/auth/register`, body);
  }

  login(body: Models.LoginRequest): Observable<Models.TokenResponse> {
    return this.http.post<Models.TokenResponse>(`${this.baseUrl}/auth/login`, body);
  }

  getMe(): Observable<Models.UserResponse> {
    return this.http.get<Models.UserResponse>(`${this.baseUrl}/auth/me`);
  }

  getLinkedAccounts(): Observable<Models.LinkedAccountResponse[]> {
    const url = `${this.baseUrl}/auth/me/accounts`;
    return this.http.get<Models.LinkedAccountResponse[]>(url);
  }

  linkAccount(
    body: Models.LinkAccountRequest
  ): Observable<Models.LinkedAccountResponse> {
    const url = `${this.baseUrl}/auth/me/accounts`;
    return this.http.post<Models.LinkedAccountResponse>(url, body);
  }

  unlinkAccount(accountId: string): Observable<{ success: boolean }> {
    const url = `${this.baseUrl}/auth/me/accounts/${accountId}`;
    return this.http.delete<{ success: boolean }>(url);
  }

  // 2. Player Profile and Match telemetry
  getPlayer(
    gameName: string,
    tagLine: string,
    region?: string
  ): Observable<Models.PlayerProfile> {
    let params = new HttpParams();
    if (region) params = params.set('region', region);
    return this.http.get<Models.PlayerProfile>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`,
      { params }
    );
  }

  getPlayerRank(
    gameName: string,
    tagLine: string,
    region?: string
  ): Observable<Models.PlayerRank> {
    let params = new HttpParams();
    if (region) params = params.set('region', region);
    return this.http.get<Models.PlayerRank>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/rank`,
      { params }
    );
  }

  getPlayerMatches(
    gameName: string,
    tagLine: string,
    limit: number = 5,
    region?: string
  ): Observable<{ matches: Models.PlayerMatch[]; count: number }> {
    let params = new HttpParams().set('limit', limit.toString());
    if (region) params = params.set('region', region);
    return this.http.get<{ matches: Models.PlayerMatch[]; count: number }>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/matches`,
      { params }
    );
  }

  getPlayerStats(
    gameName: string,
    tagLine: string
  ): Observable<Models.PlayerStatsOverview> {
    return this.http.get<Models.PlayerStatsOverview>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/stats`
    );
  }

  getPlayerOverview(
    gameName: string,
    tagLine: string,
    region?: string,
    limit: number = 10
  ): Observable<Models.CompletePlayerProfile> {
    let params = new HttpParams().set('limit', limit.toString());
    if (region) params = params.set('region', region);
    return this.http.get<Models.CompletePlayerProfile>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/overview`,
      { params }
    );
  }

  // 3. Coaching Reports & Progression
  getCoachingReports(
    gameName: string,
    tagLine: string,
    limit: number = 5,
    region?: string
  ): Observable<{ reports: Models.CoachingReportSummary[]; count: number }> {
    let params = new HttpParams().set('limit', limit.toString());
    if (region) params = params.set('region', region);
    return this.http.get<{ reports: Models.CoachingReportSummary[]; count: number }>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/reports`,
      { params }
    );
  }

  generateCoachingReport(
    gameName: string,
    tagLine: string,
    limit: number = 5,
    region?: string
  ): Observable<Models.CoachingReportDetailResponse> {
    let params = new HttpParams().set('limit', limit.toString());
    if (region) params = params.set('region', region);
    return this.http.post<Models.CoachingReportDetailResponse>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/reports`,
      {},
      { params }
    );
  }

  getCoachingReport(
    gameName: string,
    tagLine: string,
    reportId: string
  ): Observable<Models.CoachingReportDetailResponse> {
    return this.http.get<Models.CoachingReportDetailResponse>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/reports/${reportId}`
    );
  }

  getPlayerProgression(
    gameName: string,
    tagLine: string
  ): Observable<Models.PlayerProgressionResponse> {
    return this.http.get<Models.PlayerProgressionResponse>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/progression`
    );
  }

  syncPlayer(
    gameName: string,
    tagLine: string,
    region?: string
  ): Observable<{
    status: string;
    new_report_generated: boolean;
    report_id?: string;
  }> {
    let params = new HttpParams();
    if (region) params = params.set('region', region);
    const url =
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/sync`;
    return this.http.post<{
      status: string;
      new_report_generated: boolean;
      report_id?: string;
    }>(url, {}, { params });
  }

  // 4. Timeline & Economy Analytics
  getPlayerTimelineAnalytics(
    gameName: string,
    tagLine: string,
    limit: number = 5
  ): Observable<Models.PlayerTimelineAnalyticsResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<Models.PlayerTimelineAnalyticsResponse>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/timeline-analytics`,
      { params }
    );
  }

  getMatchTimeline(matchId: string): Observable<Models.MatchTimelineResponse> {
    return this.http.get<Models.MatchTimelineResponse>(
      `${this.baseUrl}/matches/${matchId}/timeline`
    );
  }

  // 5. Vision / Scoreboard OCR Ingestion
  uploadScoreboardFile(
    file: File,
    gameName?: string,
    tagLine?: string,
    saveToHistory: boolean = false
  ): Observable<Models.ScoreboardAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (gameName) formData.append('game_name', gameName);
    if (tagLine) formData.append('tag_line', tagLine);
    formData.append('save_to_history', saveToHistory ? 'true' : 'false');
    return this.http.post<Models.ScoreboardAnalysisResponse>(
      `${this.baseUrl}/vision/scoreboard/upload`,
      formData
    );
  }

  // 6. Composition Synergy & Counter-Picks
  evaluateCompositionSynergy(
    body: Models.CompositionSynergyRequest
  ): Observable<Models.CompositionSynergyResponse> {
    return this.http.post<Models.CompositionSynergyResponse>(
      `${this.baseUrl}/recommendations/composition/synergy`,
      body
    );
  }

  getCounterPicks(
    body: Models.CounterPickRequest
  ): Observable<Models.CounterPickResponse> {
    return this.http.post<Models.CounterPickResponse>(
      `${this.baseUrl}/recommendations/counter-picks`,
      body
    );
  }

  // --- Compatibility wrappers for UI code ---

  getAuthMe(): Observable<Models.UserResponse> {
    return this.getMe();
  }

  postAuthRegister(body: {
    username?: string;
    email?: string;
    password?: string;
  }): Observable<Models.UserResponse> {
    const payload: Models.UserRegisterRequest = {
      email: body.email ?? body.username ?? '',
      password: body.password ?? '',
    };
    return this.register(payload);
  }

  postAuthLogin(body: {
    username?: string;
    email?: string;
    password?: string;
  }): Observable<Models.TokenResponse> {
    const payload: Models.UserLoginRequest = {
      email: body.username ?? body.email ?? '',
      password: body.password ?? '',
    };
    return this.login(payload);
  }

  postVisionScoreboardAnalyze(
    formData: FormData
  ): Observable<Models.ScoreboardAnalysisResponse> {
    return this.http.post<Models.ScoreboardAnalysisResponse>(
      `${this.baseUrl}/vision/scoreboard/upload`,
      formData
    );
  }
}
