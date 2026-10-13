/**
 * AUTO-GENERATED FILE FROM openapi.json. DO NOT EDIT DIRECTLY.
 */

export interface AgentCounterRecommendation {
  agent_name: string;
  role: string;
  recommendation_score: number;
  counter_targets?: string[];
  counter_rationale?: string[];
  map_synergy_rationale: string;
  mastery_context?: string | unknown;
}

export interface AgentPerformanceSummary {
  matches_played: number;
  win_pct: number;
  avg_kd: number;
}

export interface Body_upload_scoreboard_file_vision_scoreboard_upload_post {
  file: string;
  game_name?: string | unknown;
  tag_line?: string | unknown;
  save_to_history?: boolean;
}

export interface CachePruneResponse {
  pruned_count: number;
}

export interface CoachingReportResponse {
  id: string;
  player_id?: string | unknown;
  schema_version?: number;
  provider?: string;
  payload: Record<string, unknown>;
  evidence?: Record<string, unknown>[];
  created_at?: string;
  summary?: string;
  strengths?: string;
  weaknesses?: string;
}

export interface CoachingReportsListResponse {
  reports: CoachingReportResponse[];
  count: number;
}

export interface CompletePlayerProfile {
  identity: PlayerIdentity;
  rank?: PlayerRank | unknown;
  stats?: PlayerStatsOverview | unknown;
  recent_matches?: PlayerMatch[] | unknown;
  unavailable_sections?: string[];
}

export interface CompositionSynergyRequest {
  map_name: string;
  allied_agents: string[];
  enemy_agents?: string[];
}

export interface CompositionSynergyResponse {
  map_name: string;
  synergy_score: number;
  tier: 'S' | 'A' | 'B' | 'C' | 'D';
  role_distribution: Record<string, number>;
  utility_coverage: UtilityCoverage;
  strengths?: string[];
  weaknesses?: string[];
  tactical_advice?: string[];
}

export interface CounterPickRequest {
  map_name: string;
  allied_agents?: string[];
  enemy_agents: string[];
}

export interface CounterPickResponse {
  map_name: string;
  recommendations: AgentCounterRecommendation[];
  enemy_threat_assessment?: string[];
}

export interface HTTPValidationError {
  detail?: ValidationError[];
}

export interface HealthResponse {
  status: string;
  version: string;
  providers?: Record<string, string> | unknown;
}

export interface KillEvent {
  kill_index: number;
  round_time_millis: number;
  game_time_millis?: number | unknown;
  killer_puuid?: string | unknown;
  killer_name: string;
  killer_team: string;
  victim_puuid?: string | unknown;
  victim_name: string;
  victim_team: string;
  assistants?: string[];
  weapon?: string | unknown;
  is_headshot?: boolean;
  is_trade_kill?: boolean;
  traded_killer_name?: string | unknown;
  trade_window_millis?: number | unknown;
}

export interface LinkPlayerAccountRequest {
  game_name: string;
  tag_line: string;
  region?: string | null;
  is_primary?: boolean;
}

export interface LinkedPlayerAccountResponse {
  id: string;
  user_id: string;
  game_name: string;
  tag_line: string;
  puuid?: string | null;
  region?: string | null;
  is_primary: boolean;
  linked_at: string;
  last_synced_at?: string | null;
}

export interface MatchTimelineResponse {
  match_id: string;
  map_name?: string;
  game_mode?: string;
  friendly_team?: string | unknown;
  rounds?: RoundTimeline[];
  total_rounds?: number;
  summary?: TimelineTacticalSummary;
}

export interface MetricDataPoint {
  timestamp: number | string;
  value: number;
}

export interface PlayerIdentity {
  puuid?: string | null;
  game_name: string;
  tag_line: string;
  region?: string | null;
  account_level?: number | null;
  avatar_url?: string | null;
  source?: 'tracker' | 'henrik' | 'riot' | string | null;
}

