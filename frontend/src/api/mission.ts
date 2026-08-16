/** Typed API functions for mission operations */

import { apiClient } from './client';
import type {
  Mission,
  CandidatePlan,
  TelemetrySample,
  MissionForecastResponse,
  AnomalyDetectionResponse,
  StrategyGenerationResponse,
} from '../types/mission';

// Scenario response shape from GET /api/scenario
export interface ScenarioResponse {
  mission_id: string;
  label: string;
  waypoints: Array<{
    id: string;
    x: number;
    y: number;
    label: string;
    is_science_target: boolean;
  }>;
}

// HTTP API calls

export async function getMissionState(): Promise<Mission> {
  const response = await apiClient.get<Mission>('/mission/state');
  return response.data;
}

export async function getScenario(): Promise<ScenarioResponse> {
  const response = await apiClient.get<ScenarioResponse>('/scenario');
  return response.data;
}

export async function startMission(): Promise<Mission> {
  const response = await apiClient.post<Mission>('/mission/start');
  return response.data;
}

export async function pauseMission(): Promise<Mission> {
  const response = await apiClient.post<Mission>('/mission/pause');
  return response.data;
}

export async function resumeMission(): Promise<Mission> {
  const response = await apiClient.post<Mission>('/mission/resume');
  return response.data;
}

export async function resetMission(): Promise<Mission> {
  const response = await apiClient.post<Mission>('/mission/reset');
  return response.data;
}

export async function injectAnomaly(): Promise<Mission> {
  const response = await apiClient.post<Mission>('/mission/inject-anomaly');
  return response.data;
}

export async function generatePlans(): Promise<CandidatePlan[]> {
  const response = await apiClient.post<CandidatePlan[]>('/plans/generate');
  return response.data;
}

export async function approvePlan(planId: string): Promise<CandidatePlan> {
  const response = await apiClient.post<CandidatePlan>(
    `/plans/${encodeURIComponent(planId)}/approve`
  );
  return response.data;
}

// Forecasting API (Phase 3A / Phase 5A)
export interface ForecastParams {
  horizon?: number;
  interval?: number;
}

export async function getForecast(params?: ForecastParams): Promise<MissionForecastResponse> {
  const response = await apiClient.get<MissionForecastResponse>('/forecast', { params });
  return response.data;
}

// Anomaly Detection API (Phase 3B / Phase 5A)
export interface AnomalyParams {
  use_forecast?: boolean;
  forecast_horizon?: number;
}

export async function getAnomalies(params?: AnomalyParams): Promise<AnomalyDetectionResponse> {
  const response = await apiClient.get<AnomalyDetectionResponse>('/anomalies', { params });
  return response.data;
}

// Strategy Generation API (Phase 4A / Phase 5B)
export interface StrategyParams {
  use_forecast?: boolean;
  forecast_horizon?: number;
}

export async function getStrategies(params?: StrategyParams): Promise<StrategyGenerationResponse> {
  const response = await apiClient.get<StrategyGenerationResponse>('/strategies', { params });
  return response.data;
}

// WebSocket message types (for type-safe handling in useMissionSocket)

export interface WSMessage<T = unknown> {
  event: string;
  timestamp: string;
  payload: T;
}

export type TelemetryUpdatedPayload = TelemetrySample;

export interface MissionStatusPayload {
  mission_id: string;
  status: string;
}

export interface AnomalyInjectedPayload {
  mission_id: string;
  status: string;
}

export interface PlansGeneratedPayload {
  mission_id: string;
  status: string;
  plan_count: number;
}

export interface PlanApprovedPayload {
  mission_id: string;
  status: string;
  approved_plan_id: string;
  approved_plan_label: string;
}

export interface MissionResetPayload {
  mission_id: string;
  status: string;
}