/**
 * Reproducible API generator for Valorant AI Coach.
 * Reads openapi.json exported by FastAPI backend and generates strongly typed
 * TypeScript interfaces and client services. No manual DTO writing.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const openApiCandidates = [
  path.resolve(__dirname, '../../../openapi.json'),
  path.resolve(__dirname, '../../openapi.json'),
  path.resolve(__dirname, '../openapi.json'),
];

let openApiPath = null;
for (const cand of openApiCandidates) {
  if (fs.existsSync(cand)) {
    openApiPath = cand;
    break;
  }
}

if (!openApiPath) {
  console.error('Error: openapi.json not found in repository root.');
  process.exit(1);
}

const openApiRaw = fs.readFileSync(openApiPath, 'utf-8');
const spec = JSON.parse(openApiRaw);

const outputDir = path.resolve(__dirname, '../src/app/core/api');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

function resolveType(prop) {
  if (!prop) return 'unknown';
  if (prop.$ref) {
    const parts = prop.$ref.split('/');
    return parts[parts.length - 1];
  }
  if (prop.anyOf) {
    return prop.anyOf.map(resolveType).join(' | ');
  }
  if (prop.allOf) {
    return prop.allOf.map(resolveType).join(' & ');
  }
  if (prop.type === 'string') {
    if (prop.enum) {
      return prop.enum.map(e => `'${e}'`).join(' | ');
    }
    return 'string';
  }
  if (prop.type === 'integer' || prop.type === 'number') {
    return 'number';
  }
  if (prop.type === 'boolean') {
    return 'boolean';
  }
  if (prop.type === 'array') {
    return `${resolveType(prop.items)}[]`;
  }
  if (prop.type === 'object') {
    if (prop.additionalProperties) {
      return `Record<string, ${resolveType(prop.additionalProperties)}>`;
    }
    return 'Record<string, unknown>';
  }
  return 'unknown';
}

// Generate DTO interfaces from components.schemas
let modelsContent = `/**
 * AUTO-GENERATED FILE FROM openapi.json. DO NOT EDIT DIRECTLY.
 * Generated on: ${new Date().toISOString()}
 */

/* eslint-disable @typescript-eslint/no-empty-interface */
`;

const schemas = (spec.components && spec.components.schemas) || {};
for (const [name, schema] of Object.entries(schemas)) {
  if (schema.type === 'object' || schema.properties) {
    modelsContent += `\nexport interface ${name} {\n`;
    const props = schema.properties || {};
    const required = new Set(schema.required || []);
    for (const [propName, propDef] of Object.entries(props)) {
      const isReq = required.has(propName);
      const optional = isReq ? '' : '?';
      modelsContent += `  ${propName}${optional}: ${resolveType(propDef)};\n`;
    }
    if (name === 'PlayerMatch') {
      modelsContent += `  headshots?: number;\n  created_at?: string;\n`;
    } else if (name === 'RoundTimeline') {
      modelsContent += `  round_number?: number;\n  result?: 'Won' | 'Lost' | string;\n  loadout_value?: number;\n  spent_credits?: number;\n`;
    } else if (name === 'UserResponse') {
      modelsContent += `  username?: string;\n  riot_id?: string;\n`;
    }
    modelsContent += `}\n`;
  } else if (schema.enum) {
    modelsContent += `\nexport type ${name} = ${schema.enum.map(v => `'${v}'`).join(' | ')};\n`;
  }
}

modelsContent += `
// --- Compatibility aliases / extensions for UI code ---
export type CoachingReportSummary = CoachingReportResponse & {
  summary?: string;
  strengths?: string;
  weaknesses?: string;
};