export interface PlayerMatch {
  match_id: string;
  map_name: string;
  mode?: string;
  timestamp?: number | string;
  result: string;
  kills: number;
  deaths: number;
  assists: number;
  score?: number | unknown;
  agent_name: string;
  provider?: 'tracker' | 'henrik' | 'riot' | 'vision' | unknown;
  provider_score?: number | unknown;
  headshots?: number;
  created_at?: string;
}

export interface PlayerMatchResponse {
  match_id: string;
  map_name: string;
  mode: string;
  timestamp: number | string;
  result: string;
  kills: number;
  deaths: number;
  assists: number;
  score?: number | unknown;
  agent_name: string;
  provider?: 'tracker' | 'henrik' | 'riot' | 'vision' | unknown;
  provider_score?: number | unknown;
}

export interface PlayerMatchesResponse {
  matches: PlayerMatchResponse[];
  count: number;
}

export interface PlayerProfileResponse {
  puuid?: string | null;
  game_name: string;
  tag_line: string;
  region?: string | null;
  account_level?: number | null;
  avatar_url?: string | null;
  source?: 'tracker' | 'henrik' | 'riot' | string | null;
  rank_name?: string | null;
  rank_tier?: string | null;
  rank_icon_url?: string | null;
}

export interface PlayerProgressionMetric {
  name: string;
  current: number;
  historical_avg: number;
  trend: 'improving' | 'declining' | 'stable';
  change_pct: number;
  data_points?: MetricDataPoint[];
}

export interface PlayerProgressionResponse {
  game_name: string;
  tag_line: string;
  total_matches_analyzed: number;
  total_reports_generated: number;
  kd_metric: PlayerProgressionMetric;
  headshot_metric: PlayerProgressionMetric;
  win_rate_metric: PlayerProgressionMetric;
  resolved_focus_areas?: string[];
  active_focus_areas?: string[];
  agent_trends?: Record<string, AgentPerformanceSummary>;
  trajectory_narrative: string;
  overall_trend?: string;
}

export interface PlayerRank {
  tier_name: string;
  rank_name?: string | unknown;
  rank_icon_url?: string | unknown;
  points?: number | unknown;
  source?: 'tracker' | 'henrik' | unknown;
}

export interface PlayerRankResponse {
  tier_name: string;
  rank_name?: string | unknown;
  rank_icon_url?: string | unknown;
  points?: number | unknown;
  source?: 'tracker' | 'henrik' | unknown;
}

export interface PlayerRoundEconomy {
  puuid?: string | unknown;
  player_name?: string | unknown;
  loadout_value?: number;
  weapon?: string | unknown;
  armor?: string | unknown;
  remaining_credits?: number;
  category?: 'eco' | 'semi-eco' | 'semi-buy' | 'full-buy' | 'bonus';
}

export interface PlayerStatsOverview {
  kills: number;
  deaths: number;
  assists: number;
  kd_ratio: number;
  win_pct: number;
  headshot_pct: number;
  matches_played?: number | unknown;
  damage_per_round?: number | unknown;
  source?: string;
}

export interface PlayerSyncResponse {
  synced: boolean;
  game_name: string;
  tag_line: string;
  new_report_generated: boolean;
  report_id?: string | unknown;
  matches_synced: number;
  synced_at: string;
}

export interface PlayerTimelineAnalyticsResponse {
  game_name: string;
  tag_line: string;
  matches_analyzed: number;
  total_rounds_analyzed: number;
  overall_attack_win_rate?: number;
  overall_defense_win_rate?: number;
  overall_trade_efficiency?: number;
  overall_clutch_win_rate?: number;
  clutches_won_breakdown?: Record<string, number>;
  anti_eco_losses_total?: number;
  retake_success_rate?: number;
  identified_tactical_leaks?: string[];
}

export interface ReadinessResponse {
  status: string;
  database: string;
  providers_configured: number;
}

