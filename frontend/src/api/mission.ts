/** Typed API functions for mission operations */

import { apiClient } from './client';
import type {
  Mission,
  CandidatePlan,
  TelemetrySample,
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