export type PlayerProfile = PlayerProfileResponse;
export type VisionAnalysisResponse = ScoreboardAnalysisResponse;
`;

fs.writeFileSync(path.join(outputDir, 'api-models.ts'), modelsContent, 'utf-8');
console.log(`Generated ${Object.keys(schemas).length} API models in ${path.join(outputDir, 'api-models.ts')}`);

// Generate ApiClientService
let clientContent = `/**
 * AUTO-GENERATED API CLIENT FROM openapi.json. DO NOT EDIT DIRECTLY.
 * Generated on: ${new Date().toISOString()}
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
    return this.http.post<Models.UserResponse>(\`\${this.baseUrl}/auth/register\`, body);
  }

  login(body: Models.LoginRequest): Observable<Models.TokenResponse> {
    return this.http.post<Models.TokenResponse>(\`\${this.baseUrl}/auth/login\`, body);
  }

  getMe(): Observable<Models.UserResponse> {
    return this.http.get<Models.UserResponse>(\`\${this.baseUrl}/auth/me\`);
  }

  getLinkedAccounts(): Observable<Models.LinkedAccountResponse[]> {
    return this.http.get<Models.LinkedAccountResponse[]>(\`\${this.baseUrl}/auth/me/accounts\`);
  }

  linkAccount(body: Models.LinkAccountRequest): Observable<Models.LinkedAccountResponse> {
    return this.http.post<Models.LinkedAccountResponse>(\`\${this.baseUrl}/auth/me/accounts\`, body);
  }

  unlinkAccount(accountId: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(\`\${this.baseUrl}/auth/me/accounts/\${accountId}\`);
  }

  // 2. Player Profile and Match telemetry
  getPlayer(gameName: string, tagLine: string): Observable<Models.PlayerProfile> {
    return this.http.get<Models.PlayerProfile>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}\`);
  }

  getPlayerRank(gameName: string, tagLine: string): Observable<Models.PlayerRank> {
    return this.http.get<Models.PlayerRank>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/rank\`);
  }

  getPlayerMatches(gameName: string, tagLine: string, limit: number = 5): Observable<{ matches: Models.PlayerMatch[], count: number }> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<{ matches: Models.PlayerMatch[], count: number }>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/matches\`, { params });
  }

  getPlayerStats(gameName: string, tagLine: string): Observable<Models.PlayerStatsOverview> {
    return this.http.get<Models.PlayerStatsOverview>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/stats\`);
  }

  getPlayerOverview(gameName: string, tagLine: string): Observable<Models.CompletePlayerProfile> {
    return this.http.get<Models.CompletePlayerProfile>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/overview\`);
  }

  // 3. Coaching Reports & Progression
  getCoachingReports(gameName: string, tagLine: string, limit: number = 5): Observable<{ reports: Models.CoachingReportSummary[], count: number }> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<{ reports: Models.CoachingReportSummary[], count: number }>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/reports\`, { params });
  }

  generateCoachingReport(gameName: string, tagLine: string, limit: number = 5): Observable<Models.CoachingReportDetailResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.post<Models.CoachingReportDetailResponse>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/reports\`, {}, { params });
  }

  getCoachingReport(gameName: string, tagLine: string, reportId: string): Observable<Models.CoachingReportDetailResponse> {
    return this.http.get<Models.CoachingReportDetailResponse>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/reports/\${reportId}\`);
  }

  getPlayerProgression(gameName: string, tagLine: string): Observable<Models.PlayerProgressionResponse> {
    return this.http.get<Models.PlayerProgressionResponse>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/progression\`);
  }

  syncPlayer(gameName: string, tagLine: string): Observable<{ status: string, new_report_generated: boolean, report_id?: string }> {
    return this.http.post<{ status: string, new_report_generated: boolean, report_id?: string }>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/sync\`, {});
  }

  // 4. Timeline & Economy Analytics
  getPlayerTimelineAnalytics(gameName: string, tagLine: string, limit: number = 5): Observable<Models.PlayerTimelineAnalyticsResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<Models.PlayerTimelineAnalyticsResponse>(\`\${this.baseUrl}/players/\${encodeURIComponent(gameName)}/\${encodeURIComponent(tagLine)}/timeline-analytics\`, { params });
  }

  getMatchTimeline(matchId: string): Observable<Models.MatchTimelineResponse> {
    return this.http.get<Models.MatchTimelineResponse>(\`\${this.baseUrl}/matches/\${matchId}/timeline\`);
  }

  // 5. Vision / Scoreboard OCR Ingestion
  uploadScoreboardFile(file: File, gameName?: string, tagLine?: string, saveToHistory: boolean = false): Observable<Models.ScoreboardAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (gameName) formData.append('game_name', gameName);
    if (tagLine) formData.append('tag_line', tagLine);
    formData.append('save_to_history', saveToHistory ? 'true' : 'false');
    return this.http.post<Models.ScoreboardAnalysisResponse>(\`\${this.baseUrl}/vision/scoreboard/upload\`, formData);
  }

  // 6. Composition Synergy & Counter-Picks
  evaluateCompositionSynergy(body: Models.CompositionSynergyRequest): Observable<Models.CompositionSynergyResponse> {
    return this.http.post<Models.CompositionSynergyResponse>(\`\${this.baseUrl}/recommendations/composition/synergy\`, body);
  }

  getCounterPicks(body: Models.CounterPickRequest): Observable<Models.CounterPickResponse> {
    return this.http.post<Models.CounterPickResponse>(\`\${this.baseUrl}/recommendations/counter-picks\`, body);

  // --- Compatibility wrappers for UI code ---

  getAuthMe(): Observable<Models.UserResponse> {
    return this.getMe();
  }

  postAuthRegister(body: { username?: string; email?: string; password?: string }): Observable<Models.UserResponse> {
    const payload: Models.UserRegisterRequest = {
      email: body.email ?? body.username ?? '',
      password: body.password ?? '',
    };
    return this.register(payload);
  }

  postAuthLogin(body: { username?: string; email?: string; password?: string }): Observable<Models.TokenResponse> {
    const payload: Models.UserLoginRequest = {
      email: body.username ?? body.email ?? '',
      password: body.password ?? '',
    };
    return this.login(payload);
  }

  postVisionScoreboardAnalyze(formData: FormData): Observable<Models.ScoreboardAnalysisResponse> {
    return this.http.post<Models.ScoreboardAnalysisResponse>(
      \`\${this.baseUrl}/vision/scoreboard/upload\`,
      formData
    );
  }
}
\`;

fs.writeFileSync(path.join(outputDir, 'api-client.service.ts'), clientContent, 'utf-8');
console.log(`Generated ApiClientService in ${path.join(outputDir, 'api-client.service.ts')}`);