export interface RoundTimeline {
  round_num: number;
  winning_team: string;
  winning_side: 'attack' | 'defense' | 'unknown';
  win_type: 'Eliminated' | 'Bomb defused' | 'Bomb detonated' | 'Time out' | 'Surrender' | 'Unknown';
  friendly_won?: boolean | unknown;
  ceremony?: string | unknown;
  is_clutch?: boolean;
  clutch_player?: string | unknown;
  clutch_opponents?: number;
  clutch_won?: boolean;
  is_thrifty?: boolean;
  is_anti_eco_loss?: boolean;
  first_blood?: KillEvent | unknown;
  first_death?: KillEvent | unknown;
  spike_plant?: SpikeEvent | unknown;
  spike_defuse?: SpikeEvent | unknown;
  retake_situation?: boolean;
  retake_successful?: boolean;
  kills?: KillEvent[];
  player_economies?: Record<string, PlayerRoundEconomy>;
  team_loadouts?: Record<string, number>;
  friendly_score_after?: number;
  enemy_score_after?: number;
  round_number?: number;
  result?: 'Won' | 'Lost' | string;
  loadout_value?: number;
  spent_credits?: number;
}

export interface ScoreboardAnalysisResponse {
  match_id: string;
  map_name: string;
  game_mode?: string;
  result: 'Victory' | 'Defeat' | 'Draw' | 'Unknown';
  rounds_won: number;
  rounds_lost: number;
  target_player_stats?: ScoreboardPlayerRow | unknown;
  scoreboard_rows?: ScoreboardPlayerRow[];
  confidence_score?: number | unknown;
  extractor_engine: string;
  tactical_takeaways?: string[];
  persisted_as_match?: boolean;
  persistence_note?: string | unknown;
}

export interface ScoreboardIngestRequest {
  image_base64: string;
  game_name?: string | unknown;
  tag_line?: string | unknown;
  save_to_history?: boolean;
}

export interface ScoreboardPlayerRow {
  player_name: string;
  tag_line?: string | unknown;
  agent: string;
  team?: 'friendly' | 'enemy' | 'blue' | 'red' | 'unknown';
  score?: number | unknown;
  kills: number;
  deaths: number;
  assists: number;
  damage_per_round?: number | unknown;
  first_bloods?: number | unknown;
  plants?: number | unknown;
  defuses?: number | unknown;
}

export interface SpikeEvent {
  event_type: 'plant' | 'defuse';
  round_time_millis: number;
  site?: string | unknown;
  player_puuid?: string | unknown;
  player_name?: string | unknown;
  player_team?: string | unknown;
  success?: boolean;
}

export interface TimelineTacticalSummary {
  total_rounds: number;
  attack_rounds_won?: number;
  attack_rounds_total?: number;
  attack_win_rate?: number;
  defense_rounds_won?: number;
  defense_rounds_total?: number;
  defense_win_rate?: number;
  first_bloods_count?: number;
  first_deaths_count?: number;
  first_blood_conversion_rate?: number;
  trade_kills_count?: number;
  trade_efficiency_rate?: number;
  clutch_attempts?: number;
  clutch_wins?: number;
  clutch_win_rate?: number;
  anti_eco_losses?: number;
  thrifty_wins?: number;
  retake_attempts?: number;
  retake_successes?: number;
  retake_success_rate?: number;
  tactical_takeaways?: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  is_active: boolean;
  is_admin?: boolean;
  created_at: string;
  username?: string;
  riot_id?: string;
}

export interface UtilityCoverage {
  smokes: boolean;
  flashes: boolean;
  recon_info: boolean;
  sentinel_anchor: boolean;
  entry_duelist: boolean;
}

export interface ValidationError {
  loc: string | number[];
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>;
}

// --- Compatibility aliases / extensions for UI code ---
export interface CoachingReportSummary {
  id: string;
  created_at?: string;
  summary?: string;
  strengths?: string;
  weaknesses?: string;
  payload?: Record<string, unknown>;
  player_id?: string;
}

export type PlayerProfile = PlayerProfileResponse;
export type VisionAnalysisResponse = ScoreboardAnalysisResponse;
export type RegisterRequest = UserRegisterRequest;
export type LoginRequest = UserLoginRequest;
export type LinkedAccountResponse = LinkedPlayerAccountResponse;
export type LinkAccountRequest = LinkPlayerAccountRequest;
export type CoachingReportDetailResponse = CoachingReportResponse & {
  status?: string;
  report?: CoachingReportResponse;
};
