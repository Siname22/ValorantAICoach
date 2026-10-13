"""Python runner for openapi code generation for frontend/web.
Generates TypeScript interfaces and ApiClientService from openapi.json.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OPENAPI_CANDIDATES = [
    ROOT / "openapi.json",
    Path(__file__).resolve().parents[1] / "openapi.json",
]
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "src" / "app" / "core" / "api"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OPENAPI_PATH = next((p for p in OPENAPI_CANDIDATES if p.exists()), None)

if OPENAPI_PATH is None:
    # Try generating directly from backend FastAPI app
    try:
        from backend.main import app

        spec = app.openapi()
        OPENAPI_PATH = Path(__file__).resolve().parents[1] / "openapi.json"
        with open(OPENAPI_PATH, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)
    except Exception as exc:
        raise FileNotFoundError("Could not find or generate openapi.json") from exc
else:
    with open(OPENAPI_PATH, encoding="utf-8") as f:
        spec = json.load(f)


def resolve_type(prop: dict) -> str:
    if not prop:
        return "unknown"
    if "$ref" in prop:
        return prop["$ref"].split("/")[-1]
    if "anyOf" in prop:
        return " | ".join(resolve_type(p) for p in prop["anyOf"])
    if "allOf" in prop:
        return " & ".join(resolve_type(p) for p in prop["allOf"])

    t = prop.get("type")
    if t == "string":
        if "enum" in prop:
            return " | ".join(f"'{e}'" for e in prop["enum"])
        return "string"
    if t in ("integer", "number"):
        return "number"
    if t == "boolean":
        return "boolean"
    if t == "array":
        return f"{resolve_type(prop.get('items', {}))}[]"
    if t == "object":
        if isinstance(prop.get("additionalProperties"), dict):
            return f"Record<string, {resolve_type(prop['additionalProperties'])}>"
        return "Record<string, unknown>"
    return "unknown"


# 1. Models
models_lines = [
    "/**",
    " * AUTO-GENERATED FILE FROM openapi.json. DO NOT EDIT DIRECTLY.",
    " */",
    "",
]

schemas = spec.get("components", {}).get("schemas", {})
for name, schema in schemas.items():
    if schema.get("type") == "object" or "properties" in schema:
        models_lines.append(f"export interface {name} {{")
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        for prop_name, prop_def in props.items():
            optional = "" if prop_name in required else "?"
            models_lines.append(f"  {prop_name}{optional}: {resolve_type(prop_def)};")
        models_lines.append("}\n")
    elif "enum" in schema:
        enum_types = " | ".join(f"'{v}'" for v in schema["enum"])
        models_lines.append(f"export type {name} = {enum_types};\n")

models_path = OUTPUT_DIR / "api-models.ts"
models_path.write_text("\n".join(models_lines), encoding="utf-8")
print(f"Generated {len(schemas)} models in {models_path}")

# 2. Client Service
client_code = """/**
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
  getPlayer(gameName: string, tagLine: string): Observable<Models.PlayerProfile> {
    return this.http.get<Models.PlayerProfile>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}`
    );
  }

  getPlayerRank(gameName: string, tagLine: string): Observable<Models.PlayerRank> {
    return this.http.get<Models.PlayerRank>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/rank`
    );
  }

  getPlayerMatches(
    gameName: string,
    tagLine: string,
    limit: number = 5
  ): Observable<{ matches: Models.PlayerMatch[]; count: number }> {
    const params = new HttpParams().set('limit', limit.toString());
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
    tagLine: string
  ): Observable<Models.CompletePlayerProfile> {
    return this.http.get<Models.CompletePlayerProfile>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/overview`
    );
  }

  // 3. Coaching Reports & Progression
  getCoachingReports(
    gameName: string,
    tagLine: string,
    limit: number = 5
  ): Observable<{ reports: Models.CoachingReportSummary[]; count: number }> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<{ reports: Models.CoachingReportSummary[]; count: number }>(
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/reports`,
      { params }
    );
  }

  generateCoachingReport(
    gameName: string,
    tagLine: string,
    limit: number = 5
  ): Observable<Models.CoachingReportDetailResponse> {
    const params = new HttpParams().set('limit', limit.toString());
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
    tagLine: string
  ): Observable<{
    status: string;
    new_report_generated: boolean;
    report_id?: string;
  }> {
    const url =
      `${this.baseUrl}/players/${encodeURIComponent(gameName)}/${encodeURIComponent(tagLine)}/sync`;
    return this.http.post<{
      status: string;
      new_report_generated: boolean;
      report_id?: string;
    }>(url, {});
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
}
"""
client_path = OUTPUT_DIR / "api-client.service.ts"
client_path.write_text(client_code, encoding="utf-8")
print(f"Generated ApiClientService in {client_path}")
