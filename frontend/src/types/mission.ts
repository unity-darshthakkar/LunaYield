/** LunaYield Mission Lab — TypeScript types mirroring backend/app/schemas.py exactly */

// Enums
export enum MissionStatus {
  IDLE = 'IDLE',
  RUNNING = 'RUNNING',
  PAUSED = 'PAUSED',
  ANOMALY = 'ANOMALY',
  PLANNING = 'PLANNING',
  AWAITING_APPROVAL = 'AWAITING_APPROVAL',
  EXECUTING = 'EXECUTING',
  COMPLETED = 'COMPLETED',
  RESET = 'RESET',
}

export enum PlanStatus {
  VALID = 'VALID',
  REJECTED = 'REJECTED',
  APPROVED = 'APPROVED',
}

export enum WaypointProgressStatus {
  COMPLETED = 'COMPLETED',
  CURRENT = 'CURRENT',
  UPCOMING = 'UPCOMING',
  SKIPPED = 'SKIPPED',
}

// Resource models
export interface RoverResources {
  battery_pct: number;
  storage_pct: number;
  temperature_c: number;
  comm_window_remaining_s: number;
  op_time_remaining_s: number;
}

// Telemetry
export interface TelemetrySample {
  mission_id: string;
  elapsed_s: number;
  resources: RoverResources;
  timestamp: string; // ISO datetime string
}

// Route models
export interface RouteWaypoint {
  id: string;
  x: number;
  y: number;
  label: string;
  is_science_target: boolean;
  progress_status?: WaypointProgressStatus;
  segment_elapsed_s?: number;
  science_collected?: boolean;
}

export interface MissionRoute {
  waypoints: RouteWaypoint[];
}

// Safety / planning models
export interface ConstraintViolation {
  rule_id: string;
  description: string;
  measured_value: number;
  threshold_value: number;
}

export interface CandidatePlan {
  plan_id: string;
  label: string;
  description: string;
  waypoints: RouteWaypoint[];
  science_yield_score: number;
  predicted_return_battery_pct: number;
  status: PlanStatus;
  violations: ConstraintViolation[];
  is_recommended: boolean;
  rank: number | null;
}

// Audit
export interface AuditEvent {
  event_id: string;
  event_type: string;
  description: string;
  timestamp: string; // ISO datetime string
  metadata: Record<string, unknown>;
}

// Mission
export interface Mission {
  mission_id: string;
  label: string;
  status: MissionStatus;
  elapsed_s: number;
  resources: RoverResources;
  original_route: MissionRoute;
  active_route: MissionRoute;
  candidate_plans: CandidatePlan[];
  anomaly_active: boolean;
  audit_trail: AuditEvent[];
}

// Plan approval result
export interface PlanApprovalResult {
  approved_plan_id: string;
  updated_route: MissionRoute;
  audit_event: AuditEvent;
  mission_status: MissionStatus;
}

// Forecasting types (Phase 3A / Phase 5A)
export interface ResourceForecast {
  battery_pct: number;
  storage_pct: number;
  temperature_c: number;
  comm_window_remaining_s: number;
  op_time_remaining_s: number;
}

export interface ForecastPoint {
  forecast_seconds_ahead: number;
  elapsed_s: number;
  resources: ResourceForecast;
}

export interface MissionForecastResponse {
  mission_id: string;
  current_elapsed_s: number;
  current_resources: RoverResources;
  forecast_horizon_s: number;
  forecast_tick_interval_s: number;
  forecast_points: ForecastPoint[];
}

// Anomaly Detection types (Phase 3B / Phase 5A)
export type AnomalySeverity = 'INFO' | 'WARNING' | 'CRITICAL';

export type AnomalyResource = 'BATTERY' | 'STORAGE' | 'TEMPERATURE' | 'COMM_WINDOW' | 'OP_TIME';

export interface AnomalyFinding {
  resource: AnomalyResource;
  severity: AnomalySeverity;
  observed_value: number;
  threshold_value: number;
  reason: string;
  is_forecast: boolean;
  forecast_seconds_ahead: number | null;
}

export interface AnomalyDetectionResponse {
  mission_id: string;
  current_elapsed_s: number;
  anomalies: AnomalyFinding[];
  anomaly_count: number;
  has_critical: boolean;
  has_warning: boolean;
}

// Strategy Generation types (Phase 4A / Phase 5B)
export interface StrategyCandidate {
  strategy_id: string;
  title: string;
  rationale: string;
  priority: number; // 1 = highest, 5 = lowest
  affected_resources: AnomalyResource[];
  recommended_actions: string[];
  source_anomalies: string[];
  requires_operator_approval: boolean;
}

export interface StrategyGenerationResponse {
  mission_id: string;
  current_elapsed_s: number;
  strategies: StrategyCandidate[];
  strategy_count: number;
  has_critical_priority: boolean;
}

// Strategy Validation types (Phase 4B / Phase 5C)
export interface StrategyValidationResult {
  strategy_id: string;
  is_valid: boolean;
  rejection_reasons: string[];
}

export interface StrategyValidationResponse {
  mission_id: string;
  current_elapsed_s: number;
  validation_results: StrategyValidationResult[];
  validation_count: number;
  all_valid: boolean;
}

// Strategy Approval types (Phase 4C / Phase 5C)
export type StrategyApprovalStatus = 'APPROVED' | 'REJECTED' | 'VALIDATION_FAILED' | 'NOT_FOUND' | 'ALREADY_APPROVED';

export interface StrategyApprovalResult {
  strategy_id: string;
  approved: boolean;
  approval_status: StrategyApprovalStatus;
  rejection_reasons: string[];
}
