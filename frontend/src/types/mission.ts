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